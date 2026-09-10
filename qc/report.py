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
from datetime import datetime
from io import BytesIO

import openpyxl
import pandas as pd
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

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

# D-06: the unconditional sheet order. "Columns Renamed" stays out of this tuple and is
# appended by build_workbook only when a rename is supplied (Phase 2 D-11) -- a clean
# submission gets no sheet at all, not an empty one.
SHEET_NAMES = (
    "QC Report Cover",
    "QC Summary",
    *(f"{name} Issue Detail" for name in LAYER_ORDER),
    "Raw MLoS Data",
    "Raw Takeoffpoint Data",
)

# The detail-sheet title text per layer (D-09's write_detail keeps this styled title row
# unchanged). Schema's "rows" are missing columns, not source rows (D-13's precedent) so its
# title says so rather than reusing the four row-oriented layers' wording.
_DETAIL_TITLES = {
    "Schema": "Schema Table — Missing Columns",
    "MLoS": "MLoS Table — Detailed Issue Rows",
    "Settlement": "Settlement Table — Detailed Issue Rows",
    "Takeoffpoint": "Takeoffpoint Table — Detailed Issue Rows",
    "Boundary": "Boundary Table — Detailed Issue Rows",
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

    @property
    def gap_clause(self) -> str:
        """The empty string when every layer ran, otherwise each unrun layer's own clause
        joined with "; ", in LAYER_ORDER order. D-05's generic requirement: written for the
        (currently unreachable) case of more than one unrun layer, not a case the user has
        ruled on."""
        return "; ".join(
            f"{name} layer not checked ({self.layers[name].not_run_reason})"
            for name in LAYER_ORDER
            if name in self.layers and not self.layers[name].ran
        )

    @property
    def verdict_short(self) -> str:
        """CLEAN or FAILING (n check(s)) -- no gap clause. Exists solely for the D-16 email
        subject template; every prose site reads verdict_text instead."""
        if self.n_fail == 0:
            return "CLEAN"
        return f"FAILING ({self.n_fail} check{'s' if self.n_fail != 1 else ''})"

    @property
    def verdict_text(self) -> str:
        """The two-state verdict (CLEAN / FAILING), with the D-04 gap clause appended in the
        same position after either state whenever a layer did not run. A third state is Phase
        6's advisory tier, not this phase's -- this property returns exactly one of two
        prefixes, ever."""
        if not self.gap_clause:
            return self.verdict_short
        return f"{self.verdict_short} — {self.gap_clause}"


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


def summary_rows(summary: QcSummary) -> list:
    """Row dicts for the combined ``QC Summary`` sheet (D-06/D-07/D-08).

    One row per check that ran, in registry canonical order, plus exactly one placeholder row
    for any layer that ran zero checks, in that layer's canonical position -- so the sheet
    alone can never read as a four-layer tool (D-07). The ``Layer`` column is sourced from
    ``qc.results.get_rule`` (the single registry), never a second hand-kept lookup
    (03-RESEARCH.md Pattern 2, the same class of divergence INTEG-03/F7 already closed once for
    column names). A check whose registry layer disagrees with the layer whose checks list it
    arrived in raises ``ValueError`` naming the identifier and both layer names, rather than
    silently misfiling it on the sheet.

    Does not rely on the caller having sorted a layer's checks: ``sort_by_registry`` is applied
    here, inside this function, to every layer's own checks list before it is emitted.
    """
    rows = []
    for name in LAYER_ORDER:
        layer = summary.layers[name]
        if not layer.ran:
            rows.append({
                "Layer": name,
                "Status": "—",
                "Rule#": "—",
                "QC Check": f"{name} — not run: {layer.not_run_reason}",
                "Description": f"{name} layer contributed no score this run",
                "Failing Rows": "n/a",
                "Total Rows": "n/a",
                "Fail %": "n/a",
            })
            continue
        for check in sort_by_registry(layer.checks):
            registry_layer = get_rule(check["Rule#"]).layer
            if registry_layer != name:
                raise ValueError(
                    f"Rule {check['Rule#']!r} is registered under layer {registry_layer!r} but "
                    f"arrived in the {name!r} layer's checks list -- a rule is registered under "
                    f"the wrong layer and would be silently misfiled on the QC Summary sheet"
                )
            rows.append({
                "Layer": name,
                "Status": check["Status"],
                "Rule#": check["Rule#"],
                "QC Check": check["QC Check"],
                "Description": check["Description"],
                "Failing Rows": check["Failing Rows"],
                "Total Rows": check["Total Rows"],
                "Fail %": check["Fail %"],
            })
    return rows


def build_workbook(summary: QcSummary, mlos_raw: "pd.DataFrame", takeoff_df: "pd.DataFrame",
                    column_renames=None) -> bytes:
    """Build the downloadable QC report workbook, relocated from ``app.py``'s
    ``build_excel_report`` (Analog D, 03-PATTERNS.md).

    Task 1's scope: the cover reads ``summary.verdict_text``/``summary.score_display`` instead
    of recomputing a two-layer failing-count sum (F1/VERDICT-01/VERDICT-02) -- the case that
    filed a Boundary-only failure as CLEAN. The sheet set (still ``MLoS QC Summary`` /
    ``Takeoffpoint QC Summary`` / two detail sheets / two raw sheets / the conditional renames
    sheet) and the per-cell styling are unchanged here; task 2 reshapes the sheet set into one
    combined ``QC Summary`` plus a detail sheet per layer (D-06/D-07), and task 3 removes
    per-cell styling from the raw and detail sheets (ENGINE-08/D-09).
    """
    out = BytesIO()
    wb = openpyxl.Workbook()

    BLU = "1D4ED8"
    GRN = "15803D"; LGN = "F0FDF4"
    RED = "DC2626"; LRD = "FFF1F2"
    LGY = "F8FAFC"
    WHT = "FFFFFF"

    hdr_fill  = PatternFill("solid", fgColor=BLU)
    hdr_font  = Font(bold=True, color=WHT, size=10, name="Calibri")
    pass_fill = PatternFill("solid", fgColor=LGN)
    fail_fill = PatternFill("solid", fgColor=LRD)
    lgry_fill = PatternFill("solid", fgColor=LGY)
    body_font = Font(size=10, name="Calibri")
    bold_font = Font(bold=True, size=10, name="Calibri")
    ctr       = Alignment(horizontal="center", vertical="center", wrap_text=True)
    lft       = Alignment(horizontal="left",   vertical="center", wrap_text=True)
    thin      = Side(style="thin", color="D1D5DB")
    bdr       = Border(left=thin, right=thin, top=thin, bottom=thin)

    def hdr_row(ws, row, cols):
        for ci, col in enumerate(cols, 1):
            c = ws.cell(row=row, column=ci, value=col)
            c.fill = hdr_fill; c.font = hdr_font; c.alignment = ctr; c.border = bdr

    # ── Sheet 1: Cover ──
    ws = wb.active; ws.title = "QC Report Cover"
    ws.sheet_view.showGridLines = False
    ws.column_dimensions["A"].width = 38
    ws.column_dimensions["B"].width = 52
    ws.merge_cells("A1:B1")
    ws["A1"].value = "MLOS CHECKOUT — QUALITY CONTROL REPORT"
    ws["A1"].font  = Font(bold=True, size=15, color=WHT, name="Calibri")
    ws["A1"].fill  = PatternFill("solid", fgColor=BLU)
    ws["A1"].alignment = ctr
    ws.row_dimensions[1].height = 38

    # D-08: exactly five metadata rows -- File, Generated At, MLoS Rows, Takeoffpoint Rows,
    # Weighted Score -- and no per-layer counts. Per-layer counts moved to the QC Summary sheet.
    meta = [
        ("File",              summary.filename),
        ("Generated At",      datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        ("MLoS Rows",         len(mlos_raw)),
        ("Takeoffpoint Rows", len(takeoff_df)),
        ("Weighted Score",    summary.score_display),
    ]
    for ri, (k, v) in enumerate(meta, 3):
        ka = ws.cell(row=ri, column=1, value=k); ka.font=bold_font; ka.border=bdr
        vb = ws.cell(row=ri, column=2, value=v); vb.font=body_font; vb.border=bdr; vb.alignment=lft
        if ri % 2 == 0: ka.fill=lgry_fill; vb.fill=lgry_fill

    # Verdict row index computed from the metadata block's own length, never hard-coded -- a
    # literal row number here is exactly what would land the verdict inside the metadata table
    # the moment the block's length changed (ten rows down to five, D-08).
    last_meta_row = 2 + len(meta)
    verdict_row = last_meta_row + 2
    ws.merge_cells(f"A{verdict_row}:B{verdict_row}")
    vd = ws.cell(row=verdict_row, column=1)
    vd.value     = summary.verdict_text
    vd.fill      = PatternFill("solid", fgColor=GRN if summary.n_fail == 0 else RED)
    vd.font      = Font(bold=True, size=12, color=WHT, name="Calibri")
    vd.alignment = ctr
    ws.row_dimensions[verdict_row].height = 30

    # helper to write the one combined QC summary sheet (D-06): rows come from summary_rows(),
    # each carrying its own Layer column sourced from the registry. A placeholder row (an
    # unrun layer, D-07) gets the light-grey fill rather than pass or fail -- a not-run layer
    # is neither.
    def write_summary(ws_s, rows):
        ws_s.sheet_view.showGridLines = False
        ws_s.merge_cells("A1:H1")
        ws_s["A1"].value     = "Combined QC Check Summary — All Layers"
        ws_s["A1"].font      = Font(bold=True, size=13, color=WHT, name="Calibri")
        ws_s["A1"].fill      = PatternFill("solid", fgColor=BLU)
        ws_s["A1"].alignment = ctr
        ws_s.row_dimensions[1].height = 30
        cols = ["Layer","Status","Rule#","QC Check","Description","Failing Rows","Total Rows","Fail %"]
        hdr_row(ws_s, 2, cols)
        left_cols = {"QC Check", "Description"}
        for ri, row in enumerate(rows, 3):
            is_placeholder = row["Failing Rows"] == "n/a"
            is_fail = (not is_placeholder) and "FAIL" in row["Status"]
            for ci, key in enumerate(cols, 1):
                c = ws_s.cell(row=ri, column=ci, value=row[key])
                c.font=body_font; c.border=bdr
                c.alignment = lft if key in left_cols else ctr
                if is_placeholder:
                    c.fill = lgry_fill
                else:
                    c.fill = fail_fill if is_fail else pass_fill
        for i, w in enumerate([14,14,8,32,50,14,12,9], 1):
            ws_s.column_dimensions[get_column_letter(i)].width = w

    # helper to write issue detail sheet
    def write_detail(ws_d, title, detail_df):
        ws_d.sheet_view.showGridLines = False
        if detail_df.empty:
            ws_d["A1"].value     = f"✅ No issues — {title} passed all checks"
            ws_d["A1"].font      = Font(bold=True, size=12, color=WHT, name="Calibri")
            ws_d["A1"].fill      = PatternFill("solid", fgColor=GRN)
            ws_d["A1"].alignment = ctr
            return
        nc = len(detail_df.columns)
        ws_d.merge_cells(f"A1:{get_column_letter(nc)}1")
        ws_d["A1"].value     = title
        ws_d["A1"].font      = Font(bold=True, size=12, color=WHT, name="Calibri")
        ws_d["A1"].fill      = PatternFill("solid", fgColor=RED)
        ws_d["A1"].alignment = ctr
        ws_d.row_dimensions[1].height = 26
        hdr_row(ws_d, 2, list(detail_df.columns))
        for ri, (_, row) in enumerate(detail_df.iterrows(), 3):
            for ci, v in enumerate(row.values, 1):
                c = ws_d.cell(row=ri, column=ci, value=v)
                c.font=body_font; c.border=bdr; c.alignment=lft
                if ri % 2 == 0: c.fill = PatternFill("solid", fgColor="FFF5F5")
        for ci in range(1, nc+1):
            mx = max(len(str(detail_df.columns[ci-1])),
                     max((len(str(v)) for v in detail_df.iloc[:, ci-1].astype(str)), default=0))
            ws_d.column_dimensions[get_column_letter(ci)].width = min(max(mx+3, 12), 42)

    # helper to write raw data sheet
    def write_raw(ws_r, df):
        ws_r.sheet_view.showGridLines = False
        if df.empty: return
        hdr_row(ws_r, 1, list(df.columns))
        for ri, (_, row) in enumerate(df.iterrows(), 2):
            for ci, v in enumerate(row.values, 1):
                c = ws_r.cell(row=ri, column=ci, value=v)
                c.font=body_font; c.border=bdr; c.alignment=lft
                if ri % 2 == 0: c.fill = lgry_fill
        for ci in range(1, len(df.columns)+1):
            ws_r.column_dimensions[get_column_letter(ci)].width = 18

    # D-06: one combined QC Summary sheet, then one detail sheet per layer in LAYER_ORDER --
    # never concatenated across layers (Takeoffpoint keys on its own table, Schema on columns,
    # so a union would be mostly blanks).
    write_summary(wb.create_sheet("QC Summary"), summary_rows(summary))
    for name in LAYER_ORDER:
        write_detail(
            wb.create_sheet(f"{name} Issue Detail"),
            _DETAIL_TITLES[name],
            summary.layers[name].detail,
        )
    write_raw(wb.create_sheet("Raw MLoS Data"),         mlos_raw)
    write_raw(wb.create_sheet("Raw Takeoffpoint Data"), takeoff_df)

    # ── Columns Renamed (Phase 2 INTEG-03/D-11) ───────────────────────────────────────────
    # Reported in exactly two places: this sheet and the on-screen expander (Tab 1). No
    # Pass/Fail, no rule identifier, no score weight -- a rename is not a defect. A clean
    # submission (nothing renamed) gets no sheet at all, not an empty one.
    if column_renames:
        ws_r = wb.create_sheet("Columns Renamed")
        ws_r.sheet_view.showGridLines = False
        ws_r.merge_cells("A1:B1")
        ws_r["A1"].value     = "Columns Renamed at Load"
        ws_r["A1"].font      = Font(bold=True, size=12, color=WHT, name="Calibri")
        ws_r["A1"].fill      = PatternFill("solid", fgColor=BLU)
        ws_r["A1"].alignment = ctr
        ws_r.row_dimensions[1].height = 26
        hdr_row(ws_r, 2, ["Original Header", "Resolved To"])
        for ri, (orig, resolved) in enumerate(sorted(column_renames.items()), 3):
            c1 = ws_r.cell(row=ri, column=1, value=orig)
            c2 = ws_r.cell(row=ri, column=2, value=resolved)
            for c in (c1, c2):
                c.font = body_font; c.border = bdr; c.alignment = lft
                if ri % 2 == 0:
                    c.fill = lgry_fill
        ws_r.column_dimensions["A"].width = 32
        ws_r.column_dimensions["B"].width = 32

    wb.save(out)
    return out.getvalue()
