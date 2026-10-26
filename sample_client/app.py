"""Separate demo: python -m streamlit run sample_client/app.py --server.port 8502"""
import json
import sys
from pathlib import Path
import httpx
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sample_client.client import call_api

st.set_page_config(page_title="Customer registration | API demo", page_icon="🔌", layout="centered")
st.title("Customer registration")
st.caption("Separate integration demo · real HTTP calls · fictional details only")
st.info("This client has no database access. The API checks the same registry used by the main dashboard.")

with st.form("customer"):
    full_name = st.text_input("Name", value="Aarav Demo", max_chars=150)
    dob = st.text_input("Date of birth (YYYY-MM-DD)", value="2001-05-12", max_chars=10)
    phone = st.text_input("Phone number", value="0000000101", max_chars=40)
    address = st.text_area("Address", value="14 Example Lane, Demo Nagar", max_chars=500)
    submitted = st.form_submit_button("Check before registering", type="primary")

if submitted:
    st.session_state.pop("result", None)
    st.session_state.pop("review_request", None)
    st.session_state["details"] = dict(full_name=full_name, dob=dob, phone=phone, address=address)
    try:
        status, result = call_api("check", st.session_state["details"])
        st.session_state["result"] = result
        st.session_state["http_status"] = status
    except (ValueError, httpx.HTTPError):
        st.error("Check failed. Verify the API is running, authentication is configured and all four fields are valid. Nothing was registered.")

if "result" in st.session_state:
    result = st.session_state["result"]
    st.subheader("Actual API response")
    st.caption(f"HTTP {st.session_state['http_status']}. Actions use the last submitted details, not unsent form edits.")
    st.json(result)
    for candidate in result["candidates"]:
        with st.container(border=True):
            st.write(f"{candidate['kind'].title()} candidate · {candidate['similarity_score']}/100")
            st.code(candidate["record_id"])
            st.write("Matching fields: " + ", ".join(candidate["matching_fields"]))
            st.write("Differing fields: " + (", ".join(candidate["differing_fields"]) or "none"))
            for reason in candidate["reasons"]:
                st.write(reason)
    if result.get("status") == "registered":
        st.success("Customer registered in the shared registry.")
    elif result.get("phone_number_exists"):
        st.error("Phone number already exists.")
        st.info("Registration is blocked. Ask the registry operator to verify the phone number. No existing records were changed.")
    elif result["potential_duplicates"]:
        st.warning("Human review required. No new record was saved. Similarity is not proof of identity.")
        if st.button("Request manual review"):
            st.session_state["review_request"] = {
                "status": "prepared_not_submitted", "customer": st.session_state["details"],
                "candidate_ids": [c["record_id"] for c in result["candidates"]],
                "instructions": "Give this fictional-data request to the registry operator for manual review in the main dashboard.",
            }
        if "review_request" in st.session_state:
            st.info("Review request prepared locally, not sent to anyone. Download it and hand it to the registry operator. No automatic review queue or notification service is configured.")
            st.download_button("Download review request", json.dumps(st.session_state["review_request"], indent=2),
                               "fictional-review-request.json", "application/json")
    elif st.button("Proceed with registration", type="primary"):
        try:
            status, result = call_api("register", st.session_state["details"])
            st.session_state["result"] = result
            st.session_state["http_status"] = status
            st.rerun()
        except (ValueError, httpx.HTTPError):
            st.error("Registration was not confirmed. Check the dashboard before retrying: a lost response can occur after a successful save.")
