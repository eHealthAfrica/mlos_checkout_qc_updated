# Phase 5: Submission Record - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-12
**Phase:** 5-Submission Record
**Areas discussed:** Record contents, Write path and timing, Officer-facing feedback, Dataset repo layout

---

## Record contents

**Q1. How should the record identify the officer who ran the check?**

| Option | Description | Selected |
|--------|-------------|----------|
| Email only (Recommended) | The Workspace email Phase 4's domain gate already verified; names drift | ✓ |
| Email plus display name | Adds the Google display name; slight redundancy | |
| Everything current_officer returns | Email, name and domain; domain is always the same today | |

**User's choice:** Email only.

**Q2. How much of the QC result goes into each record beyond the verdict sentence and weighted score?**

| Option | Description | Selected |
|--------|-------------|----------|
| Per-layer summary (Recommended) | Verdict, score, achievable max, plus per layer checks run / failing / distinct issue rows, read from QcSummary | ✓ |
| Verdict and score only | The five required fields and nothing else | |
| Full per-check list | Every rule identifier with pass/fail; schema frozen forever and grows with each layer | |

**User's choice:** Per-layer summary.

**Q3. How should the record identify the file that was checked?**

| Option | Description | Selected |
|--------|-------------|----------|
| Filename plus sha256 (Recommended) | Name plus the Phase 2 content hash | |
| Filename, sha256, row counts and Takeoffpoint file | Adds MLoS and Takeoffpoint row counts and the separate Takeoffpoint file's name and hash | ✓ |
| Filename only | Just the uploaded name | |

**User's choice:** Filename, sha256, row counts and Takeoffpoint file. Chose more than the recommendation.

**Q4. Which provenance fields should every record carry?**

| Option | Description | Selected |
|--------|-------------|----------|
| Schema version and app version (Recommended) | record_schema integer plus the app version from a VERSION constant | ✓ |
| Schema version only | Just the integer | |
| Neither | Data fields only | |

**User's choice:** Schema version and app version.

---

## Write path and timing

**Q1. How should each record reach the Dataset repo?**

| Option | Description | Selected |
|--------|-------------|----------|
| Direct upload per record, background thread (Recommended) | One commit per record the moment QC completes; nothing on the ephemeral disk | ✓ |
| CommitScheduler batched pushes | The roadmap note's suggestion; records buffered locally and pushed on an interval | |
| Direct upload, synchronous before rendering the verdict | Simplest but delays the verdict, which AUDIT-05 forbids | |

**User's choice:** Direct upload per record from a background thread.
**Notes:** This supersedes the ROADMAP.md Phase 5 Notes' `CommitScheduler` suggestion. The one-file-per-submission shape stays.

**Q2. When exactly does a record fire?**

| Option | Description | Selected |
|--------|-------------|----------|
| Every fresh QC run (Recommended) | Once inside the branch that runs the layers; never in the cached branch | ✓ |
| First run per file per session only | Keyed on sha256; hides repeat runs | |
| Only when the officer generates the report or sends the email | Ties the record to an explicit action | |

**User's choice:** Every fresh QC run.

**Q3. If the upload fails or the Hub is slow, what should the background writer do?**

| Option | Description | Selected |
|--------|-------------|----------|
| Bounded retries then give up (Recommended) | A few attempts with backoff, about a minute total, then log and stop | ✓ |
| Single attempt only | One call, success or not | |
| Persistent retry queue on disk | Retry until it lands; reintroduces the ephemeral buffer | |

**User's choice:** Bounded retries then give up.

**Q4. What counts as the AUDIT-03 concurrency proof?**

| Option | Description | Selected |
|--------|-------------|----------|
| Live test against a throwaway repo at a checkpoint (Recommended) | pytest test skipping without a token; concurrent writers against a disposable private repo; run once live, output recorded | ✓ |
| Unit test with a fake Hub only | Never touches the real Hub | |
| Manual two-browser check only | Not repeatable | |

**User's choice:** Live test against a throwaway repo at a checkpoint.

---

## Officer-facing feedback

**Q1. What does the officer see about their submission record?**

| Option | Description | Selected |
|--------|-------------|----------|
| Quiet status line, three states (Recommended) | Recording / recorded / could not be saved, verdict unaffected; updates on next interaction | ✓ |
| Silent on success, notice only on failure | Warning only when the writer gave up | |
| Fully silent | Server log only | |

**User's choice:** Quiet status line, three states.

**Q2. When the write token or repo name is not configured, what should the app do?**

| Option | Description | Selected |
|--------|-------------|----------|
| Visible banner, QC still runs, nothing recorded (Recommended) | Mirrors the Phase 4 bypass banner | ✓ |
| Stop the app with a clear message | Matches Phase 4 D-03's rigour for auth | |
| Silent skip | No banner, no record | |

**User's choice:** Visible banner, QC still runs, nothing recorded.

**Q3. Where should the record's identifier appear so a filed report can be matched to its log entry?**

| Option | Description | Selected |
|--------|-------------|----------|
| Report cover and email footer (Recommended) | Printed beside generated-at on the cover and in the email | ✓ |
| On screen only | Status line only | |
| Nowhere visible | Only in the repo | |

**User's choice:** Report cover and email footer.

**Q4. When the writer gives up on a record, who learns besides the officer's status line?**

| Option | Description | Selected |
|--------|-------------|----------|
| Server-side log only (Recommended) | Record id and error class to Space stdout; never contents | ✓ |
| Also a line in the QC email | Footer says saved / not saved | |
| Nobody else | No trace beyond the screen | |

**User's choice:** Server-side log only.

---

## Dataset repo layout

**Q1. Who owns the private Dataset repo that holds the log?**

| Option | Description | Selected |
|--------|-------------|----------|
| An eHealth Africa organisation on Hugging Face (Recommended) | Survives staff changes; collaborator list reviewable | ✓ |
| Your personal Hugging Face account | Fastest today; depends on one person's account | |

**User's choice:** An eHealth Africa organisation on Hugging Face.

**Q2. How should record files be arranged inside the repo?**

| Option | Description | Selected |
|--------|-------------|----------|
| Year/month folders (Recommended) | records/YYYY/MM/ from the record's UTC timestamp | ✓ |
| One flat folder | Grows without bound | |
| Per-state folders | State not reliably known at record time | |

**User's choice:** Year/month folders.

**Q3. What should each record file be named?**

| Option | Description | Selected |
|--------|-------------|----------|
| UTC timestamp then UUID (Recommended) | Sorts chronologically, collision-free, stem is the record id | ✓ |
| UUID only | Random listing order | |
| File sha256 then timestamp | Leaks a content hash into the path; can collide | |

**User's choice:** UTC timestamp then UUID.

**Q4. How should the app receive the write credential and the repo name?**

| Option | Description | Selected |
|--------|-------------|----------|
| Fine-grained token plus repo-id secret (Recommended) | Single-repo write token and repo id as two Space secrets | ✓ |
| Classic write token, repo id in code | User-wide token; moving the log means a deploy | |

**User's choice:** Fine-grained token plus repo-id secret.

---

## Claude's Discretion

- Append-only guard mechanics for AUDIT-04 (create-only uploader, AST no-delete test, token scope as second line).
- Module boundary: pure record builder versus thin uploader; which module imports `huggingface_hub`.
- Exact JSON key names, status-line and banner wording, `VERSION` constant location, retry schedule, thread implementation.
- Whether the Dataset repo carries a README describing the record schema.
- Confirming the new writer stays inside Phase 4's no-upload-persistence guard.

## Deferred Ideas

- Querying or charting the log inside the app (already v2 with longitudinal comparison).
- `CommitScheduler` batched pushes, as a fallback if volume grows.
- A saved / not-saved line in the QC email.
- Officer display name or domain in the record.
- Per-state folders in the repo.
- Stopping the app when recording is unconfigured.
