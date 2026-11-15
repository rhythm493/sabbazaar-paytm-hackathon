from __future__ import annotations

import threading

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from langgraph.checkpoint.memory import InMemorySaver

from apps.api.bill_intake.container import build_container
from apps.api.bill_intake.routes import install
from apps.api.bill_intake.settings import Settings
from sabbazaar_agents.extraction import FixtureExtractor, content_hash
from sabbazaar_commerce.memory import memory_repositories
from sabbazaar_connectors.fake import FakeConnector
from sabbazaar_connectors.registry import ConnectorRegistry
from sabbazaar_connectors.shopify_ops.connector import ShopifyConnector
from sabbazaar_connectors.shopify_ops.credentials import StaticCredentialsProvider
from sabbazaar_contracts.bill import BillExtraction, ExtractedLine
from sabbazaar_contracts.channels import ErrorCode

BILL = b"\x89PNG synthetic sample bill"
ANSWERS = [
    {"question_id": "L2:price:selling_price", "value": "399"},
    {"question_id": "L3:price:selling_price", "value": "450"},
    {"question_id": "L4:confirm_match", "value": "yes"},
    {"question_id": "L6:price:selling_price", "value": "549"},
]


def make_client(tmp_path, extraction, *, connector=None, seed=True):
    fake = connector or FakeConnector("shopify")
    registry = ConnectorRegistry()
    registry.register(fake)
    extractor = FixtureExtractor({content_hash(BILL): extraction})
    settings = Settings(
        _env_file=None, channel_mode="fake", model_enabled=False, upload_dir=tmp_path / "uploads"
    )
    container = build_container(
        settings,
        repos=memory_repositories(),
        registry=registry,
        extractor=extractor,
        checkpointer=InMemorySaver(),
    )
    app = FastAPI()
    install(app, container)
    client = TestClient(app)
    if seed:
        assert client.post("/v1/dev/seed").status_code == 200
    return client, fake, container


def upload(client, content=BILL, key=None):
    headers = {"Idempotency-Key": key} if key else {}
    return client.post(
        "/v1/ingestions", files={"file": ("bill.png", content, "image/png")}, headers=headers
    )


@pytest.fixture
def ready(tmp_path, sample_extraction):
    """An ingestion answered and waiting for confirmation."""
    client, fake, container = make_client(tmp_path, sample_extraction)
    iid = upload(client).json()["id"]
    body = client.post(f"/v1/ingestions/{iid}/answers", json={"answers": ANSWERS}).json()
    assert body["status"] == "awaiting_confirmation"
    return client, fake, container, iid, body


def test_golden_path(ready):
    client, fake, container, iid, body = ready
    assert body["simulated_channels"] == ["shopify"]
    assert body["fallback_used"] is True
    r = client.post(f"/v1/ingestions/{iid}/confirm", json={"preview_version": 1})
    assert r.status_code == 200, r.text
    done = r.json()
    assert done["status"] == "completed"
    assert all(j["status"] == "succeeded" for j in done["jobs"])
    products = {p["sku"]: p for p in client.get("/v1/books").json()}
    assert products["9781847941831"]["on_hand"] == 20  # 12 + 5 + 3 merged
    assert products["9789390166268"]["selling_price"] == "399.00"
    assert products["9788173711466"]["on_hand"] == 12
    assert products["9781786330895"]["on_hand"] == 6
    assert fake.find_by_sku("9781847941831").quantity == 20
    assert fake.products["9789390166268"]["price"] == 399
    assert fake.products["9781786330895"]["payload"].status == "draft"
    events = [e["event_type"] for e in client.get(f"/v1/ingestions/{iid}/audit").json()]
    for expected in (
        "ingestion.received",
        "action.proposed",
        "action.approved",
        "inventory.changed",
        "connector.job.succeeded",
        "ingestion.completed",
    ):
        assert expected in events


def test_upload_needs_input_with_questions(tmp_path, sample_extraction):
    client, *_ = make_client(tmp_path, sample_extraction)
    r = upload(client)
    assert r.status_code == 202
    body = client.get(f"/v1/ingestions/{r.json()['id']}").json()
    assert body["status"] == "needs_input"
    assert len(body["questions"]) == 4


def test_duplicate_upload_returns_same_ingestion(tmp_path, sample_extraction):
    client, *_ = make_client(tmp_path, sample_extraction)
    first = upload(client, key="abc")
    again = upload(client)
    same_key = upload(client, key="abc")
    reused = upload(client, content=b"\x89PNG other", key="abc")
    assert again.status_code == 200 and again.json()["id"] == first.json()["id"]
    assert same_key.json()["id"] == first.json()["id"]
    assert reused.status_code == 422 and reused.json()["error"]["code"] == "idempotency_key_reused"


def test_double_confirm_applies_once(ready):
    client, fake, container, iid, _ = ready
    results = []

    def go():
        results.append(client.post(f"/v1/ingestions/{iid}/confirm", json={"preview_version": 1}))

    threads = [threading.Thread(target=go) for _ in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert all(r.status_code == 200 for r in results)
    assert container.repos.inventory.on_hand("9781847941831") == 20
    assert len(container.repos.jobs.list_for(iid)) == 6


def test_stale_preview_version_rejected(ready):
    client, _, _, iid, _ = ready
    edited = client.post(
        f"/v1/ingestions/{iid}/preview/edit",
        json={"line_id": "L3", "fields": {"selling_price": "480"}},
    ).json()
    assert edited["preview"]["version"] == 2
    r = client.post(f"/v1/ingestions/{iid}/confirm", json={"preview_version": 1})
    assert r.status_code == 409 and r.json()["error"]["code"] == "stale_preview"
    assert (
        client.post(f"/v1/ingestions/{iid}/confirm", json={"preview_version": 2}).json()["status"]
        == "completed"
    )


@pytest.mark.parametrize("value", ["abc", "0", "-1", ""])
def test_invalid_answer_values_keep_flow_paused(tmp_path, sample_extraction, value):
    client, *_ = make_client(tmp_path, sample_extraction)
    iid = upload(client).json()["id"]
    r = client.post(
        f"/v1/ingestions/{iid}/answers",
        json={"answers": [{"question_id": "L3:price:selling_price", "value": value}]},
    )
    assert r.status_code == 422
    assert "L3:price:selling_price" in r.json()["error"]["fields"]
    body = client.get(f"/v1/ingestions/{iid}").json()
    assert body["status"] == "needs_input" and len(body["questions"]) == 4


def test_answers_for_unknown_question_or_wrong_state(ready, tmp_path, sample_extraction):
    client, _, _, iid, _ = ready
    r = client.post(
        f"/v1/ingestions/{iid}/answers",
        json={"answers": [{"question_id": "L3:price:selling_price", "value": "1"}]},
    )
    assert r.status_code == 409
    client2, *_ = make_client(tmp_path / "b", sample_extraction)
    iid2 = upload(client2).json()["id"]
    r2 = client2.post(
        f"/v1/ingestions/{iid2}/answers", json={"answers": [{"question_id": "nope", "value": "1"}]}
    )
    assert r2.status_code == 422


def test_channel_failure_then_retry(ready):
    client, fake, container, iid, _ = ready
    fake.fail_next["publish_product"] = ErrorCode.TRANSIENT
    done = client.post(f"/v1/ingestions/{iid}/confirm", json={"preview_version": 1}).json()
    assert done["status"] == "partially_failed"
    failed = [j for j in done["jobs"] if j["status"] != "succeeded"]
    assert len(failed) == 1 and failed[0]["error_code"] == "transient"
    stock_before = container.repos.inventory.on_hand("9781847941831")
    again = client.post(f"/v1/ingestions/{iid}/retry").json()
    assert again["status"] == "completed"
    assert container.repos.inventory.on_hand("9781847941831") == stock_before  # no re-apply


def test_reject_applies_nothing(ready):
    client, fake, container, iid, _ = ready
    assert client.post(f"/v1/ingestions/{iid}/reject").json()["status"] == "rejected"
    assert container.repos.inventory.on_hand("9781847941831") == 12
    assert (
        client.post(f"/v1/ingestions/{iid}/confirm", json={"preview_version": 1}).status_code == 409
    )


def test_all_lines_dropped_confirms_with_no_jobs(tmp_path):
    ext = BillExtraction(lines=[ExtractedLine(line_no=1, title=None, quantity=None)])
    client, *_ = make_client(tmp_path, ext)
    iid = upload(client).json()["id"]
    body = client.post(
        f"/v1/ingestions/{iid}/answers",
        json={"answers": [{"question_id": "L1:missing_field:title", "drop_line": True}]},
    ).json()
    assert body["status"] == "awaiting_confirmation" and body["preview"]["lines"] == []
    done = client.post(f"/v1/ingestions/{iid}/confirm", json={"preview_version": 1}).json()
    assert done["status"] == "completed" and done["jobs"] == []


def test_shopify_not_connected_is_honest(tmp_path, sample_extraction):
    conn = ShopifyConnector(StaticCredentialsProvider(None))
    client, *_ = make_client(tmp_path, sample_extraction, connector=conn)
    assert client.get("/v1/channels").json()[0]["ok"] is False
    iid = upload(client).json()["id"]
    client.post(f"/v1/ingestions/{iid}/answers", json={"answers": ANSWERS})
    done = client.post(f"/v1/ingestions/{iid}/confirm", json={"preview_version": 1}).json()
    assert done["status"] == "partially_failed"
    assert {j["error_code"] for j in done["jobs"]} == {"not_configured"}
    assert done["simulated_channels"] == []


def test_bad_uploads(tmp_path, sample_extraction):
    client, *_ = make_client(tmp_path, sample_extraction, seed=False)
    r = client.post("/v1/ingestions", files={"file": ("x.txt", b"hello", "text/plain")})
    assert r.status_code == 415
    r = client.post("/v1/ingestions", files={"file": ("x.png", b"", "image/png")})
    assert r.status_code == 422
    big = b"%PDF" + b"0" * (10 * 1024 * 1024)
    assert (
        client.post("/v1/ingestions", files={"file": ("x.pdf", big, "application/pdf")}).status_code
        == 413
    )


def test_interrupted_confirm_resumes_without_double_apply(ready):
    client, fake, container, iid, _ = ready
    catalogue = container.repos.catalogue
    real_add = catalogue.add
    calls = {"n": 0}

    def flaky_add(book):
        calls["n"] += 1
        if calls["n"] == 2:  # crash after the first new book is stored
            raise RuntimeError("db hiccup")
        real_add(book)

    catalogue.add = flaky_add
    crashing = TestClient(client.app, raise_server_exceptions=False)
    assert (
        crashing.post(f"/v1/ingestions/{iid}/confirm", json={"preview_version": 1}).status_code
        == 500
    )
    assert client.get(f"/v1/ingestions/{iid}").json()["status"] == "applying"
    done = client.post(f"/v1/ingestions/{iid}/confirm", json={"preview_version": 1}).json()
    assert done["status"] == "completed"
    assert container.repos.inventory.on_hand("9781847941831") == 20
    assert len(container.repos.jobs.list_for(iid)) == 6
    assert len(fake.products) == 5  # 3 seeded + 2 new, no duplicates


def test_ambiguous_publish_is_not_auto_retried(ready):
    client, fake, container, iid, _ = ready
    fake.fail_next["publish_product"] = ErrorCode.UNKNOWN
    done = client.post(f"/v1/ingestions/{iid}/confirm", json={"preview_version": 1}).json()
    failed = [j for j in done["jobs"] if j["status"] != "succeeded"]
    assert len(failed) == 1 and failed[0]["status"] == "terminal_failure"
    assert "Outcome unknown" in failed[0]["message"]
    assert client.post(f"/v1/ingestions/{iid}/retry").status_code == 409


def test_job_stuck_running_is_recovered(ready):
    client, fake, container, iid, _ = ready
    client.post(f"/v1/ingestions/{iid}/confirm", json={"preview_version": 1})
    jobs = container.repos.jobs.list_for(iid)
    inv = next(j for j in jobs if j.operation == "set_inventory")
    pub = next(j for j in jobs if j.operation == "publish_product")
    inv.status, pub.status = "running", "running"  # simulate a crash mid-call
    container.repos.jobs.update(inv)
    container.repos.jobs.update(pub)
    container.service.apply.run_jobs(iid)
    after = {j.id: j for j in container.repos.jobs.list_for(iid)}
    assert after[inv.id].status == "succeeded"
    assert after[pub.id].status == "terminal_failure"
