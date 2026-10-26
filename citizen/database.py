"""SQLite persistence, transactional registration and human pair decisions."""
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sqlite3
import uuid
from .matching import candidates, compare, fingerprint, validate
from .documents import validate_documents


def utcnow():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class DuplicatePhoneError(ValueError):
    def __init__(self):
        super().__init__("Phone number already exists.")


class NewMatchesError(ValueError):
    def __init__(self, message, matches=()):
        super().__init__(message)
        self.matches = list(matches)


class Registry:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS citizens (
                id TEXT PRIMARY KEY, full_name TEXT NOT NULL, dob TEXT NOT NULL,
                phone TEXT NOT NULL, address TEXT NOT NULL, fingerprint TEXT NOT NULL,
                created_at TEXT NOT NULL, review_note TEXT NOT NULL DEFAULT ''
            );
            CREATE INDEX IF NOT EXISTS idx_fingerprint ON citizens(fingerprint);
            CREATE TABLE IF NOT EXISTS reviews (
                first_id TEXT NOT NULL REFERENCES citizens(id) ON DELETE CASCADE,
                second_id TEXT NOT NULL REFERENCES citizens(id) ON DELETE CASCADE,
                decision TEXT NOT NULL CHECK(decision IN ('Confirmed duplicate', 'Distinct records')),
                note TEXT NOT NULL, reviewed_at TEXT NOT NULL,
                PRIMARY KEY(first_id, second_id)
            );
            CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            """)
            # Add optional demo references without changing existing records or fingerprints.
            columns = {row[1] for row in db.execute("PRAGMA table_info(citizens)")}
            for column in ("aadhaar_ref", "licence_ref"):
                if column not in columns:
                    db.execute(f"ALTER TABLE citizens ADD COLUMN {column} TEXT NOT NULL DEFAULT ''")

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        try:
            with db:
                yield db
        finally:
            db.close()

    @staticmethod
    def _records(db):
        return [dict(row) for row in db.execute("SELECT * FROM citizens ORDER BY created_at DESC, rowid DESC")]

    def records(self):
        with self.connection() as db:
            return self._records(db)

    def exact(self, data):
        with self.connection() as db:
            return [dict(row) for row in db.execute("SELECT * FROM citizens WHERE fingerprint=?", (fingerprint(data),))]

    def check(self, data):
        # Use the indexed fingerprint lookup first, then fuzzy-screen the remaining records.
        exact_records = self.exact(data)
        exact_ids = {r["id"] for r in exact_records}
        records = exact_records + [r for r in self.records() if r["id"] not in exact_ids]
        return candidates(data, records)

    @staticmethod
    def _insert(db, data, note=""):
        record_id = "CIT-" + uuid.uuid4().hex[:12].upper()
        docs = validate_documents(data)
        db.execute("INSERT INTO citizens(id,full_name,dob,phone,address,fingerprint,created_at,review_note,aadhaar_ref,licence_ref) VALUES(?,?,?,?,?,?,?,?,?,?)", (
            record_id, data["full_name"], data["dob"], data["phone"], data["address"],
            fingerprint(data), utcnow(), note, docs["aadhaar_ref"], docs["licence_ref"],
        ))
        return record_id

    @staticmethod
    def _phone_exists(db, phone):
        # Existing display storage may include a plus; match the engine's digit convention.
        digits = phone.lstrip("+")
        return db.execute("SELECT 1 FROM citizens WHERE replace(replace(replace(replace(replace(phone,'+',''),' ',''),'(',''),')',''),'-','')=? LIMIT 1", (digits,)).fetchone() is not None

    def phone_exists(self, phone):
        with self.connection() as db:
            return self._phone_exists(db, phone)

    def ensure_phone_available(self, data):
        if self.phone_exists(validate(data)["phone"]):
            raise DuplicatePhoneError()

    def register(self, data, reviewed_ids=(), note=""):
        data = {**validate(data), **validate_documents(data)}
        with self.connection() as db:
            # Recheck under the write lock. Another session cannot slip in between check and save.
            db.execute("BEGIN IMMEDIATE")
            if self._phone_exists(db, data["phone"]):
                raise DuplicatePhoneError()
            # Indexed exact lookup is also performed inside the save transaction.
            exact_rows = [dict(r) for r in db.execute("SELECT * FROM citizens WHERE fingerprint=?", (fingerprint(data),))]
            exact_ids = {r["id"] for r in exact_rows}
            remaining = [r for r in self._records(db) if r["id"] not in exact_ids]
            matches = candidates(data, exact_rows + remaining)
            expected = set(reviewed_ids)
            if any(m["record"]["id"] not in expected for m in matches):
                raise NewMatchesError("Potential matches changed. Check this record again before saving.", matches)
            if matches and not note.strip():
                raise ValueError("Add a review reason before saving a flagged record.")
            return self._insert(db, data, note.strip() if matches else "")

    def pairs(self):
        with self.connection() as db:
            records = self._records(db)
            reviews = {(r["first_id"], r["second_id"]): dict(r) for r in db.execute("SELECT * FROM reviews")}
        found = []
        for i, left in enumerate(records):
            for right in records[i + 1:]:
                match = compare(left, right)
                if match["kind"]:
                    ids = tuple(sorted((left["id"], right["id"])))
                    found.append({"left": left, "right": right, **match, "review": reviews.get(ids)})
        return sorted(found, key=lambda p: (-p["score"], p["left"]["id"], p["right"]["id"]))

    def decide(self, first, second, decision, note):
        if first == second or decision not in ("Confirmed duplicate", "Distinct records") or not note.strip():
            raise ValueError("Choose two different records, a valid decision and a review note.")
        first, second = sorted((first, second))
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            rows = [dict(r) for r in db.execute("SELECT * FROM citizens WHERE id IN (?,?)", (first, second))]
            if len(rows) != 2 or not compare(*rows)["kind"]:
                raise ValueError("This candidate pair no longer exists.")
            db.execute("INSERT INTO reviews VALUES(?,?,?,?,?) ON CONFLICT(first_id,second_id) DO UPDATE SET decision=excluded.decision,note=excluded.note,reviewed_at=excluded.reviewed_at",
                       (first, second, decision, note.strip(), utcnow()))

    def stats(self):
        pairs = self.pairs()
        pending = [p for p in pairs if p["review"] is None]
        cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat(timespec="seconds")
        with self.connection() as db:
            total = db.execute("SELECT count(*) FROM citizens").fetchone()[0]
            recent = db.execute("SELECT count(*) FROM citizens WHERE created_at>=?", (cutoff,)).fetchone()[0]
        return {"total": total, "exact": sum(p["kind"] == "Exact" for p in pending),
                "probable": sum(p["kind"] == "Probable" for p in pending), "recent": recent,
                "reviewed": len(pairs) - len(pending)}

    def load_demo(self, records):
        """One explicit, all-or-nothing demo load. No automatic data on startup."""
        cleaned = [{**validate(r), **validate_documents(r)} for r in records]
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            if db.execute("SELECT 1 FROM settings WHERE key='demo_loaded'").fetchone():
                return False
            for record in cleaned:
                self._insert(db, record, "Fictional demo fixture; intentionally includes duplicate candidates.")
            db.execute("INSERT INTO settings VALUES('demo_loaded','1')")
        return True
