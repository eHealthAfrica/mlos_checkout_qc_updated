"""Package facade for the QC engine.

The only module allowed to import from all the others under ``qc/``. Importing this package
imports every layer submodule, which triggers every import-time ``register()`` call — so
``import qc`` alone is enough to populate the registry. Re-exports the registry surface
(``Rule``, ``register``, ``canonical_order``) and provides ``sort_by_registry``, the canonical
re-sort helper every layer's call site pipes its checks through.
"""

from . import schema
from .results import Rule, register, canonical_order


def sort_by_registry(checks: list[dict]) -> list[dict]:
    """Return ``checks`` sorted by each check's ``"Rule#"`` position in ``canonical_order()``.

    Uses ``sorted``, which is stable, so two check rows carrying the same identifier keep their
    relative emission order rather than being swapped.
    """
    order_index = {rule_id: i for i, rule_id in enumerate(canonical_order())}
    return sorted(checks, key=lambda c: order_index[c["Rule#"]])
