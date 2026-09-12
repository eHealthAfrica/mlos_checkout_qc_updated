# Phase 5: Submission Record - Context

**Gathered:** 2026-09-12
**Status:** Ready for planning

<domain>
## Phase Boundary

After every completed QC run, the application writes one JSON record naming the officer, the
time, the file and the verdict to a **private Hugging Face Dataset repo**, one file per
submission, never edited or deleted, and never delaying the verdict the officer sees. Two
officers submitting at the same moment both get their record. When the record cannot be
written, the officer is told plainly and the verdict is unaffected.

It delivers **no querying, no dashboard, no longitudinal comparison and no access
segregation**. The log is an append-only record, not a database: reading it back inside the
app is out of scope (PROJECT.md Out of Scope; FEATURES.md anti-features). Threshold
configuration and new QC layers are Phases 6 and 7.

Requirements closed: AUDIT-01, AUDIT-02, AUDIT-03, AUDIT-04, AUDIT-05.

</domain>

<decisions>
## Implementation Decisions

### Record Contents (AUDIT-01)

- **D-01:** The officer is identified by **Workspace email only**, read through
  `auth.current_officer()["email"]` (the accessor Phase 4 built for this log; nothing else may
  read `st.user`). Display name and domain were offered and not chosen: the email is the
  identity Phase 4's domain gate verified, and names drift.
- **D-02:** Beyond the verdict, each record carries a **per-layer summary read from the shared
  `QcSummary`**: the verdict sentence (`verdict_text`), the weighted score, the achievable
  maximum, and for each of the five layers its checks run, checks failing and distinct issue
  rows (null where the layer has no source row count, as Schema does; a layer that did not run
  appears with zero checks, so the record can never look like a four-layer tool). The record
  **never recomputes** anything the summary already derives. The full per-check list and a
  bare verdict-and-score record were offered and not chosen. — **Reversibility:** costly — the
  log is append-only, so every record ever written keeps this shape; a change means bumping
  `record_schema` (D-04) and every future reader handling both shapes.
- **D-03:** The file is identified by its **uploaded filename, the sha256 Phase 2 already
  computes over the uploaded bytes (`_file_sha256`), the MLoS row count, the Takeoffpoint row
  count, and, when a separate Takeoffpoint file was uploaded, that file's filename and sha256**
  (null otherwise). A renamed file is therefore visibly the same file, and "did they supply
  Takeoffpoint" is answerable without re-running.
- **D-04:** Every record carries a **`record_schema` integer (starting at 1) and the app version
  that produced it**, read from a `VERSION` constant in the repository — the Space exposes no
  git sha. A reader of an old record knows how to parse it and which rule set ran. Records also
  carry their UTC timestamp in ISO 8601.

### Write Path and Timing (AUDIT-02, AUDIT-03, AUDIT-05)

- **D-05:** Each record is **uploaded directly as its own commit from a background thread** the
  moment the QC run completes, using `huggingface_hub`. Nothing is buffered on the Space's
  ephemeral disk, and "the record exists" is true as soon as the thread's upload returns.

  *Recorded deviation:* the ROADMAP.md Phase 5 Notes suggested `CommitScheduler` watching a
  local folder. It was presented and **not chosen**: records sitting in its buffer between
  pushes are lost when the Space rebuilds or is killed, and at tens of runs a day the per-commit
  cost it saves is negligible. The planner must not revert to it as the "documented" path.
  The one-file-per-submission shape the Notes fix **stays**; only the delivery mechanism changes.
- **D-06:** A record **fires exactly once per fresh QC run**, inside the branch of `app.py` that
  actually runs the five layers and populates session state, and **never in the cached branch**
  that replays results on a tab switch or rerun. Pressing Run again on the same file is a new run
  and a new record; that is what "each completed QC run" means.
- **D-07:** On a failed or slow upload the writer makes **a few bounded retries with backoff,
  about a minute in total, then gives up**: it logs server-side (D-12) and stops. No on-disk
  retry queue (it would reintroduce the buffer D-05 rejected), no unbounded thread, no exception
  ever reaches the officer's page. The thread must be a daemon so it cannot hold the process.
- **D-08:** AUDIT-03 is a **launch gate**, proven by a pytest test that **skips when no write
  token is present**, spawns many concurrent writers against a **disposable private Dataset
  repo**, then lists the repo and asserts every record landed with a distinct path. It is run
  live once at a `checkpoint:human-action` (`blocking-human`) and its output recorded in the plan
  summary. Network-free unit tests cover record building and filename uniqueness. A fake-Hub-only
  test and a manual two-browser check were offered and not chosen. The disposable repo is the
  test's to create and remove; the **application** code must still contain no delete path (D-16).

### Officer-Facing Feedback (AUDIT-05)

- **D-09:** The officer sees a **quiet three-state status line near the verdict banner**:
  recording in progress, recorded, or could not be saved with the words "your verdict is
  unaffected". Because the write is in a background thread, the line updates on the officer's
  next interaction rather than live. It never blocks and never changes the verdict, score or
  report. Silent success and fully silent were offered and not chosen.
- **D-10:** When the write token or repo id is **not configured** (developer laptop, or a Space
  secret left unset), the app shows a **persistent visible banner** that submission recording is
  not configured, **QC still runs, and nothing is recorded**. This mirrors Phase 4 D-03's bypass
  banner: honest locally, and on the Space the banner is the tell that a secret is missing.
  Stopping the app and a silent skip were offered and not chosen.
- **D-11:** The **record id (the JSON filename stem, D-14) is printed on the workbook cover
  beside the generated-at line and in the QC email footer**, so a filed report can be traced to
  exactly one log entry. The id is minted before the upload starts, so it is always known
  regardless of the upload's outcome. Both surfaces already read from the shared summary path
  Phase 3 built; the planner threads the id through that path rather than adding a second one.
- **D-12:** When the writer gives up, **only the Space's server-side log learns of it**: the
  record id and the error class, never the record's contents. No line in the QC email; the data
  team reads Space logs when an officer reports a failed status line.

### Dataset Repo Layout (AUDIT-02, AUDIT-04)

- **D-13:** The log lives in a **private Dataset repo owned by an eHealth Africa organisation on
  Hugging Face**, not a personal account, so it survives staff changes and its collaborator list
  can be reviewed at each milestone as PITFALLS.md asks. **A human creates the repo** at a
  `checkpoint:human-action` (`blocking-human`); no task may create it, name it in code, or
  fabricate its id. — **Reversibility:** costly — moving the log later means either migrating
  history into a new repo or reading two repos forever.
- **D-14:** Records are stored at **`records/YYYY/MM/<UTC compact timestamp>_<uuid4>.json`**,
  the partition derived from the record's own UTC timestamp, for example
  `records/2026/09/20260912T101530Z_3f2a….json`. Any one folder stays in the hundreds, listings
  sort chronologically, concurrent writers cannot collide, and the filename stem is the record id
  the officer sees (D-11). A flat folder, per-state folders, UUID-only names and sha256-led names
  were offered and not chosen. — **Reversibility:** costly — records already written keep their
  paths (the log is append-only), so a later layout change leaves two layouts coexisting.
- **D-15:** The app receives a **fine-grained Hugging Face token with write access to that one
  Dataset repo only, plus the repo id, as two Space secrets**, read through the same `auth.secret`
  surface as every other credential and never committed. Secret names are the planner's choice
  (for example `MLOS_LOG_TOKEN`, `MLOS_LOG_REPO`) and must be added to README §Hugging Face
  Spaces and to the Phase 4 no-committed-secrets guard's awareness. A user-wide classic token
  with a hard-coded repo id was offered and not chosen.

### Claude's Discretion

- **D-16:** Append-only guard (AUDIT-04) — the application must offer no path to edit or delete a
  record. Strongly recommended: the uploader is create-only with unique names, and a standing
  AST test in the Phases 1 to 4 idiom asserts that tracked application source contains no call
  that deletes or overwrites repo content (`delete_file`, `delete_folder`, `delete_repo`, delete
  operations inside `create_commit`, or an upload to an existing path). Token scope (D-15) is the
  second line of defence, not the first.
- **Module boundary.** Following `qc/` and `auth.py` precedent: a pure, Streamlit-free record
  builder (record dict, record id, repo path) unit-tested without a network, and a thin uploader
  that is the only module importing `huggingface_hub`. Whether the uploader lives in `auth.py`'s
  sibling or its own thin module is the planner's call. The record must be built from the
  `QcSummary` object and `auth.current_officer()`, not from session state scraps.
- **New dependency.** `huggingface_hub>=1.30.0,<2.0.0` per `.planning/research/STACK.md`,
  pinned with an upper bound, with the Phase 1 package-legitimacy checkpoint precedent applied.
- **Exact JSON key names, status-line wording, banner wording, the `VERSION` constant's
  location and maintenance, the retry schedule, and the thread implementation.**
- **The no-upload-persistence guard.** Phase 4's standing test asserts no upload is written to
  disk outside the request. The record writer uploads from memory (D-05) and must stay inside
  that guard; the planner confirms the guard's scope covers the new module.
- **Whether the Dataset repo carries a README** describing the record schema. Recommended, and
  it is not a record, so writing it once does not violate AUDIT-04.
- **An officer navigating away while the upload is in flight.** The daemon thread completes on
  its own; nothing further is required beyond the status line reflecting the outcome on return.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope and requirements
- `.planning/ROADMAP.md` — Phase 5 section: goal, five success criteria, the Notes paragraph
  (one file per submission; the `CommitScheduler` suggestion superseded by D-05); the "M2 launch
  gates" paragraph naming AUDIT-03's concurrent-write test as pre-rollout
- `.planning/REQUIREMENTS.md` — AUDIT-01 to AUDIT-05; the Out of Scope rows on an external
  managed database and on longitudinal comparison, which bound this phase to an append-only log
- `.planning/PROJECT.md` — Storage, Privacy and Configuration constraints; Key Decision "Private
  HF Dataset repo for the submission log"; Out of Scope on the external database and the
  queryable dashboard
- `.planning/STATE.md` — the open Phase 4 blocker on the data-governance sign-off (D-06 there):
  real settlement files still wait on it; this phase's live tests use synthetic fixtures only

### Prior-phase decisions this phase inherits
- `.planning/phases/04-central-deployment-and-officer-identity/04-CONTEXT.md` — D-01 (Google
  identity is what the log records as "who"), D-03 (visible-banner bypass pattern reused by
  D-10), D-06 (governance sign-off gates real data), D-07 (secrets pattern reused by D-15), D-09
  (Space public, Dataset repo private — the scope boundary), and the code_context note that
  Phase 5 reads identity through one accessor
- `.planning/phases/02-detection-correctness-and-three-format-harness/02-CONTEXT.md` — D-12
  (generated `eha_guid` is session-scoped and must not key anything durable) and D-13 to D-15
  (submission identity is a sha256 over uploaded bytes)
- `.planning/phases/03-verdict-and-report-integrity/03-CONTEXT.md` — the one shared `QcSummary`
  and the rule that no presentation site recomputes verdict, score or counts

### Technical grounding
- `.planning/research/STACK.md` — the `huggingface_hub>=1.30.0,<2.0.0` pin; the
  "Alternatives Considered" row comparing `CommitScheduler` with direct `upload_file` /
  `create_commit`, which D-05 resolves in favour of direct upload
- `.planning/research/ARCHITECTURE.md` — the submission-log module sketch and the
  "fire-and-forget relative to the verdict" principle; the note not to introduce an abstract
  audit-sink interface for a single implementation
- `.planning/research/PITFALLS.md` — the Dataset repo is a git repo, not a database: serialise
  or isolate writes (one file per submission); verify the Dataset repo's private visibility
  independently of the Space's; review the repo's collaborator list at each milestone
- `.planning/research/FEATURES.md` — attribution row and append-only history as table stakes;
  the cross-state dashboard as an anti-feature deferred with longitudinal comparison
- `https://huggingface.co/docs/huggingface_hub/` — `HfApi.upload_file` / `create_commit`,
  fine-grained token scopes, and Dataset repo behaviour under concurrent commits; fetch current
  versions during research

### Subject code
- `auth.py` — `current_officer()` (the only permitted identity source) and `secret()` (the
  secrets surface D-15 reuses)
- `qc/report.py` — `QcSummary`, `LayerSummary`, `build_summary`, `summary_rows` and
  `build_email_subject_and_body`: the record reads from these, and the record id (D-11) travels
  through the same path to the workbook cover and the email
- `app.py` — `_file_sha256` / `_submission_identity` (D-03's hashes); the fresh-run branch that
  populates session state after Step 5 of 5 (D-06's only trigger point); the `summary =
  qc.report.build_summary(...)` site; `send_qc_email`; the verdict banner region where D-09's
  status line sits
- `tests/test_no_streamlit_in_qc.py`, `tests/test_no_committed_secrets.py`,
  `tests/test_no_upload_persistence.py` — the guard-of-the-guard AST idiom for D-16, and the
  two existing guards the new module must stay inside
- `requirements.txt` — add the pinned `huggingface_hub`; keep every existing pin
- `README.md` — §Hugging Face Spaces secrets list to extend with the two new secrets (D-15) and
  a note on the log's location and shape

**No external ADRs or specs exist** for this project.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `auth.current_officer()` returns `{"email", "name", "domain"}` or `None`; it was written for
  this phase and is the sole identity accessor.
- `qc.report.QcSummary` already exposes `verdict_text`, `weighted_score`, `achievable_max`,
  per-layer `LayerSummary` objects with checks and `source_row_count`, and `count_failing`;
  the record is a projection of this object.
- `app._file_sha256` and `_submission_identity` compute the sha256 digests D-03 needs, once,
  in the sidebar.
- `auth.secret()` reads Space secrets uniformly; Phase 4's `mail_config` shows the shape of a
  small pure config reader over it.
- The AST standing-test idiom (Phases 1 to 4) fits D-16's no-delete guard directly.

### Established Patterns
- `qc/` stays Streamlit-free and network-free at import; Streamlit- or network-touching code
  lives in `app.py` or a thin module. The record builder is pure; only the uploader imports
  `huggingface_hub`.
- Anything derived on one branch of the cache if/else is F4's shape; the record must be built
  from the same `summary` object both branches converge on, but **fired** only from the
  fresh-run branch (D-06).
- Configuration that must change without a deploy lives in Space secrets (D-15 follows D-07).
- Blocking-human gates for facts only a human can establish: the repo's creation (D-13) and
  the live concurrency run (D-08), as Phase 4 did for the OAuth client and the Space.
- New dependencies are pinned with an upper bound and pass a package-legitimacy checkpoint
  (Phase 1 precedent).

### Integration Points
- The record fires at the end of the fresh-run branch in `app.py`, immediately after the five
  `(checks, detail)` pairs are stored in session state and before or as `summary` is built;
  the thread is handed the finished `summary`, the officer email and the file identity.
- The record id reaches the workbook cover and the email footer through `qc/report.py`'s
  existing builders (a new keyword parameter defaulting to `None`, as `column_renames` did in
  Phase 2, keeps existing callers and tests working).
- The status line (D-09) and the unconfigured banner (D-10) render near the verdict banner and
  are driven by session state keyed on the record id.
- README §Hugging Face Spaces and the no-committed-secrets guard gain the two new secret names.

</code_context>

<specifics>
## Specific Ideas

- The record must be traceable from paper: a report on someone's desk carries the record id,
  and the id is a filename in the repo (D-11, D-14).
- Nothing about the log may quietly do nothing: an unset secret shows a banner, a failed write
  shows a status line, and a run is never logged twice from a cached replay.
- The concurrency proof must touch the real Hub once, with the output kept, before rollout.
- The organisation, not a person, owns the audit history.

</specifics>

<deferred>
## Deferred Ideas

- **Querying or charting the log inside the app** (pass rates by state, national rollup) —
  already deferred to v2 with longitudinal comparison; both need the append-only log turned into
  a queryable store (PROJECT.md, FEATURES.md).
- **`CommitScheduler` batched pushes** — offered, not chosen; remains the fallback if submission
  volume ever makes one commit per run costly.
- **A "submission record: saved / not saved" line in the QC email** — offered, not chosen;
  revisit if the data team cannot read Space logs.
- **Officer display name or domain in the record** — offered, not chosen; additive if ever
  wanted, with a `record_schema` bump.
- **Per-state folders in the repo** — offered, not chosen; the state is not reliably known at
  record time.
- **Stopping the app when recording is unconfigured** — offered, not chosen; D-10 prefers the
  banner. Revisit if an unlogged run on the deployed Space is ever judged unacceptable.

</deferred>

---

*Phase: 5-Submission Record*
*Context gathered: 2026-09-12*
