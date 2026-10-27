from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest
from citizen.database import Registry
from citizen.demo import DEMO


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("CITIZEN_DB", str(tmp_path / "ui.sqlite3"))
    return AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"), default_timeout=15).run()


def button(app, label):
    return next(b for b in app.button if b.label == label)


def test_empty_dashboard_and_navigation(app):
    assert not app.exception
    assert [m.value for m in app.metric] == ["0", "0", "0", "0", "0"]
    button(app, "Open register citizen").click().run()
    assert "Check first" in app.title[0].value
    assert not app.exception


def test_demo_dashboard_and_review(app):
    button(app, "Load fictional demo").click().run()
    assert [m.value for m in app.metric] == ["8", "1", "2", "0", "8"]
    app.sidebar.radio[0].set_value("Duplicate review").run()
    assert not app.exception
    app.radio[1].set_value("Confirmed duplicate")
    app.text_area[0].set_value("Identical fictional details")
    button(app, "Save review decision").click().run()
    assert not app.exception
    app.sidebar.radio[0].set_value("Dashboard").run()
    assert [m.value for m in app.metric] == ["8", "0", "2", "0", "8"]


def test_registration_workflow(app):
    from datetime import date
    app.sidebar.radio[0].set_value("Register citizen").run()
    app.text_input[0].set_value("First Example")
    app.date_input[0].set_value(date(2000, 1, 1))
    app.text_input[1].set_value("0000000999")
    app.text_area[0].set_value("14 Fiction Street")
    button(app, "Check for duplicates").click().run()
    assert not app.exception
    button(app, "Save citizen record").click().run()
    assert "Citizen saved." in app.success[0].value
    app.text_input[1].set_value("0000000998")
    button(app, "Check for duplicates").click().run()
    assert "potential match" in app.warning[0].value
    button(app, "Continue to review").click().run()
    assert not app.exception
    assert button(app, "Save separate record").disabled
    app.text_area[1].set_value("Presentation needs an intentional duplicate")
    app.checkbox[0].check().run()
    button(app, "Save separate record").click().run()
    assert "Citizen saved." in app.success[0].value
    app.sidebar.radio[0].set_value("Dashboard").run()
    assert app.metric[0].value == "2"
    assert app.metric[2].value == "1"


def test_records_search(app):
    button(app, "Load fictional demo").click().run()
    app.sidebar.radio[0].set_value("Citizen records").run()
    app.text_input[0].set_value("Mira").run()
    assert not app.exception
    assert len([b for b in app.button if b.label == "Mira Sample"]) == 1
    button(app, "Mira Sample").click().run()
    assert not app.exception
    assert any("DEMO-AAD-" in m.value for m in app.markdown)
    app.text_input[0].set_value("zzznothing").run()
    assert "No records match" in app.info[0].value


def test_invalid_registration_stays_unsaved(app):
    app.sidebar.radio[0].set_value("Register citizen").run()
    button(app, "Check for duplicates").click().run()
    assert app.error
    app.sidebar.radio[0].set_value("Dashboard").run()
    assert app.metric[0].value == "0"


def test_flagged_cancel_adds_nothing(app):
    from datetime import date
    button(app, "Load fictional demo").click().run()
    app.sidebar.radio[0].set_value("Register citizen").run()
    app.text_input[0].set_value(DEMO[0]["full_name"])
    app.date_input[0].set_value(date(2001, 5, 12))
    app.text_input[1].set_value("0000000999")
    app.text_area[0].set_value(DEMO[0]["address"])
    button(app, "Check for duplicates").click().run()
    button(app, "Cancel registration").click().run()
    app.sidebar.radio[0].set_value("Dashboard").run()
    assert app.metric[0].value == "8"


def test_profile_documents_and_hidden_ids(app):
    button(app, "Load fictional demo").click().run()
    assert not any("CIT-" in m.value for m in app.markdown)
    button(app, "Rohan Fiction").click().run()
    assert not app.exception
    assert any("DEMO-AAD-0008" in m.value for m in app.markdown)
    assert any("DEMO-DL-0008" in m.value for m in app.markdown)


def test_fictional_documents_registration(app):
    from datetime import date
    app.sidebar.radio[0].set_value("Register citizen").run()
    app.text_input[0].set_value("Document Example")
    app.date_input[0].set_value(date(2000, 1, 1))
    app.text_input[1].set_value("0000000998")
    app.text_area[0].set_value("15 Fiction Street")
    app.text_input[2].set_value("DEMO-AAD-TEST")
    app.text_input[3].set_value("DEMO-DL-TEST")
    button(app, "Check for duplicates").click().run()
    button(app, "Save citizen record").click().run()
    assert not app.exception
    app.sidebar.radio[0].set_value("Citizen records").run()
    button(app, "Document Example").click().run()
    assert any("DEMO-AAD-TEST" in m.value for m in app.markdown)


def test_phone_duplicate_error(app):
    from datetime import date
    button(app, "Load fictional demo").click().run()
    app.sidebar.radio[0].set_value("Register citizen").run()
    app.text_input[0].set_value("A Different Fictional Person")
    app.date_input[0].set_value(date(2000, 1, 1))
    app.text_input[1].set_value("+000 (000) 0101")
    app.text_area[0].set_value("Another Fictional Address")
    button(app, "Check for duplicates").click().run()
    assert any(e.value == "Phone number already exists." for e in app.error)
    assert not any(b.label in ("Save citizen record", "Save separate record") for b in app.button)
    app.sidebar.radio[0].set_value("Dashboard").run()
    assert app.metric[0].value == "8"
