# Phase 2: Detection Correctness and Three-Format Harness - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-10
**Phase:** 2-Detection Correctness and Three-Format Harness
**Areas discussed:** Blank-side match reporting, Column normalisation scope, Snapshot + eha_guid determinism, Boundary fallback visibility

Four areas were offered and all four selected. A fifth cluster (golden fixture construction,
ENGINE-06) was offered twice and declined both times as largely settled by the requirement text.

---

## Blank-side match reporting (INTEG-02)

### Q1 — How should a blank that can no longer satisfy a cross-table match be reported?

| Option | Description | Selected |
|--------|-------------|----------|
| Same rule ID, reason column | Blank fails the existing rule; detail row gains a column distinguishing blank from mismatch. No new identifiers. | |
| Same rule ID only | Blank simply fails R2/R3/R4/TP2/TP3/TP4. Smallest change. | |
| New registered findings | Six new identifiers separate "nothing to match on" from "no match found". Costs 6 registry entries, sidebar updates, 6 Excel sheets. | ✓ |

**User's choice:** New registered findings
**Notes:** Chose the sharpest signal despite the highest cost. A blank is a data-entry gap and a mismatch is a reconciliation problem — different fixes for the officer.

### Q2 — What should the six new identifiers be called?

| Option | Description | Selected |
|--------|-------------|----------|
| `2.blank` / `TP2.blank` | Reason-named; "blank" is unambiguous about the data state. | |
| `2.missing` / `TP2.missing` | Same shape, matching vocabulary already in use — Rule 1 "Not Null", B0 "Not Available on Data", INTEG-01 "missing required fields". | ✓ |
| `2.takeoffpoint` / `TP2.name` | Strictly field-named per Phase 1's D-01, but redundant since R2 already means takeoffpoint. | |

**User's choice:** `2.missing` / `TP2.missing`
**Notes:** Vocabulary consistency across the rule set was the deciding factor. Longest resulting Excel sheet name `Rule TP2.missing` is 16 chars, inside the 31-char limit.

### Q3 — A blank `ward_code` will fire Rule 1, `4.missing` and B0. Acceptable?

| Option | Description | Selected |
|--------|-------------|----------|
| Report independently | Each layer reports what it sees. Phase 3's VERDICT-04 already fixes row totals. | ✓ |
| Suppress overlap | `4.missing` excludes rows already failing Rule 1 or B0. Cleaner summary, but a check's outcome depends on which other layers ran. | |

**User's choice:** Report independently (recommended)
**Notes:** The decisive argument was that suppression makes `4.missing` read PASS for a row with no ward code at all, and couples layers in the way Phase 1's seam exists to prevent.

### Q4 — What counts as an absent value?

| Option | Description | Selected |
|--------|-------------|----------|
| Null, empty, whitespace | Three states, no content inspection. Cannot collide with "NA" or any domain value. **Recommended.** | |
| Also known null sentinels | Adds case-insensitive `null`, `none`, `n/a`, `nan`, `-`. Catches stringified nulls; decides absence by reading content. | ✓ |

**User's choice:** Also known null sentinels — **chosen against the recommendation**
**Notes:** Deliberate. Recorded in CONTEXT.md as a stated deviation with the risk named, so the planner does not quietly narrow it back. Requires the sentinel list and the `"NA"` exemption to be a version-controlled constant with a standing test.

### Q5 — Uniform sentinel list, or restricted on the domain columns?

| Option | Description | Selected |
|--------|-------------|----------|
| Restrict on the domain columns | Flag columns, urban/rural/scattered and `state_code` use null/empty/whitespace only; rules 11/12 judge their validity. Nasarawa survives by construction. **Recommended.** | |
| Uniform list, exempt `"NA"` only | One predicate everywhere, single case-sensitive exemption. Simplest to test; `highrisk = "N/A"` becomes missing rather than a rule 12 failure. | ✓ |

**User's choice:** Uniform list, exempt `"NA"` only — **chosen against the recommendation**
**Notes:** Second consecutive deviation in the same area. The `"NA"` exemption is now the only thing keeping a genuine Nasarawa submission's `state_code` from reading as missing, which CONTEXT.md records as one-way for real data.

### Q6 — Which table's blanks does each `.missing` finding report?

| Option | Description | Selected |
|--------|-------------|----------|
| Own subject table | `2.missing` reports MLoS rows, `TP2.missing` reports Takeoffpoint rows; both sides covered by the pair. Detail frames stay single-table. | ✓ |
| Both sides per rule | One finding tells the whole story of a join, but detail frames must mix two tables with different identifying columns. | |

**User's choice:** Own subject table (recommended)
**Notes:** Preserves the one-table-per-detail-frame invariant that the drilldown, longitudinal view and Excel sheet builder all assume.

### Q7 — Should `2.missing` / `3.missing` / `4.missing` run with no Takeoffpoint table?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — single-table checks | They test MLoS's own columns and emit unconditionally. Real added coverage for CSV submissions, which today get no cross-table checking. | ✓ |
| No — keep each pair together | A rule and its blank-variant always appear or vanish together. Simpler, but a blank `takeoffpoint` in a CSV is reported nowhere. | |

**User's choice:** Yes — single-table checks (recommended)
**Notes:** The Takeoffpoint-side trio still runs only when that table exists, so zero rows never reports PASS.

---

## Column normalisation scope (INTEG-03)

### Q1 — How far should load-time normalisation go?

| Option | Description | Selected |
|--------|-------------|----------|
| Strip + lowercase, spaces→underscores | Purely typographic; handles the common `Ward Code` .xlsx case. No semantic guessing. | ✓ |
| Strip + lowercase only | Exactly what S1 already assumes. Smallest change; `Ward Code` still fails S1 and skips rules, but consistently. | |
| Add a known-alias map | Typographic plus `wardcd`→`ward_code`, `lat`→`latitude`. Most files pass, but infers intent from a name. | |

**User's choice:** Strip + lowercase, spaces→underscores (recommended)
**Notes:** Alias mapping recorded as a deferred idea rather than rejected outright — revisit with evidence of which aliases officers actually submit.

### Q2 — Canonical target vocabulary (user directive, not a menu)

**User's instruction, verbatim:** "change all the column name to match the preloaded column in the readme.md"

**Verification performed during discussion:** README.md's "Required MLoS Columns (43)" and "Required Takeoffpoint Columns (4)" tables were parsed and compared against `qc/domain.py`'s `MLOS_REQUIRED_COLS` and `TAKEOFF_REQUIRED_COLS`. Result: 43 and 4 names respectively, **zero drift in either direction**, all already lowercase snake_case. No reconciliation work needed before planning.

**Outcome:** README.md becomes a canonical reference with authority over column naming (D-20 in CONTEXT.md). A future divergence between README.md and `qc/domain.py` is to be treated as a defect.

### Q3 — A header normalises to something not in README's 47 names. Rename anyway?

| Option | Description | Selected |
|--------|-------------|----------|
| Rename only into the canonical set | Renames only when the result is one of the 47; everything else keeps the officer's exact header. Literal reading of "match the preloaded column". **Recommended.** | |
| Rename every header | Uniform snake_case across the whole frame, no set-membership test. Rewrites columns no rule reads. | ✓ |

**User's choice:** Rename every header — chosen against the recommendation
**Notes:** README's 47 names remain the authority on what is *required*; the transform is applied uniformly regardless.

### Q4 — Two headers normalise to the same label. What happens?

| Option | Description | Selected |
|--------|-------------|----------|
| Fail a registered check, leave the pair alone | New `S3` fails naming both original headers; colliding pair left un-normalised so no duplicate label is created. Nothing guessed, dropped or crashed. | ✓ |
| Suffix the duplicates | `ward_code` / `ward_code__2`; nothing lost, QC completes, but column order decides which is validated. | |
| Keep the first, drop the rest | Simplest frame downstream, but removes an officer's column from the submission entirely. | |

**User's choice:** Fail a registered check, leave the pair alone (recommended)
**Notes:** Must be handled either way — duplicate labels make `mlos["ward_code"]` return a DataFrame, so the next `.astype(str).str.strip()` raises. `S3` is free; the Schema layer holds only `S1`/`S2`.

### Q5 — Where does the officer see which columns were renamed?

| Option | Description | Selected |
|--------|-------------|----------|
| On-screen panel + report sheet | Expander listing only real changes, plus a "Columns Renamed" sheet so the record travels with the file. No Pass/Fail, no score impact. | ✓ |
| On-screen only | Smallest change; report builder untouched. Rename record doesn't survive the download. | |
| Screen + report sheet + email | Most complete, but overlaps Phase 3's email work (VERDICT-03). | |

**User's choice:** On-screen panel + report sheet (recommended)
**Notes:** Constraint that shaped the options: a rename is not a defect, and Advisory severity (ADVIS-01) is Phase 6, so a check row would have to read PASS or FAIL — neither of which is true of "I renamed three headers."

---

## Snapshot + eha_guid determinism (ENGINE-03, ENGINE-04)

### Q1 — What should a generated `eha_guid` derive from?

| Option | Description | Selected |
|--------|-------------|----------|
| Content hash — UUIDv5 over row identity | Same settlement, same ID forever — across sessions, machines and re-uploads. Reproducible and verifiable; makes v2 HIST-01's churn detection meaningful. **Recommended.** | |
| Cached random UUID per submission | `uuid4()` once per submission, reused for every render and the download. Satisfies success criterion 4 literally; stable only within the session. | ✓ |
| UUIDv5 over filename + row index | Deterministic but re-keys on row insertion and collides on duplicate filenames. | |

**User's choice:** Cached random UUID per submission — chosen against the recommendation
**Notes:** Accepted consequence recorded in CONTEXT.md: the same file uploaded next month, by a colleague, or after a Space restart mints different IDs, so an ID cited in a filed report cannot be regenerated. Rated one-way. A cheap middle option — seeding the generator from the D-13 content hash — was noted as a deferred idea rather than pressed.

### Q2 — What identifies "one submission" for the cached snapshot?

| Option | Description | Selected |
|--------|-------------|----------|
| Content hash of the uploaded bytes | sha256 over both uploads. Identical bytes → same snapshot; two different files can never collide. | ✓ |
| Keep filename + size | No change; two submissions sharing a name and byte size collide, and the second officer sees the first's results. | |
| Filename + size + last-modified | Cheaper than hashing, but Streamlit's UploadedFile does not reliably expose mtime. | |

**User's choice:** Content hash of the uploaded bytes (recommended)
**Notes:** Templated monthly exports (`mlos_checkout.xlsx`) made the collision concrete. Side benefit noted at the time: within a session, a byte-identical re-upload now hits the same snapshot, confining D-12's drift to across sessions.

### Q3 — One corrected frame in session state, or both raw and corrected?

| Option | Description | Selected |
|--------|-------------|----------|
| One corrected snapshot only | Correction runs inside the load-and-cache step; no uncorrected frame survives. Divergence structurally impossible; halves peak memory. **Recommended.** | |
| Keep both, explicitly labelled | `mlos_raw` / `mlos_corrected` under separate keys, one rule about which is read where. Auditable as-submitted record inside the report. | ✓ |

**User's choice:** Keep both, explicitly labelled — chosen against the recommendation
**Notes:** User wanted the as-submitted record recoverable from the report itself. Accepted costs recorded: two versions coexist (the condition F4 arose from) and peak memory doubles on the free-tier Space where SQ4 is quadratic and the report builder is memory-hungry.

### Q4 — How do we stop a future edit handing a QC layer the raw frame again?

| Option | Description | Selected |
|--------|-------------|----------|
| AST standing test over app.py | Distinct names plus a test parsing `app.py` to pin every consumer to `mlos_corrected`, with `mlos_raw` at exactly one call site. Reuses Phase 1's established idiom. | ✓ |
| Introduce `qc.run_all(snapshot, on_step=...)` | One entry point, one frame; progress preserved via callback. Stronger guarantee, but overturns Phase 1's explicit choice and enlarges the diff into orchestration. | |

**User's choice:** AST standing test over `app.py` (recommended)
**Notes:** Phase 1 declined a `run_all()` façade at `qc/__init__.py:10` with stated reasoning about interleaved progress reporting. That decision stands; CONTEXT.md instructs the planner not to introduce it as an improvement.

---

## Boundary fallback visibility (INTEG-04)

### Q1 — How should the national-set fallback reach the officer, and what happens to B1?

| Option | Description | Selected |
|--------|-------------|----------|
| New B4 fails; B1 still runs, scope stated | B4 fails on widening; B1 keeps running because a code absent from even the national set is a true finding. B3 independently catches the cross-state case. | ✓ |
| New B4 fails; B1 withheld entirely | Strictest reading of "no check passes because a value was absent", but 12 genuinely invalid ward codes go unreported. | |
| Third return value + UI warning only | Cleanest separation, no forced Pass/Fail, but changes the signature and every call site, and the warning doesn't reach the report or email. | |

**User's choice:** New B4 fails; B1 still runs, scope stated (recommended)
**Notes:** Two findings surfaced while checking the code and are recorded in CONTEXT.md — the fallback widens **B2 as well as B1** (`filtered_bbox` is reassigned at `qc/boundary.py:91`), which is wider than INTEG-04's wording; and B3 already covers most of the blind spot, making the fallback a trust problem rather than a total detection hole.

### Q2 — Should B4 emit on every run, or only when the fallback fires?

| Option | Description | Selected |
|--------|-------------|----------|
| Always emit | PASS naming the state's ward count, FAIL naming the widening. Matches every other check's behaviour; absence of a row would carry no information. | ✓ |
| Only on fallback | Quieter on the common path, but the check's absence could mean "fine" or "not implemented". | |

**User's choice:** Always emit (recommended)
**Notes:** Noted that canonical boundary order becomes B0, B1, B2, B3, B4 — consistent with Phase 3's VERDICT-06.

### Q3 — What should B4 report when the reference is missing entirely?

Raised by the user selecting "More on boundary fallback" at the wrap-up gate. Investigation showed this was not a separate concern but a hole D-17 would open: with the reference files absent, the fallback branch never fires (it is guarded on `not ref_df.empty`), so B4 as specified would report **PASS — "validated against N wards"** when there are no wards at all.

| Option | Description | Selected |
|--------|-------------|----------|
| One B4, two failure modes | Fails on either condition with a description naming which. One identifier, one concept. **Recommended.** | |
| Two identifiers: B4 widened, B5 unavailable | Each check answers exactly one question; two registry entries and two Excel sheets, both PASS on a normal run. | ✓ |
| B4 covers widening only | Narrow to INTEG-04's literal text; leave the missing-reference case to Phase 3's VERDICT-05. | |

**User's choice:** Two identifiers: B4 widened, B5 unavailable — chosen against the recommendation
**Notes:** The selected preview itself flagged that B4 would "still be misleading unless separately guarded", which drove the follow-up question below.

### Q4 — With B5 reporting the unavailable reference, what does B4 do in that run?

| Option | Description | Selected |
|--------|-------------|----------|
| B4 not emitted | No reference means no scope to describe; B5 carries the whole story. Follows B0's early-return precedent. | ✓ |
| B4 fails too | Constant boundary-section shape, but one cause counted as two failing checks. | |

**User's choice:** B4 not emitted (recommended)
**Notes:** Closes the false-PASS uncovered in Q3. Canonical boundary order is B0, B1, B2, B3, B4, B5.

---

## Claude's Discretion

- Which of the four load paths normalisation covers — MLoS, same-file Takeoffpoint, separately uploaded Takeoffpoint (`app.py:520`), bundled boundary reference CSVs (`app.py:290`). Raised at the wrap-up gate for this area and explicitly left to the planner. Constraint: it must be the same single helper wherever applied.
- `Failing Rows` / `Total Rows` for the run-level checks `S3`, `B4` and `B5`. `S1`/`S2` set a non-row-denominator precedent.
- Where the absence predicate and sentinel constant live (`qc/predicates.py` / `qc/domain.py` suggested; names are the planner's).
- Golden fixture construction (ENGINE-06) — declined as a discussion area twice. Strong recommendation recorded in CONTEXT.md: round-trip through the real loaders, because a fixture that synthesises frames directly cannot catch INTEG-01.
- `_NOT_NULL_COLS` membership is explicitly **not** open for revision — the PostgreSQL schema defines that set.

## Deferred Ideas

- Nearest non-matching candidate suggestion on cross-table mismatch detail rows — a fuzzy-matching reconciliation aid, its own phase.
- Known-alias column map (`wardcd`→`ward_code`, `lat`→`latitude`) — rejected here; revisit with evidence of real submissions.
- Content-derived `eha_guid` (UUIDv5), or seeding the generator from the D-13 content hash — revisit alongside v2's HIST-01.
- Telling the officer that generated `eha_guid` values are session-scoped — raised at a wrap-up gate and not taken up.
- B2's unmatched-bounding-box silent pass (`qc/boundary.py:155`) — same defect family, belongs with Phase 7's GEO-01/GEO-03.
- Missing-boundary-reference *scoring* (as distinct from visibility) — Phase 3's VERDICT-05.
- `qc.run_all()` façade — declined, consistent with Phase 1's documented reasoning.
