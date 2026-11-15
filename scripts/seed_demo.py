from decimal import Decimal

from sabbazaar_commerce import SessionLocal, create_product
from sabbazaar_contracts import ProductDraftIn


def main() -> None:
    with SessionLocal() as db:
        product = create_product(
            db,
            ProductDraftIn(
                title="Kanjivaram Silk Saree",
                description="<p>Handwoven Kanjivaram silk saree with a rich zari border.</p>",
                vendor="Meena's Sarees",
                product_type="Sarees",
                tags=["saree", "kanjivaram", "silk"],
                price_inr=Decimal("8999.00"),
                sku="SBZ-SARI-0001",
                evidence={"source": "demo fixture", "fields": ["image", "catalog"]},
                confidence=0.95,
                missing_fields=[],
            ),
        )
        db.commit()
        print(f"Seeded product #{product.id}: {product.title}")


if __name__ == "__main__":
    main()
