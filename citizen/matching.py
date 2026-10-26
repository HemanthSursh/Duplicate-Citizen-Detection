"""Deterministic exact matching and explainable fuzzy candidate screening."""
from datetime import date
import hashlib
import json
import re
import unicodedata
from rapidfuzz import fuzz

FIELDS = ("full_name", "dob", "phone", "address")
WEIGHTS = {"full_name": .40, "dob": .25, "phone": .20, "address": .15}
THRESHOLD = 78.0


def clean_text(value):
    return " ".join(unicodedata.normalize("NFKC", str(value) if value is not None else "").split())


def validate(data):
    """Return cleaned display values. Never silently repair an invalid date."""
    result = {field: clean_text(data.get(field, "")) for field in FIELDS}
    if any(not value for value in result.values()):
        raise ValueError("Fill in all four fields.")
    if len(result["full_name"]) > 150 or len(result["address"]) > 500:
        raise ValueError("Use at most 150 characters for the name and 500 for the address.")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", result["dob"]):
        raise ValueError("Enter the date of birth as YYYY-MM-DD.")
    try:
        birthday = date.fromisoformat(result["dob"])
    except ValueError as exc:
        raise ValueError("Enter a valid calendar date.") from exc
    if birthday > date.today():
        raise ValueError("Date of birth cannot be in the future.")
    phone = result["phone"]
    if not re.fullmatch(r"\+?[0-9 ()-]+", phone):
        raise ValueError("Use digits, spaces, parentheses or hyphens for the phone number.")
    phone = re.sub(r"[ ()-]", "", phone)
    if not re.fullmatch(r"\+?[0-9]{7,15}", phone):
        raise ValueError("Phone numbers must contain 7 to 15 digits, with an optional leading +.")
    result["phone"] = phone
    return result


def normalize(data):
    """Same rules at save, hash, exact lookup and fuzzy comparison time."""
    result = validate(data)
    for field in ("full_name", "address"):
        result[field] = result[field].casefold()
    # A plus is presentation, not part of the digit sequence. Country codes are not inferred.
    result["phone"] = result["phone"].lstrip("+")
    return result


def serialize(data):
    # Named fields avoid delimiter collisions; sort_keys gives stable ordering.
    return json.dumps(normalize(data), sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def fingerprint(data):
    return hashlib.sha256(serialize(data).encode("utf-8")).hexdigest()


def compare(left, right):
    a, b = normalize(left), normalize(right)
    scores = {
        "full_name": round(fuzz.token_sort_ratio(a["full_name"], b["full_name"]), 2),
        "dob": 100.0 if a["dob"] == b["dob"] else 0.0,
        "phone": 100.0 if a["phone"] == b["phone"] else 0.0,
        "address": round(fuzz.token_sort_ratio(a["address"], b["address"]), 2),
    }
    score = round(sum(scores[k] * WEIGHTS[k] for k in FIELDS), 2)
    exact = fingerprint(left) == fingerprint(right)
    probable = scores["full_name"] >= 65 and score >= THRESHOLD
    return {
        "kind": "Exact" if exact else "Probable" if probable else None,
        "score": score,
        "scores": scores,
        "matching_fields": [k for k in FIELDS if a[k] == b[k]],
    }


def candidates(data, records):
    found = []
    for record in records:
        match = compare(data, record)
        if match["kind"]:
            found.append({"record": record, **match})
    return sorted(found, key=lambda m: (-m["score"], m["record"]["id"]))
