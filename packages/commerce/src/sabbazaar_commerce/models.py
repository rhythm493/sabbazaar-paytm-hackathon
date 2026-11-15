from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)


class Store(Base, TimestampMixin):
    __tablename__ = "stores"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)
    price_change_threshold_percent: Mapped[float] = mapped_column(default=10.0, nullable=False)
    shopify_shop_domain: Mapped[str | None] = mapped_column(String(255))
    shopify_location_id: Mapped[str | None] = mapped_column(String(255))


class Product(Base, TimestampMixin):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description_html: Mapped[str] = mapped_column(Text, default="", nullable=False)
    vendor: Mapped[str] = mapped_column(String(160), default="SabBazaar", nullable=False)
    product_type: Mapped[str] = mapped_column(String(160), default="General", nullable=False)
    tags_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    handle: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False)
    price_inr: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    confidence: Mapped[float] = mapped_column(default=1.0, nullable=False)
    missing_fields_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    evidence_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    version: Mapped[int] = mapped_column(default=1, nullable=False)
    external_product_id: Mapped[str | None] = mapped_column(String(255))
    admin_url: Mapped[str | None] = mapped_column(Text)

    variants: Mapped[list["ProductVariant"]] = relationship(back_populates="product", cascade="all, delete-orphan")


class ProductVariant(Base, TimestampMixin):
    __tablename__ = "product_variants"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    external_variant_id: Mapped[str | None] = mapped_column(String(255))
    sku: Mapped[str] = mapped_column(String(80), nullable=False)
    title: Mapped[str] = mapped_column(String(255), default="Default Title", nullable=False)
    price_inr: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    compare_at_price_inr: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    option_values_json: Mapped[str] = mapped_column(Text, default='["Default Title"]', nullable=False)
    inventory_item_id: Mapped[str | None] = mapped_column(String(255))
    stock_on_hand: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

    product: Mapped[Product] = relationship(back_populates="variants")


class ProposedAction(Base, TimestampMixin):
    __tablename__ = "proposed_actions"
    __table_args__ = (UniqueConstraint("idempotency_key", name="uq_proposed_action_idempotency"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    action_type: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="proposed", nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)


class ConnectorJob(Base, TimestampMixin):
    __tablename__ = "connector_jobs"
    __table_args__ = (UniqueConstraint("idempotency_key", name="uq_connector_job_idempotency"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    action_id: Mapped[int] = mapped_column(ForeignKey("proposed_actions.id"), nullable=False)
    connector: Mapped[str] = mapped_column(String(40), nullable=False)
    operation: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="queued", nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    request_summary_json: Mapped[str] = mapped_column(Text, nullable=False)
    response_summary_json: Mapped[str | None] = mapped_column(Text)
    external_product_id: Mapped[str | None] = mapped_column(String(255))
    admin_url: Mapped[str | None] = mapped_column(Text)
    error_code: Mapped[str | None] = mapped_column(String(80))
    error_message: Mapped[str | None] = mapped_column(Text)


class Listing(Base, TimestampMixin):
    __tablename__ = "listings"
    __table_args__ = (UniqueConstraint("product_id", "channel", name="uq_listing_product_channel"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    channel: Mapped[str] = mapped_column(String(40), nullable=False)
    external_product_id: Mapped[str] = mapped_column(String(255), nullable=False)
    external_variant_id: Mapped[str | None] = mapped_column(String(255))
    admin_url: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False)


class InventoryLedger(Base):
    """Append-only stock ledger. `source_key` is unique so applying the same bill twice is a no-op."""

    __tablename__ = "inventory_ledger"
    __table_args__ = (UniqueConstraint("source_key", name="uq_inventory_ledger_source_key"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    variant_id: Mapped[int] = mapped_column(
        ForeignKey("product_variants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    delta: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    source_key: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    actor: Mapped[str] = mapped_column(String(80), default="merchant", nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(80))
    entity_id: Mapped[str | None] = mapped_column(String(255))
    message: Mapped[str] = mapped_column(Text, nullable=False)
    details_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
