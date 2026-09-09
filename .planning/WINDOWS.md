---
schema_version: 1
open_count: 1
waived_count: 0
fixed_count: 0
total_count: 1
last_updated: 2026-09-09T19:51:35.763Z
---

# Broken Windows Ledger

> Cross-phase defect register. With `workflow.windows_enforce` enabled, `/gsd-ship` blocks while `open_count > 0`.
> Waive with `gsd-tools windows waive <id> "<reason>"` (reason required).
> Mark fixed with `gsd-tools windows fixed <id>`.

| id | phase | kind | file | line | description | status | reason | recorded_at | resolved_at |
|----|-------|------|------|------|-------------|--------|--------|-------------|-------------|
| 1 | 01 | deviation | app.py |  | Task 1 acceptance criterion 'grep -c VALID_ACC app.py reports 1' is structurally unsatisfiable within this plan's declared scope: run_mlos_qc (relocates in plan 04) still uses VALID_ACC in app.py, so grep -c reports 2 (import line + usage line), same as the pre-refactor baseline. | open |  | 2026-09-09T19:51:35.763Z |  |

````json
[
  {
    "id": 1,
    "kind": "deviation",
    "phase": "01",
    "file": "app.py",
    "line": null,
    "description": "Task 1 acceptance criterion 'grep -c VALID_ACC app.py reports 1' is structurally unsatisfiable within this plan's declared scope: run_mlos_qc (relocates in plan 04) still uses VALID_ACC in app.py, so grep -c reports 2 (import line + usage line), same as the pre-refactor baseline.",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-09-09T19:51:35.763Z",
    "resolved_at": null
  }
]
````
