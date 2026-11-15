"""Voice/text command intake: transcript -> proposed inventory actions -> approval gate.

Self-contained on purpose: imports ORM/helpers from ``sabbazaar_commerce`` and the
speech/parse helpers from ``sabbazaar_agents.voice`` but NOT ``apps.api.main``
(which pulls the LangGraph graphs). Mount with ``install(app)``.

Flow (ADR 0003 — policy gate between agents and connectors):

  Sarvam STT / typed text
    -> ``propose_inventory_commands`` (typed ``CommandExtraction``)
    -> deterministic product resolution in code (exact SKU, else title/handle ILIKE)
    -> ``ProposedAction`` rows (``awaiting_approval``)
    -> merchant approves/rejects via ``/v1/actions/{id}/approve`` / ``/reject``
    -> on approve: a ``ConnectorJob`` (fake or shopify-ops connector) runs
"""

from __future__ import annotations

import hashlib
import json
import os
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, FastAPI, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from sabbazaar_agents.voice import (
    SpeechError,
    SpeechUnavailable,
    propose_inventory_commands,
    speech_enabled,
    transcribe_audio,
)
from sabbazaar_commerce import (
    ConnectorJob,
    Product,
    ProductVariant,
    ProposedAction,
    SessionLocal,
    audit,
)
from sabbazaar_contracts.channels import ErrorCode
from sabbazaar_contracts.commands import (
    ActionOut,
    CommandOp,
    CommandResponse,
    InventoryCommand,
)

MAX_AUDIO_BYTES = 10 * 1024 * 1024  # 10 MB
RESOLVED_STATUSES = ("executed", "rejected", "cancelled")

router = APIRouter(tags=["voice-commands"])


def get_db():
    with SessionLocal() as db:
        yield db


def int_id(value: str | int, field: str = "id") -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise HTTPException(422, f"Invalid {field}: expected an integer ID") from None
    if parsed < 1:
        raise HTTPException(422, f"Invalid {field}: expected a positive integer ID")
    return parsed


_connector = None


def get_connector():
    """Lazily build the shared connector. Tests rely on this being a singleton."""
    global _connector
    if _connector is None:
        if os.getenv("SHOPIFY_CONNECTOR", "shopify").lower() == "fake":
            from sabbazaar_connectors.fake import FakeConnector

            _connector = FakeConnector("shopify")
        else:
            from sabbazaar_connectors.shopify_ops.connector import ShopifyConnector
            from sabbazaar_connectors.shopify_ops.credentials import EnvCredentialsProvider

            _connector = ShopifyConnector(EnvCredentialsProvider())
    return _connector


# ─── Helpers ─────────────────────────────────────────────────────────────────


def action_out(db: Session, action: ProposedAction) -> ActionOut:
    product = db.get(Product, action.product_id)
    payload = json.loads(action.payload_json) if action.payload_json else {}
    if not isinstance(payload, dict):
        payload = {}
    return ActionOut(
        id=action.id,
        store_id=product.store_id if product else 0,
        type=action.action_type,
        status=action.status,
        payload=payload,
        rationale=payload.get("rationale"),
        idempotency_key=action.idempotency_key,
        created_at=action.created_at,
        resolved_at=action.updated_at if action.status in RESOLVED_STATUSES else None,
    )


def _escape_ilike(query: str) -> str:
    return query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _resolve_variants(db: Session, query: str) -> list[tuple[Product, ProductVariant]]:
    """Deterministic product resolution. Never delegates matching to the model."""
    q = query.strip()
    if not q:
        return []
    exact = db.scalar(
        select(ProductVariant).where(func.lower(ProductVariant.sku) == q.lower())
    )
    if exact:
        product = db.get(Product, exact.product_id)
        return [(product, exact)] if product else []
    pattern = f"%{_escape_ilike(q)}%"
    products = db.scalars(
        select(Product)
        .where(
            or_(
                Product.title.ilike(pattern, escape="\\"),
                Product.handle.ilike(pattern, escape="\\"),
            )
        )
        .limit(5)
    ).all()
    matches: list[tuple[Product, ProductVariant]] = []
    for product in products:
        variant = db.scalar(
            select(ProductVariant)
            .where(ProductVariant.product_id == product.id)
            .order_by(ProductVariant.id)
        )
        if variant:
            matches.append((product, variant))
    return matches


def _command_value(cmd: InventoryCommand) -> float | int | None:
    if cmd.op == CommandOp.SET_PRICE:
        return cmd.price_inr
    if cmd.op == CommandOp.SET_STOCK:
        return cmd.quantity
    return cmd.delta


def _idempotency_key(cmd: InventoryCommand, variant_id: int, normalized_transcript: str) -> str:
    digest = hashlib.sha1(  # noqa: S324 - idempotency keys, not security
        f"{cmd.op.value}:{variant_id}:{_command_value(cmd)}:{normalized_transcript}".encode()
    ).hexdigest()
    return f"cmd:{digest[:16]}"


def _build_payload(cmd: InventoryCommand, product: Product, variant: ProductVariant) -> dict[str, Any]:
    base = {
        "intent": cmd.op.value,
        "product_id": product.id,
        "variant_id": variant.id,
        "sku": variant.sku,
        "title": product.title,
        "rationale": cmd.rationale,
    }
    if cmd.op == CommandOp.SET_PRICE:
        base["operation"] = "update_product"
        base["price_inr_old"] = float(variant.price_inr)
        base["price_inr_new"] = float(cmd.price_inr) if cmd.price_inr is not None else None
    elif cmd.op == CommandOp.SET_STOCK:
        base["operation"] = "set_inventory"
        base["quantity"] = cmd.quantity
    else:  # adjust_stock
        base["operation"] = "set_inventory"
        base["delta"] = cmd.delta
    return base


def _propose_for_command(
    db: Session, cmd: InventoryCommand, normalized_transcript: str
) -> tuple[ProposedAction | None, str | None]:
    """Create (or reuse) one ProposedAction for a resolved command.

    Returns (action, note). `note` is an unparsed/ambiguity message when resolution
    fails, else None.
    """
    # Incomplete model output is unparseable, never guessed (AGENTS.md rule 5).
    if cmd.op == CommandOp.SET_PRICE and cmd.price_inr is None:
        return None, f"missing price for '{cmd.product_query}' — specify a price, e.g. 450"
    if cmd.op == CommandOp.SET_STOCK and cmd.quantity is None:
        return None, f"missing stock level for '{cmd.product_query}' — specify a quantity, e.g. 40"
    if cmd.op == CommandOp.ADJUST_STOCK and cmd.delta is None:
        return None, f"missing stock delta for '{cmd.product_query}' — e.g. 'add 5' or 'remove 3'"

    matches = _resolve_variants(db, cmd.product_query)
    if len(matches) == 0:
        return None, f"no product matches '{cmd.product_query}'"
    if len(matches) > 1:
        titles = ", ".join(p.title for p, _ in matches[:3])
        return None, f"'{cmd.product_query}' matches: {titles} — please be specific"
    product, variant = matches[0]
    op_map = {
        CommandOp.SET_PRICE: "shopify.update_product",
        CommandOp.SET_STOCK: "shopify.set_inventory",
        CommandOp.ADJUST_STOCK: "shopify.set_inventory",
    }
    key = _idempotency_key(cmd, variant.id, normalized_transcript)
    existing = db.scalar(select(ProposedAction).where(ProposedAction.idempotency_key == key))
    if existing:
        return existing, None
    action = ProposedAction(
        product_id=product.id,
        action_type=op_map[cmd.op],
        status="awaiting_approval",
        payload_json=json.dumps(_build_payload(cmd, product, variant)),
        idempotency_key=key,
    )
    db.add(action)
    db.flush()
    audit(
        db,
        "action.proposed.v1",
        f"Proposed {cmd.op.value} for {product.title}",
        "product",
        str(product.id),
        {"sku": variant.sku, "op": cmd.op.value, "query": cmd.product_query},
    )
    return action, None


# ─── Routes ──────────────────────────────────────────────────────────────────


@router.post("/v1/commands", response_model=CommandResponse)
async def create_command(
    file: UploadFile | None = File(None),
    text: str | None = Form(None),
    db: Session = Depends(get_db),
):
    if (file is None) == (text is None):
        raise HTTPException(400, "Send exactly one of `file` (audio) or `text`")

    language_code: str | None = None
    if file is not None:
        if not speech_enabled():
            raise HTTPException(503, "voice input is disabled (SPEECH_ENABLED=false)")
        content = await file.read()
        if len(content) > MAX_AUDIO_BYTES:
            raise HTTPException(413, "Audio file too large (max 10 MB)")
        try:
            transcript, language_code = transcribe_audio(
                content,
                file.filename or "command.webm",
                file.content_type,
            )
        except SpeechUnavailable as exc:
            raise HTTPException(503, str(exc)) from exc
        except SpeechError as exc:
            raise HTTPException(502, str(exc)[:200]) from exc
    else:
        transcript = (text or "").strip()

    if not transcript.strip():
        return CommandResponse(
            transcript=transcript,
            language_code=language_code,
            actions=[],
            unparsed=[],
            message="I didn't catch that — try again.",
        )

    try:
        extraction = propose_inventory_commands(transcript)
    except SpeechUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc
    except SpeechError as exc:
        raise HTTPException(502, f"Could not parse the instruction ({str(exc)[:200]})") from exc

    normalized_transcript = transcript.strip().lower()
    unparsed = list(extraction.unparsed)
    actions: list[ActionOut] = []
    ambiguity_notes: list[str] = []
    for command in extraction.commands:
        action, note = _propose_for_command(db, command, normalized_transcript)
        if note:
            unparsed.append(note)
            if " matches: " in note:
                ambiguity_notes.append(note)
        elif action is not None:
            actions.append(action_out(db, action))
    db.commit()

    if actions:
        n = len(actions)
        message = f"Proposed {n} change{'s' if n > 1 else ''} — approve or reject it below."
    elif ambiguity_notes:
        message = f"Which product did you mean? {'; '.join(ambiguity_notes)}"
    else:
        message = "I didn't understand that — try: 'stock of <product> to 40' or 'price of <product> to 450'."

    return CommandResponse(
        transcript=transcript,
        language_code=language_code,
        actions=actions,
        unparsed=unparsed,
        message=message,
    )


@router.get("/v1/actions", response_model=list[ActionOut])
def list_actions(
    status: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    stmt = (
        select(ProposedAction, Product.store_id)
        .join(Product, ProposedAction.product_id == Product.id)
        .order_by(ProposedAction.created_at.desc(), ProposedAction.id.desc())
    )
    if status:
        stmt = stmt.where(ProposedAction.status == status)
    rows = db.execute(stmt).all()
    return [action_out(db, action) for action, _store_id in rows]


def _latest_job(db: Session, action_id: int) -> ConnectorJob | None:
    return db.scalar(
        select(ConnectorJob)
        .where(ConnectorJob.action_id == action_id)
        .order_by(ConnectorJob.id.desc())
    )


def _remember_job(db: Session, action: ProposedAction, operation: str, request_summary: dict) -> ConnectorJob:
    job = _latest_job(db, action.id)
    if job is not None:
        job.status = "running"
        job.operation = operation
        job.connector = "shopify"
        job.request_summary_json = json.dumps(request_summary)
        job.error_code = None
        job.error_message = None
        job.response_summary_json = None
        return job
    job = ConnectorJob(
        action_id=action.id,
        connector="shopify",
        operation=operation,
        status="running",
        idempotency_key=action.idempotency_key,
        request_summary_json=json.dumps(request_summary),
    )
    db.add(job)
    db.flush()
    return job


@router.post("/v1/actions/{action_id}/approve", response_model=ActionOut)
def approve_action(action_id: str, db: Session = Depends(get_db)):
    action_id_int = int_id(action_id, "action_id")
    action = db.get(ProposedAction, action_id_int)
    if not action:
        raise HTTPException(404, "Action not found")
    if action.status in ("rejected", "cancelled"):
        raise HTTPException(409, f"Action is {action.status} and cannot be approved")

    latest = _latest_job(db, action.id)
    if latest is not None and latest.status == "succeeded":
        # Idempotent re-approve: the job already ran; return the current state.
        return action_out(db, action)

    product = db.get(Product, action.product_id)
    payload = json.loads(action.payload_json) if action.payload_json else {}
    sku = str(payload.get("sku") or "")
    operation = str(payload.get("operation") or "")

    action.status = "approved"
    audit(
        db,
        "action.approved.v1",
        f"Approved {payload.get('intent', operation)} for {product.title if product else sku}",
        "product",
        str(action.product_id),
        {"sku": sku, "op": payload.get("intent"), "operation": operation},
    )

    connector = get_connector()
    variant = db.get(ProductVariant, payload.get("variant_id")) if payload.get("variant_id") else None

    if operation == "update_product":
        # NOTE: store.price_change_threshold_percent is stored but deliberately NOT
        # enforced here. This endpoint IS the merchant-approval gate; inventing
        # threshold semantics would change product behaviour silently.
        new_price = Decimal(str(payload.get("price_inr_new")))
        request_summary = {"operation": operation, "sku": sku, "price_inr": str(new_price)}
        job = _remember_job(db, action, operation, request_summary)
        if variant:
            variant.price_inr = new_price
        if product:
            product.price_inr = new_price
            product.version += 1
        # Durable job + audit are committed before any external channel I/O.
        db.commit()
        ref = connector.find_by_sku(sku) if sku else None
        if ref is None:
            # Price is catalogue data; applying it locally is honest without a channel push.
            job.status = "succeeded"
            job.response_summary_json = json.dumps(
                {"ok": True, "message": "Applied to local catalogue only; product not on Shopify yet."}
            )
            action.status = "executed"
            audit(
                db,
                "connector.job.succeeded.v1",
                f"Price change for {sku} applied to local catalogue only (not on Shopify yet)",
                "product",
                str(action.product_id),
                {"sku": sku, "local_only": True},
            )
        else:
            result = connector.update_product(ref, new_price, action.idempotency_key)
            admin_url = result.ref.admin_url if result.ref else ref.admin_url
            job.response_summary_json = json.dumps(
                {"ok": result.ok, "message": result.message, "admin_url": admin_url}
            )
            if result.ok:
                job.status = "succeeded"
                job.admin_url = admin_url
                action.status = "executed"
                if admin_url and product:
                    product.admin_url = product.admin_url or admin_url
                audit(
                    db,
                    "connector.job.succeeded.v1",
                    f"Shopify price update succeeded for {sku}",
                    "product",
                    str(action.product_id),
                    {"sku": sku, "admin_url": admin_url},
                )
            else:
                job.status = "failed"
                job.error_code = result.error_code.value if result.error_code else "unknown"
                job.error_message = result.message
                audit(
                    db,
                    "connector.job.failed.v1",
                    f"Shopify price update failed for {sku}",
                    "product",
                    str(action.product_id),
                    {"sku": sku, "error_code": job.error_code},
                )
    elif operation == "set_inventory":
        ref = connector.find_by_sku(sku) if sku else None
        if ref is None:
            job = _remember_job(
                db,
                action,
                operation,
                {"operation": operation, "sku": sku, "quantity": payload.get("quantity"), "delta": payload.get("delta")},
            )
            job.status = "failed"
            job.error_code = ErrorCode.NOT_CONFIGURED.value
            job.error_message = "product not on Shopify yet — publish it first"
            job.response_summary_json = json.dumps({"ok": False, "message": job.error_message})
            # Action stays "approved": the merchant can publish first, then retry.
            audit(
                db,
                "connector.job.failed.v1",
                f"Inventory sync for {sku} blocked: product not on Shopify",
                "product",
                str(action.product_id),
                {"sku": sku, "error_code": job.error_code},
            )
        else:
            intent = payload.get("intent")
            if intent == "set_stock":
                absolute = int(payload["quantity"])
            else:  # adjust_stock
                if ref.quantity is None:
                    job = _remember_job(
                        db,
                        action,
                        operation,
                        {"operation": operation, "sku": sku, "delta": payload.get("delta")},
                    )
                    job.status = "failed"
                    job.error_code = ErrorCode.VALIDATION_FAILED.value
                    job.error_message = (
                        "Channel does not report current stock; set an absolute stock level instead"
                    )
                    job.response_summary_json = json.dumps({"ok": False, "message": job.error_message})
                    audit(
                        db,
                        "connector.job.failed.v1",
                        f"Inventory sync for {sku} blocked: channel stock unknown",
                        "product",
                        str(action.product_id),
                        {"sku": sku, "error_code": job.error_code},
                    )
                    db.commit()
                    db.refresh(action)
                    return action_out(db, action)
                absolute = max(0, ref.quantity + int(payload["delta"]))
            request_summary = {
                "operation": operation,
                "sku": sku,
                "quantity": absolute,
                "expected_current": ref.quantity,
            }
            job = _remember_job(db, action, operation, request_summary)
            db.commit()  # durable job before external channel mutation
            result = connector.set_inventory(
                ref, absolute, expected_current=ref.quantity, idempotency_key=action.idempotency_key
            )
            job.response_summary_json = json.dumps(
                {"ok": result.ok, "quantity": result.quantity, "message": result.message}
            )
            if result.ok:
                job.status = "succeeded"
                job.admin_url = result.ref.admin_url if result.ref else ref.admin_url
                action.status = "executed"
                audit(
                    db,
                    "connector.job.succeeded.v1",
                    f"Shopify inventory set to {absolute} for {sku}",
                    "product",
                    str(action.product_id),
                    {"sku": sku, "quantity": absolute},
                )
            else:
                job.status = "failed"
                job.error_code = result.error_code.value if result.error_code else "unknown"
                # On CONFLICT the message shows channel stock; we do not blindly retry.
                job.error_message = result.message
                audit(
                    db,
                    "connector.job.failed.v1",
                    f"Shopify inventory sync failed for {sku}",
                    "product",
                    str(action.product_id),
                    {"sku": sku, "error_code": job.error_code},
                )
    else:
        # Unknown operation: do not guess — leave a failed job with a clear message.
        job = _remember_job(db, action, operation or "unknown", {"operation": operation, "sku": sku})
        job.status = "failed"
        job.error_code = ErrorCode.VALIDATION_FAILED.value
        job.error_message = f"Unsupported operation in action payload: {operation!r}"
        job.response_summary_json = json.dumps({"ok": False, "message": job.error_message})

    db.commit()
    db.refresh(action)
    return action_out(db, action)


@router.post("/v1/actions/{action_id}/reject", response_model=ActionOut)
def reject_action(action_id: str, db: Session = Depends(get_db)):
    action = db.get(ProposedAction, int_id(action_id, "action_id"))
    if not action:
        raise HTTPException(404, "Action not found")
    if action.status not in ("proposed", "awaiting_approval"):
        raise HTTPException(409, f"Action is {action.status} and cannot be rejected")
    action.status = "rejected"
    payload = json.loads(action.payload_json) if action.payload_json else {}
    audit(
        db,
        "action.rejected.v1",
        f"Rejected {payload.get('intent', action.action_type)} for sku {payload.get('sku', '')}",
        "product",
        str(action.product_id),
        {"sku": payload.get("sku"), "op": payload.get("intent")},
    )
    db.commit()
    db.refresh(action)
    return action_out(db, action)


def install(app: FastAPI) -> None:
    """Mount voice-command routes on an existing app."""
    app.include_router(router)
