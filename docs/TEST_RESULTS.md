# Test results

Run on October 26, 2026 using Python 3.10.12 on Linux.

## Baseline

Before changes, cloned commit `7c09747f7e82059458ef0ff7ae3d04f7d5012d7b` passed all **54 tests**.

## Extended suite

Command: `.venv/bin/python -m pytest -q`

**103 passed**. One upstream Starlette warning says its httpx TestClient adapter is deprecated in favor of httpx2. The tests currently work with pinned httpx 0.28.1. This is a dependency deprecation warning, not a failed test. Automated tests ran locally, not GitHub CI.

Coverage includes:
- Original normalization, SHA-256, fuzzy rules, profile and document metadata, database persistence, reviews and dashboard flows.
- Phone uniqueness across different personal details, leading-plus/format normalization, concurrent writers, reviewed-save bypass prevention and preservation of existing duplicate phones.
- API key present/missing/wrong/unconfigured, health without personal data, exact/fuzzy parity, safe missing/invalid fields, body limit including streamed bytes, sanitized DB errors and privacy-limited logging.
- Transaction-time registration recheck, actual candidate explanations, no sensitive stored fields in API responses.
- Separate client clear/registration, similarity review handoff, network failures and phone-conflict blocking.

Where the new phone rule superseded the old behavior, tests were intentionally updated: exact same-phone duplicates cannot be saved even after review. The reviewed-save and stale-review tests now use a new phone with otherwise similar details to keep exercising fuzzy review protections.

## Real process checks

Started the API, dashboard and separate client as actual local processes against one temporary fictional registry. Checked HTTP exact-candidate response, 409 phone block, sample-client probable-candidate explanation and downloadable review request, successful HTTP registration of a clear case, and the main dashboard's phone error. A successful client registration increased the same registry from 8 to 9 records. No real citizen data or user's runtime database was accessed.

Inspected rendered browser screenshots for readability and flow:
- `phone-duplicate-error.png`: original dashboard with the explicit error and no save action.
- `api-client-review.png`: actual probable candidates, matching/differing fields, reasons and local review download notice.
- `api-client-registered.png`: actual 201 JSON and saved confirmation.
- `api-client-phone.png`: existing-phone block in the separate client.
- `api-docs.png`: interactive FastAPI docs.

Screenshots show fictional data. Generated IDs vary. This is demo validation, not a production security audit or performance test.
