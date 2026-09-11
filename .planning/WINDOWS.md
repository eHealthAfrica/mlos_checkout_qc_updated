---
schema_version: 1
open_count: 2
waived_count: 0
fixed_count: 1
total_count: 3
last_updated: 2026-09-11T15:57:11.334Z
---

# Broken Windows Ledger

> Cross-phase defect register. With `workflow.windows_enforce` enabled, `/gsd-ship` blocks while `open_count > 0`.
> Waive with `gsd-tools windows waive <id> "<reason>"` (reason required).
> Mark fixed with `gsd-tools windows fixed <id>`.

| id | phase | kind | file | line | description | status | reason | recorded_at | resolved_at |
|----|-------|------|------|------|-------------|--------|--------|-------------|-------------|
| 1 | 01 | deviation | app.py |  | Task 1 acceptance criterion 'grep -c VALID_ACC app.py reports 1' is structurally unsatisfiable within this plan's declared scope: run_mlos_qc (relocates in plan 04) still uses VALID_ACC in app.py, so grep -c reports 2 (import line + usage line), same as the pre-refactor baseline. | fixed |  | 2026-09-09T19:51:35.763Z | 2026-09-09T20:07:50.683Z |
| 2 | 04 | deviation | tests/test_no_upload_persistence.py |  | Plan 04-01 acceptance criteria assumed both load_submission frames are non-empty and the write-mode offender set is {auth.py} alone; actual golden-fixture/repo state has takeoff_df genuinely empty by design and a second pre-existing write-mode file (tests/baseline/capture_baseline.py) -- test asserts the real, documented shape instead. | open |  | 2026-09-11T15:57:11.211Z |  |
| 3 | 04 | deviation | auth.py |  | TDD RED-evidence tooling (gsd_run check tdd-red-evidence) parses Node --test TAP output only; this Python/pytest project's genuine RED phase for brand-new modules manifests as a collection-time ModuleNotFoundError, which the tool would classify INVALID_RED. Manual RED/GREEN confirmation was substituted (tests run against implementation temporarily removed, then restored) instead of invoking the tool. | open |  | 2026-09-11T15:57:11.334Z |  |

````json
[
  {
    "id": 1,
    "kind": "deviation",
    "phase": "01",
    "file": "app.py",
    "line": null,
    "description": "Task 1 acceptance criterion 'grep -c VALID_ACC app.py reports 1' is structurally unsatisfiable within this plan's declared scope: run_mlos_qc (relocates in plan 04) still uses VALID_ACC in app.py, so grep -c reports 2 (import line + usage line), same as the pre-refactor baseline.",
    "status": "fixed",
    "reason": "",
    "recorded_at": "2026-09-09T19:51:35.763Z",
    "resolved_at": "2026-09-09T20:07:50.683Z"
  },
  {
    "id": 2,
    "kind": "deviation",
    "phase": "04",
    "file": "tests/test_no_upload_persistence.py",
    "line": null,
    "description": "Plan 04-01 acceptance criteria assumed both load_submission frames are non-empty and the write-mode offender set is {auth.py} alone; actual golden-fixture/repo state has takeoff_df genuinely empty by design and a second pre-existing write-mode file (tests/baseline/capture_baseline.py) -- test asserts the real, documented shape instead.",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-09-11T15:57:11.211Z",
    "resolved_at": null
  },
  {
    "id": 3,
    "kind": "deviation",
    "phase": "04",
    "file": "auth.py",
    "line": null,
    "description": "TDD RED-evidence tooling (gsd_run check tdd-red-evidence) parses Node --test TAP output only; this Python/pytest project's genuine RED phase for brand-new modules manifests as a collection-time ModuleNotFoundError, which the tool would classify INVALID_RED. Manual RED/GREEN confirmation was substituted (tests run against implementation temporarily removed, then restored) instead of invoking the tool.",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-09-11T15:57:11.334Z",
    "resolved_at": null
  }
]
````
