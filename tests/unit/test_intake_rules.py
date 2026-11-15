from __future__ import annotations

from decimal import Decimal

import pytest

from commerce.domain import Listing
from commerce.intake.matching import classify
from commerce.intake.normalize import normalize_extraction
from commerce.intake.preview import build_preview
from commerce.intake.questions import AnswerError, apply_answers, open_questions
from commerce.isbn import normalize_isbn
from contracts.bill import BillExtraction, ExtractedLine
from contracts.channels import ExternalRef
from contracts.ingestion import Answer, LineKind

CHANNELS = ["shopify"]


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("978-1-84794-183-1", "9781847941831"),
        ("9780099590089", None),  # bad check digit
        ("0306406152", "9780306406157"),  # ISBN-10 -> 13
        ("030640615X", None),
        ("", None),
        (None, None),
        ("abc", None),
    ],
)
def test_normalize_isbn(raw, expected):
    assert normalize_isbn(raw) == expected


def _classified(sample_extraction, repos):
    return classify(normalize_extraction(sample_extraction), repos.catalogue)


def test_normalize_merges_duplicate_isbn_and_flags_invalid(sample_extraction):
    lines = normalize_extraction(sample_extraction)
    assert [ln.id for ln in lines] == ["L1", "L2", "L3", "L4", "L6"]
    l1 = lines[0]
    assert l1.line_nos == [1, 5]
    assert l1.get("quantity") == 8
    assert l1.get("mrp") == Decimal("799.00")
    sapiens = lines[-1]
    assert sapiens.get("isbn") is None
    assert "not valid" in sapiens.notes[0]


def test_classification(sample_extraction, repos):
    kinds = {ln.id: ln.kind for ln in _classified(sample_extraction, repos)}
    assert kinds == {
        "L1": LineKind.RESTOCK,
        "L2": LineKind.RESTOCK,
        "L3": LineKind.NEW,
        "L4": LineKind.UNCERTAIN_MATCH,
        "L6": LineKind.NEW,
    }


def test_unreadable_line():
    ext = BillExtraction(lines=[ExtractedLine(line_no=1, title=None, quantity=2)])
    from commerce.memory import memory_repositories

    r = memory_repositories()
    lines = classify(normalize_extraction(ext), r.catalogue)
    assert lines[0].kind == LineKind.UNREADABLE
    qs = open_questions(lines, r.catalogue, CHANNELS)
    assert [q.id for q in qs] == ["L1:missing_field:title"]
    assert qs[0].allow_drop
    dropped = apply_answers(lines, qs, [Answer(question_id=qs[0].id, drop_line=True)], r.catalogue)
    assert dropped[0].dropped
    assert open_questions(dropped, r.catalogue, CHANNELS) == []


def test_questions_for_sample(sample_extraction, repos):
    qs = open_questions(_classified(sample_extraction, repos), repos.catalogue, CHANNELS)
    assert {q.id: q.suggestion for q in qs} == {
        "L2:price:selling_price": "399.00",  # MRP changed 350 -> 399
        "L3:price:selling_price": "499.00",
        "L4:confirm_match": "yes",
        "L6:price:selling_price": "599.00",
    }
    # L1 is a restock with unchanged MRP: no price question.
    assert not any(q.line_id == "L1" for q in qs)


def _answered(sample_extraction, repos):
    lines = _classified(sample_extraction, repos)
    qs = open_questions(lines, repos.catalogue, CHANNELS)
    answers = [
        Answer(question_id="L2:price:selling_price", value="399"),
        Answer(question_id="L3:price:selling_price", value="450"),
        Answer(question_id="L4:confirm_match", value="Yes"),
        Answer(question_id="L6:price:selling_price", value="549.50"),
    ]
    return apply_answers(lines, qs, answers, repos.catalogue)


def test_answers_resolve_everything(sample_extraction, repos):
    lines = _answered(sample_extraction, repos)
    assert open_questions(lines, repos.catalogue, CHANNELS) == []
    l4 = next(ln for ln in lines if ln.id == "L4")
    assert l4.kind == LineKind.RESTOCK and l4.matched_book_id == "9788173711466"
    assert lines[1].fields["selling_price"].source == "owner"


@pytest.mark.parametrize("value", ["abc", "0", "-5", "", None, "99999999"])
def test_invalid_price_answers_rejected(sample_extraction, repos, value):
    lines = _classified(sample_extraction, repos)
    qs = open_questions(lines, repos.catalogue, CHANNELS)
    with pytest.raises(AnswerError) as err:
        apply_answers(
            lines, qs, [Answer(question_id="L3:price:selling_price", value=value)], repos.catalogue
        )
    assert "L3:price:selling_price" in err.value.errors


def test_unknown_question_and_bad_drop_rejected(sample_extraction, repos):
    lines = _classified(sample_extraction, repos)
    qs = open_questions(lines, repos.catalogue, CHANNELS)
    with pytest.raises(AnswerError) as err:
        apply_answers(
            lines,
            qs,
            [
                Answer(question_id="nope", value="1"),
                Answer(question_id="L3:price:selling_price", drop_line=True),
            ],
            repos.catalogue,
        )
    assert set(err.value.errors) == {"nope", "L3:price:selling_price"}


def test_confirm_match_no_makes_it_new(sample_extraction, repos):
    lines = _classified(sample_extraction, repos)
    qs = open_questions(lines, repos.catalogue, CHANNELS)
    out = apply_answers(
        lines, qs, [Answer(question_id="L4:confirm_match", value="no")], repos.catalogue
    )
    l4 = next(ln for ln in out if ln.id == "L4")
    assert l4.kind == LineKind.NEW
    q_ids = {q.id for q in open_questions(out, repos.catalogue, CHANNELS)}
    assert "L4:price:selling_price" in q_ids


def test_preview(sample_extraction, repos):
    # Atomic Habits is already listed on Shopify with 12 units.
    repos.listings.upsert(
        Listing(
            book_id="9781847941831",
            channel="shopify",
            ref=ExternalRef(product_id="p1", variant_id="v1", inventory_item_id="i1"),
            last_known_quantity=12,
        )
    )
    lines = _answered(sample_extraction, repos)
    p = build_preview(
        ingestion_id="abcdef1234",
        lines=lines,
        catalogue=repos.catalogue,
        inventory=repos.inventory,
        listings=repos.listings,
        channels=CHANNELS,
        version=1,
    )
    by = {pl.line_id: pl for pl in p.lines}
    assert (by["L1"].stock_before, by["L1"].stock_after) == (12, 20)
    assert by["L1"].price_after == Decimal("699.00") and by["L1"].price_change_pct is None
    assert [c.operation for c in by["L1"].channel_changes] == ["set_inventory"]
    assert by["L1"].channel_changes[0].expected_current == 12
    assert by["L2"].price_change_pct == 17.35
    assert [c.operation for c in by["L2"].channel_changes] == ["publish_product"]  # not listed yet
    assert (by["L4"].stock_before, by["L4"].stock_after) == (2, 12)
    assert by["L3"].kind == LineKind.NEW and by["L3"].sku == "9781786330895"
    assert by["L6"].sku == "SB-abcdef12-L6"
    assert by["L6"].price_after == Decimal("549.50")
    assert "Shopify: isbn is missing (recommended)" in by["L6"].warnings
    payload = by["L3"].channel_changes[0].payload
    assert payload.status == "draft" and payload.quantity == 6 and payload.price == Decimal("450")
    # Hash is stable for identical input and changes with content.
    p2 = build_preview(
        ingestion_id="abcdef1234",
        lines=lines,
        catalogue=repos.catalogue,
        inventory=repos.inventory,
        listings=repos.listings,
        channels=CHANNELS,
        version=2,
    )
    assert p2.hash == p.hash
