from __future__ import annotations

import json
from pathlib import Path

import pytest

from commerce.memory import memory_repositories
from commerce.repositories import Repositories
from commerce.seed import seed_catalogue
from contracts.bill import BillExtraction

FIXTURES = Path(__file__).parent / "fixtures" / "bills"


@pytest.fixture
def sample_extraction() -> BillExtraction:
    data = json.loads((FIXTURES / "sample_bill.extraction.json").read_text(encoding="utf-8"))
    return BillExtraction.model_validate(data)


@pytest.fixture
def repos() -> Repositories:
    r = memory_repositories()
    seed_catalogue(r)
    return r
