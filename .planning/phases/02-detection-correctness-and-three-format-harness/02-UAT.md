---
status: complete
phase: 02-detection-correctness-and-three-format-harness
source: [02-VERIFICATION.md]
started: 2026-09-10T18:22:41Z
updated: 2026-09-10T18:35:24Z
---

## Current Test

[testing complete]

## Tests

### 1. Generated eha_guid is stable across a rerun, the download and a same-session re-upload
expected: Upload an MLoS file containing at least one row whose eha_guid is not a valid UUID. Click Run QC, open the Auto Correct tab, note the generated identifier and the rows-fixed count. Trigger a rerun by interacting with any widget (for example change a filter on the Raw Data tab). Download the auto-corrected Excel file. Re-upload the identical file and click Run QC again in the same session. The identifier and the rows-fixed count are unchanged after the rerun, the downloaded file carries the same identifier the screen showed, and the re-upload reproduces the same identifier.
result: pass

## Summary

total: 1
passed: 1
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps
