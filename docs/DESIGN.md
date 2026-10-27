# Design notes

## Flow

```text
Four input fields
    -> required/date/phone validation
    -> display cleanup and normalized comparison values
    -> stable sorted JSON -> SHA-256 -> indexed exact lookup
    -> RapidFuzz screening of remaining records
    -> existing normalized phone: block new registration
    -> no candidates: preview then save
    -> candidates: cancel OR review + reason + explicit separate-record save
    -> transaction rechecks matches before INSERT
```

The review screen scans unordered pairs, shows matching fields and weighted scores, and saves a human decision. It does not modify citizen details.

## Tables

`citizens(id, full_name, dob, phone, address, fingerprint, created_at, review_note, aadhaar_ref, licence_ref)`

- `id`: primary key.
- `fingerprint`: indexed, not unique.
- `created_at`: ISO UTC timestamp.

`reviews(first_id, second_id, decision, note, reviewed_at)`

- Sorted pair IDs form a compound primary key.
- Foreign keys refer to citizen records.
- Decisions are either Confirmed duplicate or Distinct records.

`settings(key, value)`

- Holds the one-time demo-loaded flag.

## Practical choices

A few short Python modules keep the project explainable. There is no account system, upload workflow or trained model. An optional authenticated FastAPI interface reuses the same engine and SQLite registry. Pandas presents tables; SQLite owns permanent data. The interface has one sidebar and four screens, neutral surfaces, a blue action color, navy sidebar, highlighted home/dashboard and clickable-name profiles and explicit empty states.

The exact fingerprint ignores letter casing and repeated whitespace, but does not remove address punctuation or guess abbreviations. The fuzzy rule handles some of those differences. No country-code inference is performed.

Optional document references must start with DEMO-AAD- or DEMO-DL-. They are fictional display metadata, excluded from matching. A lightweight schema migration adds these columns to earlier local databases.


## API extension

`citizen/matching.py` is shared by dashboard and API. `citizen/service.py` maps its real match results into field explanations without stored personal details. API and dashboard share `citizen/config.py` and `Registry`. No schema change or second database was needed. NewMatchesError carries the candidates computed under the write lock so a 409 cannot be based on a stale second query.

A user-requested exact-phone business rule now prevents new registrations with an existing normalized phone, even if the other details differ or a fuzzy review was acknowledged. It runs under the same BEGIN IMMEDIATE lock, preserving pre-existing duplicate data. The separate explicit fictional demo loader retains its intentionally duplicated fixtures. No UI or API edits/deletes existing records.

The API key authorizes the whole local registry. No role/tenant isolation is implied. The separate sample client only calls HTTP; human review requests are downloadable local handoffs, not a notification service. See API.md for contracts and limits.

## Same-name screening update

After Exact and Probable checks, equality of normalized full names yields a separate Name review category. Scores remain unchanged. Candidate reasons, API enum and dashboard counts distinguish this lower-confidence trigger. The pair scanner discovers earlier saved pairs without rewriting records; saved human decisions still suppress pending counts. Phone blocking retains precedence.
