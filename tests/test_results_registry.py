"""Standing guards for the rule-identity registry in qc/results.py.

These tests defend two invariants the whole extraction rests on: a rule identifier registered
twice collides rather than merges (uniqueness is global, never per-layer), and an empty registry
is a valid state — ``canonical_order()`` returns ``[]``, not ``None``, and raises nothing.
"""

import importlib.util
from pathlib import Path

import pytest

from qc.results import register


def _unregister(rule_id: str) -> None:
    """Remove a throwaway identifier from the shared, process-global registry.

    ``register()`` mutates module-level state in ``qc.results`` that survives for the rest of
    the pytest process — every other test in this session, including
    ``tests/test_rules_reference_matches_registry.py``'s exact-set-equality comparison against
    ``canonical_order()``, imports the same module object. A throwaway id left registered here
    would make that comparison see a rule identifier neither the engine nor the sidebar
    reference ever really declared. Cleanup must run even if the test's own assertions fail.
    """
    from qc.results import _REGISTRY, _ORDER
    _REGISTRY.pop(rule_id, None)
    if rule_id in _ORDER:
        _ORDER.remove(rule_id)


def test_duplicate_rule_id_raises_at_registration():
    """Registering a throwaway identifier, then registering it again, raises ValueError whose
    message names the identifier and the first registration's layer. The registry retains the
    first registration, not the second."""
    try:
        register("__test_dup_same_layer__", "Test", "first", "...")
        with pytest.raises(ValueError, match="Duplicate rule id"):
            register("__test_dup_same_layer__", "Test", "second", "...")

        from qc.results import _REGISTRY
        assert _REGISTRY["__test_dup_same_layer__"].name == "first"
    finally:
        _unregister("__test_dup_same_layer__")


def test_duplicate_is_rejected_across_different_layers():
    """The same collision is raised when the two registrations declare different layer names —
    uniqueness is global, never per-layer."""
    try:
        register("__test_dup_cross_layer__", "LayerA", "first", "...")
        with pytest.raises(ValueError, match="Duplicate rule id"):
            register("__test_dup_cross_layer__", "LayerB", "second", "...")
    finally:
        _unregister("__test_dup_cross_layer__")


def test_current_ruleset_has_no_duplicates():
    """Importing the real qc package raises nothing, and canonical_order() has as many entries
    as it has distinct entries. The order must also be non-empty, so a package that registered
    nothing cannot pass this test."""
    import qc  # importing the real package triggers every register() call
    from qc.results import canonical_order

    ids = canonical_order()
    assert len(ids) > 0, "canonical_order() reported zero registrations"
    assert len(ids) == len(set(ids)), f"Duplicate ids found: {ids}"


def test_canonical_order_of_an_empty_registry_is_an_empty_list():
    """A freshly-loaded copy of the results module, with no registrations performed against it,
    returns [] — a list, not None — and raises nothing. Loaded under a throwaway module name via
    importlib so the shared, already-populated registry is left untouched."""
    results_path = Path(__file__).resolve().parent.parent / "qc" / "results.py"
    spec = importlib.util.spec_from_file_location("qc_results_fresh_copy", results_path)
    fresh_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fresh_module)

    order = fresh_module.canonical_order()
    assert order == []
    assert isinstance(order, list)
