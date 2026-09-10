---
status: complete
phase: 03-verdict-and-report-integrity
source: [03-VERIFICATION.md]
started: 2026-09-10T21:05:39Z
updated: 2026-09-10T21:11:13Z
---

## Current Test

[testing complete]

## Tests

### 1. Upload a real submission (any format) and visually confirm the on-screen metric bar, verdict banner, Tab 2 sco
expected: Metric bar shows checks_run/n_pass/n_fail/headline_distinct/pct_pass/weighted_score; banner shows the D-04 verdict sentence; Tab 2's score table shows n/a Layer Pass Rate and a numeric 0.0% Weighted Contribution for any unrun layer; colour band matches the capped score.
result: pass

### 2. Upload a .csv MLoS export with no separate Takeoffpoint file, open the Generate Report tab, and confirm the fi
expected: All five layers appear on the card; Takeoffpoint shows the not-run reason instead of counts; the on-screen combined table and the workbook's QC Summary sheet agree row for row.
result: pass

### 3. Skim the rewritten README §8 (Weighted QC Score), §10 (Generate & Download Report) and §11 (Send QC Email) for
expected: Sections read clearly to an officer and accurately describe the shipped behaviour.
result: pass

## Summary

total: 3
passed: 3
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps
