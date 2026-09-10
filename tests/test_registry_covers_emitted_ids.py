"""Standing proof that the registry and the engine describe the same rule set (T-01-19).

Rule identity's whole point, from qc/results.py onward, is that a ``Rule`` record declared via
``register()`` is the primary definition of a check, and the ``"Rule#"`` value a QC layer
attaches to a check dictionary is a reference into that record — never an independent second
identity. A check emitted under an identifier nobody registered is a spoofed reference (nothing
backs it); a registered identifier the full fixture never emits is a rule this suite's coverage
does not actually exercise. Both are a drift between two sources of truth that must describe one
thing, and this file asserts against both directions.
"""

import pandas as pd

import qc


def _emitted_identifiers(mlos_df, takeoff_df, boundary_refs) -> set:
    """Run all five QC layers against the fixture and return the set of every "Rule#" any of
    them emitted. Mirrors the real app.py orchestration's five call sites, minus the
    sort_by_registry piping — set membership does not depend on order.

    The boundary layer is called twice, not once: once against the real bundled reference
    (``boundary_refs``), and again with two empty reference frames. Neither call alone can
    cover every registered boundary identifier — B5 ("Boundary Reference Unavailable") is
    defined by the reference's *absence*, a state a single reference frame can never be in
    and out of at the same time, so the first call can never emit it; conversely B1, B2, B3
    and B4 all require a reference to validate against, so the second call can never emit
    those. The union of both scenarios is what makes every registered boundary identifier
    reachable by this helper (INTEG-04, ENGINE-06 Pitfall 3)."""
    ref_df, bbox_df = boundary_refs
    emitted: set = set()

    checks, _ = qc.schema.run_schema_qc(mlos_df, takeoff_df)
    emitted.update(c["Rule#"] for c in checks)

    checks, _ = qc.mlos.run_mlos_qc(mlos_df, takeoff_df)
    emitted.update(c["Rule#"] for c in checks)

    checks, _ = qc.settlement.run_settlement_qc(mlos_df)
    emitted.update(c["Rule#"] for c in checks)

    checks, _ = qc.takeoff.run_takeoff_qc(takeoff_df, mlos_df)
    emitted.update(c["Rule#"] for c in checks)

    checks, _ = qc.boundary.run_ward_boundary_qc(mlos_df, ref_df, bbox_df)
    emitted.update(c["Rule#"] for c in checks)

    # Second boundary scenario: reference absent (mirrors this file's own
    # direct-call-with-a-modified-argument pattern rather than a new fixture).
    checks, _ = qc.boundary.run_ward_boundary_qc(mlos_df, pd.DataFrame(), pd.DataFrame())
    emitted.update(c["Rule#"] for c in checks)

    return emitted


def test_every_emitted_identifier_is_registered(mlos_df, takeoff_df, boundary_refs):
    """Every identifier any of the five layers emits against the fixture resolves to exactly
    one registered rule — nothing is reported under an id the registry never declared."""
    emitted = _emitted_identifiers(mlos_df, takeoff_df, boundary_refs)
    registered = set(qc.canonical_order())

    unregistered = sorted(emitted - registered)
    assert not unregistered, (
        f"the following identifiers were emitted by a QC layer but never registered: "
        f"{unregistered}"
    )


def test_every_registered_identifier_is_emitted_by_the_fixture(mlos_df, takeoff_df, boundary_refs):
    """Every registered identifier appears in the emitted set — the fixture carries all 43
    required MLoS columns and a Takeoffpoint orphan row precisely so this holds for every
    identifier that a single reference state can produce. B5 needs a second, reference-absent
    boundary scenario to appear at all (see ``_emitted_identifiers``'s docstring); with that
    scenario unioned in, this stays an exact-equality coverage proof, not a weakened
    one-direction check. A registered rule neither scenario ever triggers is a rule nothing in
    this suite actually covers, named explicitly in the failure message rather than left to a
    bare count mismatch."""
    emitted = _emitted_identifiers(mlos_df, takeoff_df, boundary_refs)
    registered = set(qc.canonical_order())

    unemitted = sorted(registered - emitted)
    assert not unemitted, (
        f"the following registered identifiers were never emitted by the full fixture: "
        f"{unemitted}"
    )


def test_reference_absent_scenario_emits_B5_by_itself(mlos_df):
    """The reference-absent boundary scenario must emit B5 on its own, so the union inside
    ``_emitted_identifiers`` cannot silently lose B5 coverage while the overall
    two-direction test still passes because the real-reference scenario happened to grow."""
    checks, _ = qc.boundary.run_ward_boundary_qc(mlos_df, pd.DataFrame(), pd.DataFrame())
    ids = {c["Rule#"] for c in checks}
    assert "B5" in ids, ids
