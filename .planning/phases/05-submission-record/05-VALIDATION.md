---
phase: "5"
slug: "submission-record"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-09-12"
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (`pytest>=8.0.0,<10.0.0`, Phase 1 pin — already installed) |
| **Config file** | `pytest.ini` at the repository root (`testpaths = tests`, `python_files = test_*.py`) |
| **Quick run command** | `python3 -m pytest tests/test_submission_record_end_to_end.py tests/test_submission_record_builder.py tests/test_submission_record_path.py -q` |
| **Full suite command** | `python3 -m pytest tests/ -q` |
| **Estimated runtime** | ~45 seconds full suite; under 20 seconds for any per-task quick run (the retry test uses an injected clock and never sleeps) |

---

## Sampling Rate

- **After every task commit:** Run that task's `<automated>` commands (see map below)
- **After every plan wave:** Run `python3 -m pytest tests/ -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 45 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 5-01-01 | 01 | 1 | AUDIT-02 | T-05-SC | The one new dependency is the genuine Hugging Face client, confirmed by a human before install | checkpoint (blocking-human) | — (human gate; no automated command) | n/a | ⬜ pending |
| 5-01-02 | 01 | 1 | AUDIT-01, AUDIT-02, AUDIT-05 | T-05-01 / T-05-03 / T-05-05 | Token passed explicitly, upload off the render path, no stale parent-commit keyword | unit + AST | `python3 -m pytest tests/test_submission_record_end_to_end.py -q` | ❌ W0 | ⬜ pending |
| 5-01-02 | 01 | 1 | AUDIT-02 | T-05-SC | Dependency declared with both bounds and the installed version inside them | unit | `python3 -m pytest tests/test_environment_pins.py tests/test_no_streamlit_in_qc.py -q` | ✅ | ⬜ pending |
| 5-01-02 | 01 | 1 | AUDIT-05 | T-05-03 / T-05-05 | Exactly one fire site; worker reaches neither the UI framework nor the secrets surface | AST | `python3 -c '...fire-site count, worker attribute scan, parent-commit absence...'` (full command in plan) | n/a | ⬜ pending |
| 5-01-03 | 01 | 1 | AUDIT-01 | T-05-02 | Record carries the email only; every layer present; score survives JSON unchanged | unit | `python3 -m pytest tests/test_submission_record_builder.py tests/test_submission_record_path.py -q` | ❌ W0 | ⬜ pending |
| 5-02-01 | 02 | 2 | AUDIT-05 | T-05-08 / T-05-09 / T-05-10 / T-05-12 | Bounded retry on an injected clock, no escaping exception, failure line carries id and error class only, no on-disk queue | unit (fakes + injected clock) | `python3 -m pytest tests/test_uploader_retry_and_thread.py -q --durations=3` | ❌ W0 | ⬜ pending |
| 5-02-02 | 02 | 2 | AUDIT-04 | T-05-11 | The cached replay branch calls nothing in this phase's modules; the fire site is flag-guarded | AST guard + synthetic self-test | `python3 -m pytest tests/test_no_fire_on_cached_rerun.py -q` | ❌ W0 | ⬜ pending |
| 5-02-03 | 02 | 2 | AUDIT-04 | T-05-07 | No tracked application source deletes a repo file, folder or repo, or uploads to a literal path | standing AST guard | `python3 -m pytest tests/test_no_delete_in_submission_log.py -q` | ❌ W0 | ⬜ pending |
| 5-02-03 | 02 | 2 | AUDIT-04 | T-05-07 | The guard is non-vacuous — it scanned at least 20 files and reported zero offenders | guard-of-the-guard | `python3 -c 'import sys; sys.path.insert(0,"tests"); import test_no_delete_in_submission_log as g; ...'` (full command in plan) | ❌ W0 | ⬜ pending |
| 5-03-01 | 03 | 3 | AUDIT-05 | T-05-13 / T-05-14 | Three quiet states worded once; a missing secret raises a persistent named banner | unit + AST | `python3 -m pytest tests/test_recording_status_surfaces.py -q` | ❌ W0 | ⬜ pending |
| 5-03-02 | 03 | 3 | AUDIT-01 | T-05-13 / T-05-15 | Record id on the workbook cover and in the email footer; stated placeholder when absent | unit | `python3 -m pytest tests/test_submission_record_id_threading.py tests/test_report_workbook_shape.py tests/test_email_body.py -q` | ❌ W0 (new file) / ✅ (two existing) | ⬜ pending |
| 5-03-03 | 03 | 3 | AUDIT-02 | T-05-16 / T-05-17 | Both secret names documented with no value; documented record keys match the shipped record | doc check + standing scan | `python3 -m pytest tests/test_no_committed_secrets.py tests/test_readme_columns_match_domain.py -q` | ✅ | ⬜ pending |
| 5-04-01 | 04 | 4 | AUDIT-03 | T-05-20 / T-05-21 | Live test skips cleanly without credentials; test credential distinct from the production one; one removal call, in a `finally` | integration (skip-clean) + AST | `env -u MLOS_TEST_HF_TOKEN -u MLOS_TEST_HF_NAMESPACE python3 -m pytest tests/test_audit03_concurrent_writes.py -q -rs` | ❌ W0 | ⬜ pending |
| 5-04-02 | 04 | 4 | AUDIT-02 | T-05-18 / T-05-19 / T-05-24 | Org-owned private Dataset repo, fine-grained single-repo token, collaborator list recorded | checkpoint (blocking-human) | — (human gate; no automated command) | n/a | ⬜ pending |
| 5-04-03 | 04 | 4 | AUDIT-03 | T-05-22 / T-05-23 | Concurrency proven against the real Hub, output kept verbatim, synthetic payloads only | **live, human-gated** | `python3 -m pytest tests/test_audit03_concurrent_writes.py -q -rs` (run once by a human with live credentials) | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Every test file below is created inside the task that needs it — this phase has no separate Wave 0
plan, because each new test file is authored alongside the code it covers and no task's
`<automated>` command references a file another task was supposed to create.

- [ ] `tests/test_submission_record_end_to_end.py` — AUDIT-01/02/05 tracer proof (created in 5-01-02)
- [ ] `tests/test_submission_record_builder.py` — AUDIT-01, D-01 to D-04 (created in 5-01-03)
- [ ] `tests/test_submission_record_path.py` — AUDIT-02, D-14 (created in 5-01-03)
- [ ] `tests/test_uploader_retry_and_thread.py` — AUDIT-05, D-05 to D-07, D-12 (created in 5-02-01)
- [ ] `tests/test_no_fire_on_cached_rerun.py` — D-06 (created in 5-02-02)
- [ ] `tests/test_no_delete_in_submission_log.py` — AUDIT-04, D-16 (created in 5-02-03)
- [ ] `tests/test_recording_status_surfaces.py` — AUDIT-05, D-09, D-10 (created in 5-03-01)
- [ ] `tests/test_submission_record_id_threading.py` — AUDIT-01, D-11 (created in 5-03-02)
- [ ] `tests/test_audit03_concurrent_writes.py` — AUDIT-03, D-08 (created in 5-04-01)
- [x] Framework install — none needed; pytest is already present and configured

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| The one new dependency is the genuine, maintained Hugging Face client | AUDIT-02 | A legitimacy verdict is a trust judgement about an external registry; it is never auto-approvable and must happen before install | Plan 05-01 Task 1: check `pypi.org/project/huggingface-hub/` for the source repo link, the multi-year release history and the maintainer, then approve or reject |
| The Dataset repo exists, is owned by an eHealth Africa organisation, and reads Private on the repo itself | AUDIT-02, D-13 | Repo creation, ownership and visibility live in a Hugging Face account no automated task may reach or fabricate | Plan 05-04 Task 2, steps 1-8 |
| The production token is fine-grained and scoped to that one repo | D-15 | Token scope is set in a web console and is not observable from the test suite | Plan 05-04 Task 2, step 5 |
| Two simultaneous submissions both land, against the real Hub | AUDIT-03 | The Hub's server-side commit behaviour under a genuine sub-second burst cannot be established from documentation or from a double; ROADMAP names this an M2 launch gate | Plan 05-04 Task 3: export the two test variables, run `python3 -m pytest tests/test_audit03_concurrent_writes.py -q -rs`, paste the complete output |
| The deployed Space shows no not-configured banner once both secrets are set | D-10 | Confirms the two secrets resolved in the real Space environment, which local runs cannot show | Plan 05-04 Task 2 verification: load the Space and confirm the banner is absent |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or are human gates with no automatable equivalent
- [x] Sampling continuity: no 3 consecutive tasks without automated verify (the only consecutive pair without one is 5-04-02 and 5-04-03, and 5-04-03 carries a live command)
- [x] Wave 0 covers all MISSING references — every new test file is created by the task that uses it
- [x] No watch-mode flags
- [x] Feedback latency < 45s
- [ ] `nyquist_compliant: true` set in frontmatter — pending `/gsd-validate-phase`

**Approval:** pending
