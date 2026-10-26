# Design notes

## Flow

```text
Four input fields
    -> required/date/phone validation
    -> display cleanup and normalized comparison values
    -> stable sorted JSON -> SHA-256 -> indexed exact lookup
    -> RapidFuzz screening of remaining records
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

A few short Python modules keep the project explainable. There is no unnecessary account system, upload workflow, API, trained model or framework beyond the requested stack. Pandas presents tables; SQLite owns permanent data. The interface has one sidebar and four screens, neutral surfaces, a blue action color, navy sidebar, highlighted home/dashboard and clickable-name profiles and explicit empty states.

The exact fingerprint ignores letter casing and repeated whitespace, but does not remove address punctuation or guess abbreviations. The fuzzy rule handles some of those differences. No country-code inference is performed.

Optional document references must start with DEMO-AAD- or DEMO-DL-. They are fictional display metadata, excluded from matching. A lightweight schema migration adds these columns to earlier local databases.

