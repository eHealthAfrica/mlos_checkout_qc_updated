---
phase: 04-central-deployment-and-officer-identity
plan: 03
subsystem: deploy
tags: [hugging-face-spaces, readme, front-matter, docs-correction, d-09]

# Dependency graph
requires:
  - phase: 04-02 (SMTP recipients from Space secrets)
    provides: "qc.mail_config / app.py::get_recipients — the SMTP_TO/SMTP_CC secrets this plan documents in README §Deployment"
  - phase: 04-01 (Google login gate)
    provides: "auth.py's AUTH_ENV_KEYS/CONTACT_ENV_VAR/BYPASS_ENV_VAR — the secrets this plan documents in README §Deployment"
provides:
  - "README.md Hugging Face Space front matter (sdk: streamlit, python_version 3.11, app_file app.py) the platform supervisor reads to build and launch the Space"
  - "tests/test_space_metadata.py — standing parser + assertions on required/forbidden front-matter keys"
  - "README.md § Hugging Face Spaces — the secrets table, the public-Space-is-deliberate rationale, the direct-URL requirement, and the idle-sleep note"
  - "REQUIREMENTS.md, ROADMAP.md, PROJECT.md, .claude/CLAUDE.md corrected to the D-09 public-Space-with-app-gate wording, with every private-Dataset-repo mention left untouched"
affects: [04-04, 04-05, 04-06]

# Actuals (#2632)
actuals:
  tokens: 5334
  tasks: 3
  commits: 3
plan_head_before: e9921308b2789c6a86b12d0b9b449f8c26429cff

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Flat key: value front-matter parser (no YAML dependency) for an eight-line Hugging Face Space metadata block, mirroring qc/ modules' avoidance of a new runtime dependency for a small, flat-structured need."
    - "Classify-before-touch wording sweep: a lowercase adjective search across four documents partitioned into an edit set and a do-not-touch set before any edit, verified afterward by an exact per-file occurrence count plus a following-context regex — catches both a missed edit and an accidental Dataset-repo change with one command."

key-files:
  created:
    - tests/test_space_metadata.py
  modified:
    - README.md
    - .planning/REQUIREMENTS.md
    - .planning/ROADMAP.md
    - .planning/PROJECT.md
    - .claude/CLAUDE.md

key-decisions:
  - "Native streamlit SDK chosen over docker in the front matter, per STACK.md: the Docker SDK does not receive the XSRF/cookie workaround st.file_uploader needs inside the platform's iframe."
  - "sdk_version and hf_oauth kept provably absent from the front matter (asserted by tests/test_space_metadata.py) — requirements.txt stays the single source of truth for the Streamlit version, and native HF OAuth was researched and declined per D-01."
  - "README §Deployment documents every secret by variable name only, never by value — the data-team contact and the two recipient lists are named, not typed, so the standing tests/test_no_committed_secrets.py scan has nothing new to catch."
  - "Task 3's wording sweep treated the private HF Dataset repo (Phase 5's submission log) as an explicit non-edit target in seven of the fourteen 'private' occurrences found before editing, verified by the exact per-file post-edit counts ([2, 1, 3, 1]) matching the plan's own numbers."

requirements-completed: [DEPLOY-01, DEPLOY-04]

coverage:
  - id: D1
    description: "README.md opens with a Hugging Face Space front-matter block (sdk: streamlit, python_version \"3.11\", app_file: app.py, pinned: false) with sdk_version and hf_oauth both provably absent, asserted by a new standing test."
    requirement: "DEPLOY-01"
    verification:
      - kind: unit
        ref: "tests/test_space_metadata.py -- 12 tests (front matter parsing, required keys/values, both forbidden keys absent), plus tests/test_readme_columns_match_domain.py unaffected"
        status: pass
      - kind: other
        ref: "python3 -c one-liner: parse_front_matter() returns sdk=streamlit, python_version='3.11', app_file='app.py', sdk_version and hf_oauth both absent; README.md read(3) == '---'"
        status: pass
    human_judgment: false
  - id: D2
    description: "README §Hugging Face Spaces replaces §Streamlit Cloud: names every secret the app reads (four auth env keys, the contact variable, the bypass variable, both SMTP recipient variables, four SMTP credential keys), states the Space is deliberately public at the platform level with the app-level Google gate as the real control, gives the cookie-secret generation command, names the redirect-URI shape, requires the direct *.hf.space address over the huggingface.co/spaces embed, and states the 48-hour idle-sleep behaviour. How to Run Locally now names the dev opt-out variable."
    requirement: "DEPLOY-04"
    verification:
      - kind: unit
        ref: "python3 -c one-liner checking every required variable name, 'hf.space', 'huggingface.co/spaces', '## Hugging Face Spaces' present and '## Streamlit Cloud' absent in README.md"
        status: pass
      - kind: unit
        ref: "tests/test_no_committed_secrets.py -- 10 tests (no address literal introduced by the rewrite)"
        status: pass
    human_judgment: false
  - id: D3
    description: "REQUIREMENTS.md DEPLOY-01, ROADMAP.md's milestone narrative/Phase 4 index entry/Phase 4 success criterion 1, PROJECT.md's M2 checklist bullet and Privacy constraint, and .claude/CLAUDE.md's Privacy constraint no longer describe the Space as platform-private; every mention of the private Hugging Face Dataset repo (Phase 5's submission log) is untouched, and the two Privacy constraint lines are character-identical."
    requirement: "DEPLOY-01"
    verification:
      - kind: other
        ref: "python3 -c regex check: zero remaining 'private' occurrences NOT followed by 'HF Dataset'/'Hugging Face Dataset'; per-file counts exactly [2, 1, 3, 1] for REQUIREMENTS.md/ROADMAP.md/PROJECT.md/CLAUDE.md"
        status: pass
      - kind: other
        ref: "python3 -c line-equality check: PROJECT.md's and .claude/CLAUDE.md's '- **Privacy**' lines are byte-identical"
        status: pass
      - kind: unit
        ref: "python3 -m pytest tests/ -q -- 334 passed (full regression, no code changed)"
        status: pass
    human_judgment: false

duration: continuation (see Performance note)
completed: 2026-09-12
status: complete
---

# Phase 4 Plan 3: Space front matter, README §Deployment rewrite, and the D-09 wording sweep Summary

**README.md now carries a Hugging Face Space front-matter block the platform supervisor can build from, a §Hugging Face Spaces section that tells an operator every secret to set and an officer the direct address to use and why, and four planning/instruction documents no longer claim a platform-private Space that D-09 never shipped.**

## Performance

- **Duration:** continuation dispatch — Task 1 was committed (`daf8afc`) in a prior session that
  died before writing SUMMARY.md; this session verified Task 1 and executed Tasks 2 and 3. The
  wall-clock span from `daf8afc` (2026-09-11T17:32:07+01:00) to this SUMMARY
  (2026-09-12T08:18:38Z) spans a session gap, not continuous work; actual work in this session
  was well under an hour.
- **Started:** 2026-09-11T16:32:07Z (`daf8afc` commit time, UTC)
- **Completed:** 2026-09-12T08:18:38Z
- **Tasks:** 3 (1 verified from a prior session, 2 executed this session)
- **Files modified:** 6 (1 created, 5 modified)

## Accomplishments

- `README.md` opens with a Hugging Face Space front-matter block declaring the native `streamlit`
  SDK, the Python 3.11 floor, `app.py` as the entry point, and no `sdk_version`/`hf_oauth` keys —
  standing-tested by `tests/test_space_metadata.py` (12 tests).
- `README.md` §Hugging Face Spaces replaces the old §Streamlit Cloud section: every secret the
  app reads is named in a table (never by value), the Space's deliberate public-at-platform-level
  posture is explained alongside the not-found consequence of "fixing" it to private, the
  cookie-secret generation command is given, the redirect-URI shape is stated, officers are told
  to use the direct `*.hf.space` address and why the embed breaks sign-in, and the 48-hour
  idle-sleep behaviour is documented. §How to Run Locally now names the dev opt-out variable.
- Seven surgical wording edits across `REQUIREMENTS.md`, `ROADMAP.md`, `PROJECT.md` and
  `.claude/CLAUDE.md` replace platform-private Space language with the D-09 public-Space,
  app-gated wording; every mention of the private Hugging Face Dataset repo (Phase 5's submission
  log) was left untouched, verified by exact per-file occurrence counts and a following-context
  regex.

## Task Commits

Each task was committed atomically:

1. **Task 1: Space front matter, with the two keys that must stay absent** - `daf8afc` (feat) — committed in a prior session; re-verified in this session (see Deviations)
2. **Task 2: Rewrite README §Deployment for Hugging Face Spaces and the direct URL** - `f070e09` (docs)
3. **Task 3: Correct every document that still promises a platform-private Space** - `5ad5256` (docs)

**Plan metadata:** commit hash recorded after this SUMMARY is written (see completion report).

## Files Created/Modified

- `README.md` - Space front matter (Task 1) + §Hugging Face Spaces rewrite (Task 2)
- `tests/test_space_metadata.py` - standing front-matter parser/assertions (Task 1, new)
- `.planning/REQUIREMENTS.md` - DEPLOY-01 wording corrected (Task 3)
- `.planning/ROADMAP.md` - milestone narrative, Phase 4 index entry, Phase 4 success criterion 1 corrected (Task 3)
- `.planning/PROJECT.md` - M2 checklist bullet and Privacy constraint corrected (Task 3)
- `.claude/CLAUDE.md` - Privacy constraint corrected to mirror PROJECT.md (Task 3)

## Decisions Made

See `key-decisions` in frontmatter above. No new architectural decisions; this plan executed
CONTEXT.md's D-09 wording change and the planner's own Space-metadata discretion exactly as
specified.

## Deviations from Plan

None — plan executed exactly as written. Task 1's acceptance criteria (grep checks on the front
matter, `pytest tests/test_space_metadata.py tests/test_readme_columns_match_domain.py -q`, and
the `python3 -c` front-matter assertion one-liner) were all re-run in this session per the
continuation instructions and passed without needing any fix:

- `python3 -m pytest tests/test_space_metadata.py tests/test_readme_columns_match_domain.py -q` — 12 passed
- Front-matter one-liner — `front matter ok ['app_file', 'colorFrom', 'colorTo', 'emoji', 'pinned', 'python_version', 'sdk', 'short_description', 'title']`
- `grep -c 'streamlit' README.md` — 4 (SDK declaration line plus prose mentions only, no version number)

No second Task 1 commit was created.

## Issues Encountered

None. The prior session's die-off after `daf8afc` left no uncommitted work in the tree affecting
this plan's files — `git show --stat daf8afc` confirmed exactly `README.md` and
`tests/test_space_metadata.py` were touched, matching the continuation state's record.

## User Setup Required

None triggered in this plan. No secret value was read, fabricated, or committed — README
§Deployment names every secret by variable only.

## Next Phase Readiness

- Plan 04-04 (deploy the public Space, verify sign-in) can now build the Space directly from this
  repository's front matter and follow §Hugging Face Spaces for the secrets list and the
  direct-URL distribution requirement.
- Plan 04-06's history-rewrite checklist (D-08) is unaffected by this plan; no address literal was
  introduced anywhere in this plan's edits (`tests/test_no_committed_secrets.py` — 10 passed).
- No blockers.

## Self-Check: PASSED

- `README.md`, `tests/test_space_metadata.py`, `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md`,
  `.planning/PROJECT.md`, `.claude/CLAUDE.md` — all verified present on disk via `[ -f ]`.
- All three commit hashes (`daf8afc`, `f070e09`, `5ad5256`) verified present via
  `git log --oneline --all`.
- All plan-level `<acceptance_criteria>` re-run per task and passing (see per-task verify output
  above and in Deviations).
- Full plan `<verification>` block re-run: `python3 -m pytest tests/ -q` — 334 passed;
  `parse_front_matter()` returns the required keys/values with neither forbidden key;
  `README.md` starts with the front-matter delimiter at byte 0; every environment variable the
  app reads is named in §Deployment; every remaining lowercase visibility adjective in the four
  edited documents belongs to a Dataset-repo phrase at the exact per-file counts `[2, 1, 3, 1]`;
  the Privacy constraint line is character-identical in `.planning/PROJECT.md` and
  `.claude/CLAUDE.md`.

---
*Phase: 04-central-deployment-and-officer-identity*
*Completed: 2026-09-12*
