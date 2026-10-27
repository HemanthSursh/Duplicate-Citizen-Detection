# Local REST API and integration guide

This extends the existing application, not a replacement. Keep using the main dashboard on port 8501. The API runs on 8000 and the separate sample client on 8502. Use fictional data only.

## Install

Python 3.10+ is required. From the repository folder:

Windows:
```powershell
py -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

macOS/Linux:
```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

## Configure authentication

`CITIZEN_API_KEY` must be a private value of at least 32 characters. Generate it locally, never paste it into chat, code or GitHub. No active key is included in this project.

PowerShell (run once in every terminal used for API/sample client):
```powershell
$env:CITIZEN_API_KEY = (& .venv\Scripts\python -c "import secrets; print(secrets.token_urlsafe(32))")
```

For additional terminals, use the **same** locally generated value, not a newly generated key. You can enter it without displaying it:
```powershell
$env:CITIZEN_API_KEY = [System.Net.NetworkCredential]::new('', (Read-Host 'Existing local API key' -AsSecureString)).Password
```

macOS/Linux (first terminal):
```bash
export CITIZEN_API_KEY="$(.venv/bin/python -c 'import secrets; print(secrets.token_urlsafe(32))')"
```

Additional terminals must use the same value, supplied through your local secret manager or a hidden prompt:
```bash
read -rs -p 'Existing local API key: ' CITIZEN_API_KEY; echo
export CITIZEN_API_KEY
```

Alternatively start all processes from a parent shell that already has the key in its environment. `.env` files are ignored by Git but **not automatically loaded**. Do not commit secrets. The API fails closed with 503 when its key is missing/short and 401 for a missing/wrong request key. Send `X-API-Key` as a header, never a URL parameter.

One key authorizes access to **the entire configured local registry**, not only records belonging to a particular app or person. Only give it to an application permitted to check that registry. This is not multi-tenant authorization. The dashboard remains an unprotected local operator interface.

## Run three separate terminals

Windows PowerShell:
```powershell
# Terminal 1: main dashboard
.venv\Scripts\python -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501
# Terminal 2: API (set CITIZEN_API_KEY first)
.venv\Scripts\python -m uvicorn api.main:app --host 127.0.0.1 --port 8000 --no-access-log --log-level info
# Terminal 3: separate sample client (same CITIZEN_API_KEY)
.venv\Scripts\python -m streamlit run sample_client/app.py --server.address 127.0.0.1 --server.port 8502
```

macOS/Linux:
```bash
# Terminal 1
.venv/bin/python -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501
# Terminal 2 (set CITIZEN_API_KEY first)
.venv/bin/python -m uvicorn api.main:app --host 127.0.0.1 --port 8000 --no-access-log --log-level info
# Terminal 3 (same CITIZEN_API_KEY)
.venv/bin/python -m streamlit run sample_client/app.py --server.address 127.0.0.1 --server.port 8502
```

Open http://127.0.0.1:8501 for the main app, http://127.0.0.1:8502 for the demo and http://127.0.0.1:8000/docs for interactive API documentation. In docs choose **Authorize**, enter the local API key, then try the endpoints. The schema is at `/openapi.json`. Health and documentation are public locally; both POST endpoints require authentication. Stop each process using Ctrl+C.

By default both dashboard and API resolve `storage/citizens.sqlite3` relative to the repository, regardless of the working directory. To use another file set `CITIZEN_DB` to the same absolute path in **both** processes. Relative overrides also resolve from the repository root. The sample client never opens a database; its `CITIZEN_API_URL` defaults to `http://127.0.0.1:8000`. This URL is trusted server configuration, not user input. No keys go to browser JavaScript. No CORS wildcard is enabled. For a real website, call from a trusted backend; never embed the key in public frontend code.

## Request contract

Both POST endpoints accept a JSON object with exactly these required string keys:
```json
{
  "full_name": "Aarav Demo",
  "dob": "2001-05-12",
  "phone": "0000000101",
  "address": "14 Example Lane, Demo Nagar"
}
```

`full_name`: 1-150 characters; `dob`: YYYY-MM-DD, real calendar date, not future; `phone`: 7-15 digits, optional leading +, spaces/parentheses/hyphens allowed (40 input characters max); `address`: 1-500 characters. Whitespace-only values, nulls, missing fields, wrong types and unknown keys are rejected with 422. The full body, including streamed/chunked requests, is limited to 8192 bytes (413 if exceeded). The matching engine validates and normalizes these values with exactly the dashboard rules. Partial records do not produce a misleading no-match response.

## Endpoints

### GET /api/v1/health

Liveness only, not database readiness. No key or personal data:
```json
{"status":"ok","service":"citizencheck","version":"1.0.0"}
```

### POST /api/v1/duplicates/check

Read-only. Returns 200 and actual candidates from the shared engine. Candidate output contains internal IDs, similarity and per-field scores, matching/differing field names, reasons and next steps. It never returns names, phone numbers, birthdays, addresses, document refs, stored hashes or review notes.

Example **shape**, not a hardcoded response (IDs vary; `CIT-EXAMPLE` is a placeholder):
```json
{
  "phone_number_exists": true,
  "potential_duplicates": true,
  "candidates": [{
    "record_id": "CIT-EXAMPLE",
    "kind": "exact",
    "similarity_score": 100.0,
    "field_scores": {"full_name":100.0,"dob":100.0,"phone":100.0,"address":100.0},
    "matching_fields": ["full_name","dob","phone","address"],
    "differing_fields": [],
    "reasons": ["All four normalized fields have the same SHA-256 fingerprint."],
    "recommended_next_step": "verify"
  }],
  "recommended_next_step": "review"
}
```

Candidate `kind` is `exact`, `probable` or `name_review`. The additive `name_review` value identifies equal normalized full names below the probable threshold; clients that validate enum values must accept it. Its reasons explain the name trigger and actual score, without claiming the threshold was met. Both check and registration use this rule; registration returns 409 `review_required`, without saving, for same-name candidates with an available phone. No new notification service or API review-bypass is added.

A clean result has `potential_duplicates:false`, `candidates:[]`, `phone_number_exists:false` and `recommended_next_step:"continue"`. A reused phone can be present even without a fuzzy candidate: `phone_number_exists:true` then requires review/correction and blocks registration. It does not invent a candidate or similarity score. Field matches mean normalized equality; a fuzzy name/address can have a high score while still appearing in `differing_fields`. Similarity is **not a probability or identity proof**. No country codes are guessed.

### POST /api/v1/customers/register

The same four-field JSON. Saves into the existing `citizens` table, not a separate customer store. It checks again under SQLite `BEGIN IMMEDIATE` before inserting, so the preview is not authority to bypass newly added matches.

- 201 `status:"registered"`, generated `record_id`, no candidates: saved.
- 409 `status:"phone_duplicate"`, `detail:"Phone number already exists."`, `phone_number_exists:true`: no new record saved. This is the user's explicit phone-uniqueness rule, separate from fuzzy matching. Formatting or a leading + does not bypass it. It takes precedence over review-required when both apply.
- 409 `status:"review_required"`, actual candidates: no new record saved. A probable/exact similarity is a request for human review, not an automatic merge or rejection of a person. The API has no review-bypass field.
- 401 auth missing/wrong; 422 invalid details; 413 body limit; 503 auth not configured or registry unavailable.

Existing duplicate phones remain intact, with no destructive schema migration. No unique index is created on a database that already contains duplicates. Ordinary registrations are serialized under a write lock and checked for the normalized phone. The explicitly requested fictional demo loader intentionally bypasses registration to load its eight test fixtures, including duplicate phones. There is no record-edit screen or API; nothing edits existing phones. External direct SQLite writers are outside this application-level rule.

## curl

From a shell where the local key is set, macOS/Linux:
```bash
curl -s http://127.0.0.1:8000/api/v1/health
curl -s -X POST http://127.0.0.1:8000/api/v1/duplicates/check \
  -H "X-API-Key: $CITIZEN_API_KEY" -H 'Content-Type: application/json' \
  --data '{"full_name":"Aarav Demo","dob":"2001-05-12","phone":"0000000101","address":"14 Example Lane, Demo Nagar"}'
```

PowerShell (uses curl.exe, not PowerShell's old curl alias):
```powershell
'{"full_name":"Aarav Demo","dob":"2001-05-12","phone":"0000000101","address":"14 Example Lane, Demo Nagar"}' | Set-Content -Encoding ascii fictional-request.json
curl.exe -s -X POST http://127.0.0.1:8000/api/v1/duplicates/check -H "X-API-Key: $env:CITIZEN_API_KEY" -H "Content-Type: application/json" --data-binary "@fictional-request.json"
```

For registration, replace `/duplicates/check` with `/customers/register`; only do that when you want to save. On a fresh database this request can save; with the main dashboard's fictional demo loaded the phone already exists. The API never silently loads sample records. After loading the fictional fixture, try the sample client: its default Aarav request should show exact/probable candidates and the phone error. For a clear case use a new fictional name, birthday, phone and address. For probable review without phone conflict, submit Aarav's other details with phone `0000000999` (same name/DOB/address gives an 80 score).

## Separate client and manual review

The sample app on 8502 collects fictional details, checks by HTTP, displays the actual JSON and field explanations, and enables registration only when clear. It shows a same-phone error rather than a proceed action. Registration rechecks the current database even if the check was clear.

For similarity candidates without a phone conflict, **Request manual review** prepares a downloadable JSON request locally. It is explicitly **not submitted or notified** to anyone: hand it to the registry operator. It contains entered fictional details and candidate IDs, so handle it privately. No persistent review queue, email, webhook or background service is implied. The operator can use the existing main dashboard to inspect candidates and register a reviewed separate record with a reason only when the phone is available. The sample client has no merge, delete, bypass or direct DB access.

## Logging and production boundary

The API emits only method, fixed route label, status and duration through logger `citizen.api`. Unknown paths are labeled `unmatched`; bodies, query strings, raw unknown paths, keys, IPs and personal details are not logged. Validation errors do not echo invalid payloads. Disable Uvicorn access logs with `--no-access-log` as shown, since generic server logs may include URLs. Error responses omit database paths and SQL details. Responses use `Cache-Control: no-store`. Metadata is printed to the server console by the `citizen.api` logger; no request log file is created by this project.

A timeout/lost response is **not confirmed failure**: registration might have committed. Check the operator dashboard before retrying. A retry will hit the phone rule rather than insert a second record, but it is not an idempotency-key protocol.

Do not expose this demo publicly. Real deployment needs HTTPS, stronger authentication, scoped record permissions, tenant isolation, rate limits, upstream body/read timeouts, key rotation, encrypted storage/backups, consent/legal review, audit controls and privacy safeguards against enumeration. A key holder can infer that a submitted phone exists; this is why keys must be restricted. SQLite is plain text data, not encrypted by SHA-256. Matching remains O(n) and pair scanning O(n²). Protect the dashboard separately before any network exposure.

## Tests

```bash
# macOS/Linux
.venv/bin/python -m pytest -q
# Windows
.venv\Scripts\python -m pytest -q
```

Tests use temporary databases and fictional data, never your saved registry. They cover auth, health, exact/fuzzy parity, field validation, request-size enforcement including streamed bodies, safe errors/logging, transaction races, shared-phone rejection and concurrency, legacy data preservation, dashboard flow and separate-client clear/review/error branches.
