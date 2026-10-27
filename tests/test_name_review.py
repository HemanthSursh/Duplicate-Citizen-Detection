"""Same-name review without changing weighted matching or saved records."""
from datetime import date
import pytest
from citizen.matching import compare, match_reasons
from citizen.database import Registry, NewMatchesError, DuplicatePhoneError
from streamlit.testing.v1 import AppTest
from pathlib import Path

A = dict(full_name="Test1", dob="2007-04-25", phone="0000000901", address="Chennai")
B = dict(full_name="Test1", dob="2026-10-15", phone="0000000902", address="Chennai")

@pytest.mark.parametrize('name', ['Test1', '  TEST1  ', 'Ｔｅｓｔ１'])
def test_same_name_below_threshold(name):
    m = compare(A, {**B, 'full_name': name})
    assert m['kind'] == 'Name review' and m['score'] == 55
    assert 'below' in ' '.join(match_reasons(m))
    assert m['matching_fields'] == ['full_name', 'address']

def test_name_alone_and_near_name_not_equal():
    assert compare(A, {**B, 'address': 'Elsewhere'})['kind'] == 'Name review'
    assert compare(A, {**B, 'full_name': 'Test2'})['kind'] is None

def test_name_review_registration_and_decision(tmp_path):
    r = Registry(tmp_path / 'r.db'); first = r.register(A)
    with pytest.raises(NewMatchesError): r.register(B)
    with pytest.raises(ValueError, match='review reason'): r.register(B, [first])
    second = r.register(B, [first], 'Shared name, different details')
    assert r.stats()['name_review'] == 1
    before = r.records()
    r.decide(first, second, 'Distinct records', 'Different fictional people')
    assert r.stats()['name_review'] == 0 and r.stats()['reviewed'] == 1
    assert Registry(r.path).records() == before
    with pytest.raises(DuplicatePhoneError): r.register({**B, 'phone': A['phone']}, [first], 'Reviewed')

def test_preexisting_pair_found_without_record_change(tmp_path):
    r = Registry(tmp_path / 'old.db')
    # Fixture insertion simulates two records saved before the rule existed.
    with r.connection() as db:
        r._insert(db, A); r._insert(db, B)
    before = r.records()
    reopened = Registry(r.path)
    assert len(reopened.pairs()) == 1 and reopened.pairs()[0]['kind'] == 'Name review'
    assert reopened.records() == before

def test_api_name_review(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from api.main import create_app
    key = 'fictional-' + 'x' * 40
    monkeypatch.setenv('CITIZEN_API_KEY', key)
    path = tmp_path / 'api.db'; r = Registry(path); r.register(A)
    c = TestClient(create_app(path)); headers = {'X-API-Key': key}
    result = c.post('/api/v1/duplicates/check', json=B, headers=headers).json()
    m = result['candidates'][0]
    assert m['kind'] == 'name_review' and m['similarity_score'] == 55
    assert m['recommended_next_step'] == 'review'
    assert all('meets the' not in reason for reason in m['reasons'])
    response = c.post('/api/v1/customers/register', json=B, headers=headers)
    assert response.status_code == 409 and response.json()['status'] == 'review_required'
    assert len(r.records()) == 1

def test_ui_same_name_flow(tmp_path, monkeypatch):
    monkeypatch.setenv('CITIZEN_DB', str(tmp_path / 'ui.db'))
    r = Registry(tmp_path / 'ui.db'); r.register(A)
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py')).run()
    def click(label): next(b for b in app.button if b.label == label).click().run()
    app.sidebar.radio[0].set_value('Register citizen').run()
    app.text_input[0].set_value(B['full_name']); app.date_input[0].set_value(date.fromisoformat(B['dob']))
    app.text_input[1].set_value(B['phone']); app.text_area[0].set_value(B['address'])
    click('Check for duplicates')
    assert any('Name review candidate' in m.value for m in app.markdown)
    assert any('below' in m.value for m in app.caption)
    assert len(r.records()) == 1
    click('Continue to review'); app.text_area[1].set_value('Fictional shared name'); app.checkbox[0].check().run()
    click('Save separate record')
    app.sidebar.radio[0].set_value('Duplicate review').run()
    assert any('Identical normalized full name' in m.value for m in app.info)
    app.radio[1].set_value('Distinct records'); app.text_area[0].set_value('Different demo people')
    click('Save review decision')
    assert not app.exception and r.stats()['reviewed'] == 1
