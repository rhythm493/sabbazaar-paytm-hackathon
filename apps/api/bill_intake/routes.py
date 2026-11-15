"""Bill-intake HTTP routes, mounted on the main API app via `install(app)`."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, Depends, FastAPI, File, Header, Request, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from apps.api.bill_intake.container import Container, build_container
from apps.api.bill_intake.service import sniff_media_type
from sabbazaar_commerce.domain import Listing
from sabbazaar_commerce.intake.apply import ApplyError
from sabbazaar_commerce.intake.questions import AnswerError
from sabbazaar_commerce.seed import seed_catalogue
from sabbazaar_contracts.ingestion import Answer, IngestionView


class AnswersBody(BaseModel):
    answers: list[Answer] = Field(min_length=1)


class ConfirmBody(BaseModel):
    preview_version: int


class EditBody(BaseModel):
    line_id: str
    fields: dict[str, str | None] = Field(default_factory=dict)
    drop: bool = False


def _container(request: Request) -> Container:
    container = getattr(request.app.state, "bill_intake", None)
    if container is None:  # built lazily so importing the app has no side effects
        container = request.app.state.bill_intake = build_container()
    return container


C = Annotated[Container, Depends(_container)]


def _error(status: int, code: str, message: str, fields: dict | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"error": {"code": code, "message": message, "fields": fields or {}}},
    )


router = APIRouter(tags=["bill-intake"])


def install(app: FastAPI, container: Container | None = None) -> None:
    """Mount bill-intake routes and error handlers on an existing app."""
    if container is not None:
        app.state.bill_intake = container
    app.include_router(router)

    @app.exception_handler(ApplyError)
    async def _apply_error(_: Request, exc: ApplyError) -> JSONResponse:
        return _error(exc.status, exc.code, exc.message)

    @app.exception_handler(AnswerError)
    async def _answer_error(_: Request, exc: AnswerError) -> JSONResponse:
        return _error(422, "invalid_answers", "Some answers need fixing", exc.errors)


@router.post("/v1/ingestions", status_code=202, response_model=IngestionView)
async def upload(
    container: C,
    background: BackgroundTasks,
    file: UploadFile = File(...),
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> Any:
    limit = container.settings.max_upload_bytes
    content = await file.read(limit + 1)
    if not content:
        return _error(422, "empty_file", "The uploaded file is empty")
    if len(content) > limit:
        return _error(413, "file_too_large", f"Bills must be at most {limit // 1_048_576} MB")
    media_type = sniff_media_type(content)
    if media_type is None:
        return _error(415, "unsupported_file", "Upload a PNG, JPEG, WebP image or a PDF bill")
    ing, created = container.service.create(
        content, file.filename or "bill", media_type, idempotency_key
    )
    if created:
        background.add_task(container.service.run, ing.id)
        return container.service.view(ing.id)
    return JSONResponse(
        status_code=200, content=container.service.view(ing.id).model_dump(mode="json")
    )

@router.get("/v1/ingestions/{iid}", response_model=IngestionView)
def get_ingestion(iid: str, container: C) -> Any:
    return container.service.view(iid)

@router.post("/v1/ingestions/{iid}/answers", response_model=IngestionView)
def answer(iid: str, body: AnswersBody, container: C) -> Any:
    container.service.answer(iid, body.answers)
    return container.service.view(iid)

@router.post("/v1/ingestions/{iid}/preview/edit", response_model=IngestionView)
def edit_preview(iid: str, body: EditBody, container: C) -> Any:
    container.service.edit_preview(iid, body.line_id, body.fields, body.drop)
    return container.service.view(iid)

@router.post("/v1/ingestions/{iid}/confirm", response_model=IngestionView)
def confirm(iid: str, body: ConfirmBody, container: C) -> Any:
    container.service.confirm(iid, body.preview_version)
    return container.service.view(iid)

@router.post("/v1/ingestions/{iid}/retry", response_model=IngestionView)
def retry(iid: str, container: C) -> Any:
    container.service.apply.retry(iid)
    return container.service.view(iid)

@router.post("/v1/ingestions/{iid}/reject", response_model=IngestionView)
def reject(iid: str, container: C) -> Any:
    container.service.apply.reject(iid)
    return container.service.view(iid)

@router.get("/v1/ingestions/{iid}/audit")
def audit(iid: str, container: C) -> Any:
    return [e.model_dump(mode="json") for e in container.service.audit(iid)]

@router.get("/v1/channels")
def channels(container: C) -> Any:
    return [
        container.registry.get(ch).health_check().model_dump()
        for ch in container.registry.channels()
    ]

@router.get("/v1/books")
def books(container: C) -> Any:
    r = container.repos
    out = []
    for b in r.catalogue.list():
        listings = {}
        for ch in container.registry.channels():
            listing = r.listings.get(b.id, ch)
            if listing:
                listings[ch] = {
                    "admin_url": listing.ref.admin_url,
                    "last_known_quantity": listing.last_known_quantity,
                }
        out.append(
            {
                **b.model_dump(mode="json"),
                "on_hand": r.inventory.on_hand(b.id),
                "listings": listings,
            }
        )
    return out

@router.post("/v1/dev/seed")
def dev_seed(container: C) -> Any:
    if container.settings.app_env != "development":
        return _error(404, "not_found", "Not found")
    seeded = seed_catalogue(container.repos)
    linked = []
    for book, stock in seeded:
        for ch in container.registry.channels():
            conn = container.registry.get(ch)
            if container.repos.listings.get(book.id, ch):
                continue
            if conn.simulated and hasattr(conn, "add_existing"):
                ref = conn.find_by_sku(book.sku) or conn.add_existing(
                    book.sku, book.selling_price, stock
                )
            else:
                ref = conn.find_by_sku(book.sku)  # read-only; never creates
            if ref:
                container.repos.listings.upsert(
                    Listing(
                        book_id=book.id, channel=ch, ref=ref, last_known_quantity=ref.quantity
                    )
                )
                linked.append({"sku": book.sku, "channel": ch})
    return {
        "books": [b.sku for b, _ in seeded],
        "linked": linked,
        "simulated_channels": container.registry.simulated_channels(),
    }

