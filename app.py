"""Run with: python -m streamlit run app.py"""
from datetime import date
from pathlib import Path
import os
import pandas as pd
import streamlit as st
from citizen.database import Registry, NewMatchesError
from citizen.demo import DEMO
from citizen.documents import validate_documents
from citizen.matching import FIELDS, THRESHOLD, WEIGHTS, validate, serialize, fingerprint

st.set_page_config(page_title="Citizen records | Duplicate detection", page_icon="🔎", layout="wide")
ROOT = Path(__file__).resolve().parent
registry = Registry(os.environ.get("CITIZEN_DB", ROOT / "storage" / "citizens.sqlite3"))
LABELS = {"full_name": "Full name", "dob": "Date of birth", "phone": "Phone number", "address": "Address"}
PAGES = ["Dashboard", "Register citizen", "Citizen records", "Duplicate review"]

st.markdown("""<style>
.block-container {max-width:1280px;padding-top:2rem;padding-bottom:3rem}
[data-testid="stAppViewContainer"] {background:#f3f6fb}
[data-testid="stHeader"] {background:#f3f6fb}
h1 {font-size:2.15rem!important;letter-spacing:-.035em;font-weight:750!important;line-height:1.18!important}
h2,h3 {letter-spacing:-.025em;font-weight:650!important}
[data-testid="stSidebar"] {background:#111d35;border-right:0}
[data-testid="stSidebar"] * {color:#dae3f4}
[data-testid="stSidebar"] h3 {color:white!important;font-size:1.45rem}
[data-testid="stSidebar"] [data-testid="stRadio"] label {padding:10px 12px;border-radius:8px}
[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {background:#284475}
[data-testid="stSidebar"] hr {border-color:#2c3950}
[data-testid="stSidebar"] button {background:#253752;border-color:#405574}
[data-testid="stSidebar"] [data-testid="stExpander"] {background:#172741;border-color:#35465d}
[data-testid="stMetric"] {background:white;border-radius:14px;padding:22px;border:1px solid #e2e8f2;box-shadow:0 3px 12px #18305605;border-top:4px solid #3676ed}
[data-testid="stMetricLabel"] p {color:#65738c;font-size:13px}
[data-testid="stMetricValue"] {font-size:2.25rem;font-weight:750;color:#15294c}
[data-testid="stButton"] button {min-height:44px;border-radius:8px;font-weight:600}
[data-testid="stForm"] {background:white;border-radius:14px;border-color:#e2e8f2;padding:26px}
[data-testid="stVerticalBlockBorderWrapper"] > div {border-color:#e2e8f2}
[data-testid="stExpander"] {background:white;border-radius:12px}
.small-label {font-size:11px;font-weight:750;letter-spacing:.13em;color:#3676ed;margin-bottom:10px}
.hero-note {color:#65738c;font-size:15px;max-width:680px;margin-bottom:22px;line-height:1.65}
.st-key-homehero {background:linear-gradient(115deg,#14294e,#214e94);border-radius:18px;padding:30px 34px;margin-bottom:26px;box-shadow:0 12px 30px #18305616}
.st-key-homehero h1 {color:white!important;font-size:2.65rem!important;max-width:640px}
.st-key-homehero .small-label {color:#a9c9ff}
.st-key-homehero .hero-note {color:#cedcf4;margin-bottom:0;max-width:650px}
.st-key-homehero button {background:white;color:#20487f;border:0}
[data-testid="stButton"] button[kind="secondary"]:hover {border-color:#3676ed;color:#215bc1}
.footer-note {font-size:11px;color:#65738c;margin-top:36px;border-top:1px solid #dde5f0;padding-top:16px}
@media(max-width:640px){.block-container{padding:1.4rem 1rem}h1{font-size:1.85rem!important}.st-key-homehero{padding:22px}.st-key-homehero h1{font-size:2rem!important}}
</style>""", unsafe_allow_html=True)


def go(page):
    st.session_state["nav"] = page


@st.dialog("Citizen profile", width="large")
def profile(record):
    st.subheader(record["full_name"])
    st.caption("Citizen details · fictional demonstration data")
    left, right = st.columns(2)
    with left:
        for field in FIELDS:
            st.caption(LABELS[field])
            st.write(record[field])
    with right:
        st.markdown("**Identity documents**")
        st.caption("Fictional Aadhaar reference · not a real Aadhaar number")
        st.write(record.get("aadhaar_ref") or "Not provided")
        st.caption("Fictional driving-licence reference")
        st.write(record.get("licence_ref") or "Not provided")
        st.caption("These demo references are not verified and are not used for duplicate matching.")
    with st.expander("Internal record details"):
        st.caption("Internal record ID")
        st.code(record["id"], language=None)
        st.caption("Registered (UTC)")
        st.write(record["created_at"])
        st.caption("SHA-256 fingerprint")
        st.code(record["fingerprint"], language=None, wrap_lines=True)
        st.caption("Normalized matching fields")
        st.code(serialize(record), language="json", wrap_lines=True)
        st.caption("Registration review note")
        st.write(record["review_note"] or "No candidates were found at registration.")


def table(records, context="records"):
    # Real buttons make the name the entry point. IDs only serve as hidden widget keys.
    for record in records:
        with st.container(border=True):
            name_col, details_col = st.columns([2, 3])
            if name_col.button(record["full_name"], key=f"profile_{context}_{record['id']}", width="stretch"):
                profile(record)
            details_col.caption(f"Born {record['dob']} · {record['phone']}")
            details_col.write(record["address"])


def identity(record):
    if st.button(record["full_name"], key="identity_" + record["id"], width="stretch"):
        profile(record)
    for field in ("dob", "phone", "address"):
        st.caption(LABELS[field])
        st.write(record[field])


def heading(kicker, title, detail):
    st.markdown(f'<div class="small-label">{kicker}</div>', unsafe_allow_html=True)
    st.title(title)
    st.markdown(f'<div class="hero-note">{detail}</div>', unsafe_allow_html=True)


def show_match(match):
    r = match["record"]
    with st.container(border=True):
        st.markdown(f"**{match['kind']} candidate · {match['score']:.1f}/100 similarity**")
        if st.button(r["full_name"], key="match_" + r["id"]):
            profile(r)
        st.caption("Identical after normalization: " + (", ".join(LABELS[f] for f in match["matching_fields"]) or "none"))
        st.write(f"Born {r['dob']} · {r['phone']}")
        st.write(r["address"])
        with st.expander("See field scores"):
            st.dataframe(pd.DataFrame([{"Field": LABELS[f], "Score / 100": match["scores"][f], "Weight": f"{WEIGHTS[f]:.0%}"} for f in FIELDS]), hide_index=True, width="stretch")


with st.sidebar:
    st.markdown("### CitizenCheck")
    st.caption("CITIZEN RECORD WORKSPACE")
    st.divider()
    page = st.radio("Workspace", PAGES, key="nav", label_visibility="collapsed")
    st.divider()
    st.markdown("**Local by design**")
    st.caption("SQLite storage. No external API. Human decisions, always.")
    with st.expander("Demo data"):
        st.caption("Load 8 fictional records once. Includes exact and probable candidates for a presentation. Nothing is loaded automatically.")
        if st.button("Load fictional demo", width="stretch"):
            added = registry.load_demo(DEMO)
            st.session_state["flash"] = "8 fictional demo records loaded." if added else "The demo has already been loaded. No records were added."
            st.rerun()

if "flash" in st.session_state:
    st.success(st.session_state.pop("flash"))

if page == "Dashboard":
    with st.container(key="homehero"):
        heading("HOME / LIVE DASHBOARD", "One registry. A clearer picture.", "Keep citizen records organised. Catch repeated details before they become duplicate records, with a person in control of every decision.")
        st.button("+ Register a citizen", on_click=go, args=("Register citizen",), key="hero_register")
    st.subheader("Registry at a glance")
    stats = registry.stats()
    for col, (label, key, help_text) in zip(st.columns(4), [
        ("Citizen records", "total", "All saved citizen records."),
        ("Exact candidates", "exact", "Unreviewed pairs with identical normalized fields."),
        ("Probable candidates", "probable", "Unreviewed pairs that pass the fuzzy screening rule."),
        ("Added in 7 days", "recent", "Saved in the last rolling seven days, using UTC timestamps.")
    ]):
        col.metric(label, stats[key], help=help_text)
    st.caption("Candidate counts are record pairs awaiting review, not unique people. No record is merged or deleted.")
    st.write("")
    st.subheader("Quick actions")
    for col, title, copy, target in zip(st.columns(3), ["Register a citizen", "Browse the registry", "Review candidates"],
        ["Check a new record before saving it.", "Search saved names, phones and addresses.", "Compare matching fields side by side."], PAGES[1:]):
        with col, st.container(border=True):
            st.markdown(f"**{title}**")
            st.caption(copy)
            st.button("Open " + target.lower(), key=target, on_click=go, args=(target,), width="stretch")
    st.write("")
    st.subheader("Recent citizens")
    records = registry.records()
    if records:
        st.caption("Click a citizen's name to open their complete profile and fictional identity-document details.")
        table(records[:5], "recent")
    else:
        st.info("Your registry is empty. Register a citizen, or load the fictional demo from the sidebar.")
    st.write("")
    activity, workload = st.columns([3, 2])
    with activity, st.container(border=True):
        st.markdown("**Registration activity**")
        st.caption("Actual registrations in the last 7 UTC calendar days")
        today = pd.Timestamp.now(tz="UTC").normalize()
        days = pd.date_range(end=today, periods=7, freq="D")
        timestamps = pd.to_datetime([r["created_at"] for r in records], utc=True)
        counts = pd.Series(1, index=timestamps).resample("D").sum().reindex(days, fill_value=0) if len(timestamps) else pd.Series(0, index=days)
        chart = pd.DataFrame({"Registrations": counts.values}, index=days.strftime("%d %b"))
        st.bar_chart(chart, height=190, color="#3676ed")
    with workload, st.container(border=True):
        st.markdown("**Review workspace**")
        pending_count = stats["exact"] + stats["probable"]
        st.write(f"{pending_count} candidate pairs need a decision.")
        total_pairs = pending_count + stats["reviewed"]
        st.progress(stats["reviewed"] / total_pairs if total_pairs else 0)
        st.caption(f"{stats['reviewed']} of {total_pairs} candidate pairs reviewed")
        st.button("Go to duplicate review", on_click=go, args=("Duplicate review",), width="stretch")

elif page == "Register citizen":
    heading("NEW RECORD", "Check first. Save with care.", "Enter four details. We check exact fingerprints and similar records before anything is added.")
    st.caption("1 · Enter details     /     2 · Check matches     /     3 · Review and save")
    with st.form("registration"):
        col1, col2 = st.columns(2)
        name = col1.text_input("Full name", placeholder="e.g. Mira Sample", max_chars=150)
        dob = col2.date_input("Date of birth", value=None, min_value=date(1900, 1, 1), max_value=date.today(), format="YYYY-MM-DD")
        phone = st.text_input("Phone number", placeholder="7–15 digits; optional +country code", max_chars=30)
        address = st.text_area("Address", placeholder="House, street, locality and city", max_chars=500, height=95)
        with st.expander("Optional fictional identity documents"):
            st.caption("Demonstration references only. Never enter real Aadhaar or driving-licence numbers.")
            aadhaar = st.text_input("Fictional Aadhaar reference", placeholder="DEMO-AAD-0001", max_chars=33)
            licence = st.text_input("Fictional driving-licence reference", placeholder="DEMO-DL-0001", max_chars=32)
        checked = st.form_submit_button("Check for duplicates", type="primary", width="stretch")
    if checked:
        st.session_state.pop("pending", None)
        st.session_state.pop("registration_note", None)
        st.session_state.pop("registration_ack", None)
        try:
            data = validate(dict(full_name=name, dob=dob.isoformat() if dob else "", phone=phone, address=address))
            data.update(validate_documents(dict(aadhaar_ref=aadhaar, licence_ref=licence)))
            matches = registry.check(data)
            st.session_state["pending"] = {"data": data, "matches": matches, "review": False}
        except ValueError as exc:
            st.error(str(exc))
    pending = st.session_state.get("pending")
    if pending:
        matches = pending["matches"]
        st.divider()
        if matches:
            st.warning(f"{len(matches)} potential match(es). Nothing has been saved.")
            for match in matches:
                show_match(match)
            if not pending["review"]:
                col1, col2 = st.columns(2)
                if col1.button("Continue to review", type="primary", width="stretch"):
                    pending["review"] = True
                    st.rerun()
                if col2.button("Cancel registration", width="stretch"):
                    st.session_state.pop("pending")
                    st.rerun()
        else:
            st.success("No candidates found with the current rules. Review the details below before saving.")
        if not matches or pending["review"]:
            st.subheader("Review the new record")
            st.caption("This is the checked snapshot. If you edit the form above, press Check for duplicates again to use those edits.")
            for field in FIELDS:
                st.write(f"{LABELS[field]}: {pending['data'][field]}")
            for field, label in (("aadhaar_ref", "Fictional Aadhaar reference"), ("licence_ref", "Fictional driving-licence reference")):
                st.write(f"{label}: {pending['data'].get(field) or 'Not provided'}")
            note = st.text_area("Why should this flagged record be kept?", key="registration_note") if matches else ""
            acknowledged = st.checkbox("I checked the matches and want to keep a separate record.", key="registration_ack") if matches else True
            col1, col2 = st.columns(2)
            if col1.button("Save separate record" if matches else "Save citizen record", type="primary", disabled=not acknowledged or (bool(matches) and not note.strip()), width="stretch"):
                try:
                    record_id = registry.register(pending["data"], [m["record"]["id"] for m in matches], note)
                    st.session_state.pop("pending")
                    st.session_state["flash"] = "Citizen saved. No existing record was changed."
                    st.rerun()
                except NewMatchesError as exc:
                    pending["matches"] = registry.check(pending["data"])
                    pending["review"] = False
                    st.warning(str(exc))
                except ValueError as exc:
                    st.error(str(exc))
            if col2.button("Cancel", width="stretch"):
                st.session_state.pop("pending")
                st.rerun()

elif page == "Citizen records":
    heading("REGISTRY", "Every record, easy to find.", "Search your saved records and click a citizen's name to view their full profile, including fictional document references.")
    search = st.text_input("Search name, phone or address", placeholder="Type to filter records...")
    all_records = registry.records()
    query = search.strip().casefold()
    records = [r for r in all_records if any(query in r[f].casefold() for f in ("full_name", "phone", "address"))]
    st.caption(f"{len(records)} of {len(all_records)} records")
    if records:
        table(records)
    else:
        st.info("No records match this search." if all_records else "No records yet. Start with registration or load the fictional demo.")

else:
    heading("HUMAN REVIEW", "Similar is a signal, not a verdict.", "Compare candidate pairs, record your decision, and preserve both records. Nothing is automatically merged or rejected.")
    with st.expander("How matching works"):
        st.write("Exact: SHA-256 of all four normalized fields in sorted-key JSON. Name and address use Unicode normalization, case folding and collapsed whitespace. Phone separators and a leading + are ignored; country codes are never inferred.")
        st.write(f"Probable: weighted score at least {THRESHOLD:.0f}/100, plus a name score of at least 65. Name 40%, date of birth 25%, phone 20%, address 15%. RapidFuzz token-sort similarity scores name and address. Date and phone score 100 only when identical, otherwise 0.")
        st.caption("These are demonstration screening rules, not calibrated probabilities or proof of identity. Some duplicates will be missed. Shared details can flag different people.")
    pairs = registry.pairs()
    filter_choice = st.radio("Show", ["Awaiting review", "Reviewed", "All candidates"], horizontal=True)
    filtered = [p for p in pairs if filter_choice == "All candidates" or (p["review"] is None) == (filter_choice == "Awaiting review")]
    st.caption(f"{len(filtered)} candidate pairs · decisions are saved in SQLite")
    if not filtered:
        st.info("No candidate pairs in this view. Load the fictional demo or register similar records to try the workflow.")
    else:
        indices = list(range(len(filtered)))
        index = st.selectbox("Choose a candidate pair", indices, format_func=lambda i: f"{filtered[i]['kind']} · {filtered[i]['left']['full_name']} / {filtered[i]['right']['full_name']} · {filtered[i]['score']:.1f}/100")
        pair = filtered[index]
        st.markdown(f"### {pair['kind']} candidate · {pair['score']:.1f}/100")
        left, right = st.columns(2)
        with left, st.container(border=True):
            identity(pair["left"])
        with right, st.container(border=True):
            identity(pair["right"])
        st.caption("Identical after normalization: " + (", ".join(LABELS[f] for f in pair["matching_fields"]) or "none"))
        st.dataframe(pd.DataFrame([{"Field": LABELS[f], "Similarity / 100": pair["scores"][f], "Weight": f"{WEIGHTS[f]:.0%}"} for f in FIELDS]), hide_index=True, width="stretch")
        prior = pair["review"]
        if prior:
            st.info(f"Saved decision: {prior['decision']} · {prior['reviewed_at']}")
            st.write(prior["note"])
        # Pair-specific keys stop a note/choice carrying over to another person.
        pair_key = "_".join(sorted((pair["left"]["id"], pair["right"]["id"])))
        with st.form("decision_" + pair_key):
            decision = st.radio("Your decision", ["Confirmed duplicate", "Distinct records"], index=None)
            note = st.text_area("Review note", placeholder="Explain which details support your decision.")
            st.caption("Saving a decision never merges, edits or deletes either citizen record. Reviewed pairs leave the dashboard's pending counts.")
            submit = st.form_submit_button("Save review decision", type="primary")
        if submit:
            try:
                registry.decide(pair["left"]["id"], pair["right"]["id"], decision, note)
                st.session_state["flash"] = "Review decision saved. Both citizen records are unchanged."
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))

st.markdown('<div class="footer-note">Intelligent Duplicate Citizen Record Detection System · Local college-project demonstration · Use fictional data only</div>', unsafe_allow_html=True)
