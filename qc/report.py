"""Verdict, score and issue-row computation, relocated report/email builders.

This module is the Streamlit-free relocation target for the pure verdict/score/count logic that
today sits inline in ``app.py`` (F1/F6/F8's root cause: four independent presentation sites each
deriving their own answer), and — in later plans of this phase — for the report workbook and
email body/subject builders. One computation, built once from the five QC layers' checks and
detail frames, is read by every on-screen site, the downloaded report and the emailed summary.

Deliberately NOT imported by ``qc/__init__.py``: the facade (``qc/__init__.py``) imports every
layer submodule before defining ``sort_by_registry``, so a package-init edge from this module
back to the facade would be a cycle. ``app.py`` reaches this module the way it already reaches
``qc.columns`` — an explicit ``import qc.report``.
"""

from dataclasses import dataclass

import pandas as pd

from . import sort_by_registry
from .results import canonical_order, get_rule

LAYER_ORDER = ("Schema", "MLoS", "Settlement", "Takeoffpoint", "Boundary")

# Same five values as today's app.py LAYER_WEIGHTS block, renamed keys only (layer weights stay
# literals for this phase per 03-CONTEXT.md's Deferred Ideas).
LAYER_WEIGHTS = {
    "Schema": 0.10,
    "MLoS": 0.40,
    "Settlement": 0.20,
    "Takeoffpoint": 0.20,
    "Boundary": 0.10,
}

# D-05: "did not run" is generic across all five layers, so a future sixth layer produces a
# sentence rather than a KeyError — the lookup at NOT_RUN_REASON.get(name, ...) below always
# has a fallback.
NOT_RUN_REASON = {
    "Schema": "no Schema data supplied",
    "MLoS": "no MLoS data supplied",
    "Settlement": "no Settlement data supplied",
    "Takeoffpoint": "no Takeoffpoint data supplied",
    "Boundary": "no Boundary data supplied",
}


@dataclass(frozen=True)
class LayerSummary:
    name: str
    checks: list
    detail: "pd.DataFrame"
    weight: float
    source_row_count: "int | None"  # None for Schema (D-13); MLoS/Settlement/Boundary and
                                     # Takeoffpoint each carry their own source table's row count

    @property
    def ran(self) -> bool:
        """D-05: the only definition of "did not run" — the checks list is empty."""
        return len(self.checks) > 0

    @property
    def n_fail(self) -> int:
        return sum(1 for c in self.checks if "FAIL" in c["Status"])

    @property
    def n_pass(self) -> int:
        return len(self.checks) - self.n_fail

    @property
    def pass_rate(self) -> "float | None":
        """None when the layer did not run — the branch that used to award a perfect pass rate
        (F6). Never a float substitute for "not applicable"."""
        if not self.ran:
            return None
        return self.n_pass / len(self.checks)

    @property
    def weighted_contribution(self) -> float:
        """Always a float, never None (D-02, RESEARCH Pitfall 2's two-contracts rule) — 0.0 for
        an unrun layer, otherwise the pass rate times this layer's weight times 100."""
        if self.pass_rate is None:
            return 0.0
        return self.pass_rate * self.weight * 100

    @property
    def not_run_reason(self) -> str:
        return NOT_RUN_REASON.get(self.name, f"no {self.name} data supplied")

    @property
    def distinct_issue_rows(self) -> int:
        """D-11: each source row counted once, keyed on the detail frame's own index (the
        source frame's original row position) — never re-derived from a display-only merge
        derivative (RESEARCH.md Pitfall 1)."""
        return 0 if self.detail.empty else self.detail.index.nunique()

    @property
    def findings(self) -> int:
        """D-12: the old rule-row-pair count, kept visible so an officer can reconcile the
        headline distinct count against what the per-rule expanders add up to."""
        return len(self.detail)

    @property
    def issue_line(self) -> str:
        """D-13's approved per-layer line, e.g. "312 issue rows (6.2% of 5,000) across 1,040
        findings" — the parenthesised share is omitted entirely when source_row_count is None
        or 0, so no division by zero and no meaningless denominator is ever printed."""
        if not self.ran:
            return f"not run: {self.not_run_reason}"
        distinct = self.distinct_issue_rows
        findings = self.findings
        if not self.source_row_count:
            return f"{distinct:,} issue rows across {findings:,} findings"
        share = f"{distinct / self.source_row_count * 100:.1f}%"
        return f"{distinct:,} issue rows ({share} of {self.source_row_count:,}) across {findings:,} findings"


@dataclass(frozen=True)
class QcSummary:
    filename: str
    layers: "dict[str, LayerSummary]"

    @property
    def all_checks(self) -> list:
        """Every layer's checks, concatenated then piped through sort_by_registry so the union
        is in registry canonical order — no second sort is invented."""
        combined = []
        for layer in self.layers.values():
            combined.extend(layer.checks)
        return sort_by_registry(combined)

    @property
    def checks_run(self) -> int:
        return len(self.all_checks)

    @property
    def n_fail(self) -> int:
        return sum(1 for c in self.all_checks if "FAIL" in c["Status"])

    @property
    def n_pass(self) -> int:
        return self.checks_run - self.n_fail

    @property
    def pct_pass(self) -> str:
        return f"{self.n_pass / self.checks_run * 100:.1f}%" if self.checks_run else "0.0%"

    @property
    def pct_fail(self) -> str:
        return f"{self.n_fail / self.checks_run * 100:.1f}%" if self.checks_run else "0.0%"

    @property
    def not_run_layers(self) -> list:
        return [name for name in LAYER_ORDER if name in self.layers and not self.layers[name].ran]

    @property
    def weighted_score(self) -> float:
        return sum(layer.weighted_contribution for layer in self.layers.values())

    @property
    def achievable_max(self) -> float:
        """The plain sum of weight*100 over layers that ran — never renormalised (D-01)."""
        return sum(layer.weight * 100 for layer in self.layers.values() if layer.ran)

    @property
    def score_display(self) -> str:
        # Summing the LAYER_WEIGHTS literals is not exactly representable in binary floating
        # point, so callers and tests compare this one-decimal rendering, never the raw float.
        return f"{self.weighted_score:.1f}% of {self.achievable_max:.1f}% achievable"

    @property
    def score_band(self) -> str:
        """Driven by the capped weighted score out of 100, never by the score relative to the
        achievable maximum (D-03) — a 72-of-80 run is amber, not green."""
        if self.weighted_score >= 80:
            return "green"
        if self.weighted_score >= 60:
            return "amber"
        return "red"

    @property
    def headline_distinct(self) -> int:
        """D-10: the plain sum of the four non-Schema layers' distinct counts — a settlement
        failing in two layers counts twice in the headline and once in each layer. Schema is
        excluded because it has no distinct-row line (its "rows" are columns, D-13)."""
        return sum(
            layer.distinct_issue_rows for name, layer in self.layers.items() if name != "Schema"
        )

    @property
    def headline_findings(self) -> int:
        return sum(
            layer.findings for name, layer in self.layers.items() if name != "Schema"
        )

    @property
    def headline_issue_line(self) -> str:
        return f"{self.headline_distinct:,} issue rows across {self.headline_findings:,} findings"


def build_summary(filename, layer_results, mlos_row_count, takeoff_row_count) -> QcSummary:
    """Build the one shared ``QcSummary`` from the five layers' ``(checks, detail)`` pairs.

    ``layer_results`` is a ``dict[str, tuple[list, pd.DataFrame]]`` keyed by layer name. Fails
    loud, mirroring ``register()``'s own convention: raises ``KeyError`` naming any key not in
    ``LAYER_ORDER``, and raises ``KeyError`` naming any member of ``LAYER_ORDER`` absent from the
    dict — a site that forgets a layer cannot silently produce a four-layer summary (F11's shape).
    """
    unknown = set(layer_results) - set(LAYER_ORDER)
    if unknown:
        raise KeyError(f"Unknown layer name(s) in layer_results: {sorted(unknown)!r}")
    missing = [name for name in LAYER_ORDER if name not in layer_results]
    if missing:
        raise KeyError(f"layer_results is missing required layer(s): {missing!r}")

    layers = {}
    for name in LAYER_ORDER:
        checks, detail = layer_results[name]
        if name == "Schema":
            source_row_count = None
        elif name == "Takeoffpoint":
            source_row_count = takeoff_row_count
        else:
            source_row_count = mlos_row_count
        layers[name] = LayerSummary(
            name=name,
            checks=checks,
            detail=detail,
            weight=LAYER_WEIGHTS[name],
            source_row_count=source_row_count,
        )
    return QcSummary(filename=filename, layers=layers)
