"""Render the synthetic sample bill (tests/fixtures/bills/sample_bill.extraction.json) to PNG + PDF.

Synthetic test data only. Run: uv run python scripts/make_sample_bill.py
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "tests" / "fixtures" / "bills"


def font(size: int) -> ImageFont.ImageFont:
    for name in ("arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def main() -> None:
    data = json.loads((FIX / "sample_bill.extraction.json").read_text("utf-8"))
    img = Image.new("RGB", (1400, 900), "white")
    d = ImageDraw.Draw(img)
    big, mid, small = font(34), font(22), font(18)
    d.text((40, 30), "TAX INVOICE", font=big, fill="black")
    d.text((40, 80), data["supplier_name"], font=mid, fill="black")
    d.text(
        (40, 112),
        "12, Daryaganj, New Delhi 110002  |  GSTIN: 07AAAAA0000A1Z5 (sample)",
        font=small,
        fill="black",
    )
    d.text((1000, 80), f"Invoice: {data['invoice_number']}", font=mid, fill="black")
    d.text((1000, 112), f"Date: {data['invoice_date']}", font=mid, fill="black")
    d.text((40, 150), "Bill to: Sample Book Corner, Pune", font=small, fill="black")

    cols = [
        (40, "#"),
        (80, "Title / Author"),
        (520, "ISBN"),
        (720, "Publisher"),
        (960, "Qty"),
        (1030, "MRP"),
        (1130, "Disc%"),
        (1210, "Rate"),
        (1300, "Amount"),
    ]
    y = 200
    d.line((40, y - 8, 1370, y - 8), fill="black", width=2)
    for x, label in cols:
        d.text((x, y), label, font=small, fill="black")
    y += 34
    d.line((40, y - 6, 1370, y - 6), fill="black", width=1)
    total = Decimal(0)
    for ln in data["lines"]:
        mrp, rate = Decimal(ln["mrp"]), Decimal(ln["unit_cost"])
        disc = ((mrp - rate) / mrp * 100).quantize(Decimal("1"))
        amount = rate * ln["quantity"]
        total += amount
        title = ln["title"] + (f" - {ln['author']}" if ln.get("author") else "")
        row = [
            str(ln["line_no"]),
            title[:38],
            ln.get("isbn") or "",
            ln.get("publisher") or "",
            str(ln["quantity"]),
            f"{mrp}",
            f"{disc}",
            f"{rate}",
            f"{amount}",
        ]
        for (x, _), text in zip(cols, row, strict=True):
            d.text((x, y), text, font=small, fill="black")
        y += 40
    d.line((40, y, 1370, y), fill="black", width=1)
    gst = Decimal(0)  # printed books are GST-exempt in India
    d.text((1000, y + 20), f"Taxable value: {total}", font=small, fill="black")
    d.text((1000, y + 48), f"GST (exempt, 0%): {gst}", font=small, fill="black")
    d.text((1000, y + 76), f"Total payable: INR {total + gst}", font=mid, fill="black")
    d.text((40, 860), "SAMPLE - synthetic test data, not a real invoice", font=small, fill="gray")

    img.save(FIX / "sample_bill.png", optimize=False)
    img.save(FIX / "sample_bill.pdf", "PDF", resolution=150)
    print("wrote", FIX / "sample_bill.png", "and", FIX / "sample_bill.pdf")


if __name__ == "__main__":
    main()
