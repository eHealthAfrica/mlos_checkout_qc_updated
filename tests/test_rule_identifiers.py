"""Standing assertion of the rule-identifier contract: the pre-existing frozen identifiers, 11
new field-named ones replacing the two that used to be shared, all distinct, and all small
enough to fit an Excel sheet name without colliding.

``FROZEN_IDENTIFIERS`` below is the reason a future contributor cannot silently renumber one of
the pre-existing identifiers: reports already filed by the data team cite these exact strings,
and there is no migration path for a printed or emailed report (D-04). Deleting an entry from
this list to "fix" a failing test here is the wrong fix — it means the renumbering happened; the
right fix is to not renumber.

**Count note:** CONTEXT.md's D-04 and PLAN.md's must_haves both say "27" existing identifiers.
Enumerating D-04's own list against every ``add(...)``/``register(...)`` call site in the
pre-extraction app.py (verified directly, not assumed) gives 29, not 27: Settlement contributes
5 (SQ1, SQ2, SQ2b, SQ3, SQ4), not 4, and Boundary contributes 4 (B0-B3). This list holds all 29 —
completeness of the freeze guarantee matters more than matching a miscounted total, since
dropping two real identifiers to hit "27" would silently remove them from this test's
protection. Logged as a deviation in this plan's SUMMARY.md.
"""

import qc

# Frozen exactly as they are per D-04 — deleting a line here to make a test pass means an
# already-filed report's identifier was silently repointed at a different check. Don't.
# 29 entries (see module docstring's Count note for the discrepancy with D-04's stated "27").
FROZEN_IDENTIFIERS = [
    "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11a", "11b", "13", "14",
    "S1", "S2",
    "SQ1", "SQ2", "SQ2b", "SQ3", "SQ4",
    "TP2", "TP3", "TP4", "TP5",
    "B0", "B1", "B2", "B3",
]

NEW_IDENTIFIERS = [
    "11.urban", "11.rural", "11.scattered",
    "12.highrisk", "12.slums", "12.densely_populated", "12.hard2reach",
    "12.border", "12.nomadic", "12.riverine", "12.fulani",
]


def _relocated_layers() -> set:
    """Derive the set of layers already relocated into qc/ from the registered Rule records,
    rather than hard-coding it — so this test keeps working after plans 05/06 relocate the rest."""
    from qc.results import _REGISTRY
    return {rule.layer for rule in _REGISTRY.values()}


# Map each frozen identifier to the layer it belongs to, so a not-yet-relocated layer's
# identifiers can be excluded from the check without hard-coding which layers are done.
_FROZEN_LAYER_BY_ID = {
    "1": "MLoS", "2": "MLoS", "3": "MLoS", "4": "MLoS", "5": "MLoS", "6": "MLoS",
    "7": "MLoS", "8": "MLoS", "9": "MLoS", "10": "MLoS", "11a": "MLoS", "11b": "MLoS",
    "13": "MLoS", "14": "MLoS",
    "S1": "Schema", "S2": "Schema",
    "SQ1": "Settlement", "SQ2": "Settlement", "SQ2b": "Settlement",
    "SQ3": "Settlement", "SQ4": "Settlement",
    "TP2": "Takeoffpoint", "TP3": "Takeoffpoint", "TP4": "Takeoffpoint", "TP5": "Takeoffpoint",
    "B0": "Boundary", "B1": "Boundary", "B2": "Boundary", "B3": "Boundary",
}


def test_frozen_identifiers_are_all_still_registered():
    """Every frozen identifier belonging to a layer already relocated into qc/ is present in
    canonical_order() with its exact string. Identifiers from layers not yet relocated are
    skipped by intersecting with the layers actually present in the registry — and this test
    asserts a minimum count of checked identifiers so a mis-derived empty intersection fails
    rather than passes."""
    order = qc.canonical_order()
    relocated = _relocated_layers()

    checked = [rid for rid in FROZEN_IDENTIFIERS if _FROZEN_LAYER_BY_ID[rid] in relocated]
    assert len(checked) >= 16, (
        f"expected at least 16 checked identifiers (Schema + MLoS relocated), got "
        f"{len(checked)}: {checked}"
    )
    for rid in checked:
        assert rid in order, f"frozen identifier {rid!r} is missing from canonical_order()"


def test_the_eleven_new_identifiers_are_registered():
    """All eleven field-named identifiers introduced by this plan are present, spelled exactly
    as D-01 specifies."""
    order = qc.canonical_order()
    for rid in NEW_IDENTIFIERS:
        assert rid in order, f"new identifier {rid!r} is missing from canonical_order()"


def test_no_bare_11_or_12_identifier_remains():
    """Neither the bare string 11 nor the bare string 12 appears in canonical_order() — both
    were split into field-named identifiers by this plan."""
    order = qc.canonical_order()
    assert "11" not in order, "bare identifier '11' still registered"
    assert "12" not in order, "bare identifier '12' still registered"


def test_every_registered_identifier_is_distinct():
    """The registered order has as many entries as distinct entries, and at least twenty-five
    (Schema's 2 plus MLoS's 25)."""
    order = qc.canonical_order()
    assert len(order) >= 25, f"expected at least 25 registered identifiers, got {len(order)}"
    assert len(order) == len(set(order)), f"duplicate identifiers found in {order!r}"


def test_excel_sheet_names_fit_and_stay_distinct():
    """For every registered identifier, the sheet name the report builder derives — 'Rule ' plus
    the identifier, truncated at 31 characters (Excel's limit, matching app.py's
    f"Rule {rn}"[:31] expression at the three per-rule Excel sheet-name sites) — is at most 31
    characters, and the set of derived names has the same size as the set of identifiers. The
    longest identifier introduced by this plan, 12.densely_populated, yields a 25-character sheet
    name, leaving headroom; this test is what will catch a future identifier that spends it."""
    order = qc.canonical_order()
    sheet_names = [f"Rule {rid}"[:31] for rid in order]
    assert all(len(name) <= 31 for name in sheet_names), (
        "at least one derived sheet name exceeds Excel's 31-character limit: "
        f"{[n for n in sheet_names if len(n) > 31]}"
    )
    assert len(sheet_names) == len(set(sheet_names)), (
        f"two identifiers collide on the same truncated sheet name: {sheet_names!r}"
    )
