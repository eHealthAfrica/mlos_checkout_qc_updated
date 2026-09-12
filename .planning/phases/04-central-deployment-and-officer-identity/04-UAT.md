---
status: complete
phase: 04-central-deployment-and-officer-identity
source: [04-01-SUMMARY.md, 04-02-SUMMARY.md, 04-03-SUMMARY.md]
started: 2026-09-12T08:34:00Z
updated: 2026-09-12T08:36:59Z
---

## Current Test

[testing complete]

## Tests

### 1. Auth secrets materialise and the five-outcome login gate precedes the uploader (04-01 D1)
expected: Flat Space env vars render into a deterministic .streamlit/secrets.toml [auth] table before any Streamlit call; require_login() resolves any visitor into exactly one of unconfigured/bypass/signin/refused/allowed and gates app.py's sidebar and uploader.
result: pass
source: automated
coverage_id: D1
covered_by: tests/test_secrets_materializer.py (9), tests/test_auth_domain.py (21), tests/test_auth_gate.py (38), AST statement-order check on app.py

### 2. The three stopping branches render the required content and never a file uploader (04-01 D2)
expected: Unconfigured branch names the missing variables and the bypass variable; bypass branch warns naming MLOS_AUTH_DISABLED; refusal page shows the secrets-sourced contact with a neutral fallback.
result: pass
source: automated
coverage_id: D2
covered_by: tests/test_auth_gate.py (four named branch tests)

### 3. No password storage and no upload persistence (04-01 D3)
expected: No tracked source file accepts or stores a password-typed input; the SMTP credential never leaves send_qc_email; load_submission leaves no new file on disk.
result: pass
source: automated
coverage_id: D3
covered_by: tests/test_no_password_storage.py (3), tests/test_no_upload_persistence.py

### 4. Recipients from Space secrets, Send button disabled with a stated reason (04-02 D1)
expected: SMTP_TO/SMTP_CC are read through auth.secret via get_recipients with whitespace-tolerant, de-duplicated parsing; Send is disabled with a visible reason when SMTP_TO is empty; send_qc_email raises before any SMTP connection.
result: pass
source: automated
coverage_id: D1
covered_by: tests/test_smtp_recipients.py (13), AST check on app.py literals

### 5. No organisational address in any tracked file, standing scan in place (04-02 D2)
expected: README.md and 04-RESEARCH.md redacted by pattern; tests/test_no_committed_secrets.py fails the build if an organisational address, a generic address in shipped Python, or a secret-shaped literal returns, with non-vacuous scope proven.
result: pass
source: automated
coverage_id: D2
covered_by: tests/test_no_committed_secrets.py (10), live scan of 161 tracked files / 53 .py files

### 6. 04-01 credential-scope guard still holds after the recipient rework (04-02 D3)
expected: smtp_pass is referenced only inside send_qc_email; app.py keeps CRLF line endings.
result: pass
source: automated
coverage_id: D3
covered_by: tests/test_no_password_storage.py, tests/test_no_streamlit_in_qc.py, tests/test_auth_gate.py

### 7. Space front matter present with sdk_version and hf_oauth provably absent (04-03 D1)
expected: README.md opens with sdk: streamlit, python_version "3.11", app_file: app.py, pinned: false, and neither forbidden key.
result: pass
source: automated
coverage_id: D1
covered_by: tests/test_space_metadata.py (12)

### 8. README Hugging Face Spaces section names every secret, the direct address rule, and idle sleep (04-03 D2)
expected: Section replaces Streamlit Cloud; lists every secret by name only; explains the public-at-platform posture; gives the cookie-secret command and redirect-URI shape; requires the direct *.hf.space address; states the 48-hour sleep.
result: pass
source: automated
coverage_id: D2
covered_by: README content check, tests/test_no_committed_secrets.py (10)

### 9. Planning and instruction docs no longer promise a platform-private Space (04-03 D3)
expected: REQUIREMENTS.md, ROADMAP.md, PROJECT.md and .claude/CLAUDE.md use the public-Space, app-gated wording; every private Dataset-repo mention untouched; the two Privacy constraint lines byte-identical.
result: pass
source: automated
coverage_id: D3
covered_by: regex and line-equality checks, full suite 334 passed at plan close

## Commit Claim Reconciliation

- 04-01-SUMMARY.md: no plan_head_before field (pre-#3968 legacy). Git shows 6 commits scoped (04-01) against a declared 5, consistent under the plus-one rule (the metadata commit lands after measurement). WARNING only, because the base field is absent.
- 04-02-SUMMARY.md: plan_head_before 83887cb, declared 6, measured 6 up to its last commit e992130. Consistent.
- 04-03-SUMMARY.md: plan_head_before e992130, declared 3, measured 5 up to its last commit 8fa9515: three task commits plus two docs commits (SUMMARY, then STATE/ROADMAP). All five accounted for; nothing uncommitted or lost. Recorded as a note, not a blocker.

## Summary

total: 9
passed: 9
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

[none yet]
