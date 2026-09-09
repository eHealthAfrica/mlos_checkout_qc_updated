"""Standing proof that the registry and the engine describe the same rule set (T-01-19).

Rule identity's whole point, from qc/results.py onward, is that a ``Rule`` record declared via
``register()`` is the primary definition of a check, and the ``"Rule#"`` value a QC layer
attaches to a check dictionary is a reference into that record — never an independent second
identity. A check emitted under an identifier nobody registered is a spoofed reference (nothing
backs it); a registered identifier the full fixture never emits is a rule this suite's coverage
does not actually exercise. Both are a drift between two sources of truth that must describe one
thing, and this file asserts against both directions.
"""

import qc


def _emitted_identifiers(mlos_df, takeoff_df, boundary_refs) -> set:
    """Run all five QC layers against the fixture and return the set of every "Rule#" any of
    them emitted. Mirrors the real app.py orchestration's five call sites, minus the
    sort_by_registry piping — set membership does not depend on order."""
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
    required MLoS columns and a Takeoffpoint orphan row precisely so this holds. A registered
    rule the fixture never triggers is a rule nothing in this suite actually covers, named
    explicitly in the failure message rather than left to a bare count mismatch."""
    emitted = _emitted_identifiers(mlos_df, takeoff_df, boundary_refs)
    registered = set(qc.canonical_order())

    unemitted = sorted(registered - emitted)
    assert not unemitted, (
        f"the following registered identifiers were never emitted by the full fixture: "
        f"{unemitted}"
    )
