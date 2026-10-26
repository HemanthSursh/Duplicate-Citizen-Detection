import asyncio
import logging
import sqlite3
import pytest
from fastapi.testclient import TestClient
from api.main import create_app, MAX_BODY_BYTES
from citizen.database import Registry
from citizen.demo import DEMO
from citizen.matching import FIELDS

KEY = "fictional-test-only-" + "x" * 32
DATA = {k: DEMO[0][k] for k in FIELDS}


@pytest.fixture
def setup(tmp_path, monkeypatch):
    monkeypatch.setenv("CITIZEN_API_KEY", KEY)
    path = tmp_path / "api.sqlite3"
    return TestClient(create_app(path)), Registry(path)


def post(client, path, data=DATA, **kwargs):
    return client.post("/api/v1/" + path, json=data, headers={"X-API-Key": KEY}, **kwargs)


def test_health_no_pii(setup):
    client, registry = setup
    registry.load_demo(DEMO)
    assert client.get("/api/v1/health").json() == {"status": "ok", "service": "citizencheck", "version": "1.0.0"}


@pytest.mark.parametrize("path", ["duplicates/check", "customers/register"])
def test_auth(setup, monkeypatch, path):
    client, registry = setup
    assert client.post("/api/v1/"+path, json=DATA).status_code == 401
    assert client.post("/api/v1/"+path, json=DATA, headers={"X-API-Key": "wrong"}).status_code == 401
    assert registry.records() == []
    monkeypatch.delenv("CITIZEN_API_KEY")
    assert post(client, path).status_code == 503
    monkeypatch.setenv("CITIZEN_API_KEY", "short")
    assert post(client, path).status_code == 503


def test_clear_register_and_exact(setup):
    client, registry = setup
    assert post(client, "duplicates/check").json() == {"phone_number_exists": False, "potential_duplicates": False, "candidates": [], "recommended_next_step": "continue"}
    saved = post(client, "customers/register")
    assert saved.status_code == 201
    result = post(client, "duplicates/check").json()
    match = result["candidates"][0]
    assert match["record_id"] == saved.json()["record_id"]
    assert match["kind"] == "exact" and match["similarity_score"] == 100
    assert match["matching_fields"] == list(FIELDS) and match["differing_fields"] == []
    assert match["reasons"] and match["recommended_next_step"] == "verify"
    assert DATA["full_name"] not in str(result) and "fingerprint" not in match
    blocked = post(client, "customers/register")
    assert blocked.status_code == 409 and blocked.json()["status"] == "phone_duplicate"
    assert len(registry.records()) == 1


def test_fuzzy_uses_actual_engine(setup):
    client, registry = setup
    rid = registry.register(DEMO[2])
    data = {k: DEMO[3][k] for k in FIELDS}
    expected = registry.check(data)[0]
    match = post(client, "duplicates/check", data).json()["candidates"][0]
    assert match["record_id"] == rid and match["kind"] == "probable"
    assert match["similarity_score"] == expected["score"]
    assert match["field_scores"] == expected["scores"]
    assert match["matching_fields"] == ["dob", "phone"]
    assert match["differing_fields"] == ["full_name", "address"]
    data = {**DEMO[2], "phone": "0000000999"}
    flagged = post(client, "customers/register", {k: data[k] for k in FIELDS})
    assert flagged.status_code == 409 and flagged.json()["status"] == "review_required"
    assert len(registry.records()) == 1


@pytest.mark.parametrize("change", [
    {"full_name": None}, {"full_name": " "}, {"full_name": "x"*151}, {"phone": 1234567890},
    {"phone": "1"*41}, {"phone": "abcdefg"}, {"dob": "2001-02-30"}, {"dob": "2999-01-01"},
    {"address": "x"*501}, {"extra": "forbidden"},
])
@pytest.mark.parametrize("path", ["duplicates/check", "customers/register"])
def test_invalid(setup, change, path):
    client, registry = setup
    response = post(client, path, {**DATA, **change})
    assert response.status_code == 422
    assert DATA["full_name"] not in response.text
    assert registry.records() == []


@pytest.mark.parametrize("field", FIELDS)
def test_missing(setup, field):
    client, registry = setup
    data = {k: v for k, v in DATA.items() if k != field}
    assert post(client, "duplicates/check", data).status_code == 422
    assert post(client, "customers/register", data).status_code == 422
    assert registry.records() == []


def test_malformed_and_limits(setup):
    client, registry = setup
    assert client.post("/api/v1/duplicates/check", content='{"full_name": secret', headers={"X-API-Key": KEY, "Content-Type": "application/json"}).status_code == 422
    result = client.post("/api/v1/duplicates/check", content=b"x" * (MAX_BODY_BYTES+1))
    assert result.status_code == 413 and registry.records() == []


def test_chunked_actual_limit(setup):
    client, _ = setup
    app = client.app
    events = iter([{"type": "http.request", "body": b"x" * 4096, "more_body": True},
                   {"type": "http.request", "body": b"x" * 4097, "more_body": False}])
    sent = []
    async def receive(): return next(events)
    async def send(message): sent.append(message)
    asyncio.run(app({"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1", "method": "POST",
                     "scheme": "http", "path": "/api/v1/duplicates/check", "raw_path": b"/api/v1/duplicates/check",
                     "query_string": b"", "headers": [], "server": ("test", 80), "client": ("test", 123)}, receive, send))
    assert sent[0]["status"] == 413


@pytest.mark.parametrize("path,method", [("duplicates/check", "check"), ("customers/register", "register")])
def test_db_error_sanitized(setup, monkeypatch, path, method):
    client, _ = setup
    def fail(*args, **kwargs): raise sqlite3.OperationalError("sensitive DB path and details")
    monkeypatch.setattr(Registry, method, fail)
    response = post(client, path)
    assert response.status_code == 503
    assert "sensitive" not in response.text


def test_unwritable_db(tmp_path, monkeypatch):
    monkeypatch.setenv("CITIZEN_API_KEY", KEY)
    path = tmp_path / "a-directory"
    path.mkdir()
    client = TestClient(create_app(path))
    assert post(client, "duplicates/check").status_code == 503


def test_private_logging_and_no_cache(setup, caplog):
    client, _ = setup
    with caplog.at_level(logging.INFO, logger="citizen.api"):
        response = post(client, "duplicates/check")
        client.get("/unknown-PRIVATE?name=secret")
    logs = " ".join(r.getMessage() for r in caplog.records if r.name == "citizen.api")
    assert "route=/api/v1/duplicates/check" in logs
    assert all(value not in logs for value in [KEY, DATA["full_name"], DATA["address"], "PRIVATE", "secret"])
    assert response.headers["cache-control"] == "no-store"


def test_transaction_rechecks_not_preview(setup, monkeypatch):
    client, registry = setup
    original = Registry.register
    def concurrent_insert(self, data, *args, **kwargs):
        original(self, data)
        return original(self, data)
    monkeypatch.setattr(Registry, "register", concurrent_insert)
    response = post(client, "customers/register")
    assert response.status_code == 409
    assert response.json()["status"] == "phone_duplicate"
    assert len(registry.records()) == 1


def test_openapi_auth(setup):
    client, _ = setup
    spec = client.get("/openapi.json").json()
    assert spec["components"]["securitySchemes"]["APIKeyHeader"]["name"] == "X-API-Key"
    assert spec["paths"]["/api/v1/duplicates/check"]["post"]["security"]


def test_same_phone_different_person_is_business_error(setup):
    client, registry = setup
    registry.register(DEMO[0])
    data = {k: DEMO[6][k] for k in FIELDS}
    data["phone"] = "+000 (000) 0101"
    check = post(client, "duplicates/check", data).json()
    assert check["potential_duplicates"] is False
    assert check["phone_number_exists"] is True
    result = post(client, "customers/register", data)
    assert result.status_code == 409 and result.json()["detail"] == "Phone number already exists."
    assert len(registry.records()) == 1
