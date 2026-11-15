"""In-memory channel used by tests and `CHANNEL_MODE=fake`. Always reports itself as simulated."""

from __future__ import annotations

import threading
from decimal import Decimal

from sabbazaar_contracts.channels import (
    ConnectorHealth,
    ConnectorResult,
    ErrorCode,
    ExternalRef,
    ListingPayload,
)


class FakeConnector:
    simulated = True

    def __init__(self, channel: str = "shopify") -> None:
        self.channel = channel
        self.products: dict[str, dict] = {}  # sku -> {ref, price, quantity, payload}
        self.calls: list[tuple[str, str]] = []  # (operation, idempotency_key)
        self.fail_next: dict[str, ErrorCode] = {}
        self._results: dict[str, ConnectorResult] = {}
        self._lock = threading.Lock()
        self._n = 0

    def health_check(self) -> ConnectorHealth:
        return ConnectorHealth(
            channel=self.channel, ok=True, simulated=True, message="Simulated channel (test data)"
        )

    def find_by_sku(self, sku: str) -> ExternalRef | None:
        row = self.products.get(sku)
        if not row:
            return None
        return row["ref"].model_copy(update={"quantity": row["quantity"]})

    def _idempotent(self, op: str, key: str) -> ConnectorResult | None:
        self.calls.append((op, key))
        if key in self._results:
            return self._results[key]
        if op in self.fail_next:
            code = self.fail_next.pop(op)
            return ConnectorResult.fail(code, f"simulated {code.value}")
        return None

    def _remember(self, key: str, result: ConnectorResult) -> ConnectorResult:
        self._results[key] = result
        return result

    def add_existing(self, sku: str, price: Decimal, quantity: int) -> ExternalRef:
        """Test/dev helper: pretend a product already exists on the channel."""
        self._n += 1
        ref = ExternalRef(
            product_id=f"fake-p{self._n}",
            variant_id=f"fake-v{self._n}",
            inventory_item_id=f"fake-i{self._n}",
            admin_url=f"fake://{self.channel}/products/{self._n}",
        )
        self.products[sku] = {"ref": ref, "price": price, "quantity": quantity, "payload": None}
        return ref.model_copy(update={"quantity": quantity})

    def publish_product(self, payload: ListingPayload, idempotency_key: str) -> ConnectorResult:
        with self._lock:
            if r := self._idempotent("publish_product", idempotency_key):
                return r
            if payload.sku in self.products:  # reconcile instead of duplicating
                ref = self.find_by_sku(payload.sku)
                return self._remember(idempotency_key, ConnectorResult(ok=True, ref=ref))
            ref = self.add_existing(payload.sku, payload.price, payload.quantity)
            self.products[payload.sku]["payload"] = payload
            return self._remember(
                idempotency_key, ConnectorResult(ok=True, ref=ref, quantity=payload.quantity)
            )

    def _by_ref(self, ref: ExternalRef) -> dict | None:
        return next(
            (p for p in self.products.values() if p["ref"].variant_id == ref.variant_id), None
        )

    def update_product(
        self, ref: ExternalRef, price: Decimal, idempotency_key: str
    ) -> ConnectorResult:
        with self._lock:
            if r := self._idempotent("update_product", idempotency_key):
                return r
            row = self._by_ref(ref)
            if not row:
                return ConnectorResult.fail(ErrorCode.VALIDATION_FAILED, "product not found")
            row["price"] = price
            return self._remember(idempotency_key, ConnectorResult(ok=True, ref=row["ref"]))

    def set_inventory(
        self,
        ref: ExternalRef,
        quantity: int,
        expected_current: int | None,
        idempotency_key: str,
    ) -> ConnectorResult:
        with self._lock:
            if r := self._idempotent("set_inventory", idempotency_key):
                return r
            row = self._by_ref(ref)
            if not row:
                return ConnectorResult.fail(ErrorCode.VALIDATION_FAILED, "product not found")
            if expected_current is not None and row["quantity"] != expected_current:
                return ConnectorResult.fail(
                    ErrorCode.CONFLICT,
                    f"channel stock is {row['quantity']}, expected {expected_current}",
                )
            row["quantity"] = quantity
            return self._remember(
                idempotency_key, ConnectorResult(ok=True, ref=row["ref"], quantity=quantity)
            )
