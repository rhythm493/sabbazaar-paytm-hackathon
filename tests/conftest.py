from __future__ import annotations

import os
import tempfile
from pathlib import Path as _Path

# Must run before anything imports sabbazaar_commerce (its engine reads DATABASE_URL at import).
os.environ.setdefault(
    "DATABASE_URL", f"sqlite:///{_Path(tempfile.mkdtemp(prefix='sabbazaar-test-')) / 'test.db'}"
)
os.environ.setdefault("SHOPIFY_CONNECTOR", "fake")

import json  # noqa: E402
from pathlib import Path

import pytest  # noqa: E402

from sabbazaar_commerce.memory import memory_repositories
from sabbazaar_commerce.repositories import Repositories
from sabbazaar_commerce.seed import seed_catalogue
from sabbazaar_contracts.bill import BillExtraction

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
