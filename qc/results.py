"""The rule-identity seam: a single registry every QC layer declares its rule identifiers into.

Rule identity used to be a bare string literal minted at each ``add()`` call site, with five
copies of that call site and no shared definition — the shape that let identifier "11" name
three checks and "12" name eight without anything noticing. From this module on, a ``Rule``
record is declared once at import time via :func:`register`, and the ``"Rule#"`` value carried
on a check dictionary is a reference to that record rather than the record itself.

Registration order is the canonical emission order: layer import order, then declaration order
within a layer — never a lexicographic sort of the identifier string, which would order 1, 10,
11, 2 and be worse than the defect this registry replaces.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Rule:
    id: str
    layer: str
    name: str
    description: str


_REGISTRY: dict[str, Rule] = {}
_ORDER: list[str] = []


def register(id: str, layer: str, name: str, description: str) -> Rule:
    """Declare a rule identifier, raising if it is already registered.

    Registration is expected to happen once per identifier, at import time, before any QC
    function that emits that identifier is ever called. A duplicate ``id`` raises ``ValueError``
    naming both the offending identifier and the layer/name that already hold it; the registry
    keeps only the first registration.
    """
    if id in _REGISTRY:
        existing = _REGISTRY[id]
        raise ValueError(
            f"Duplicate rule id {id!r}: already registered for layer "
            f"{existing.layer!r} ({existing.name!r})"
        )
    rule = Rule(id, layer, name, description)
    _REGISTRY[id] = rule
    _ORDER.append(id)
    return rule


def canonical_order() -> list[str]:
    """Return a copy of the registration-order identifier list.

    An empty registry returns an empty list, not ``None``, and this never raises.
    """
    return list(_ORDER)


def get_rule(id: str) -> Rule:
    """Look up a registered Rule by its identifier.

    Raises ``KeyError`` naming the identifier when it was never registered — mirrors
    ``register()``'s own fail-loud convention.
    """
    if id not in _REGISTRY:
        raise KeyError(f"No rule registered for id {id!r}")
    return _REGISTRY[id]
