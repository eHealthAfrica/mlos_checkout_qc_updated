"""Column-name normalisation, new for INTEG-03/D-08/D-09/D-10.

Purely typographic: trim, lowercase, collapse a run of whitespace and/or hyphens to a
single underscore, then collapse repeated underscores. No semantic aliasing and no name
is inferred from another name — a known-alias map (``wardcd`` -> ``ward_code``) was
proposed during discovery and rejected, because a wrong guess routes real data into the
wrong rule. Because this module performs no canonical-set lookup at all, it has no
sibling module to import from and needs none; ``qc/domain.py``'s ``MLOS_REQUIRED_COLS``/
``TAKEOFF_REQUIRED_COLS`` are deliberately not referenced here — that comparison belongs
to ``qc/schema.py``'s S1/S2, not to this purely typographic transform.

Collision detection runs against the proposed rename map BEFORE any rename is applied
(D-10, Established Fact 2, verified empirically this phase): ``DataFrame.rename`` does
not raise on a colliding target label — it silently produces duplicate column labels,
after which ``frame["x"]`` returns a DataFrame instead of a Series and the next
``.str``/``.isna()`` accessor raises ``AttributeError``. Detecting collisions on the
proposed mapping first, and leaving a colliding group's original headers un-normalised,
is what prevents that crash from ever happening — a collision is reported as data (the
returned ``collisions`` list), never an exception, matching the codebase-wide convention
that a failure is a check record, not a raised error.
"""

import re

import pandas as pd

_WS_HYPHEN_RE = re.compile(r"[\s\-]+")
_REPEAT_UNDERSCORE_RE = re.compile(r"_+")


def normalize_name(col: str) -> str:
    """Purely typographic column-name normalisation (D-08).

    Strip surrounding whitespace, lower-case, collapse any run of whitespace and/or
    hyphen characters to a single underscore, then collapse any run of repeated
    underscores to one. Idempotent: ``normalize_name(normalize_name(x)) ==
    normalize_name(x)`` for every input. Never raises — the empty string and a
    whitespace-only string both normalise to the empty string.
    """
    c = col.strip().lower()
    c = _WS_HYPHEN_RE.sub("_", c)
    c = _REPEAT_UNDERSCORE_RE.sub("_", c)
    return c


def normalize_columns(df: "pd.DataFrame", original_names=None):
    """Normalise every column header, detecting collisions before any rename is applied.

    Returns a 3-tuple ``(renamed_df, rename_map, collisions)``:

    - ``renamed_df`` — ``df`` with every non-colliding header renamed to its normalised
      form. A colliding group's original headers are left exactly as they arrived, so
      ``renamed_df`` never carries a duplicate column label.
    - ``rename_map`` — a mapping from original header to new header, covering only
      headers that actually changed (a header already in canonical form is omitted).
    - ``collisions`` — a list of dicts, one per colliding group, each shaped
      ``{"normalized": <str>, "originals": [<str>, ...]}``. ``originals`` lists every
      header that normalised to ``normalized``, in the order they appeared in ``df``'s
      columns. Three or more headers colliding on one normalised form produce one group
      naming all of them, never multiple pairwise groups. Empty when nothing collided.

    Built in exactly this order and no other: first walk the original header list once,
    recording the first header seen for each normalised form; when a later header
    normalises to a form already seen, both the earlier and the later header join that
    normalised form's collision group. Second, build the rename map from only the
    headers that never joined a collision group. Third, apply that map with
    ``DataFrame.rename``. This function never raises. An empty frame (no columns)
    returns itself unchanged, an empty rename map and no collisions; a single-column
    frame can never produce a collision, since a collision requires two headers sharing
    one normalised form.

    ``original_names`` lets a caller supply the header list to normalise separately from
    ``df.columns`` (e.g. reconciling against a header list captured before some other
    transform); it defaults to ``df.columns`` itself.
    """
    original = list(df.columns) if original_names is None else list(original_names)

    seen: "dict[str, str]" = {}
    collided_originals: "set[str]" = set()
    groups: "dict[str, list[str]]" = {}

    for orig in original:
        norm = normalize_name(orig)
        if norm in seen:
            first = seen[norm]
            collided_originals.add(first)
            collided_originals.add(orig)
            groups.setdefault(norm, [first]).append(orig)
        else:
            seen[norm] = orig

    rename_map_all = {
        orig: normalize_name(orig) for orig in original if orig not in collided_originals
    }
    renamed_df = df.rename(columns=rename_map_all)
    rename_map = {o: n for o, n in rename_map_all.items() if o != n}

    collisions = [
        {"normalized": norm, "originals": originals} for norm, originals in groups.items()
    ]

    return renamed_df, rename_map, collisions
