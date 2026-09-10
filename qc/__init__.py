"""Package facade for the QC engine.

The only module allowed to import from all the others under ``qc/``. Importing this package
imports every layer submodule (``schema``, ``mlos``, ``settlement``, ``takeoff``, ``boundary``,
``autocorrect``), which triggers every import-time ``register()`` call — so ``import qc`` alone
is enough to populate the registry. Re-exports the registry surface (``Rule``, ``register``,
``canonical_order``) and provides ``sort_by_registry``, the canonical re-sort helper every
layer's call site pipes its checks through.

This facade deliberately does not gain a ``run_all()`` wrapper (01-CONTEXT.md left the choice to
the planner). The five QC-layer call sites in ``app.py`` are interleaved with per-step progress
bar updates, status lines and per-layer pass counts; collapsing them into one call would delete
that progress reporting, a user-visible change this phase has no requirement to make. The seam's
job is to own rule logic and rule identity, not orchestration.
"""

from . import schema
from . import mlos
from . import settlement
from . import takeoff
from . import boundary
from . import autocorrect
from .results import Rule, register, canonical_order, get_rule


def sort_by_registry(checks: list[dict]) -> list[dict]:
    """Return ``checks`` sorted by each check's ``"Rule#"`` position in ``canonical_order()``.

    Uses ``sorted``, which is stable, so two check rows carrying the same identifier keep their
    relative emission order rather than being swapped.
    """
    order_index = {rule_id: i for i, rule_id in enumerate(canonical_order())}
    return sorted(checks, key=lambda c: order_index[c["Rule#"]])
