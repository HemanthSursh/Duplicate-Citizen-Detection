# Verification

Tested with Python 3.10.12 on Linux and the pinned direct dependency versions in `requirements.txt`.

Command: `python -m pytest -q`

Result: **54 passed**.

Coverage includes:

- SHA-256 stability, deterministic sorted-key JSON and separator safety.
- Name/address case, whitespace and Unicode normalization.
- Each fingerprint field changing the hash.
- Missing/invalid fields, date format, leap dates, future dates and phone lengths.
- Exact and probable detection, name-score guard, weighted-score explanation and explicit country-code behavior.
- SQLite fingerprint index, restart persistence and parameterized values.
- Transactional duplicate checks, stale review protection and no-save without a review reason.
- One-time fictional demo insertion and rollback on invalid data.
- Saved pair decisions leaving citizen records unchanged.
- Streamlit dashboard metrics, navigation, registration, duplicate review, cancellation, validation records search, clickable-name profile details and optional document persistence/validation.

The running Streamlit UI was also inspected in Chromium: dashboard, registration, records, pair comparison and decision form. Dashboard layouts at 320px and 390px, plus the profile dialog at 390px, plus the profile dialog at 390px were checked with no horizontal page overflow. Screenshots in this folder show fictional demonstration records. No claim of real-world detection accuracy is made.

Windows and macOS instructions are included but were not executed on those operating systems.

Migration from the original four-field schema and unchanged fingerprints when optional fictional document references differ are also covered.

Migration from the original four-field schema and unchanged fingerprints when optional fictional document references differ are also covered.
