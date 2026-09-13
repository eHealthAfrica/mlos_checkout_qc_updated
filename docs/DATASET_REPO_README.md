# MLoS Checkout QC — Submission Log

This repository is the **append-only submission log** for the MLoS Checkout QC tool. Every time
a state-level data officer runs a QC check on a settlement submission, the application writes one
JSON record here naming who ran it, when, which file, and the verdict. It is not a record of the
submitted settlement data itself — see the field table below for exactly what each record holds.

This README is not a record, and its own presence does not violate the log's append-only rule —
it is pasted here once, by a human, and is never written by the application.

## Path layout

Records live at:

```
records/YYYY/MM/<UTC compact timestamp>_<uuid4>.json
```

for example:

```
records/2026/09/20260912T101530Z_3f2a1c9d8e7b4a6f9c0d1e2f3a4b5c6d.json
```

The partition (`YYYY/MM`) is derived from the record's own `timestamp_utc` field, so a folder
listing sorts chronologically and any one month's folder stays in the low hundreds of files at
realistic submission volume. The filename stem (everything before `.json`) is the record's own
`record_id` — the same id printed on the QC tool's downloaded report cover and in its email
footer, so a filed report on someone's desk traces back to exactly one file in this repository.

## Append-only

This repository receives **create-only** writes: the application never edits, overwrites or
deletes a record once written, and it contains no code path to do either. A record that was never
written stays that way — nothing here is a placeholder for a submission that failed to log.

## Record shape

Every record is a flat JSON object. `record_schema` is the version of this shape — a reader
of an old record uses it to know how the rest of the object should be interpreted if this shape
ever changes (it is append-only, so a change adds a new schema version rather than rewriting
history). The table below lists every top-level key, in the order the application emits them:

| Key | Meaning |
|-----|---------|
| `record_schema` | Integer version of this record's shape. A future change to what a record carries bumps this rather than rewriting already-written records. |
| `app_version` | The QC tool's own version string at the time this record was written, so a reader knows which rule set produced the verdict below. |
| `record_id` | This record's own id — identical to the filename stem above. |
| `timestamp_utc` | ISO 8601 UTC timestamp of the QC run this record describes; also the source of the `YYYY/MM` path partition. |
| `officer_email` | The signed-in officer's Workspace email address, or `null` if the app was run without a signed-in officer. |
| `file` | The submitted file's identity: filename, sha256 digest, MLoS/Takeoffpoint row counts, and — when a separate Takeoffpoint file was supplied — that file's own filename and sha256, else `null`. |
| `verdict_text` | The exact verdict sentence the officer saw, copied verbatim from the QC run — never recomputed here. |
| `weighted_score` | The run's weighted QC score, copied verbatim from the QC run. |
| `achievable_max` | The score's achievable ceiling for that run (a layer that did not run contributes 0, not an inflated denominator). |
| `layers` | Per-layer summary keyed by layer name (Schema, MLoS, Settlement, Takeoffpoint, Boundary), each holding checks run, checks failing, and distinct issue rows (`null` where the layer has no source row count). Never the full per-check list and never a settlement-level detail row. |

No token, no repository id, no email address beyond the officer's own recorded above, and no real
settlement data (coordinates, population figures, settlement names) appears anywhere in this
README or in the shape it describes beyond what the field table states.
