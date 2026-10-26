from pathlib import Path
from unittest.mock import patch
import httpx
import pytest
from streamlit.testing.v1 import AppTest
from sample_client.client import call_api

CLEAR = {"potential_duplicates": False, "candidates": [], "recommended_next_step": "continue"}
MATCH = {"potential_duplicates": True, "recommended_next_step": "review", "candidates": [{
    "record_id": "CIT-FICTIONAL", "kind": "probable", "similarity_score": 90,
    "matching_fields": ["dob", "phone"], "differing_fields": ["full_name", "address"], "reasons": ["Actual test explanation"]}]}


def client_app():
    return AppTest.from_file(str(Path(__file__).resolve().parents[1] / "sample_client/app.py")).run()


def click(app, label):
    return next(b for b in app.button if b.label == label).click().run()


def test_client_clear_register():
    with patch("sample_client.client.call_api", side_effect=[(200, CLEAR), (201, {**CLEAR, "status": "registered", "record_id": "CIT-FICTIONAL"})]) as api:
        app = client_app()
        click(app, "Check before registering")
        click(app, "Proceed with registration")
        assert not app.exception and app.success
        assert api.call_count == 2


def test_client_review_no_auto_registration():
    with patch("sample_client.client.call_api", return_value=(200, MATCH)) as api:
        app = client_app()
        click(app, "Check before registering")
        assert not app.exception and app.warning
        click(app, "Request manual review")
        assert app.session_state["review_request"]["status"] == "prepared_not_submitted"
        assert api.call_count == 1


def test_client_network_failure():
    with patch("sample_client.client.call_api", side_effect=httpx.ConnectError("private details")):
        app = client_app()
        click(app, "Check before registering")
        assert app.error and not app.exception
        assert "private details" not in app.error[0].value


def test_http_adapter(monkeypatch):
    monkeypatch.setenv("CITIZEN_API_KEY", "fictional-only-"+"x"*32)
    response = httpx.Response(200, json=CLEAR)
    with patch("httpx.Client.post", return_value=response) as post:
        assert call_api("check", {"full_name": "Fictional"}) == (200, CLEAR)
        assert post.call_args.args[0] == "http://127.0.0.1:8000/api/v1/duplicates/check"
        assert "X-API-Key" in post.call_args.kwargs["headers"]
    monkeypatch.delenv("CITIZEN_API_KEY")
    with pytest.raises(ValueError): call_api("check", {})


def test_client_phone_block():
    with patch("sample_client.client.call_api", return_value=(200, {**CLEAR, "phone_number_exists": True})):
        app = client_app()
        click(app, "Check before registering")
        assert any(e.value == "Phone number already exists." for e in app.error)
        assert not any(b.label == "Proceed with registration" for b in app.button)
