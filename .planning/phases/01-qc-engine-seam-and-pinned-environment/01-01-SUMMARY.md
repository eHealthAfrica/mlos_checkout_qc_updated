---
phase: 01-qc-engine-seam-and-pinned-environment
plan: 01
subsystem: infra
tags: [pandas, numpy, pytest, requirements, pinning, dependency-management]

# Dependency graph
requires: []
provides:
  - "Pinned requirements.txt (pandas==3.0.5 exact, numpy/streamlit/openpyxl/xlrd upper-bounded)"
  - "requirements-dev.txt layering pytest on top of requirements.txt"
  - "pytest.ini so tests/ discovers with no CLI flags"
  - "tests/test_environment_pins.py — standing regression guard against pin drift"
affects: [02-qc-engine-seam-and-pinned-environment, 03-qc-engine-seam-and-pinned-environment, phase-04-deployment]

# Actuals (#2632)
actuals:
  tokens: 4200
  tasks: 2
  commits: 2

# Tech tracking
tech-stack:
  added: [pytest>=8.0.0,<10.0.0]
  patterns:
    - "requirements-dev.txt as -r include over requirements.txt to keep the runtime install lean"
    - "pytest.ini testpaths= convention for zero-flag discovery from repo root"

key-files:
  created:
    - requirements-dev.txt
    - pytest.ini
    - tests/test_environment_pins.py
  modified:
    - requirements.txt

key-decisions:
  - "Package-legitimacy checkpoint (pandas 3.0.5, numpy>=2.0.0,<3.0.0, pytest>=8.0.0,<10.0.0) approved-with-evidence by the human coordinator; all three SUS verdicts confirmed as PyPI metadata false positives — each package publishes a real GitHub repository (pandas-dev/pandas, numpy/numpy, pytest-dev/pytest), and the specific 'no-repository' signal was simply wrong."
  - "Created a project-local .venv (already listed in .gitignore before this plan ran) to work around macOS Homebrew's PEP 668 externally-managed-environment pip restriction on the local dev machine; this is a local install path only, not a new shipped project convention."
  - "Upper-bounded all four existing dependencies (streamlit, openpyxl, xlrd in addition to pandas/numpy), per RESEARCH.md's reading of ENGINE-07's general clause rather than its two literally-named packages."

patterns-established:
  - "Standing environment-pin test: parse requirements.txt relative to the test file's own directory (not CWD), assert exact-pin lines by string equality, and require a non-vacuous minimum count of examined dependency lines."

requirements-completed: [ENGINE-07]

coverage:
  - id: D1
    description: "requirements.txt pins pandas exactly to 3.0.5 and upper-bounds numpy, streamlit, openpyxl and xlrd so no dependency can silently resolve into an untested major version"
    requirement: "ENGINE-07"
    verification:
      - kind: unit
        ref: "tests/test_environment_pins.py#test_pandas_is_pinned_to_an_exact_version"
        status: pass
      - kind: unit
        ref: "tests/test_environment_pins.py#test_numpy_is_declared_with_both_bounds"
        status: pass
      - kind: unit
        ref: "tests/test_environment_pins.py#test_every_runtime_dependency_is_bounded"
        status: pass
      - kind: other
        ref: "python3 -c \"import pandas; print(pandas.__version__)\" -> 3.0.5"
        status: pass
    human_judgment: false
  - id: D2
    description: "requirements-dev.txt layers pytest>=8.0.0,<10.0.0 on top of requirements.txt via -r include, and pytest.ini configures testpaths=tests so `python3 -m pytest tests/ -q` discovers and runs the suite from the repo root with no extra flags"
    requirement: "ENGINE-07"
    verification:
      - kind: unit
        ref: "tests/test_environment_pins.py#test_pandas_installed_version_matches_the_pin"
        status: pass
      - kind: other
        ref: "python3 -m pytest tests/ -q -> 4 passed"
        status: pass
    human_judgment: false
  - id: D3
    description: "The standing test genuinely detects drift, not just passes vacuously: reverting the pandas pin to pandas>=3.0.0 makes test_pandas_is_pinned_to_an_exact_version and test_every_runtime_dependency_is_bounded fail; reverting the change restores 4 passed"
    verification:
      - kind: other
        ref: "manual mutation-and-revert run: 2 failed, 2 passed (mutated) -> 4 passed (reverted)"
        status: pass
    human_judgment: false

# Metrics
duration: 25min
completed: 2026-09-09
status: complete
---

# Phase 01 Plan 01: Pinned Environment and Pytest Harness Summary

**Exact-pinned pandas 3.0.5 with bounded numpy/streamlit/openpyxl/xlrd, a pytest harness with zero-flag discovery, and a standing test that fails the moment the resolved environment drifts from the declaration.**

## Performance

- **Duration:** 25 min
- **Started:** 2026-09-09T18:54:24Z
- **Completed:** 2026-09-09T19:19:31Z
- **Tasks:** 2 of 2 completed (plus 1 checkpoint:decision, approved)
- **Files modified:** 4 (1 modified, 3 created)

## Accomplishments
- `requirements.txt` now declares five dependencies, each either exactly pinned (`pandas==3.0.5`) or explicitly upper-bounded (`streamlit`, `numpy`, `openpyxl`, `xlrd`) — closing the silent-drift path that let the live environment resolve pandas 3.0.2 by accident.
- `requirements-dev.txt` and `pytest.ini` stand up the test harness (previously absent from this repo entirely) so `python3 -m pytest tests/ -q` runs from the repo root with no flags.
- `tests/test_environment_pins.py` is a standing regression guard: it fails immediately if the pandas pin loosens, if numpy loses either bound, or if any runtime dependency line becomes unbounded — verified by manual mutate-and-revert.

## Task Commits

Each task was committed atomically:

1. **Task 1: Pin the runtime dependency set and split out the test-only dependency** - `2a99e63` (feat)
2. **Task 2: Standing test that the resolved environment matches the declaration** - `e4c2ae5` (test)

**Plan metadata:** committed alongside this summary

_Note: Task 2 carried `tdd="true"`, but its "implementation" (the pins the test validates) was already produced by Task 1 — there was no separate GREEN-phase production code to write. The test was authored, run (green immediately, since Task 1 had already made the declaration correct), then proven to have real detection power via a manual mutate-pandas-line-and-revert cycle per the task's acceptance criteria, rather than a literal RED-before-implementation ordering._

## Files Created/Modified
- `requirements.txt` - rewritten with five bounded dependency declarations plus a leading comment recording pandas 3.0.5's `>=3.11` Python floor
- `requirements-dev.txt` - new; `-r requirements.txt` include plus `pytest>=8.0.0,<10.0.0`
- `pytest.ini` - new; `[pytest]` section with `testpaths = tests` and `python_files = test_*.py`
- `tests/test_environment_pins.py` - new; 4 tests asserting the pin declarations and the installed environment agree

## Decisions Made
- **Package-legitimacy checkpoint approved-with-evidence.** The coordinator independently verified all three flagged packages live against PyPI: pandas latest 3.0.5 (uploaded 2026-07-22, repository `github.com/pandas-dev/pandas`); numpy latest 2.5.3 (uploaded 2026-09-06, source `github.com/numpy/numpy`, inside the declared `>=2.0.0,<3.0.0` range); pytest latest 9.1.1 (uploaded 2026-06-19, source `github.com/pytest-dev/pytest`, inside the declared `>=8.0.0,<10.0.0` range). All three resolve to their genuine upstream projects — the `SUS` verdicts in `01-RESEARCH.md` were metadata false positives, and specifically the "no-repository" signal was simply wrong since every package publishes a repository URL.
- **Deployment-floor fact carried forward, not enforced here:** pandas 3.0.5 declares `requires-python: >=3.11`. The local dev interpreter is Python 3.13.1, so Task 1 installed cleanly, but this floor is a real constraint the Phase 4 Hugging Face Space Python-version selection must satisfy (research OQ1). No enforcement was added beyond what this plan specifies — this is a recorded fact for Phase 4, not a new check.
- Upper-bounded all four existing dependencies (not just pandas/numpy) per RESEARCH.md's reading of ENGINE-07's general clause.
- Kept `pytest` out of `requirements.txt` (separate `requirements-dev.txt`) to keep the eventual Space install lean, per RESEARCH.md's assumption A3.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking issue] macOS Homebrew Python refused `pip install` with `externally-managed-environment`**
- **Found during:** Task 1
- **Issue:** `python3 -m pip install -r requirements.txt -r requirements-dev.txt` failed immediately with PEP 668's `error: externally-managed-environment` — the system Python (Homebrew) refuses to let pip write into it directly. This should have been caught by Task 1's own `<precondition>` ("pip can install into the interpreter that runs python3 (no externally-managed-environment error)"), but the read-only precondition check (`python3 -m pip --version`) does not by itself surface this failure mode; it only appeared once the actual install was attempted.
- **Fix:** Created a project-local virtual environment (`python3.13 -m venv .venv`) and installed both requirement files into it (`.venv/bin/python -m pip install -r requirements.txt -r requirements-dev.txt`). `.venv/`, `venv/` and `env/` were already listed in this repo's `.gitignore` under "Virtual environments" before this plan ran, indicating a venv-based local workflow was already anticipated even though none existed yet. All subsequent verification in this plan (`pip install`, `import pandas/numpy/pytest`, `pytest tests/ -q`) ran against `.venv/bin/python`. No application code, `requirements.txt` content, or shipped deployment behavior changed — this affects only how a package is installed locally, not what is declared or what ships to the Hugging Face Space.
- **Files modified:** none tracked by git (`.venv/` is gitignored)
- **Verification:** `.venv/bin/python -c "import pandas, numpy, pytest; print(pandas.__version__, numpy.__version__, pytest.__version__)"` printed `3.0.5 2.5.3 9.1.1`; `.venv/bin/python -m pytest tests/ -q` passed 4/4.
- **Committed in:** N/A (no tracked files changed by this fix; `.venv/` remains gitignored)

---

**Total deviations:** 1 auto-fixed (1 Rule 3 — blocking install-environment issue)
**Impact on plan:** No scope creep. The fix is purely a local-machine installation workaround; the declared `requirements.txt`/`requirements-dev.txt` content, the pytest configuration, and the standing test are exactly as the plan specified and were verified against the correct pinned versions.

## Issues Encountered
None beyond the auto-fixed deviation above.

## User Setup Required

None - no external service configuration required. (Local developers on Homebrew-managed macOS Python will need to create their own virtual environment before running `pip install -r requirements-dev.txt`, per the deviation above — this is a local dev-environment note, not a Space deployment requirement.)

## Next Phase Readiness

`requirements.txt`, `requirements-dev.txt`, `pytest.ini` and `tests/test_environment_pins.py` are in place and green. Plans 02-06 of this phase (the `qc/` package extraction, rule registry, deterministic ordering, and streamlit-import guard) can now write and run their own standing tests against exactly this pinned pandas/numpy, with `python3 -m pytest tests/ -q` as the discovery command. No blockers for the next plan in this phase.

---
*Phase: 01-qc-engine-seam-and-pinned-environment*
*Completed: 2026-09-09*

## Self-Check: PASSED

All created files verified on disk (`requirements.txt`, `requirements-dev.txt`, `pytest.ini`, `tests/test_environment_pins.py`, this SUMMARY). Both task commits (`2a99e63`, `e4c2ae5`) verified present in `git log`. All plan-level `<verification>` commands re-ran clean: `python3 -m pytest tests/ -q` → 4 passed; `python3 -c "import pandas; print(pandas.__version__)"` → `3.0.5`; `requirements.txt` confirmed to declare five bounded dependencies with no unbounded lines.
