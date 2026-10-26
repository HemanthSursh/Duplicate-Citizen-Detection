from datetime import date, timedelta
import json
import pytest
from citizen.demo import DEMO
from citizen.matching import validate, normalize, serialize, fingerprint, compare, candidates

BASE = DEMO[0]


def test_stable_hash():
    other = dict(reversed(list(BASE.items())))
    assert fingerprint(BASE) == fingerprint(other)
    assert len(fingerprint(BASE)) == 64
    assert json.loads(serialize(BASE)) == normalize(BASE)


def test_case_whitespace_and_phone_normalization():
    changed = {**BASE, "full_name": "  AARAV   DEMO ", "address": "14 EXAMPLE Lane,   Demo Nagar", "phone": "+000 (000) 0101"}
    assert fingerprint(BASE) == fingerprint(changed)


def test_unicode_equivalence():
    assert fingerprint({**BASE, "full_name": "José"}) == fingerprint({**BASE, "full_name": "Jose\u0301"})


def test_delimiters_cannot_collide():
    a = {**BASE, "full_name": "a|b", "address": "c"}
    b = {**BASE, "full_name": "a", "address": "b|c"}
    assert fingerprint(a) != fingerprint(b)


@pytest.mark.parametrize("field", ["full_name", "dob", "phone", "address"])
def test_each_field_matters(field):
    changes = {"full_name": "Other Name", "dob": "2000-01-01", "phone": "0000000999", "address": "Other Address"}
    assert fingerprint(BASE) != fingerprint({**BASE, field: changes[field]})


@pytest.mark.parametrize("change", [
    {"full_name": " "}, {"address": " "}, {"phone": "123"}, {"phone": "abcdefghij"},
    {"phone": "1+2345678"}, {"phone": "+1234567890123456"}, {"dob": "2025-02-30"},
    {"dob": "01/01/2000"}, {"dob": "2020-1-1"}, {"dob": (date.today()+timedelta(days=1)).isoformat()},
    {"full_name": "a"*151}, {"address": "a"*501},
])
def test_validation(change):
    with pytest.raises(ValueError):
        validate({**BASE, **change})


def test_leap_day():
    assert validate({**BASE, "dob": "2000-02-29"})["dob"] == "2000-02-29"


def test_demo_candidates():
    assert compare(DEMO[0], DEMO[1])["kind"] == "Exact"
    assert compare(DEMO[2], DEMO[3])["kind"] == "Probable"
    assert compare(DEMO[4], DEMO[5])["kind"] == "Probable"
    assert compare(DEMO[0], DEMO[6])["kind"] is None


def test_score_explained():
    result = compare(DEMO[2], DEMO[3])
    assert result["score"] == round(result["scores"]["full_name"]*.4 + 25 + 20 + result["scores"]["address"]*.15, 2)
    assert result["matching_fields"] == ["dob", "phone"]


def test_name_guard():
    assert compare(BASE, {**BASE, "full_name": "XYZ"})["kind"] is None


def test_country_code_not_inferred():
    assert normalize({**BASE, "phone": "919876543210"})["phone"] != normalize({**BASE, "phone": "9876543210"})["phone"]


@pytest.mark.parametrize("field", ["full_name", "dob", "phone", "address"])
def test_none_is_required(field):
    with pytest.raises(ValueError):
        validate({**BASE, field: None})


def test_phone_lengths():
    assert validate({**BASE, "phone": "1234567"})["phone"] == "1234567"
    assert validate({**BASE, "phone": "+123456789012345"})["phone"] == "+123456789012345"
