import sqlite3
import pytest
from citizen.database import Registry, NewMatchesError
from citizen.demo import DEMO


@pytest.fixture
def registry(tmp_path):
    return Registry(tmp_path / "records.sqlite3")


def test_empty(registry):
    assert registry.stats() == dict(total=0, exact=0, probable=0, recent=0, reviewed=0)
    assert registry.records() == []


def test_persistence(registry):
    rid = registry.register(DEMO[0])
    reopened = Registry(registry.path)
    assert reopened.records()[0]["id"] == rid
    assert reopened.stats()["recent"] == 1
    assert reopened.exact(DEMO[0])[0]["id"] == rid


def test_index(registry):
    with sqlite3.connect(registry.path) as db:
        plan = str(db.execute("EXPLAIN QUERY PLAN SELECT * FROM citizens WHERE fingerprint=?", ("x",)).fetchall())
    assert "idx_fingerprint" in plan


def test_exact_requires_review(registry):
    rid = registry.register(DEMO[0])
    with pytest.raises(NewMatchesError):
        registry.register(DEMO[1])
    with pytest.raises(ValueError):
        registry.register(DEMO[1], [rid])
    saved = registry.register(DEMO[1], [rid], "Keeping a demonstration duplicate")
    assert saved != rid
    assert registry.stats()["exact"] == 1


def test_probable_requires_review(registry):
    rid = registry.register(DEMO[2])
    with pytest.raises(NewMatchesError):
        registry.register(DEMO[3])
    registry.register(DEMO[3], [rid], "Reviewed details")
    assert registry.stats()["probable"] == 1


def test_stale_review_blocked(registry):
    first = registry.register(DEMO[0])
    second = registry.register(DEMO[1], [first], "demo")
    with pytest.raises(NewMatchesError):
        registry.register(DEMO[0], [first], "outdated snapshot")
    assert len(registry.records()) == 2


def test_review_persists_without_modifying_records(registry):
    registry.load_demo(DEMO)
    before = registry.records()
    pair = registry.pairs()[0]
    registry.decide(pair["left"]["id"], pair["right"]["id"], "Confirmed duplicate", "Same four details")
    assert Registry(registry.path).stats()["exact"] == 0
    assert registry.stats()["reviewed"] == 1
    assert registry.records() == before
    registry.decide(pair["left"]["id"], pair["right"]["id"], "Distinct records", "Corrected after review")
    assert registry.pairs()[0]["review"]["decision"] == "Distinct records"


def test_demo_once(registry):
    assert registry.load_demo(DEMO)
    assert not registry.load_demo(DEMO)
    assert registry.stats() == dict(total=8, exact=1, probable=2, recent=8, reviewed=0)


def test_sql_parameters(registry):
    data = {**DEMO[0], "full_name": "Robert'); DROP TABLE citizens;--"}
    registry.register(data)
    assert len(registry.records()) == 1


def test_invalid_decision(registry):
    with pytest.raises(ValueError):
        registry.decide("a", "b", None, "")


def test_rollback_invalid_demo(registry):
    with pytest.raises(ValueError):
        registry.load_demo([DEMO[0], {**DEMO[1], "dob": "invalid"}])
    assert registry.records() == []


def test_recent_window_uses_database_timestamps(registry):
    registry.load_demo(DEMO)
    with registry.connection() as db:
        db.execute("UPDATE citizens SET created_at='2000-01-01T00:00:00+00:00'")
    assert registry.stats()["total"] == 8
    assert registry.stats()["recent"] == 0


def test_documents_persist_without_changing_fingerprint(registry):
    from citizen.matching import fingerprint
    original = DEMO[0]
    modified = {**original, "aadhaar_ref": "DEMO-AAD-OTHER", "licence_ref": "DEMO-DL-OTHER"}
    assert fingerprint(original) == fingerprint(modified)
    registry.register(modified)
    row = Registry(registry.path).records()[0]
    assert row["aadhaar_ref"] == "DEMO-AAD-OTHER"
    assert row["licence_ref"] == "DEMO-DL-OTHER"


@pytest.mark.parametrize("change", [{"aadhaar_ref": "123456789012"}, {"licence_ref": "TN12345678"}])
def test_real_looking_document_references_rejected(registry, change):
    with pytest.raises(ValueError):
        registry.register({**DEMO[0], **change})
    assert registry.records() == []


def test_migration_from_original_schema(tmp_path):
    path = tmp_path / "old.sqlite3"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE citizens(id TEXT PRIMARY KEY,full_name TEXT NOT NULL,dob TEXT NOT NULL,phone TEXT NOT NULL,address TEXT NOT NULL,fingerprint TEXT NOT NULL,created_at TEXT NOT NULL,review_note TEXT NOT NULL DEFAULT '')")
    migrated = Registry(path)
    migrated.register(DEMO[0])
    assert migrated.records()[0]["aadhaar_ref"] == "DEMO-AAD-0001"
