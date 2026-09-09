# Pitfalls Research

**Domain:** Hosted geospatial data-QC tooling for public-health microplanning (point-in-polygon
boundary validation, free-tier Streamlit/Hugging Face deployment, OIDC auth) — specific to the
MLoS Checkout QC tool's M2 (central deployment) and M3 (new QC layers: point-in-polygon,
distance sanity, population plausibility, coverage) milestones.
**Researched:** 2026-09-09
**Confidence:** MEDIUM overall — geometry/library semantics are HIGH-confidence (verified against
Shapely's own docs); Nigeria-specific boundary-dataset and HF-hosting behavior is MEDIUM
(community/forum sourced, cross-checked across multiple independent pages, no single
authoritative source).

This file does **not** repeat the 14 defects already catalogued in the September 2026 code audit
(see PROJECT.md). It covers mistakes specific to *adding* M2 hosting and M3 geometry/threshold
layers on top of that fixed baseline.

---

## Critical Pitfalls

### Pitfall 1: `contains()` silently rejects settlements sitting exactly on a ward line

**What goes wrong:**
The natural first implementation of "is this point inside this ward polygon" is
`polygon.contains(point)`. Shapely's `contains()` is defined to exclude the boundary: it
returns `True` only if the point's interior lies in the polygon's *interior*, not its edge.
Any settlement whose coordinates were snapped, rounded, or originally captured with a GPS unit
that landed the point precisely on (or numerically indistinguishable from) the ward boundary
will be flagged as "outside its ward" even though it is legitimately on the line — which happens
constantly with administrative boundary data because boundaries frequently run along roads,
rivers, or straight-line surveyed edges that settlements cluster next to.

**Why it happens:**
Point-in-polygon is usually prototyped with `contains()` because it is the first method
developers reach for, and it behaves correctly for the overwhelming majority of interior test
cases during development — the boundary-exact case only surfaces at scale, against real data,
after ship.

**How to avoid:**
Use `polygon.covers(point)` (or `polygon.intersects(point)` if touching-a-neighbor-ward should
also count) for the pass/fail determination, not `contains()`. Then use a *separate*, explicitly
labeled "on boundary" state — computed via `polygon.boundary.distance(point) < epsilon` — to
distinguish "cleanly inside," "on the line (ambiguous, needs human judgment)," and "clearly
outside." Never collapse the on-boundary case into a hard fail; that is a QC-honesty issue
(see Pitfall 6).

**Warning signs:**
- QC output shows settlements near ward edges failing point-in-polygon at a noticeably higher
  rate than settlements in ward interiors.
- Officers report "this settlement is obviously in the right ward" for flagged records that,
  on inspection, sit within a few meters of the boundary line.

**Phase to address:** M3 (point-in-polygon layer build).

---

### Pitfall 2: Two ward-code-matched boundary datasets don't agree on the same ward's shape

**What goes wrong:**
GRID3 publishes Nigeria's Operational Ward Boundaries in multiple versions (v1.0, Dec 2020,
all 36 states + FCT; v3.0, later, partial-state coverage) built with CIESIN/WorldPop, and
GRID3 itself states these are **operational-use boundaries, not yet fully validated by the
relevant government authorities**. NPC (National Population Commission) enumeration area
boundaries and individual state GIS/SDG units maintain their own ward geometries, which can
diverge from GRID3's for the same nominal ward *code* — different vertex counts, different
areas near contested LGA/ward splits, sometimes different ward-code-to-name mappings entirely
after a ward creation/boundary-adjustment exercise. A settlement correctly assigned to its ward
under one dataset's boundary can fall outside that ward's polygon under another.

**Why it happens:**
There is no single canonical Nigerian ward boundary authority that all downstream tools
consume identically; boundary data is versioned, state-GIS-maintained, and periodically revised
without a shared changelog that health-sector tools subscribe to. The existing 9,410-row
`ward_boundary_ref.csv` in this repo is a snapshot of *some* source at *some* point in time —
the audit does not establish provenance/vintage, and M3 will pair it with polygon geometry from
a (likely different) GRID3 export.

**How to avoid:**
- Record the boundary dataset's source and version/vintage explicitly (in the report and in
  `config.json`), so a "wrong ward" flag can be traced back to "which boundary snapshot said so."
- Treat point-in-polygon failure as "outside according to boundary reference vX" — never bare
  "outside its ward" — in both the UI and the Excel export (this mirrors F13 in the M1 fix list,
  which already establishes the norm of surfacing reference-data provenance rather than hiding it).
- Before wiring polygons into B2, reconcile the polygon source's ward codes against the existing
  `ward_boundary_ref.csv` codes; do not assume they are the same vintage just because row counts
  are close to 9,410.

**Warning signs:**
- Point-in-polygon fail rate is not randomly distributed — it clusters in specific states or
  LGAs, suggesting a boundary-revision mismatch rather than genuinely misplaced settlements.
- A ward code present in `ward_boundary_ref.csv` has no matching (or a geometrically
  implausible) polygon in the geometry source.

**Phase to address:** M3 (point-in-polygon layer build), with the provenance-recording pattern
ideally established in M1's boundary-reference work (F13) so M3 inherits it rather than
reinventing it.

---

### Pitfall 3: Settlements legitimately outside their assigned ward due to boundary vintage

**What goes wrong:**
Even with one consistent, validated boundary dataset, a settlement can be correctly assigned
(by the field team, in the MLoS record) to a ward whose *boundary as currently drawn* does not
contain it — because the settlement was enumerated against an older ward delineation, or the
ward was split/redrawn after the settlement's ward assignment was made, or the settlement sits
in a genuinely disputed/unresolved boundary area between two LGAs. This is not a data-entry
error; it's a real-world administrative geography problem that a hard pass/fail geometry check
cannot resolve.

**Why it happens:**
Ward boundaries are political/administrative artifacts that change over time (creation,
splitting, re-demarcation) on a cadence that field enumeration and central GIS reference data
do not always track in lockstep. A "point-in-polygon" check implicitly assumes both sides
(the point's ward label and the polygon's ward code) come from the same moment in
administrative history.

**How to avoid:**
Point-in-polygon must ship as a **flag for review**, not an auto-fail. Report it as "ward code
X's polygon does not contain this settlement's coordinates" and let the officer confirm or
correct — mirroring the QC tool's existing posture (per PROJECT.md) that a wrong verdict is
worse than an unresolved flag. Do not let this rule contribute to the weighted score at the same
severity as a hard data-integrity defect (e.g., a null required field); consider a distinct
"boundary disagreement" severity tier separate from "data error" severity.

**Warning signs:**
- A cluster of "boundary fail" settlements all belong to one ward that was recently split, or
  to a state where ward re-demarcation is known to be in progress.
- Officers repeatedly override/dismiss the same flag for the same ward across submissions.

**Phase to address:** M3 (point-in-polygon layer), decision needed during phase planning on
scoring weight/severity — flag this explicitly as a roadmap question, not an implementation
detail to improvise mid-build.

---

### Pitfall 4: Picking `contains()`/geometry ops on lon/lat coordinates without ever fixing a CRS, then mixing planar and geodesic assumptions across layers

**What goes wrong:**
Shapely (via GEOS) is CRS-agnostic — it treats whatever numbers you hand it as a flat Cartesian
plane. Feeding raw WGS84 longitude/latitude pairs into `Polygon`/`Point` objects makes
point-in-polygon *topology* checks fine (a point is either inside a ring of vertices or it
isn't, regardless of units), but is silently wrong for anything involving distance, area, or
buffering computed on those same coordinates: 1 degree of longitude is not 1 degree of latitude
in real-world meters, and the discrepancy grows as you move north (irrelevant near the equator,
but Nigeria spans ~4°N to ~14°N, so it is not uniform across the country either). If the new B2
point-in-polygon layer and the existing/new distance layer (settlement-to-takeoffpoint) end up
sharing geometry objects or a "nearest boundary distance in meters" convenience feature gets
added to the polygon check, this bites immediately.

**Why it happens:**
Point-in-polygon "just works" without a CRS during development because topological containment
doesn't need real-world units — so there's no error to catch until someone computes a distance,
area, or buffer using the same unprojected geometry, often much later, in a different function.

**How to avoid:**
- For **point-in-polygon containment**: no projection needed; WGS84 lon/lat is fine since it's
  a pure topological test (Pitfall 1's boundary-inclusivity issue is separate and still applies).
- For **any distance-in-meters computation** (settlement-to-takeoffpoint, "distance to nearest
  ward boundary," buffering by a meter-based threshold): either (a) compute geodesic distance
  directly on WGS84 coordinates using `pyproj.Geod` / `Geod.inv()`, or (b) project to a suitable
  equal-distance/equal-area CRS first. Do not silently reuse the unprojected polygon/point objects
  built for containment checks as inputs to a meter-based threshold comparison.
- Document which CRS convention each function assumes, directly in the function, since this is
  exactly the kind of implicit-contract bug the M1 audit was created to catch elsewhere in the
  codebase (F4: "one frame of record").

**Warning signs:**
- A new "distance to boundary" or buffer-based rule produces distances that are off by roughly
  the degrees-to-meters conversion factor (~111km per degree at the equator, less at higher
  latitude) — a strong tell that raw degree deltas leaked into a meters-denominated threshold.
- Code review finds a `Point`/`Polygon` object created for the containment check being passed
  directly into a `.distance()` call used for a meter threshold elsewhere.

**Phase to address:** M3 (both the point-in-polygon layer and the distance-sanity layer) — treat
this as a shared-geometry-module design concern to settle once, not per-rule.

---

### Pitfall 5: Haversine looks "close enough" but is the wrong default to reach for by habit

**What goes wrong:**
The existing codebase already uses a NumPy-vectorized Haversine formula for one proximity check
(per the architecture doc). Haversine assumes a perfect sphere (radius ≈ 6,371 km); WGS84 is an
oblate spheroid. The resulting systematic error versus a true geodesic (e.g., `pyproj.Geod`,
which uses Karney's algorithm) is small in relative terms and *smaller near the equator* than
near the poles — which is a reason Nigeria's latitude range (~4°N–14°N) makes Haversine a
defensible choice for this tool, not a reason to stop thinking about it. The trap is copying the
same Haversine helper into the new M3 distance-sanity layer by habit, at a threshold precision
where the error matters (e.g., a hard "flag if >500m" cutoff), without deciding — and
recording — that the error is acceptable at that threshold.

**Why it happens:**
Haversine is the formula everyone already has in the codebase and everyone's seen in a tutorial;
extending it to a new rule is the path of least resistance, and the error is genuinely small
enough at typical settlement-to-takeoffpoint distances (usually sub-tens-of-km) that it will not
visibly break anything — which is exactly why nobody questions it, and why threshold-adjacent
records near a hard cutoff are the ones silently misclassified.

**How to avoid:**
- Keep Haversine for the new distance-sanity layer (it's adequate at Nigeria's latitudes and at
  the short distances involved) but state that decision explicitly in `config.json` or code
  comments, with the error bound, so it's a decision on record rather than an unexamined default —
  this is the same discipline the project already applies to plausibility thresholds.
  If greater precision is ever wanted cheaply, `pyproj.Geod.inv()` is a drop-in-accuracy upgrade
  with negligible added computation cost at this row scale.
- Do not use planar/Euclidean (Pythagorean) distance on raw lon/lat degrees for anything —
  that error is much larger than the Haversine-vs-geodesic gap and does not stay small even at
  low latitudes over tens of km.

**Warning signs:**
- A distance-sanity threshold flags/passes records inconsistently near the cutoff when
  re-computed with a different distance formula — evidence the formula choice, not the data,
  is driving the verdict at the margin.

**Phase to address:** M3 (distance-sanity layer design) — decide and document the formula choice
during phase planning, not silently inside implementation.

---

### Pitfall 6: A "rule of thumb" threshold quietly turns "unusual" into "wrong"

**What goes wrong:**
Population plausibility and team/activity coverage thresholds are explicitly rules of thumb
(per PROJECT.md), not a published standard. The failure mode is that once a threshold rule is
implemented as a QC "check" that contributes to the weighted score exactly like a hard
data-integrity rule (e.g., a null required field, or a genuinely duplicated GUID), officers and
the data team start treating "population implausible" or "coverage insufficient" as equivalent
in severity and certainty to "this file has a missing mandatory value" — when it is really a
statistical outlier signal that may have a perfectly good explanation (a genuinely large
settlement, a team legitimately covering two adjacent wards on one day).

**Why it happens:**
QC tools tend to have one output shape — a rule number, a pass/fail, a score contribution — and
it's far less work to bolt a new threshold rule onto that same shape than to build a second,
differently-treated category for "statistically unusual, needs a human look" versus
"definitively wrong." The scoring formula (Schema × 10% + MLoS × 40% + Settlement × 20% +
Takeoffpoint × 20% + Boundary × 10%, per the architecture doc) has no slot for "soft" flags that
don't move the pass/fail verdict.

**How to avoid:**
- Give plausibility/coverage rules a visibly different presentation from hard-integrity rules —
  e.g., a distinct "Review" or "Advisory" status alongside Pass/Fail, not folded into the same
  binary — so the *language* of the report never claims certainty the rule doesn't have.
  This is a report-design decision, not just a scoring-weight decision.
  A threshold check should never make "clean" mean "this file has no unusual values"; it should
  keep meaning "this file has no *known-wrong* values," matching the project's stated Core Value
  ("A file this tool calls clean is clean").
  Consider excluding these new layers from the weighted score entirely until they've been run
  against real submissions long enough to calibrate, or weighting them low and clearly labeled.
- Keep every threshold in `config.json` (already planned) with a comment explaining its
  provenance/rationale inline, not just its numeric value — so a future reviewer can tell "rule
  of thumb, set by X on date Y" from "validated against national data."
- Revisit thresholds against real submission data after the M2 rollout accumulates a submission
  log (the very thing M2 is building), rather than setting them once and never re-examining them.

**Warning signs:**
- Officers start disputing the *verdict*, not the *data*, on plausibility/coverage flags —
  a sign the report is presenting a rule-of-thumb as a fact.
  The weighted score visibly drops for files that a human reviewer would call clean, purely
  because of a threshold rule firing on a legitimate outlier.

**Phase to address:** M3 (plausibility + coverage layers), with the "distinct severity tier /
report language" decision made during phase planning before any rule code is written — it
determines report and scoring structure, not just rule logic.

---

### Pitfall 7: Ephemeral Space filesystem + git-backed dataset log = silent data loss or a corrupted append-only log under concurrent writes

**What goes wrong:**
A Hugging Face Space's own disk is explicitly ephemeral and wiped on rebuild/restart/sleep-wake
cycles — this is already correctly identified in PROJECT.md as the reason the submission log
goes to a private HF Dataset repo instead. The remaining risk is that the Dataset repo is itself
a git repository: `huggingface_hub`'s upload APIs (including the batching `CommitScheduler`)
reduce but do not eliminate concurrency hazards, and community reports document concurrency
errors when multiple processes access/write shared Hub-backed files at the same time. If two
officers submit within the same short window and the app appends to the log with two independent
commits (rather than one serialized writer), the second commit can race the first, silently drop
a row, or throw an error the officer never sees because Streamlit's UI doesn't surface a failed
background upload.

**Why it happens:**
"Append to a dataset repo" sounds like "append a row to a file," but it is actually "make a git
commit," and git commits from concurrent, independent processes (two separate Space visitor
sessions, each running its own Python process) are not automatically serialized unless the
application explicitly manages that — HF's `CommitScheduler` helps within a *single* process's
background thread, not across concurrent user sessions each making their own commit calls.

**How to avoid:**
- Route all writes to the submission log through a single serialization point in the app (e.g.,
  a lock, a queue, or by having exactly one long-lived background thread/process own the commit,
  with request-handling threads only enqueuing to it) rather than each Streamlit session
  independently calling the Hub API.
  Alternatively, structure each submission as its own uniquely-named small file in the dataset
  repo (e.g., one JSON per submission, named by a UUID + timestamp) rather than all sessions
  editing one shared CSV/log file — this turns "concurrent writers to one file" into "concurrent
  independent file creates," which git and the Hub API handle far more gracefully, at the cost
  of needing a small aggregation step to read the log back as a table.
- Always check and surface the result of the commit call to the user/log — a failed background
  upload must not look like a successful submission.
- Test concurrent submission explicitly before considering M2 done: two simultaneous
  submissions (scripted, not just "seemed fine when I tried it once") should both appear in the
  log afterward.

**Warning signs:**
- Submission log row count doesn't match a manually tallied count of "QC runs completed" over a
  period with multiple simultaneous users.
- Any exception in HF Hub upload calls is only logged server-side (or nowhere) rather than
  surfaced to the submitting officer.

**Phase to address:** M2 (central deployment) — this must be validated with an actual concurrent
write test before rollout, not assumed safe because the Hub API "should handle it."

---

### Pitfall 8: OIDC works locally, then breaks — or silently no-ops — once hosted

**What goes wrong:**
`st.login()`'s OIDC flow depends on a redirect URI that must match exactly between what's
registered with the identity provider and the URL the app is actually served from. A localhost
dev URL (`http://localhost:8501`) and a hosted Hugging Face Space URL
(`https://huggingface.co/spaces/<org>/<space>` or its `.hf.space` subdomain) are different
origins; if the redirect URI is hardcoded, or copied from local `.streamlit/secrets.toml` without
updating for the deployed origin, login either fails outright with an IdP error, or — more
insidiously — appears to redirect successfully but lands the user in a fresh, unauthenticated
session because the identity cookie's domain/path doesn't match what the Space actually serves
from behind Hugging Face's proxying layer.

**Why it happens:**
OIDC redirect URI configuration lives in three places that must agree — the IdP's registered
app config, the app's own config/secrets, and the actual serving origin — and only one of those
(the serving origin) changes automatically between local dev and a hosted Space. Streamlit's
own rerun model compounds this: because `st.session_state` does not survive the redirect (each
OIDC round trip is effectively a new session, per Streamlit's own docs), any authentication logic
that tries to hold intermediate state in `session_state` across the redirect will appear to work
locally (fast round-trip, same-process quirks can mask the reset) and then fail once real network
latency and a different origin are involved.

**How to avoid:**
- If using Hugging Face's native `hf_oauth: true` Space metadata (rather than a separately
  registered Google/other OIDC app), the redirect URI is handled by the Spaces platform itself,
  which removes one whole class of misconfiguration — this is the reason PROJECT.md's Open Items
  section flags it as the preferred path over registering external OAuth credentials. Prefer it
  unless there's a concrete reason officers must authenticate via a different, pre-existing
  identity source.
- Read identity via `st.user` after the redirect completes, never by threading a token through
  `st.session_state` across the login round trip.
- Test the actual OIDC flow against the deployed Space URL before considering M2's auth work
  done — a login flow that "works locally" has verified nothing about the hosted redirect URI.

**Warning signs:**
- Login redirects to the IdP and back, but `st.user` shows unauthenticated, or the user is
  bounced into an infinite login loop.
- Auth "works" for the developer (who tested only locally or only once) but state officers
  report being unable to log in, or being logged out mid-session unexpectedly.

**Phase to address:** M2 (OIDC login) — resolve the provider choice (native `hf_oauth` vs.
external IdP) explicitly during phase planning per the Open Item already recorded in PROJECT.md,
since it changes which of these failure modes even applies.

---

### Pitfall 9: Real settlement coordinates + population figures on a third-party free tier is a governance decision disguised as a hosting decision

**What goes wrong:**
Settlement-level GPS coordinates and population figures for a national public-health
microplanning programme are sensitive at the aggregate level even when no single record is
"personal data" in the individual sense — they reveal operational detail about where health
teams work, population distribution used for targeting, and (via the submission log) which
officer submitted what, when. Hosting all of this — app, data-in-transit during QC, and the
append-only submission log — on a third party's free tier means accepting that party's security,
availability, and data-handling posture as this programme's posture, without a contract governing
it the way an enterprise agreement would. PROJECT.md already treats Space privacy as
non-negotiable and identifies SMTP-credential exposure as a known current problem (real
organisational email addresses committed in source); the risk here is treating "make the Space
private" and "move secrets to Space secrets" as sufficient, when the harder question — what
happens to this data if the free-tier account lapses, is suspended, or Hugging Face changes free-
tier terms — has no owner.

**Why it happens:**
Free-tier hosting decisions get made as engineering/cost decisions ("free tier is a stated
constraint," per PROJECT.md's Constraints section) without a parallel, explicit data-governance
sign-off from whoever owns the programme's data-protection obligations — the two conversations
happen in different rooms, and the technical team is not positioned to unilaterally accept
governance risk on the programme's behalf.

**How to avoid:**
- Confirm — as a named decision, not an assumption — that a private HF Space + private HF
  Dataset repo satisfies whatever data-handling policy governs this programme's settlement and
  population data, before M2 ships, ideally documented as a Key Decision in PROJECT.md the same
  way the storage-location decision already is.
- Ensure "private" is verified at both the Space level and the Dataset repo level independently
  — they are separate visibility settings, and defaulting one to public while intending the
  other private is an easy, silent mistake.
- Plan an export/backup path for the submission log that does not depend on Hugging Face
  remaining available or the account remaining in good standing — since the log itself is meant
  to be the durable record.
- Finish removing the already-known committed email addresses from git history (not just the
  current HEAD) before or during the M2 secrets migration — a rotated secret does not retroactively
  purge history, and a private Space does not make a public GitHub history private.

**Warning signs:**
- No one can name who signed off on "settlement + population data may live on Hugging Face's
  free tier" as a governance decision, only as a technical one.
- Git history still contains real email addresses or credentials after the M2 "move secrets out
  of the repo" work is marked done — moving *current* secrets doesn't remove *historical* ones.

**Phase to address:** M2 (deployment) — this is a prerequisite decision for M2, not a follow-on
concern; it should be resolved before the Space is made reachable by officers, and the git-history
scrub should be scoped explicitly (it's easy to satisfy the checklist item "secrets moved to Space
secrets" while leaving historical exposure untouched).

---

### Pitfall 10: Growing 27 rules to 35+ without a registry turns "which rule is this" back into a guessing game

**What goes wrong:**
The M1 audit found 11 checks sharing 2 rule numbers, and F3 is fixing that. Adding three new
layers (point-in-polygon, distance, plausibility, coverage) — several rules each — without a
structural registry that assigns and validates rule numbers reintroduces exactly the collision
risk M1 just closed, except at a larger scale (potentially 35+ rules instead of 27) and against
a codebase that, per PROJECT.md's stated plan, is only getting a `qc/` package and pytest suite
in M1 — meaning M3's job is to extend that structure, not to freelance around it.

**Why it happens:**
Without a single source of truth for "which rule numbers exist and what layer/severity they
belong to," it's natural for a new rule to be added by copy-pasting a similar existing check and
incrementing a number by eye — which is exactly the pattern that produced the original
duplicate-numbering defect.

**How to avoid:**
- Treat the M1 `qc/` package + pytest suite as the actual prerequisite for M3, not just a
  parallel workstream — PROJECT.md's own Key Decisions table already states this ("Extract to
  `qc/` + pytest inside M1, not M3... There is currently no seam to add it against"). Do not
  begin M3 rule implementation before that extraction is genuinely in place and passing.
- Require every new M3 rule to be added with: a unique rule ID assigned from one canonical list
  (not chosen ad hoc per PR), a test using the M1 three-format golden fixture pattern, and an
  entry in whatever report-coverage mechanism F1 establishes (so a new rule cannot silently be
  omitted from the downloaded report the way the audited Settlement/Takeoffpoint layers currently
  can be).
- Add a test that asserts rule-number uniqueness across the whole rule set as a standing CI
  check — cheap to write, and it's the exact defect class this pitfall describes.

**Warning signs:**
- A new M3 rule is added directly in `app.py`-adjacent code rather than through the `qc/`
  package interface established in M1.
- Two rules in the same layer share a number, or a rule number exists in code but not in the
  Excel report's rule-to-sheet mapping.

**Phase to address:** M1 establishes the prerequisite (the `qc/` package, pytest suite, rule
uniqueness as a testable property); M3 must be planned as strictly downstream of that
prerequisite being complete, not concurrent with it.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|-----------------|------------------|
| Using `contains()` instead of `covers()`/`intersects()` for point-in-ward checks | Slightly simpler mental model, matches most tutorials | Systematically mis-flags boundary-adjacent settlements | Never |
| Reusing the existing Haversine helper for new M3 distance rules without stating its error bound | No new code to write/review | Threshold-adjacent misclassifications become unexplainable later | Acceptable only if the error bound is written down alongside the threshold |
| Folding plausibility/coverage flags into the same Pass/Fail scoring as hard data-integrity rules | Reuses existing report/scoring plumbing | Erodes the "clean means clean" trust the whole tool is built on | Acceptable only as an explicit interim step with a stated follow-up to separate severity tiers |
| Each Streamlit session independently appending to the HF Dataset submission log | Fast to implement, no new architecture | Races/silent drops under concurrent officer submissions | Never at hosted scale (single-user local testing hides the bug entirely) |
| Skipping a concurrent-write test for the submission log before rollout | Ships M2 faster | First real incident happens in production, against real officers, with no local repro | Never — this is a pre-launch gate, not a nice-to-have |
| Adding M3 rules directly in `app.py` instead of through the M1 `qc/` package | Avoids waiting on M1's extraction work | Reopens the duplicate-rule-number defect class at larger scale | Never — M3 should be sequenced strictly after M1's `qc/` extraction |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|--------------|------------------|--------------------|
| Shapely polygon containment | Using `contains()` for ward-assignment pass/fail | Use `covers()`/`intersects()`, and surface "on boundary" as its own state |
| pyproj / geodesic distance | Assuming Haversine error is negligible everywhere without checking it against the actual threshold in use | State the error bound explicitly next to the distance threshold in config |
| GRID3 (or any single) ward polygon source | Assuming ward codes in the polygon file line up 1:1, same-vintage, with `ward_boundary_ref.csv` | Reconcile codes and record dataset version/vintage before wiring into B2 |
| Hugging Face Dataset repo as an append-only log | Writing to it as if it were a database with row-level locking | Serialize writes through one owner (queue/lock/one-file-per-submission) |
| Streamlit `st.login()` / OIDC | Storing auth state in `st.session_state` across the redirect | Read identity from `st.user` post-redirect; treat session_state as reset by the login round trip |
| Hugging Face Space secrets | Treating "moved to Space secrets" as equivalent to "removed from git history" | Scrub git history separately; rotate any previously-committed credentials |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|-----------------|
| Naive per-point polygon containment loop over 9,410 ward polygons for every settlement row | QC run time balloons on large state files | Pre-filter by state/LGA (already-known ward code) before testing containment, or use a spatial index (STRtree) rather than testing every settlement against every polygon | Noticeable above a few thousand settlement rows tested against the full national ward set without pre-filtering |
| Loading full national ward polygon geometry into memory on every QC run inside a 16GB-RAM free-tier Space that's also running a memory-hungry Excel report builder | Increased OOM risk during large-file validation, exactly the scenario the Key Decisions table already flags for the existing quadratic proximity check | Cache parsed geometry once (module-level or `st.cache_resource`, not `st.cache_data`, since geometry objects aren't cheaply hashable/copyable) rather than re-parsing per run | At the same large-state-file scale the existing SQ4 quadratic check already strains memory on |
| Concurrent Hub API commit calls without batching | Occasional lost or delayed submission-log rows under simultaneous officer use | Serialize writes (see Pitfall 7) | As soon as two officers use the Space at genuinely the same time — plausible with a state-level rollout, not just a theoretical edge case |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Treating "Space is private" as sufficient without confirming the Dataset repo's visibility independently | Submission log (settlement/population data + who-submitted-what) exposed even though the app itself is private | Verify and document both visibility settings separately as part of M2's definition of done |
| Leaving previously-committed real email addresses in git history after moving current secrets to Space secrets | Historical exposure persists indefinitely regardless of current secret handling | Scope a git-history scrub explicitly into the M2 secrets-migration work, not just current-state secret removal |
| No audit trail for *who accessed* the submission log/Dataset repo itself (as opposed to who submitted to it) | Cannot answer "who could have seen this settlement/population data" for a governance inquiry | Restrict Dataset repo collaborator access to the minimum needed, and treat that access list itself as something to review at each milestone |
| Hardcoding an OIDC redirect URI or client config that assumes a single fixed hosting URL | Breaks silently if the Space is ever renamed/moved, or exposes the app if a stale registered URI is left active | Prefer the native `hf_oauth` Space-managed flow where the platform owns redirect URI correctness |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|--------------|-------------------|
| Presenting a plausibility/coverage flag with the same visual weight as a hard data-integrity failure | Officers lose trust in the "clean means clean" verdict once they discover a legitimate record was flagged as if it were wrong | Distinct Review/Advisory status, visually and in the exported report, for rule-of-thumb-driven flags |
| Presenting "outside ward polygon" without stating which boundary dataset/version made that determination | Officers cannot judge whether to trust or dispute the flag | Always show boundary reference provenance alongside a boundary-fail flag |
| Silent failure of a background submission-log write | Officer believes their submission was logged when it wasn't, with no way to notice | Surface commit success/failure to the user, and consider a visible submission confirmation ID |
| Login redirecting to a Space URL variant the officer didn't originally use (e.g., custom domain vs. `.hf.space` subdomain) triggering a fresh/broken session | Confusing "I was just logged in and now I'm not" reports | Standardize on one canonical Space URL for all officer-facing links, and confirm OIDC redirect config matches it exactly |

## "Looks Done But Isn't" Checklist

- [ ] **Point-in-polygon layer:** Often missing the boundary-inclusive case — verify a
  boundary-snapped test point (constructed exactly on a known ward edge) passes, not just
  interior and clearly-exterior test points.
- [ ] **Point-in-polygon layer:** Often missing ward-dataset provenance in its output — verify
  the report states which boundary source/version produced a "fail."
- [ ] **Distance-sanity layer:** Often missing a stated error bound for its chosen formula —
  verify `config.json` or code comments document why Haversine (or whichever formula) is
  adequate at the chosen threshold.
- [ ] **Plausibility/coverage layers:** Often missing a distinct severity tier from hard
  data-integrity rules — verify the report and scoring treat them differently, not identically.
- [ ] **OIDC login:** Often verified only against localhost — verify the actual redirect flow
  against the deployed Space URL before declaring M2's auth work complete.
- [ ] **Submission log:** Often verified only with a single test submission — verify two
  concurrent submissions both land correctly before declaring M2 complete.
- [ ] **Secrets migration:** Often stops at "current secrets moved to Space secrets" — verify
  git history no longer contains the previously-committed real email addresses.
- [ ] **New M3 rules:** Often added ad hoc — verify every new rule has a unique ID assigned from
  the canonical rule list, a golden-fixture test, and a report/export mapping entry, per the M1
  `qc/` package pattern.

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|-----------------|-------------------|
| `contains()` chosen instead of `covers()` and shipped | LOW | Swap the method call; re-run against historical submissions to identify previously-mis-flagged boundary-snapped records; no data migration needed since geometry isn't stored, only recomputed |
| Boundary dataset vintage mismatch discovered post-launch | MEDIUM | Add provenance labeling retroactively; re-run point-in-polygon against a reconciled dataset; communicate to officers which historical "fail" flags should be disregarded |
| Submission log races/drops rows discovered post-launch | MEDIUM | Move to one-file-per-submission pattern; cross-check gaps against Space server logs if available (may be lossy/unavailable, which is itself a governance risk to flag) |
| Git history still contains committed emails after M2 ships | MEDIUM-HIGH | Requires a history rewrite (e.g., `git filter-repo`) and coordinated force-push, plus credential rotation for any exposed accounts — disruptive to any existing clones/forks, so plan and communicate before executing |
| Rule-of-thumb thresholds discovered to be miscalibrated after real submissions accumulate | LOW | Threshold lives in `config.json` by design — update the value and document the recalibration rationale; no code change needed |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|-------------------|-----------------|
| `contains()` boundary exclusion | M3 | Unit test with a point constructed exactly on a ward edge |
| Cross-dataset ward boundary disagreement | M3 (provenance pattern ideally from M1's F13 work) | Report/export shows boundary source+version on every boundary-fail row |
| Settlements outside ward due to boundary vintage | M3 | Boundary-fail flags are reviewable, not scored identically to hard-integrity failures |
| CRS/planar-vs-geodesic mixing across geometry and distance layers | M3 | Code review confirms distance-in-meters never reuses unprojected containment geometry directly |
| Haversine error at threshold margins | M3 | Config/comments document the chosen formula's error bound next to the threshold value |
| Threshold flags treated as hard failures | M3 (design decision), verified at rollout | Report and scoring visibly distinguish Review/Advisory from Pass/Fail |
| Concurrent submission-log writes | M2 | Scripted two-simultaneous-submission test passes before rollout |
| OIDC redirect/session pitfalls | M2 | Login flow tested against the actual deployed Space URL, not just localhost |
| Data governance sign-off for free-tier hosting | M2 (prerequisite, before rollout) | Named decision recorded in PROJECT.md; both Space and Dataset repo visibility verified independently |
| Git history still containing committed secrets/emails | M2 | History-scrub scoped and completed as part of "secrets moved out" work, verified by searching full history, not just HEAD |
| Rule-set growth without a registry | M1 (prerequisite), M3 (must build on it) | Standing test asserts rule-number uniqueness across the full rule set |

## Sources

- [Shapely Manual — object.contains / covers / intersects / touches](https://github.com/shapely/shapely/blob/main/docs/manual.md) — HIGH confidence (official library documentation, via context7)
- [geodesic versus planar distance (Esri ArcGIS documentation, mirrored across multiple portals)](https://kgs.uky.edu/arcgis/help/en/portal/11.2/use/geodesic-versus-planar-distance.htm) — MEDIUM confidence
- [GIS Algorithms in Python — Point-to-Point Distances (haversine vs. pyproj comparison)](https://www.jtrive.com/posts/gis-algorithms-in-python-1/gis-algorithms-in-python-1.html) — MEDIUM confidence
- [Calculate Distance Between GPS Points in Python](https://janakiev.com/blog/gps-points-distance-python/) — MEDIUM confidence
- [GRID3 NGA — Operational Wards v1.0](https://data.grid3.org/datasets/GRID3::grid3-nga-operational-wards-v1-0/about) — MEDIUM confidence
- [GRID3 NGA — Operational Wards v3.0](https://data.grid3.org/datasets/GRID3::grid3-nga-operational-wards-v3-0/explore) — MEDIUM confidence
- [Geospatial data Nigeria — GRID3](https://grid3.org/geospatial-data-nigeria) — MEDIUM confidence
- [Disk usage on Spaces · Hugging Face docs](https://huggingface.co/docs/hub/en/spaces-storage) — MEDIUM confidence
- [Persistent disk + Spaces + Upload of data — HF Forums](https://discuss.huggingface.co/t/persistent-disk-spaces-upload-of-data/44955) — MEDIUM confidence (community, cross-checked against official docs)
- [Concurrency bug when using same cache among several jobs · huggingface/datasets #4661](https://github.com/huggingface/datasets/issues/4661) — MEDIUM confidence
- [Upload files to the Hub — huggingface_hub docs (CommitScheduler)](https://huggingface.co/docs/huggingface_hub/guides/upload) — MEDIUM confidence
- [st.login — Streamlit Docs](https://docs.streamlit.io/develop/api-reference/user/st.login) — MEDIUM confidence
- [User authentication and information — Streamlit Docs](https://docs.streamlit.io/develop/concepts/connections/authentication) — MEDIUM confidence
- [Allow advanced customization of OIDC/OAuth2 parameters in st.login() · streamlit/streamlit #11703](https://github.com/streamlit/streamlit/issues/11703) — MEDIUM confidence
- [Why session state is not persisting between refresh? — Streamlit Forum](https://discuss.streamlit.io/t/why-session-state-is-not-persisting-between-refresh/32020) — MEDIUM confidence
- [CPU-Basic Spaces hitting quota limits — HF Forums (2026)](https://discuss.huggingface.co/t/cpu-basic-spaces-hitting-quota-limits-despite-unlimited-hosting-inconsistent-behavior-with-restart-and-factory-rebuild/175681) — MEDIUM confidence
- [Question about the CPU-Basic quota limit — HF Forums](https://discuss.huggingface.co/t/question-about-the-cpu-basic-quota-limit/176628) — MEDIUM confidence
- [EPSG:32631/32632/32633 — WGS84 UTM zones covering Nigeria](https://epsg.io/32632) — MEDIUM confidence
- [Minna / UTM zone 32N — EPSG:26332](https://epsg.io/26332-1754) — MEDIUM confidence
- Project-internal: `.planning/PROJECT.md` and `.planning/codebase/ARCHITECTURE.md`,
  `INTEGRATIONS.md` (2026-09-09 codebase map) — HIGH confidence (primary source, this repository)

---
*Pitfalls research for: hosted geospatial data-QC / point-in-polygon microplanning validation*
*Researched: 2026-09-09*
