---
phase: 02-detection-correctness-and-three-format-harness
plan: 05
subsystem: qc-engine
tags: [boundary-checks, integ-04, registry-coverage, readme]

requires:
  - phase: 02-detection-correctness-and-three-format-harness
    provides: "qc.predicates.vec_is_absent (plan 01/03's D-04 predicate) and the qc.results register()/canonical_order() seam"
provides:
  - "B4 'Boundary Reference Fallback' — reports whether B1/B2 validated against the file's own state(s) or, on a fallback, against the full national reference; PASS names the state's ward count, FAIL names both B1 and B2"
  - "B5 'Boundary Reference Unavailable' — reports a missing boundary reference as an early return, emitting exactly B0 and B5 with B1-B4 suppressed"
  - "Canonical boundary order extended to B0, B1, B2, B3, B4, B5 (qc.canonical_order() now 49 entries)"
  - "qc/boundary.py's B0 blank-ward-code mask now built on the shared vec_is_absent predicate (D-04) instead of a hand-rolled null-or-empty disjunction"
  - "tests/test_boundary_reference_states.py — standing three-state invariant (state-matched, widened, unavailable), threshold/adjacency edge tests, sentinel-ward-code test, canonical-order test"
  - "tests/test_registry_covers_emitted_ids.py's registry-coverage guard extended with a second, reference-absent boundary scenario so all 49 registered identifiers (including B5) are provably emittable"
  - "app.py's Boundary Check Rules sidebar and About-this-tool blurb document B4/B5; README.md's Boundary Checks section and State filtering paragraph describe the fallback and unavailability as reported checks rather than silent branches"
affects: [02-06, 03-verdict-and-report-integrity]

actuals:
  tokens: 5540
  tasks: 2
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Run-level checks with a 1-over-1 denominator are hand-built check dictionaries following B0's early-return shape, not routed through the add() closure, because add() hard-codes Total Rows to the MLoS row count. S1/S2 (Schema layer) already set this precedent; B4/B5 follow it in the Boundary layer."
    - "A boolean captured at the mutation site, before a reassignment destroys the information needed to report on it — fallback_fired and pre_fallback_ward_count are read from filtered_ref immediately before the fallback's copy-and-reassign, mirroring how the fallback branch itself is a pre-existing pattern in the same function."
    - "A registry-coverage guard for an identifier defined by a resource's *absence* needs a second scenario, not a fixture tweak — tests/test_registry_covers_emitted_ids.py's _emitted_identifiers now calls the boundary layer twice (real reference, then two empty frames) because no single reference frame can be both present and absent."

key-files:
  created:
    - tests/test_boundary_reference_states.py
  modified:
    - qc/boundary.py
    - app.py
    - tests/test_registry_covers_emitted_ids.py
    - tests/test_deterministic_order.py
    - README.md

key-decisions:
  - "B4's FAIL description names both B1 and B2 (not just B1, which is all INTEG-04's own wording names), because the fallback reassigns filtered_bbox as well as filtered_ref, so B2's scope widens exactly as B1's does (D-16 explicitly directs this widening beyond the requirement text)."
  - "B5 is emitted as an early return placed after B0's add() call and before B1 is reached — after so the ward-code-on-data finding still reaches the officer, before so the emitted set for an absent reference is exactly {B0, B5} per D-18, mirroring the function's own pre-existing early-return pattern for a missing ward_code column."
  - "[Rule 1 - Bug] tests/test_deterministic_order.py's full-registry equality assertion (actual_ids == qc.canonical_order()) broke the instant B5 was registered, because B5 is defined by the boundary reference's absence and that test's fixture always loads the real bundled reference. Fixed by excluding B5 from the expected-order comparison there, with a comment pointing at test_registry_covers_emitted_ids.py's dedicated reference-absent scenario (this plan's Task 2) as B5's actual coverage proof. This file was not in the plan's do-not-touch list (tests/baseline/, tests/test_extraction_parity.py, tests/fixtures.py, tests/conftest.py) and the failure directly blocked Task 1's own <verify> gate, so it was fixed in-line under deviation Rule 1 rather than deferred."

patterns-established:
  - "A check whose emission is mutually exclusive with another registered check (B4 requires a reference; B5 requires its absence) needs its registry-coverage proof built from a second scenario unioned into the emitted set, not a single fixture run — documented in _emitted_identifiers' docstring for the next check that has this shape."

requirements-completed: [INTEG-04, ENGINE-06]

coverage:
  - id: D1
    description: "A fallback to the national boundary reference is reported as a failing B4 check naming both B1 and B2, instead of widening B1/B2's scope silently (INTEG-04, D-16/D-17, F13)."
    requirement: "INTEG-04"
    verification:
      - kind: unit
        ref: "tests/test_boundary_reference_states.py::test_widened_fallback_emits_b4_fail_naming_b1_and_b2"
        status: pass
      - kind: unit
        ref: "tests/test_boundary_reference_states.py::test_state_matched_emits_exactly_b0_through_b4_with_b4_pass"
        status: pass
    human_judgment: false
  - id: D2
    description: "An unavailable boundary reference is reported as a failing B5 check, with the emitted boundary set exactly B0 and B5 and B4 silent (D-18/D-19)."
    requirement: "INTEG-04"
    verification:
      - kind: unit
        ref: "tests/test_boundary_reference_states.py::test_reference_unavailable_emits_exactly_b0_and_b5"
        status: pass
    human_judgment: false
  - id: D3
    description: "Canonical boundary order reads B0 through B5, and the registry-coverage guard proves all 49 registered identifiers, including B5, are emittable by some scenario (ENGINE-06, Pitfall 3)."
    requirement: "ENGINE-06"
    verification:
      - kind: unit
        ref: "tests/test_boundary_reference_states.py::test_boundary_order_is_b0_through_b5"
        status: pass
      - kind: unit
        ref: "tests/test_registry_covers_emitted_ids.py::test_every_registered_identifier_is_emitted_by_the_fixture"
        status: pass
      - kind: unit
        ref: "tests/test_registry_covers_emitted_ids.py::test_reference_absent_scenario_emits_B5_by_itself"
        status: pass
    human_judgment: false
  - id: D4
    description: "The sidebar Boundary Check Rules reference and README.md both document B4 and B5, and README's State filtering paragraph describes the fallback as a reported check rather than a silent widening."
    requirement: "INTEG-04"
    verification:
      - kind: unit
        ref: "tests/test_rules_reference_matches_registry.py::test_reference_tables_and_registry_list_the_same_identifiers"
        status: pass
    human_judgment: false

duration: 45min
completed: 2026-09-10
status: complete
---

# Phase 2 Plan 5: Boundary Reference Fallback and Availability as Reported Checks Summary

**B4/B5 make the boundary reference's silent national-fallback widening and its silent absence into two failing checks the officer can see, closing INTEG-04.**

## Performance

- **Duration:** 45 min
- **Started:** 2026-09-10T17:19:03Z (approx, session start)
- **Completed:** 2026-09-10T17:19:03Z
- **Tasks:** 2
- **Files modified:** 6 (1 created, 5 modified)

## Accomplishments
- `B4` "Boundary Reference Fallback" reports PASS naming the ward count validated in the file's own state, or FAIL naming both `B1` and `B2` when the state-name filter came back empty and the run silently widened to the full 9,410-ward national reference — closing defect F13.
- `B5` "Boundary Reference Unavailable" reports a missing boundary reference as a failing check, emitted as an early return so the boundary layer's output for an absent reference is exactly `{B0, B5}` with `B1`, `B2`, `B3` and `B4` all suppressed.
- `qc.canonical_order()` now reads `B0, B1, B2, B3, B4, B5`, extending the registry from 47 to 49 identifiers while keeping Phase 3's VERDICT-06 boundary-ordering requirement satisfiable.
- `B0`'s blank-ward-code mask now runs through the shared `vec_is_absent` predicate (D-04) instead of a hand-rolled null-or-empty check, so a sentinel `ward_code` of `n/a` fails `B0` consistently with Rule 1 and `4.missing` elsewhere.
- The registry-coverage guard (`tests/test_registry_covers_emitted_ids.py`) now runs the boundary layer twice — once against the real reference, once with both frames empty — so every one of the 49 registered identifiers, including `B5`, is provably emittable by some scenario.
- `app.py`'s sidebar and `README.md` both document `B4`/`B5`, and `README.md`'s State filtering paragraph no longer describes the fallback as silent.

## Task Commits

Each task was committed atomically (Task 1 as a TDD RED/GREEN pair):

1. **Task 1 (RED): add failing three-state invariant test** - `4bb3cad` (test)
2. **Task 1 (GREEN): register and emit B4/B5, document in sidebar** - `3bba16e` (feat)
3. **Task 2: reach B5 with a second registry-coverage scenario, update README** - `00f4761` (feat)

**Plan metadata:** committed separately below (docs: complete plan)

_Note: Task 1 carried `tdd="true"`; no REFACTOR commit was needed — the GREEN implementation required no cleanup._

## Files Created/Modified
- `tests/test_boundary_reference_states.py` - Standing three-state invariant test (state-matched, widened, unavailable), threshold/adjacency edges, sentinel-ward-code test, canonical-order test
- `qc/boundary.py` - Registers B4/B5, captures the fallback boolean and pre-fallback ward count before reassignment, emits B5 as an early return, emits B4 at the end guarded on reference availability, rebuilds B0's mask on `vec_is_absent`
- `app.py` - Boundary Check Rules sidebar gains B4/B5 rows; About-this-tool blurb's boundary range updated from B0–B3 to B0–B5
- `tests/test_registry_covers_emitted_ids.py` - `_emitted_identifiers` unions a second reference-absent boundary scenario; new focused test asserting that scenario emits B5 alone
- `tests/test_deterministic_order.py` - Excludes B5 from the full-registry equality comparison in `test_registry_sorted_order_is_stable_across_hash_seeds`, since that test's fixture always carries a real reference and can never emit B5
- `README.md` - Boundary Checks section extended to B0–B5 with a B4/B5 table rows; State filtering paragraph rewritten to describe the fallback and unavailability as reported checks

## Decisions Made
- B4's FAIL description deliberately names both `B1` and `B2` (INTEG-04's own text names only `B1`), because the fallback reassigns `filtered_bbox` alongside `filtered_ref` and `B2` reads the bounding-box frame — D-16 directs this wider description.
- B5's early return sits after `B0`'s `add()` call and before `B1` is reached, so a run with no reference still reports a real `ward_code`-on-data finding via `B0` while emitting nothing else — mirroring the function's pre-existing early-return pattern for a missing `ward_code` column.
- The registry-coverage guard's second scenario is a direct call with an empty-frame argument (mirroring the file's own existing pattern), not a new fixture — `B5` is defined by the reference's absence, a state no single reference frame can be in and out of at once.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test_deterministic_order.py's full-registry equality assertion, broken by registering B5**
- **Found during:** Task 1 (running the plan's own verify command set, which includes `tests/test_deterministic_order.py`)
- **Issue:** `test_registry_sorted_order_is_stable_across_hash_seeds` asserted `actual_ids == qc.canonical_order()` exactly. That test's fixture always loads the real bundled boundary reference, a state in which `B5` (defined by the reference's *absence*) can never emit — so registering `B5` broke this assertion immediately, independent of anything in Task 2's declared scope.
- **Fix:** Excluded `B5` from the expected-order comparison with a comment explaining why and pointing at `tests/test_registry_covers_emitted_ids.py`'s dedicated reference-absent scenario (added in Task 2) as B5's real coverage proof. The test's actual purpose — cross-process determinism of emission order — is unaffected; the full-registry-coverage claim piggybacking on it is scoped down to what the fixture can actually prove.
- **Files modified:** tests/test_deterministic_order.py
- **Verification:** `python3 -m pytest tests/test_deterministic_order.py -q` passes (2 passed); full suite green after the fix.
- **Committed in:** 3bba16e (Task 1 GREEN commit)

---

**Total deviations:** 1 auto-fixed (1 bug, caused directly by this plan's own change to a file outside the plan's declared `files_modified` list but not on its do-not-touch list).
**Impact on plan:** Necessary for the plan's own Task 1 verification gate to pass. No scope creep — the fix is a one-line comparison adjustment with a documenting comment, not a behavior change to production code.

## Issues Encountered
- Task 1's own `<verify>` block runs the full `tests/ -q` suite and requires zero failures, but registering `B5` in Task 1 necessarily leaves `tests/test_registry_covers_emitted_ids.py::test_every_registered_identifier_is_emitted_by_the_fixture` failing until Task 2's second-scenario fix lands (the plan's own key_links explicitly predicted this: "Without the second scenario it fails naming B5 specifically"). This was treated as expected, sequenced work rather than a Task 1 blocker — Task 1's acceptance criteria (which do not include a full-suite check) all passed, and the plan-level `<verification>` section (run after both tasks) is what actually gates full-suite-green, which it does: 99 passed, zero failures, after Task 2.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- INTEG-04 and ENGINE-06 both closed for the boundary layer. `qc.canonical_order()` now stable at 49 identifiers with boundary checks reading B0 through B5, satisfying Phase 3's VERDICT-06 ordering dependency.
- Full suite green at 99 passed (up from 91 baseline entering this plan), including all standing structural-backstop tests (rules-reference-matches-registry, registry-covers-emitted-ids, deterministic-order, rule-identifiers, extraction-parity).
- No blockers for the next plan (02-06) or for Phase 3.

---
*Phase: 02-detection-correctness-and-three-format-harness*
*Completed: 2026-09-10*

## Self-Check: PASSED

- All 6 key-files (created + modified) verified present on disk.
- All 3 task commits (`4bb3cad`, `3bba16e`, `00f4761`) verified present in git history.
- Full suite re-run: 99 passed, zero failures.
- `qc.canonical_order()` re-verified at 49 identifiers.
- `tests/test_boundary_reference_states.py` re-run: 7 passed.
- `tests/test_rules_reference_matches_registry.py` re-run: 2 passed (both directions).
- `git status --porcelain tests/baseline/` confirmed empty (do-not-touch scope respected).
