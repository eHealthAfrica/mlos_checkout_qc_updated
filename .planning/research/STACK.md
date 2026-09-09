# Stack Research

**Domain:** Geospatial settlement-data QC, hosted Streamlit app on Hugging Face Spaces (free tier), public-health microplanning, Nigeria
**Scope:** M2 (central deployment + OIDC + append-only log) and M3 (point-in-polygon, distance, population, coverage QC layers) additions to an existing single-file Streamlit + pandas app
**Researched:** 2026-09-09
**Confidence:** MEDIUM overall (HIGH on package versions, verified live against PyPI; MEDIUM on API/behavior claims, verified against official docs via Context7 and web search; flagged LOW/unverified claims called out explicitly)

## Recommended Stack

### Core Additions

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| `shapely` | `>=2.1.2,<3.0.0` | Point-in-polygon geometry (B2 replacement) and settlement-to-takeoffpoint distance | Shapely 2's vectorized ufuncs (`shapely.contains(polygons, points)`) and its GEOS-backed `STRtree` do the whole job without pulling in a GDAL/pyproj/pyogrio stack. The actual B2 check is a **row-aligned exact lookup** — each settlement already declares its `ward_code`, so you test point-in-*that-ward's*-polygon, not "which of 9,410 polygons contains this point." That's `O(n)` vectorized `contains`, no spatial index required for the primary check. HIGH confidence (PyPI-verified version; MEDIUM confidence on API behavior, Context7-verified against `shapely/shapely` docs). |
| `huggingface_hub` | `>=1.30.0,<2.0.0` | Read/append the private HF Dataset submission log from inside the Space | `HfApi` + `CommitScheduler` is HF's own documented pattern for exactly this "log entries from a live app to a Hub dataset" use case (used internally in their Gradio feedback-logging guide; applies identically to Streamlit — nothing Gradio-specific about it). MEDIUM confidence, Context7-verified against `huggingface/huggingface_hub` docs. |
| `pandas` | `==3.0.5` (pin exact patch, cap major at `<4.0.0`) | DataFrame-heavy QC engine (existing) | Currently declared `>=2.0.0` with no upper bound, which is how the repo silently landed on 3.0.2/3.0.5 already. Pandas 3.0 (released 2026-01-21) is a real major-version boundary — see Pandas 3.x Breaking Changes below. Pin it deliberately rather than let it drift further. HIGH confidence (PyPI-verified, official pandas whatsnew docs). |
| `numpy` | `>=2.0.0,<3.0.0` | Vectorized numeric ops (imported today, never declared) | Must be declared explicitly per the M1 requirement already in PROJECT.md. Current PyPI release is 2.5.3; pandas 3.x requires numpy>=1.26 at minimum, so `>=2.0,<3.0` gives headroom without inviting numpy 3.x (not yet a target here). HIGH confidence (PyPI-verified). |

### Authentication (choose ONE primary path — see Alternatives Considered)

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **HF Spaces native OAuth** (`hf_oauth: true`) | Platform feature, no package pin | Primary OIDC path | Zero external IdP registration, zero client-secret provisioning by you (HF creates and injects `OAUTH_CLIENT_ID`/`OAUTH_CLIENT_SECRET`/`OPENID_PROVIDER_URL`/`SPACE_HOST` as **flat env vars**). Flat env vars are exactly what HF Space secrets naturally are, so there's no config-format mismatch. MEDIUM confidence (official `huggingface.co/docs/hub/spaces-oauth`, web-verified). |
| `Authlib` | `>=1.3.2` (only if using `st.login`) | OIDC client library Streamlit's `st.login` uses internally | Required dependency for the fallback path (`pip install streamlit[auth]`). Not needed if you go with the HF-native path and implement the redirect flow yourself (HF's guide points at Authlib too, so it's usable either way — just optional under the native path). MEDIUM confidence, Context7-verified. |
| `streamlit` | `>=1.42.0` (currently `1.63.0` on PyPI) | `st.login`/`st.user` OIDC entry points | `st.login`/`st.user` were introduced in Streamlit 1.42.0. The app already requires `>=1.32.0`; bump the floor if the `st.login` fallback path is used. MEDIUM confidence (web-verified against GitHub issue history + Streamlit docs). |

### Supporting / Build-Time-Only Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `geopandas` + `pyogrio` | `1.1.4` / `0.13.0` | One-time conversion of source ward polygons from `.shp`/`.geojson` into the app's shipped format | **Dev-time tool only — not a Space runtime dependency.** If ward polygons arrive as shapefile, use these locally to read/reproject/export to GeoJSON once. Do not add them to `requirements.txt`. |
| `mapshaper` (Node CLI) | latest | Simplify ward polygon vertex density before shipping | Run once against the source GeoJSON to cut vertex count (Douglas-Peucker simplification) and coordinate precision (`-o precision=0.00001` ≈ 1 m accuracy is plenty for ward-level QC), directly shrinking both repo size and in-memory geometry cost at runtime. Not a Python or app dependency. |
| stdlib `json` (or `orjson` if profiling shows it matters) | n/a | Parse the shipped GeoJSON at app startup | `shapely.geometry.shape()` over parsed GeoJSON dicts is enough at this scale (9,410 features); don't add a geospatial file-format library to read a file format (GeoJSON) that's just JSON. |

## Installation

```bash
# Core additions
pip install "shapely>=2.1.2,<3.0.0"
pip install "huggingface_hub>=1.30.0,<2.0.0"

# Pin the existing, currently-undeclared/unbounded deps
pip install "pandas==3.0.5" "numpy>=2.0.0,<3.0.0"

# Only if the st.login/OIDC fallback path is chosen (not needed for HF-native OAuth):
pip install "streamlit[auth]>=1.42.0"   # pulls in Authlib>=1.3.2

# Dev-time only — NOT added to requirements.txt, used locally to pre-process polygons:
pip install geopandas pyogrio   # one-off conversion script, then discard
npm install -g mapshaper        # one-off simplification pass
```

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|--------------|-------------|--------------------------|
| `shapely` 2.x vectorized `contains` + built-in `STRtree` | `geopandas.sjoin` | If the QC layer grows to need general spatial joins (e.g. "which ward contains this point" with no declared ward to check against), CRS reprojection, or reading shapefiles at runtime. For this milestone's row-aligned "does the point fall in *its declared* ward" check, geopandas is strictly heavier (GDAL/pyproj/pyogrio) for no behavioral gain. |
| `shapely` STRtree | standalone `rtree` package (libspatialindex) | Never, for this project. Shapely 2's `STRtree` is GEOS-backed and bundled with shapely itself — `rtree` wraps a *separate* native library (libspatialindex) and would be a second native dependency doing the same job. Only reach for it if some other library specifically requires the `rtree` API surface. |
| HF Spaces native OAuth (`hf_oauth: true`) | Streamlit `st.login` against Google/Microsoft Entra | If organizational policy specifically requires officers to authenticate with an existing Google Workspace or Entra ID identity rather than a Hugging Face account. This is a real possibility per PROJECT.md's own open question ("whether officers signing in with HF accounts is acceptable") — if the answer is no, `st.login` is the correct fallback, but budget for: registering an OAuth app with the external IdP, wiring a `SPACE_HOST`-based `redirect_uri`, and the secrets-format friction below. |
| Ship ward polygons in the git repo (simplified GeoJSON) | Load polygons from the private HF Dataset repo at runtime | Only if polygon files, even after simplification, become too large for comfortable git tracking (use Git LFS at that point, still in the app repo — not the Dataset repo). Keeping the Dataset repo scoped to the append-only submission log avoids conflating "reference data that changes when Nigeria's ward boundaries change" with "an audit log that must never be edited." |
| `CommitScheduler` for the submission log | Direct `HfApi.upload_file()`/`create_commit()` per submission, with `parent_commit` retry | If submission volume is high enough that batched writes lose acceptable granularity, or if a wait for the next scheduled flush is unacceptable UX. For infrequent, state-level QC submissions, batching every few minutes is invisible to users and avoids commit-storm/rate-limit risk under concurrent officers. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|--------------|
| `fiona` | Legacy GDAL binding, duplicates what `pyogrio` already does faster; geopandas >=1.0 defaults to `pyogrio` and doesn't need it. Also dev-time only regardless — irrelevant to the Space runtime. | `pyogrio` (dev-time only), or nothing at all if polygons ship as GeoJSON already. |
| `rtree` / `libspatialindex` as a runtime dependency | A second native spatial-index library doing what shapely 2's bundled `STRtree` already does. Extra native binary = extra cold-start and build-image weight for zero functional gain here. | `shapely.STRtree` (already ships with `shapely>=2.0`). |
| `pandas>=2.0.0` with no upper bound (current `requirements.txt`) | This is exactly how the repo silently landed on pandas 3.0.2, then 3.0.5, with breaking dtype/copy-on-write semantics nobody opted into. An unbounded floor-only pin is not a version decision, it's an accident waiting to happen at every fresh `pip install`. | Exact pin (`pandas==3.0.5`) or a tight range (`>=3.0.0,<3.1.0`), bumped deliberately with the pandas 3.x migration checked each time. |
| Assuming HF Space secrets populate Streamlit's nested `[auth]` TOML table automatically | They don't. HF Space secrets surface as **flat environment variables**; Streamlit's `st.secrets["auth"]["google"]["client_id"]`-style nested config is only read from an actual `secrets.toml` file (`streamlit/streamlit#10543` is open, tracking exactly this gap as of this research). If you pick the `st.login` fallback path, you must materialize `.streamlit/secrets.toml` from flat env vars at container startup (before Streamlit's own config/secrets loading) — this is extra integration work the HF-native OAuth path doesn't require at all. | Prefer HF-native OAuth (flat env vars, no nested-TOML step). If `st.login` is required, write a small startup step that renders `.streamlit/secrets.toml` from `os.environ` before the app proper runs. |
| `sdk: docker` for the Space, if a Docker-based deploy is ever considered | HF's own docs flag that Docker-SDK Spaces don't get the automatic XSRF/cookie workaround the native `streamlit` SDK applies for you — `st.file_uploader` (which this app already depends on for QC file upload) breaks inside the cross-origin iframe unless you manually set `server.enableXsrfProtection = false`. | `sdk: streamlit` (native SDK) — HF's SDK integration already handles this for you; don't reinvent it under Docker. |

## Stack Patterns by Variant

**If officers can authenticate with a Hugging Face account (default recommendation):**
- Use `hf_oauth: true` in the Space README YAML metadata.
- Read `OAUTH_CLIENT_ID`, `OAUTH_CLIENT_SECRET`, `OPENID_PROVIDER_URL`, `SPACE_HOST` directly via `os.getenv()` — no secrets.toml step.
- Implement the redirect/callback with Authlib (or a minimal manual flow per HF's documented steps) at a callback route such as `https://{SPACE_HOST}/login/callback`.
- Because Spaces pages embed the app in a cross-origin iframe (`huggingface.co/spaces/<org>/<app>` → `*.hf.space`), either set `target="_blank"` on the login trigger **or** — the cleaner fix for a small, known audience of state officers — distribute the direct `https://<space>.hf.space` URL as the bookmarked entry point instead of the `huggingface.co/spaces/...` landing page, sidestepping the iframe/cookie interaction entirely for the whole session, not just the login click.

**If organizational policy requires Google/Microsoft Entra identity specifically:**
- Use `st.login` (Streamlit `>=1.42.0`, `streamlit[auth]` extra, `Authlib>=1.3.2`).
- Register an OAuth app with the IdP; set `redirect_uri` to `https://<space-host>/oauth2callback` and keep it in sync if the Space is ever renamed/moved (`SPACE_HOST` changes).
- Add a startup step (top of `app.py`, before any `st.*` calls trigger secrets loading) that writes `.streamlit/secrets.toml` from flat HF Space secret env vars, since the `[auth]` table cannot come from flat env vars directly.
- Same iframe/cookie caveat as above applies — distribute the direct `*.hf.space` URL.

**If ward polygon geometry needs updating later (Nigeria redraws ward boundaries):**
- Re-run the one-time `geopandas`/`pyogrio` + `mapshaper` conversion locally, commit the refreshed simplified GeoJSON to the app repo (same pattern as the existing `ward_boundary_ref.csv`/`ward_boundary_bbox.csv`), redeploy. Do not build a runtime ingestion path for this — it changes rarely and the app already treats boundary reference data as versioned-with-code.

## Pandas 3.x Breaking Changes Relevant to This Codebase

The app is DataFrame-heavy, string-comparison-heavy (ward codes, state names, flag columns), and specifically relies on `"NA"` being a valid literal domain value (loaded with `keep_default_na=False` everywhere per the existing "Domain note" in PROJECT.md). Pandas 3.0 (released 2026-01-21, requires Python `>=3.11`) changes:

1. **Dedicated `str` dtype is now the default** for string columns (previously `object` dtype). `keep_default_na=False` behavior itself is unaffected — it governs NA-string *inference* in `read_csv`/`read_excel` and is orthogonal to the dtype-default change — but any code doing `df[col].dtype == "object"` to detect string columns will silently stop matching. **Action:** audit `app.py` for `dtype ==` / `dtypes ==` comparisons against `"object"` and replace with `pd.api.types.is_string_dtype(...)`.
2. **`setitem` on a `str`-dtype column now raises `TypeError` for non-string values** (previously `object` dtype silently accepted anything). If any auto-correction or QC code assigns a non-string sentinel (e.g. a bare `None`, a number, or a list) into what pandas now infers as a `str` column, it will raise instead of silently succeeding. **Action:** grep for `.loc[..., col] =` / `df[col] =` assignments feeding non-string values into text columns.
3. **Copy-on-Write is enabled by default**, replacing the pre-3.0 opt-in mode. Chained-assignment patterns (`df[df.x > 0]["y"] = 1`) that used to "work" by mutating a view now reliably no-op instead of raising `SettingWithCopyWarning` — this is exactly the kind of silent-divergence bug class the M1 audit already found once (F4: "displayed data and computed checks never describe different versions of the file"). **Action:** grep for chained-indexing assignment patterns across `run_*_qc()` and `auto_correct_mlos()`.
4. **Python `>=3.11` is required.** Confirm the HF Space README's `python_version:` field is set to `3.11` or newer before pinning pandas 3.0.5, or the Space build will fail on dependency resolution.

None of these are exotic edge cases for this codebase specifically — they land squarely in the dtype-checking and DataFrame-mutation code the M1 audit already flagged as fragile (F4, F5, F9). Recommend running the M1 pytest golden-fixture suite (once it exists) explicitly against the pinned pandas 3.0.5 as part of closing the "dependencies pinned" M1 item, rather than assuming today's passing behavior generalizes.

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|------------------|-------|
| `pandas==3.0.5` | `numpy>=2.0.0,<3.0.0` | pandas 3.x's floor is numpy>=1.26; capping at `<3.0` avoids opting into numpy 3.x, which is out of scope here. |
| `pandas==3.0.5` | Python `>=3.11` | Hard requirement — check the Space's `python_version:` README field. |
| `shapely>=2.1.2` | `geopandas==1.1.4` (dev-time only) | geopandas `>=1.0` requires `shapely>=2`; irrelevant at Space runtime since geopandas isn't shipped there. |
| `streamlit>=1.42.0` | `Authlib>=1.3.2` | Required only for the `st.login` fallback path; installed via the `streamlit[auth]` extra, not a bare `pip install streamlit`. |
| `huggingface_hub>=1.30.0` | `CommitScheduler` | Available since `huggingface_hub>=0.20`; pinning to the current `1.x` line is about getting the current documented API surface, not a hard version floor for the feature itself. |

## Sources

- PyPI JSON API (`pypi.org/pypi/<package>/json`), queried directly — current versions for `shapely`, `geopandas`, `pyogrio`, `rtree`, `huggingface_hub`, `streamlit`, `pandas`, `numpy`, `openpyxl`, `authlib`. HIGH confidence — official package registry.
- Context7 `/shapely/shapely` — STRtree API, vectorized `contains`, `prepared` geometry. MEDIUM confidence.
- Context7 `/huggingface/huggingface_hub` — `CommitScheduler`, `upload_file`, `create_commit`/`parent_commit` concurrency guard. MEDIUM confidence.
- Context7 `/streamlit/docs` — `st.login`, `st.user`, `[auth]` secrets.toml structure, secrets-management file/env-var behavior. MEDIUM confidence.
- Context7 `/websites/pandas_pydata` — pandas 3.0.0 whatsnew, string-dtype migration guide, copy-on-write. MEDIUM confidence.
- `https://huggingface.co/docs/hub/en/spaces-oauth` (fetched directly) — `hf_oauth` README metadata, injected env vars, redirect URL guidance, iframe/cookie warning. MEDIUM confidence (official docs, web-verified).
- `https://huggingface.co/docs/hub/spaces-cookie-limitations` (fetched directly) — cross-origin iframe cookie restriction, Docker-vs-native-SDK XSRF handling for `st.file_uploader`. MEDIUM confidence (official docs, web-verified).
- Web search — HF Spaces free CPU Basic tier specs (2 vCPU / 16GB RAM / 50GB ephemeral disk), pandas 3.0 Python-version floor, `streamlit[auth]`/Authlib requirement, `streamlit/streamlit#10543` (nested `[auth]` secrets vs flat env vars gap). MEDIUM confidence — cross-checked across multiple results, official-docs-adjacent but not all primary-sourced.

---
*Stack research for: geospatial settlement QC, hosted Streamlit + Hugging Face Spaces deployment*
*Researched: 2026-09-09*
