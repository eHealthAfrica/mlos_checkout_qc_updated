# Phase 3: Verdict and Report Integrity - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-10
**Phase:** 3-Verdict and Report Integrity
**Areas discussed:** Score when a layer did not run, Report workbook shape, What one issue row means, Email content

---

## Score when a layer did not run

**Q1. When Takeoffpoint ran zero checks, how should the overall weighted score read?**

| Option | Description | Selected |
|--------|-------------|----------|
| Capped total, out of 100 (Recommended) | Takeoffpoint row shows n/a and contributes 0; a perfect four-layer file scores 80.0% | |
| Capped total, shown against achievable | Same arithmetic, displayed as "72.0% of 80.0% achievable" | ✓ |
| Renormalise weights over layers that ran | Perfect four-layer file scores 100%; flagged as reopening F6 | |

**User's choice:** Capped total, shown against achievable.

**Q2. When every check that ran passed but Takeoffpoint did not run, what should the verdict say?**

| Option | Description | Selected |
|--------|-------------|----------|
| CLEAN, with the gap named (Recommended) | "CLEAN — Takeoffpoint layer not checked (no Takeoffpoint data supplied)" everywhere | ✓ |
| Plain CLEAN | Verdict text unchanged; n/a only in score table and cover rows | |
| Not CLEAN until all layers run | Third verdict state INCOMPLETE | |

**User's choice:** CLEAN, with the gap named.

**Q3. In the score breakdown table, what should the Takeoffpoint row show when it did not run?**

| Option | Description | Selected |
|--------|-------------|----------|
| Pass rate n/a, contribution n/a (Recommended) | Both cells n/a; Total row caption states achievable maximum | |
| Pass rate n/a, contribution 0.0% | Contribution numeric so the column sums visibly | |

**User's choice:** Free text — "the score is 0". Interpreted and confirmed as pass rate n/a, contribution 0.

**Q4. When the ceiling is 80%, which number drives the colour band?**

| Option | Description | Selected |
|--------|-------------|----------|
| Absolute score (Recommended) | 72.0% out of 100 is amber | ✓ |
| Score relative to achievable | 72 of 80 treated as 90%, green | |

**User's choice:** Absolute score.

---

## Report workbook shape

**Q1. How should the workbook lay out the five layers?**

| Option | Description | Selected |
|--------|-------------|----------|
| One summary + one detail sheet per layer (Recommended) | 14 sheets; existing sheet names preserved | |
| One combined summary sheet + detail sheet per layer | 10 sheets; single QC Summary with Layer column | ✓ |
| You decide | Planner picks | |

**User's choice:** One combined summary sheet + detail sheet per layer.

**Q2. What should the cover sheet carry beyond the verdict?**

| Option | Description | Selected |
|--------|-------------|----------|
| Per-layer table plus weighted score (Recommended) | One row per layer with counts, then score and verdict | |
| Verdict and weighted score only | Metadata rows plus score and full-layer verdict | ✓ |
| Today's cover, extended to five layers | Current row pattern with three more layers; no score | |

**User's choice:** Verdict and weighted score only.

**Q3. ENGINE-08 strips per-cell font and border assignment from the raw-data sheets. How far should that go?**

| Option | Description | Selected |
|--------|-------------|----------|
| Raw and detail sheets: header styling only (Recommended) | Both raw and five detail sheets plain values with styled header and widths | ✓ |
| Raw sheets only, header styling kept | Exactly ENGINE-08 as written | |
| Raw sheets only, no styling at all | Bare data dump | |

**User's choice:** Raw and detail sheets, header styling only. Accepted as going beyond ENGINE-08's letter.

**Q4. On the combined summary sheet, how should a layer that ran zero checks appear?**

| Option | Description | Selected |
|--------|-------------|----------|
| One placeholder row per skipped layer (Recommended) | Row in canonical position reading "Takeoffpoint — not run: …" with n/a cells | ✓ |
| No row; the cover states it | Summary lists only checks that ran | |

**User's choice:** One placeholder row per skipped layer.

---

## What one issue row means

**Q1. What should the headline Issue Rows figure count?**

| Option | Description | Selected |
|--------|-------------|----------|
| Distinct settlements + distinct takeoffpoints (Recommended) | Two numbers; a settlement failing in three layers counts once | |
| Sum of per-layer distinct counts | Each layer distinct, then added | ✓ |
| No headline total; per-layer figures only | Drop the metric | |

**User's choice:** Sum of per-layer distinct counts.

**Q2. What identifies one row when counting distinct issue rows within a layer?**

| Option | Description | Selected |
|--------|-------------|----------|
| Original row position in the checked frame (Recommended) | Index carried through; Boundary and Takeoffpoint must stop resetting it | ✓ |
| The id column already in the detail rows | ogc_fid or first column; may undercount on CSV | |
| You decide | Planner picks a provably unique key | |

**User's choice:** Original row position in the checked frame.

**Q3. Should the old rule-row pair count remain visible anywhere?**

| Option | Description | Selected |
|--------|-------------|----------|
| Show both, labelled (Recommended) | "312 issue rows across 1,040 findings" | ✓ |
| Distinct rows only | Pair count removed from summaries | |

**User's choice:** Show both, labelled.

**Q4. Should each layer's distinct issue-row count be shown against the layer's total rows?**

| Option | Description | Selected |
|--------|-------------|----------|
| Count with share of rows (Recommended) | "312 issue rows (6.2% of 5,000) across 1,040 findings" | ✓ |
| Count only | No percentage at layer level | |

**User's choice:** Count with share of rows.

---

## Email content

**Q1. How should the email body change?**

| Option | Description | Selected |
|--------|-------------|----------|
| One block per layer, then the check list (Recommended) | Verdict, score, five layer blocks, check list under layer headings; plain text | ✓ |
| Add the missing Settlement line only | Minimal change | |
| Mirror the report cover exactly | Same lines as the cover plus summary as text | |

**User's choice:** One block per layer, then the check list.

**Q2. Which checks should the check-by-check list include?**

| Option | Description | Selected |
|--------|-------------|----------|
| Every check that ran (Recommended) | Passing and failing in canonical order | ✓ |
| Failing checks only | Shorter email | |

**User's choice:** Every check that ran.

**Q3. Should the subject line carry the verdict?**

| Option | Description | Selected |
|--------|-------------|----------|
| Verdict in the subject (Recommended) | "MLoS QC: FAILING (12 checks) — file.xlsx" | ✓ |
| Keep "MLoS QC checks for {filename}" | Unchanged | |

**User's choice:** Verdict in the subject.

---

## Claude's Discretion

- Location and naming of the Streamlit-free module holding verdict, score, counting, report and email-body logic.
- Packaging of the single shared computation the four presentation sites consume.
- VERDICT-06 delivered as a standing test over every table and export, not a re-sort inside the boundary layer.
- Generate Report tab layout for five layers.
- Whether the achievable maximum appears in the top metric bar or only in Tab 2 and the cover.
- Placeholder-row cell values on the summary sheet.
- README §8, §10, §11 rewrite (required).
- Handling of the detail-frame index change in parity and baseline tests.

## Deferred Ideas

- Email recipients into Space secrets (Phase 4, DEPLOY-03).
- Attaching the Excel report to the email (new capability, M2 backlog).
- Layer weights and colour-band thresholds in configuration (Phase 6 CONFIG).
- HTML email (M2 presentation question).
- Uniform identifier scheme (already deferred at Phase 1 D-05).
