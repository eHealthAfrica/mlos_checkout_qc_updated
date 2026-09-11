# Phase 4: Central Deployment and Officer Identity - Research

**Researched:** 2026-09-10
**Domain:** Streamlit `st.login` OIDC auth, Hugging Face Spaces private hosting, git history scrubbing
**Confidence:** MEDIUM (HIGH on package versions and the Streamlit `[auth]` shape; MEDIUM on HF Spaces access-control interaction with app-level auth — this is the phase's central open risk)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Identity Provider (AUTH-01, AUTH-02)**

- **D-01:** Officers sign in with their **Google Workspace identity via Streamlit's `st.login`
  / `st.user`**, not with Hugging Face accounts. The research recommendation (native
  `hf_oauth: true`) was presented and **not chosen**: the user wants officers to keep their
  existing work identity. Reversibility: costly — the identity provider decides what the
  Phase 5 submission log records as "who".
  *Recorded deviation:* native Hugging Face OAuth was the recommended option and was not
  chosen. The planner must not revert to it as a "simpler" path.
  **Consequence the planner must handle:** Space secrets surface as **flat environment
  variables**, and `st.login` reads only the nested `[auth]` table of an actual
  `.streamlit/secrets.toml` (Streamlit issue #10543). A startup step must render
  `.streamlit/secrets.toml` from the flat env vars **before any `st.*` call triggers secrets
  loading**. `streamlit>=1.42.0` and `Authlib>=1.3.2` (`streamlit[auth]` extra) become declared
  dependencies; Streamlit 1.63.0 is installed and already exposes `st.login` and `st.user`.

- **D-02:** The Google OAuth client **already exists**; only the Space host's redirect URI
  needs adding to it. The plan carries **one `checkpoint:human-action`**, gated
  `blocking-human`: the user adds the redirect URI and pastes client id, client secret and a
  cookie secret into Space secrets; Claude then verifies sign-in against the deployed URL
  (AUTH-03). No plan task may fabricate or commit these values.

- **D-03:** When the app runs **with no `[auth]` configuration** (developer laptop, pytest),
  the login gate is bypassed **only when an explicit opt-out environment variable is set**
  (e.g. `MLOS_AUTH_DISABLED=1`), and the page shows a visible "authentication disabled" banner.
  Missing auth configuration **without** the flag stops the app with a clear message rather
  than running open. Automatic bypass on absent secrets was offered and rejected.

**Who Is Allowed In (AUTH-01)**

- **D-04:** Sign-in is accepted **only for the `ehealthnigeria.org` Google Workspace domain**,
  enforced on the token's hosted-domain / email-domain claim after authentication, not by
  trusting the Google consent screen alone. A domain allow-list, an explicit email allow-list,
  and "any Google account" were offered and not chosen. Reversibility: reversible.
- **D-05:** An authenticated user outside the domain sees a **refusal page**: a plain
  statement that the account is not authorised, the data-team contact address read from Space
  secrets (not hard-coded), and a sign-out button. No uploader, no tabs, no QC can run.
  Bouncing them back to sign-in with no explanation was rejected.

**Data-Governance Sign-Off (DEPLOY-01)**

- **D-06:** The sign-off for hosting settlement coordinates and population figures on a
  third-party free tier **has not yet been obtained**. The plan **must gate the first
  deployment of the private Space on it** with a `checkpoint:human-action` rated
  `blocking-human`, naming the approver and recording the decision in CONTEXT.md's
  `<decisions>` and STATE.md when it arrives. All code/config work proceeds without waiting;
  only creating or making reachable the Space holding real data waits. A deploy against
  synthetic fixture data for AUTH-03's login verification is acceptable before sign-off,
  provided no real settlement file is uploaded.

**Secrets and History Scrub (DEPLOY-02, DEPLOY-03)**

- **D-07:** SMTP recipients live in Space secrets as **two comma-separated variables**,
  `SMTP_TO` and `SMTP_CC`, whitespace-tolerant, editable in the Space UI without a deploy. A
  single JSON variable was offered and not chosen. If `SMTP_TO` is missing or empty the Send
  button is **disabled with a visible reason**, never silently emailing nobody. The existing
  `smtp_host`, `smtp_port`, `smtp_user`, `smtp_pass` keys stay as secrets; the hard-coded `TO`
  and `CC` lists in `send_qc_email` are deleted.
- **D-08:** The committed addresses are removed from history with **`git filter-repo`, run
  once, after `feature/qc-rules` has merged to `main`**, so the branch and `main` are not
  rewritten separately. Rewriting the branch now (two disruptions) and BFG Repo-Cleaner were
  offered and not chosen. Reversibility: one-way — a history rewrite plus force-push
  invalidates every existing clone. The plan must carry the rewrite as a `blocking-human`
  checkpoint with a checklist: notify collaborators, confirm no unpushed work, run
  filter-repo with the exact address literals, force-push all branches and tags, everyone
  re-clones, verify with `git log -S` on each address across all refs. "Removed from the
  working tree" (DEPLOY-02) and "removed from history" (DEPLOY-03) are separate tasks and
  separate acceptance criteria.

### Claude's Discretion

- **Where auth code lives.** ROADMAP names an `auth.py` boundary; the planner chooses the
  module and its shape (a `require_login()` gate before the uploader; a domain check helper;
  the secrets.toml materialiser). It must be importable and unit-testable without a live
  Streamlit session where possible, following `qc/` and `qc/report.py` precedent, while the
  `st.login`/`st.user` calls themselves stay in `app.py` or a thin Streamlit-only module.
- **Space metadata.** `sdk: streamlit` in the Space README front matter (Docker SDK loses the
  XSRF/iframe workaround `st.file_uploader` needs); Python 3.11 floor for `pandas==3.0.5`;
  free CPU basic hardware. Whether the Space README lives in this repo or the Space repo is
  the planner's call; the app must not depend on it either way.
- **Cookie lifetime and sign-out.** Streamlit's `[auth]` `cookie_secret` and its default
  expiry are acceptable; a sign-out button is required on the refusal page (D-05) and
  reasonable on the main page.
- **Officer instructions.** DEPLOY-04 requires officers be given the direct `*.hf.space` URL.
  README §"Deployment" should be rewritten from Streamlit Community Cloud to Hugging Face
  Spaces, including the direct-URL note and the secrets list. Required, not optional.
- **Free-tier sleep.** A free Space sleeps after 48 hours idle and cold-starts on the next
  visit. Accepted as-is; the README may mention the wait.
- **Structural guard.** A standing test that no email address literal and no secret value
  appears in tracked source (the AST/grep idiom Phases 1–3 established) is strongly
  recommended so DEPLOY-02 cannot silently regress.

### Deferred Ideas (OUT OF SCOPE)

- **Domain or email allow-list beyond the Workspace domain** — offered, not chosen; revisit if
  state officers outside `ehealthnigeria.org` need access.
- **Native Hugging Face OAuth** — the research recommendation, declined for identity reasons;
  remains the fallback if the Google OAuth client cannot be reused.
- **Always-on hosting** to avoid the 48-hour idle sleep — paid tier, out of scope by
  constraint.
- **Role-based / per-state access segregation** — already v2 (ACL-01); D-04 is authentication
  scope, not authorization.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DEPLOY-01 | App runs as a single private HF Space officers in every state reach at one URL | See "HF Spaces Private Access vs App-Level Auth" (Open Question 1) — a private Space's own access control may prevent D-01's Google-only flow from ever being reached; this is the single biggest risk to how DEPLOY-01 should be worded and built |
| DEPLOY-02 | SMTP credentials and recipient list read from Space secrets, appear nowhere in repo | See "DEPLOY-02 Mechanics" — exact edit site (`app.py:274-308`), `SMTP_TO`/`SMTP_CC` parsing, `st.secrets` vs flat env var behavior on Spaces |
| DEPLOY-03 | Addresses at `app.py:644-647` (now `app.py:286-289`) removed from git history | See "DEPLOY-03 Mechanics" — `git filter-repo` install and invocation, exact literals, verification commands, force-push checklist |
| DEPLOY-04 | Officers given direct `*.hf.space` URL, not the iframe embed | See "HF Spaces for a Private Streamlit App" — why the iframe blocks cookies, `SPACE_HOST` |
| AUTH-01 | Officer must sign in before running a QC check | See "st.login / st.user on Streamlit 1.63" and "Architecture Patterns: The Login Gate" |
| AUTH-02 | No passwords stored; identity from OIDC provider | Same as AUTH-01 — `st.login` never touches a password, Google IdP owns it |
| AUTH-03 | Login verified against the deployed Space URL, not only localhost | See "Testing Strategy" — what's unit-testable vs the manual checklist for this requirement |
</phase_requirements>

## Summary

This phase has one well-documented technical path (Streamlit `st.login` against Google OIDC,
materialising `.streamlit/secrets.toml` from HF Space's flat env-var secrets before any `st.*`
call) and one **unresolved architectural risk** that the prior research pass
(`.planning/research/STACK.md`) did not surface because it was written before D-01 locked
Google-only sign-in: **a private Hugging Face Space restricts access to the Space owner and
named collaborators/organization members at the platform level, independent of anything the
app itself does.** [CITED: huggingface.co/docs/hub/spaces-overview; community forum threads]
If that gate applies to *every* visitor (not just API/programmatic access), a state officer with
only a Google Workspace account and no Hugging Face account would get an HF-side 404 before ever
reaching `st.login`. This directly conflicts with DEPLOY-01's premise of "officers in every
state reach it" via Google identity alone, and is flagged below as **Open Question 1** rather
than silently worked around, per this task's explicit instruction.

The rest of the phase is comparatively low-risk: `st.login`/`st.user` (Streamlit 1.63.0,
already installed) plus `Authlib>=1.3.2` (`streamlit[auth]` extra) give a standard OIDC flow
against Google, with the `hd` claim available on `st.user` for domain enforcement (D-04). The
`[auth]` secrets.toml shape is fixed and documented. The DEPLOY-02/DEPLOY-03 secrets and
history-scrub work is mechanical and low-ambiguity: one edit site in `app.py`, one
`git filter-repo` invocation with exact literals, both already covered by this project's
existing AST/grep standing-test idiom.

**Primary recommendation:** Build the `st.login`-against-Google flow exactly as D-01 through
D-05 specify, but **resolve Open Question 1 with the user before or during planning** — most
likely by making the Space itself **public** (so any URL visitor reaches the Streamlit app) and
relying entirely on the **app-level** `ehealthnigeria.org` domain check as the real access
control, which is consistent with "Settlement coordinates... must be private" only if that
privacy is understood to mean "gated by the app's login+domain check," not "gated by HF's own
visibility flag." Flag this as a discussion item — do not silently pick a shape.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| OIDC sign-in / callback handling | Frontend Server (SSR-like, Streamlit's own Tornado/Starlette routes) | — | `st.login` registers `/oauth2callback` and manages the identity cookie inside Streamlit's own server process; there is no separate backend tier in this app |
| Domain (`hd`) enforcement | Frontend Server | — | Must run server-side, immediately after token exchange, before any page content renders — never trust the OAuth consent screen alone (D-04) |
| Secrets materialisation (`secrets.toml` from flat env vars) | Frontend Server (startup) | — | Must complete before Streamlit's own config/secrets loader runs on first `st.*` call; this is a process-startup concern, not a request-time one |
| Space-level access control (private/public flag) | CDN / Static (HF platform edge) | — | Enforced by Hugging Face's own infrastructure before a request ever reaches the Streamlit process; this is why Open Question 1 exists — it sits *above* the app tier entirely |
| SMTP recipient config (`SMTP_TO`/`SMTP_CC`) | Frontend Server | Database/Storage (secrets store) | Read from `st.secrets`/env at request time in `send_qc_email`; no persistence beyond the Space secrets store |
| Git history scrub | Database/Storage (equivalent — the repo itself is the "durable store" being edited) | — | Not a runtime-tier concern at all; a one-time operation on the git object store, orthogonal to the deployed app |

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| `streamlit` | PyPI | ~7 yrs, 272 releases, current `1.63.0` [VERIFIED: PyPI registry — `pypi.org/pypi/streamlit/json`] | very high (already a project dependency) | github.com/streamlit/streamlit | OK | Approved — version floor raised from `>=1.32.0` to `>=1.42.0` |
| `Authlib` | PyPI | long-established, 64 releases, current `1.8.0` [VERIFIED: PyPI registry — `pypi.org/pypi/Authlib/json`] | high (widely used OIDC/OAuth library; pulled transitively by `streamlit[auth]`) | github.com/authlib/authlib | OK | Approved — installed via `streamlit[auth]` extra, satisfies `>=1.3.2` |
| `git-filter-repo` | PyPI | 14 releases since `2.23.0`, current `2.47.0` [VERIFIED: PyPI registry — `pypi.org/pypi/git-filter-repo/json`] | maintained by a long-time Git contributor (Elijah Newren); recommended by the official Git project docs over BFG for this exact use case | github.com/newren/git-filter-repo | OK | Approved — dev-tool only, never a runtime/requirements.txt dependency |

**Packages removed due to [SLOP] verdict:** none.
**Packages flagged as suspicious [SUS]:** none.

All three packages were discovered via official documentation (Streamlit's own docs for
`streamlit[auth]`/Authlib; the official Git project's own recommendation of `git-filter-repo`
over BFG for history rewrites), then independently confirmed against the PyPI registry this
session — they earn `[VERIFIED: PyPI registry]` under the package-name provenance rule.

**Installation:**
```bash
# requirements.txt changes
streamlit>=1.42.0,<2.0.0   # was >=1.32.0,<2.0.0 -- floor raised for st.login/st.user
Authlib>=1.3.2             # new; pulled in automatically by streamlit[auth] extra

# actual pip install (extras syntax, not a separate requirements.txt line)
pip install "streamlit[auth]>=1.42.0,<2.0.0"

# dev-machine only, for the DEPLOY-03 history rewrite -- NOT added to requirements.txt
brew install git-filter-repo   # macOS; ships as a single Python script + man page
```

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `streamlit[auth]` | `>=1.42.0,<2.0.0` (1.63.0 installed) [VERIFIED: PyPI registry] | `st.login`/`st.user`/`st.logout` OIDC entry points | `st.login` and `st.user` were introduced in Streamlit 1.42.0 and are the framework's own documented auth primitive — no third-party Streamlit auth wrapper is needed [CITED: docs.streamlit.io/develop/api-reference/user/st.login] |
| `Authlib` | `>=1.3.2` (1.8.0 current) [VERIFIED: PyPI registry] | OIDC client library `st.login` uses internally | Declared dependency of the `streamlit[auth]` extra; not imported directly by app code [CITED: docs.streamlit.io] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `git-filter-repo` | `2.47.0` (dev-machine tool, not a `requirements.txt` entry) [VERIFIED: PyPI registry] | One-time removal of committed email addresses from all git history | DEPLOY-03's `blocking-human` checkpoint only; never installed on the Space itself |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `st.login` against Google OIDC directly | Native `hf_oauth: true` | Rejected by D-01 (Recorded Deviation) — do not re-litigate. Would sign officers in with HF accounts, not their Workspace identity |
| `git filter-repo` | BFG Repo-Cleaner | Rejected by D-08 — user chose `git filter-repo`; both accomplish the same history rewrite, `filter-repo` is the tool the modern Git project itself recommends |
| Startup materialisation of `secrets.toml` | Waiting for HF Spaces to support nested TOML via env vars | Streamlit issue #10543 (flat env vars vs nested `[auth]` TOML) is still open as of this research; no native fix exists, so the materialiser step is not optional |

## Architecture Patterns

### System Architecture Diagram

```
Officer's browser
      │  GET https://<space>.hf.space/            (direct URL — DEPLOY-04)
      ▼
┌─────────────────────────────────────────────────────────────────┐
│ Hugging Face Space edge (platform tier)                          │
│  - Space visibility check (private/public) ── OPEN QUESTION 1    │
│  - injects Space secrets as FLAT env vars (SMTP_*, AUTH_*, ...)  │
└───────────────────────────────┬───────────────────────────────────┘
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│ Streamlit process (app.py, startup)                               │
│  1. materialise .streamlit/secrets.toml from flat env vars        │
│     (MUST run before first st.* call touches secrets)             │
│  2. st.set_page_config(...)                                       │
└───────────────────────────────┬───────────────────────────────────┘
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│ auth gate (new module, e.g. auth.py / qc/auth.py)                 │
│  require_login():                                                  │
│    if MLOS_AUTH_DISABLED=1 and no [auth] configured:               │
│        show "auth disabled" banner, continue           (D-03)      │
│    elif no [auth] configured, no bypass flag:                      │
│        st.stop() with a clear config-missing message   (D-03)      │
│    elif not st.user.is_logged_in:                                  │
│        render "Sign in with Google" -> st.login()                  │
│        st.stop()                                                   │
│    elif domain_of(st.user) != "ehealthnigeria.org":                │
│        render refusal page (contact from secrets, sign-out) (D-05) │
│        st.stop()                                                    │
│    else:                                                            │
│        proceed to uploader                                          │
└───────────────────────────────┬───────────────────────────────────┘
                                 ▼ (only reached for signed-in, in-domain users)
┌─────────────────────────────────────────────────────────────────┐
│ existing app: uploader → 5 QC layers → report/email                │
│  send_qc_email() reads SMTP_TO / SMTP_CC (comma-separated) from    │
│  st.secrets, disables Send button if SMTP_TO empty        (D-07)   │
└─────────────────────────────────────────────────────────────────┘
```

A reader can trace the primary path: officer opens the direct URL → HF edge decides
visibility → app materialises secrets → auth gate resolves signed-in/in-domain state →
uploader/QC only renders past the gate → email send reads recipients from secrets, not
literals.

### Recommended Project Structure
```
app.py                  # st.login()/st.user/st.logout() calls, page config, uploader+QC (unchanged shape)
auth.py                 # NEW — thin Streamlit-touching module: require_login(), refusal page
qc/auth_domain.py        # NEW — pure, Streamlit-free: extract_domain(user_claims) -> str,
                         #   is_authorized_domain(domain, allowed) -> bool (unit-testable without a session)
qc/secrets_materializer.py  # NEW — pure: build_secrets_toml(env: dict) -> str (unit-testable)
tests/test_auth_domain.py       # NEW — injectable fake st.user-shaped object
tests/test_secrets_materializer.py  # NEW
tests/test_no_committed_secrets.py  # NEW — AST/grep guard, D-02/D-08 regression guard
```

### Pattern 1: Secrets Materialisation Before Any `st.*` Call
**What:** A function that reads flat env vars (`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`,
`COOKIE_SECRET`, `SPACE_HOST` or equivalent) and writes a `.streamlit/secrets.toml` file with
a nested `[auth]` table, executed as the very first lines of `app.py` — before `st.set_page_config`
or any other Streamlit call that could trigger Streamlit's own config/secrets loading.
**When to use:** Any Streamlit deployment on a platform (like HF Spaces) that only exposes
flat env vars, when using `st.login`'s file-based `[auth]` config.
**Example:**
```python
# Source: pattern derived from Streamlit issue streamlit/streamlit#10543 discussion
# [CITED: github.com/streamlit/streamlit/issues/10543] -- the gap itself is documented there;
# this materialiser is this project's own response to it, not a library-provided fix.
import os
from pathlib import Path

def materialize_auth_secrets():
    """Write .streamlit/secrets.toml [auth] table from flat env vars.
    Must run before any st.* call. No-op if GOOGLE_CLIENT_ID is unset (dev/pytest path)."""
    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    if not client_id:
        return  # D-03: no [auth] configured -- gate handles this explicitly, not here
    secrets_dir = Path(".streamlit")
    secrets_dir.mkdir(exist_ok=True)
    toml_body = f'''
[auth]
redirect_uri = "{os.environ["REDIRECT_URI"]}"
cookie_secret = "{os.environ["COOKIE_SECRET"]}"
client_id = "{client_id}"
client_secret = "{os.environ["GOOGLE_CLIENT_SECRET"]}"
server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"
'''
    (secrets_dir / "secrets.toml").write_text(toml_body)
```

### Pattern 2: Domain Enforcement on the Token, Not the Consent Screen
**What:** After `st.login()` completes, `st.user` exposes the parsed ID token claims. Google's
`hd` (hosted domain) claim is present only when the account belongs to a Google Workspace;
falling back to splitting `st.user.email` on `@` is the documented safety net when `hd` is
absent for any reason.
**When to use:** Any time a plan restricts sign-in to one organisation (D-04).
**Example:**
```python
# Source: pattern derived from Streamlit st.user docs [CITED: docs.streamlit.io/develop/api-reference/user/st.login]
# and general OIDC "hd claim" behavior for Google Workspace accounts.
def extract_domain(user) -> str:
    """user is st.user or an injectable fake exposing the same attributes."""
    hd = getattr(user, "hd", None)
    if hd:
        return hd
    email = getattr(user, "email", "") or ""
    return email.split("@")[-1].lower() if "@" in email else ""

def is_authorized_domain(domain: str, allowed: str = "ehealthnigeria.org") -> bool:
    return domain == allowed
```
**Note on claim confirmation:** the exact presence/name of `hd` on `st.user` for a Google
provider was not independently confirmed against a live token in this session (no deployed
Space exists yet to inspect) — tag this claim `[ASSUMED]`, consistent with `hd` being Google's
long-standing standard OIDC extension claim, and confirm it during AUTH-03's manual
verification against the real deployed URL.

### Anti-Patterns to Avoid
- **Trusting the Google consent screen's domain restriction alone:** D-04 explicitly requires
  server-side enforcement on the token claim. A consent-screen-only restriction (Google
  Workspace admin console's "internal" app setting) can be bypassed by app misconfiguration
  and gives no code-level assertion to test.
- **Calling `st.login()`/reading secrets before the materialiser runs:** any `st.*` call
  (including `st.set_page_config`) can trigger Streamlit's secrets loader; the materialiser
  must be the literal first executable lines in `app.py`.
- **Hard-coding the refusal-page contact address:** D-05 requires it be read from secrets,
  the same surface as D-07's SMTP config, so it can be changed without a deploy.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| OIDC token exchange, PKCE, cookie signing | A custom OAuth client using `requests` | `st.login`/`Authlib` (already the declared dependency) | Authlib handles token validation, nonce/state, and cookie signing correctly; a hand-rolled flow is a well-known source of auth vulnerabilities (CSRF via missing `state`, JWT signature bypass) |
| Git history rewriting | Manual `git filter-branch` or scripted `sed` over blobs | `git filter-repo` | `filter-branch` is officially deprecated by the Git project itself for exactly this reason (slow, easy to corrupt history, footguns around refs/tags); `filter-repo` is the tool the Git project's own docs point to |
| Comma-separated secret parsing | A regex-based custom parser | `str.split(",")` + `.strip()` per D-07's own spec ("whitespace-tolerant") | The problem is trivial enough that anything more than split+strip is over-engineering; keep the function pure and testable |

**Key insight:** everything genuinely hard here (OIDC correctness, git history integrity) has
a purpose-built, actively maintained tool; the phase's actual engineering work is wiring and
sequencing (materialise-before-login, gate-before-uploader, scrub-after-merge), not novel logic.

## Common Pitfalls

### Pitfall 1: Secrets Loaded Before Materialisation
**What goes wrong:** `st.login()` raises or silently no-ops because `st.secrets["auth"]`
doesn't exist yet.
**Why it happens:** Streamlit lazily loads `secrets.toml` on first access, but that first
access can be triggered by an earlier, unrelated `st.*` call (e.g. `st.set_page_config`,
`st.markdown` for the CSS block already at the top of `app.py`) if the materialiser runs after
it.
**How to avoid:** Materialiser must be the first import-time side effect in `app.py`, before
line 1's existing `st.set_page_config` block.
**Warning signs:** `KeyError: 'auth'` or `st.login` behaving as if unconfigured on a Space
where secrets are demonstrably set.

### Pitfall 2: Iframe Cookie Loss (DEPLOY-04's root cause)
**What goes wrong:** An officer visiting `huggingface.co/spaces/<org>/<app>` signs in, but the
identity cookie doesn't persist — every page load looks logged-out.
**Why it happens:** The `huggingface.co/spaces/...` page embeds the app in a cross-origin
`<iframe>`; many browsers' third-party-cookie restrictions (Safari ITP, Chrome's phase-out)
block cookies set inside cross-origin iframes. [CITED: huggingface.co/docs/hub/spaces-cookie-limitations,
referenced in `.planning/research/STACK.md`]
**How to avoid:** Distribute only the direct `https://<space>.hf.space` URL (DEPLOY-04); the
iframe wrapper is never the entry point officers use.
**Warning signs:** Sign-in "succeeds" but every subsequent action shows the login page again.

### Pitfall 3: Private Space Blocks Access Before the App Ever Runs
**What goes wrong:** Officers report a 404 or "Space not found" and never see a sign-in
button at all.
**Why it happens:** A private Space's own visibility control is enforced by the HF platform,
independent of and prior to anything `app.py` does. See Open Question 1.
**How to avoid:** Resolve Open Question 1 before deployment — do not assume the private flag
and app-level Google auth compose the way D-01/DEPLOY-01 imply without confirming it.
**Warning signs:** Anyone testing sign-in against the URL before confirming Space visibility
settings gets a false negative that looks like an auth bug.

### Pitfall 4: `MLOS_AUTH_DISABLED` Silently Left Set on the Deployed Space
**What goes wrong:** The dev bypass flag (D-03) is copied into Space secrets "temporarily"
during setup and never removed, defeating AUTH-01 entirely in production.
**Why it happens:** The flag exists precisely because local/test runs need it; it is easy to
carry the same env var into the Space's secret set by habit.
**How to avoid:** The AUTH-03 manual verification checklist must explicitly confirm
`MLOS_AUTH_DISABLED` is **absent** from the deployed Space's secrets, not just that sign-in
"works."
**Warning signs:** The visible "authentication disabled" banner (D-03 requires it) appearing
on the production URL is the tell — it should never be seen there.

## Runtime State Inventory

> This phase deploys the application for the first time to a new host; it does not rename or
> refactor existing identifiers, so the rename/refactor inventory categories are checked for
> completeness rather than expected to surface findings.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None found — this phase creates no new persisted data (the submission log is Phase 5/AUDIT-*, explicitly out of this phase's scope per CONTEXT.md `<domain>`) | none |
| Live service config | The four committed organisational email addresses at `app.py:286-289` [VERIFIED: app.py:286-289 — `TO  = ["[recipient address removed - DEPLOY-02]"]` / `CC  = ["[recipient address removed - DEPLOY-02]", "[recipient address removed - DEPLOY-02]", "[recipient address removed - DEPLOY-02]"]`] are the one piece of "config committed where it shouldn't be" this phase inherits — REQUIREMENTS.md's `app.py:644-647` citation is stale; line numbers moved after Phase 3's refactor. Both a code edit (DEPLOY-02, remove the literals — done, plan 04-02 Task 1) and a history migration (DEPLOY-03, `git filter-repo`) are required — they are separate tasks per D-08 | code edit (done) + history rewrite |
| OS-registered state | None — no OS-level task scheduler, pm2, launchd, or systemd registration exists anywhere in this codebase (single Streamlit process, run via `streamlit run app.py` or the HF Space's own supervisor) | none |
| Secrets/env vars | New secrets this phase introduces on the Space: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `COOKIE_SECRET`, `REDIRECT_URI` (or equivalent names — planner's choice), `SMTP_TO`, `SMTP_CC`, plus the existing `smtp_host`/`smtp_port`/`smtp_user`/`smtp_pass` which stay as-is (D-07). None of these currently exist in the working tree or history — they are populated only by the human at the D-02 checkpoint | code reads new secret names; no existing secret is renamed |
| Build artifacts | None — no compiled/installed artifact in this repo carries the addresses or old auth-related names; `requirements.txt`'s version floor bump (`streamlit>=1.32.0` → `>=1.42.0`) is a declaration change, not a stale artifact | reinstall after `requirements.txt` bump (`pip install -r requirements.txt`) |

**Canonical question answered:** after DEPLOY-02's code edit lands, the four addresses still
exist in every commit prior to the fix, in every clone, and in every fork — DEPLOY-03's
`git filter-repo` run is the only mechanism that reaches that state, which is why CONTEXT.md
and ROADMAP.md both insist the two requirements stay separately scoped.

## Code Examples

### DEPLOY-02: SMTP Recipients from Comma-Separated Secrets
```python
# Source: pattern derived from D-07's spec; st.secrets.get() usage matches the existing
# app.py:294-303 pattern for smtp_host/smtp_port/smtp_user/smtp_pass [VERIFIED: app.py:294-303]
def get_recipients():
    """Returns (to_list, cc_list, error_message_or_None)."""
    to_raw = st.secrets.get("SMTP_TO", "") or os.environ.get("SMTP_TO", "")
    cc_raw = st.secrets.get("SMTP_CC", "") or os.environ.get("SMTP_CC", "")
    to_list = [a.strip() for a in to_raw.split(",") if a.strip()]
    cc_list = [a.strip() for a in cc_raw.split(",") if a.strip()]
    if not to_list:
        return [], [], "SMTP_TO is not configured — Send is disabled."
    return to_list, cc_list, None
```
**Verification note on `st.secrets` reading env vars:** Streamlit's `st.secrets` object reads
from `.streamlit/secrets.toml` (and Streamlit Cloud's secrets UI, which materialises the same
file server-side). On Hugging Face Spaces, secrets are injected as **plain OS environment
variables**, not as a `secrets.toml` file HF writes for you — `st.secrets` will **not**
automatically see them. This is the same flat-env-var-vs-nested-TOML gap D-01 already
identifies for `[auth]`, and it applies identically to `SMTP_TO`/`SMTP_CC`/`smtp_host` etc.
**Recommendation:** read secrets via `os.environ.get(...)` (with an `st.secrets.get(...)`
fallback for local `.streamlit/secrets.toml`-based dev), not `st.secrets` alone, for every
value this phase adds — this affects both the SMTP block and the `[auth]` materialiser inputs.
Tag `[ASSUMED]`: this is standard Streamlit-on-arbitrary-container-host behavior (matches the
documented rationale for the `[auth]` materialiser itself) but was not independently confirmed
against a live HF Space this session — add to the Assumptions Log.

### DEPLOY-03: History Scrub with `git filter-repo`
```bash
# Source: git-filter-repo's own README pattern for --replace-text
# [CITED: github.com/newren/git-filter-repo] -- exact literals from app.py:286-289
# 1. Notify collaborators; confirm no unpushed work anywhere (blocking-human checklist item)
brew install git-filter-repo   # macOS

# 2. Build the replacement-expressions file (one literal per line -> redacted).
#    [recipient address removed - DEPLOY-02]: the four exact address literals are NOT
#    transcribed into any tracked file (this one included) -- plan 04-06's preparation task
#    derives them from git history at run time (e.g. `git log -p` over the pre-04-02 commits
#    that introduced app.py's TO/CC literals), so this guide's own text cannot become the
#    thing DEPLOY-03's standing scan (tests/test_no_committed_secrets.py, plan 04-02 Task 2)
#    would have to exempt.
cat > /tmp/addresses.txt <<'EOF'
<address-1>==>REDACTED
<address-2>==>REDACTED
<address-3>==>REDACTED
<address-4>==>REDACTED
EOF

# 3. Run from a FRESH clone (filter-repo refuses to run on a repo with an existing remote
#    by default, as a safety check) -- run once, after feature/qc-rules has merged to main (D-08)
git clone git@github.com:eHealthAfrica/mlos_checkout_qc.git scrub-clone
cd scrub-clone
git filter-repo --replace-text /tmp/addresses.txt

# 4. Verify BEFORE force-pushing -- across all refs, not just HEAD
git log --all -S '<address-1>' --oneline   # expect: no output (repeat per address)
git grep -I 'ehealthnigeria.org' $(git rev-list --all) 2>/dev/null | grep -v REDACTED  # expect: no output

# 5. Force-push all branches and tags (blocking-human -- see checklist below)
git push origin --force --all
git push origin --force --tags

# 6. Every collaborator re-clones (existing clones are now diverged and cannot be merged back)
```
**DEPLOY-03 blocking-human checklist (per D-08):**
1. Confirm `feature/qc-rules` has merged to `main` (do not rewrite before merge).
2. Notify all collaborators; confirm nobody has unpushed local work.
3. Run `git filter-repo --replace-text` with the exact four literals (derived from git history
   at run time, per the note above — not transcribed into this or any other tracked file), on a
   fresh clone.
4. Verify with `git log --all -S '<address>'` for each of the four addresses — expect zero
   hits — and a full-history `git grep` sweep.
5. Force-push all branches and tags to `eha` (`github.com/eHealthAfrica/mlos_checkout_qc.git`).
6. Every collaborator deletes their local clone and re-clones fresh; existing clones are
   permanently incompatible with the rewritten history.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| `git filter-branch` for history rewrites | `git filter-repo` | Git project's own docs have recommended against `filter-branch` for several years, pointing to `filter-repo` instead | Faster, safer, avoids the classic `filter-branch` footguns around tags/refs and stale reflog entries |
| Streamlit Community Cloud + `st.secrets` from its own UI | Hugging Face Spaces + flat env-var secrets | This project's own PROJECT.md constraint (RAM headroom) | `st.secrets`'s TOML-file assumption doesn't hold on Spaces without a materialisation step — this is the D-01 consequence and the DEPLOY-02 `SMTP_TO`/`SMTP_CC` gotcha both stem from the same underlying platform difference |

**Deprecated/outdated:**
- `git filter-branch`: superseded by `git filter-repo` for history rewrites; do not use.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Google's `hd` claim is exposed on `st.user` exactly as named, with the documented `.email`/`@`-split fallback behaving as described | Architecture Patterns: Pattern 2 | If the claim name differs or is absent in Streamlit 1.63's actual token parsing, D-04's domain check silently never fires or always fails-closed; must be confirmed live during AUTH-03 |
| A2 | `st.secrets` does not automatically surface HF Space env-var-injected secrets, requiring `os.environ.get()` reads instead for `SMTP_TO`/`SMTP_CC` and any other new secret | Code Examples: DEPLOY-02 | If wrong (i.e., `st.secrets` does transparently proxy env vars on Spaces), the `os.environ` fallback is harmless but unnecessary; if right and unaddressed, `SMTP_TO`/`SMTP_CC` silently read as empty on the deployed Space even though the human correctly set them, disabling the Send button in production with no obvious cause |
| A3 | A private HF Space's visibility gate applies to every browser visitor, not only to programmatic/API access, meaning it would block a non-HF-account officer before `st.login` ever runs | Summary / Open Question 1 / Pitfall 3 | This is the load-bearing assumption behind the entire Open Question — if wrong (private Spaces only gate API/clone access, not the rendered app page for anyone with the direct link), DEPLOY-01 as worded is achievable exactly as D-01 assumes and no redesign is needed. This must be confirmed by an actual test against a real private Space before planning finalizes the Space-visibility decision |

**If this table is empty:** N/A — three assumptions above require confirmation; the highest-priority is A3 (Open Question 1).

## Open Questions

1. **Does a private Hugging Face Space's own access control block a visitor with no Hugging Face account from ever reaching the rendered app — even if they have the direct `*.hf.space` URL?**
   - What we know: Hugging Face's docs and community threads describe private Spaces as
     "only accessible to the owner and collaborators," with non-collaborator visitors getting a
     404 [CITED: huggingface.co/docs/hub/en/spaces-overview; community forum threads on private
     Space access]. This describes repository/API-level access clearly; whether the *rendered
     Space page itself* (the iframe'd or directly-hosted app) enforces the same gate for a
     browser visitor with only the URL is not fully disambiguated by the sources fetched this
     session.
   - What's unclear: If the gate does apply to the rendered page, state officers (Google
     Workspace accounts, not Hugging Face accounts) could never reach `st.login` at all — DEPLOY-01's
     "one private Space officers in every state reach" would be unbuildable as worded without
     first adding every officer as an HF org member/collaborator, which reintroduces exactly
     the second-identity-system problem D-01 was written to avoid.
   - Recommendation: **Before finalising the plan, have the user (or Claude, with the user's
     Space) create a throwaway private Space and test whether an unauthenticated, non-collaborator
     browser (e.g. an incognito window with no HF login) can reach the rendered app at its direct
     URL.** If it can (the private flag governs API/git access only, not page rendering), D-01/DEPLOY-01
     proceed exactly as decided. If it cannot, raise back to the user as a **discuss-phase-level
     decision, not a planner's call**: likely resolutions are (a) make the Space public and rely
     on the app-level Google-domain check as the real gate (the most consistent with D-01's
     intent), or (b) keep it private and add every officer as an org member (reopens the
     "officers need HF accounts" problem D-01 rejected). Do not let the planner silently choose
     between these — CONTEXT.md's `<decisions>` would need a new entry either way.

2. **Exact claim name and structure for Google's hosted-domain signal on `st.user`.**
   - What we know: Google's OIDC `hd` claim is the standard mechanism; Streamlit's docs
     describe `st.user` exposing parsed ID token attributes generically (name, email) without
     an exhaustive claims list in the pages fetched this session.
   - What's unclear: Whether `st.user.hd` is populated verbatim, requires accessing a raw
     claims dict, or needs `expose_tokens = true` in `[auth]` to surface at all.
   - Recommendation: confirm empirically once a Space with real `[auth]` config exists (part of
     AUTH-03's verification), and adjust `extract_domain()` (Pattern 2) accordingly; the
     email-domain-split fallback already in that function should make this low-risk either way.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `streamlit[auth]` (Authlib) | AUTH-01, AUTH-02 | ✓ (streamlit already installed) | 1.63.0 installed; Authlib 1.8.0 on PyPI, not yet installed | Install via `pip install "streamlit[auth]"` — no fallback needed, this is a standard pip install |
| `git-filter-repo` | DEPLOY-03 | not checked this session (macOS dev machine, not sandboxed here) | 2.47.0 on PyPI/Homebrew | `brew install git-filter-repo`; BFG Repo-Cleaner is the documented alternative but was explicitly rejected by D-08 |
| A live/reachable Hugging Face Space | AUTH-03, DEPLOY-01, DEPLOY-04, D-06's synthetic-data deploy | Not yet created — this phase creates it | — | None — this is the deliverable itself; the `blocking-human` checkpoints (D-02, D-06) gate its creation |
| Google Cloud OAuth client with a registered redirect URI | AUTH-01, AUTH-02 | Exists already per D-02, but the Space's redirect URI is not yet added to it | — | None — D-02's `checkpoint:human-action` is the only path; no plan task may fabricate these values |

**Missing dependencies with no fallback:**
- The deployed Space itself (blocks AUTH-03's real verification) — expected; this phase's job is to create it, gated by D-02 and D-06.
- The registered redirect URI on the existing Google OAuth client — requires the D-02 human action.

**Missing dependencies with fallback:**
- `Authlib` — trivially installed via the `streamlit[auth]` extra; no risk.
- `git-filter-repo` — standard Homebrew install on macOS; no risk.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (installed, `pytest>=8.0.0,<10.0.0` per Phase 1 pin) |
| Config file | `pytest.ini` — `testpaths = tests`, `python_files = test_*.py` |
| Quick run command | `python3 -m pytest tests/test_auth_domain.py tests/test_secrets_materializer.py tests/test_no_committed_secrets.py -q` |
| Full suite command | `python3 -m pytest tests/ -q` (195 tests as of Phase 3; this phase adds new files, does not remove existing ones) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AUTH-01 | Uploader/QC never renders for a signed-out user | unit (injectable fake `st.user`) | `pytest tests/test_auth_gate.py -x` | ❌ Wave 0 |
| AUTH-02 | No password field or password-storing code path exists anywhere in the auth module | static/AST guard | `pytest tests/test_no_password_storage.py -x` | ❌ Wave 0 |
| AUTH-03 | Sign-in works against the real deployed `*.hf.space` URL | **manual-only** — no browser automation available for a live OIDC round-trip against Google in this environment | Manual checklist (see below); not automatable in CI | N/A |
| D-04 (domain enforcement, feeds AUTH-01) | `is_authorized_domain()` returns True only for `ehealthnigeria.org`, False for others, handles missing `hd` via email-domain fallback | unit | `pytest tests/test_auth_domain.py -x` | ❌ Wave 0 |
| D-03 (dev bypass banner) | `MLOS_AUTH_DISABLED=1` with no `[auth]` shows the banner and lets the app proceed; absent both, app stops with a clear message | unit (env var injection, `st.stop()` mocked/caught) | `pytest tests/test_auth_bypass_flag.py -x` | ❌ Wave 0 |
| D-05 (refusal page) | Out-of-domain signed-in user sees refusal text, contact address from secrets, no uploader rendered | unit (rendering-call assertion, not visual) | `pytest tests/test_refusal_page.py -x` | ❌ Wave 0 |
| DEPLOY-02 | `get_recipients()` parses comma-separated `SMTP_TO`/`SMTP_CC`, disables Send with empty `SMTP_TO` | unit | `pytest tests/test_smtp_recipients.py -x` | ❌ Wave 0 |
| DEPLOY-02/DEPLOY-03 | No email-address literal or secret value appears in tracked source | standing AST/grep guard (reuses `tests/test_no_streamlit_in_qc.py`'s idiom) | `pytest tests/test_no_committed_secrets.py -x` | ❌ Wave 0 |
| Secrets materialiser | `.streamlit/secrets.toml` renders correctly from a fake env dict; no-ops when `GOOGLE_CLIENT_ID` unset | unit | `pytest tests/test_secrets_materializer.py -x` | ❌ Wave 0 |
| DEPLOY-01/DEPLOY-04 | Direct `*.hf.space` URL reachable with cookies intact | **manual-only** — requires a real deployed Space and a real browser | Manual checklist | N/A |

### Sampling Rate
- **Per task commit:** the quick run command above.
- **Per wave merge:** `python3 -m pytest tests/ -q` (full suite).
- **Phase gate:** Full suite green before `/gsd-verify-work`, plus the two manual-only items
  (AUTH-03, DEPLOY-01/04) walked through against the real deployed Space by a human.

### Wave 0 Gaps
- [ ] `tests/test_auth_gate.py` — covers AUTH-01
- [ ] `tests/test_no_password_storage.py` — covers AUTH-02
- [ ] `tests/test_auth_domain.py` — covers D-04
- [ ] `tests/test_auth_bypass_flag.py` — covers D-03
- [ ] `tests/test_refusal_page.py` — covers D-05
- [ ] `tests/test_smtp_recipients.py` — covers DEPLOY-02
- [ ] `tests/test_no_committed_secrets.py` — covers DEPLOY-02/DEPLOY-03 regression guard, reusing `tests/test_no_streamlit_in_qc.py`'s AST-walk idiom against a literal-string/email-pattern scan instead of an import scan
- [ ] `tests/test_secrets_materializer.py` — covers the `[auth]` TOML-rendering helper
- [ ] Framework install: none needed — pytest already present and configured

### Manual-Only Verification Checklist (AUTH-03, DEPLOY-01, DEPLOY-04)
Cannot be scripted in this environment (no live browser, no real Google OAuth round-trip, no
deployed Space). Human-executed checklist for the `blocking-human` checkpoint:
1. Open the direct `https://<space>.hf.space` URL in an incognito/private browser window.
2. Confirm the sign-in prompt appears before any uploader or tab is visible.
3. Sign in with an `ehealthnigeria.org` Google account; confirm the uploader appears.
4. Sign out; sign in with a non-`ehealthnigeria.org` Google account (or a personal Gmail);
   confirm the refusal page appears, showing the contact address and a sign-out button, with
   no uploader/tabs reachable.
5. Reload the page after step 3's successful sign-in; confirm the session persists (cookie
   intact) without re-prompting.
6. Confirm `MLOS_AUTH_DISABLED` is **not** present in the Space's secrets (Pitfall 4).
7. Confirm the `huggingface.co/spaces/...` embed URL is **not** the one distributed to
   officers (DEPLOY-04) — document the direct URL in README §"Deployment" instead.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | Delegated entirely to Google OIDC via `st.login`/Authlib — no password is ever accepted, stored, or compared by this application (AUTH-02) |
| V3 Session Management | yes | Streamlit's `[auth]` `cookie_secret`-signed identity cookie; default expiry accepted per CONTEXT.md discretion; `st.logout()` invalidates the local session (does not revoke the IdP-side session, a documented Streamlit limitation) |
| V4 Access Control | yes | Domain-claim check (D-04) enforced server-side on every render via the `require_login()` gate, not client-side or consent-screen-only |
| V5 Input Validation | yes | `SMTP_TO`/`SMTP_CC` parsing must reject/strip malformed entries defensively (comma-split + strip, per D-07); no new file-upload surface is introduced by this phase |
| V6 Cryptography | yes | `cookie_secret` must be a strong, randomly generated value per Streamlit's own guidance [CITED: docs.streamlit.io] — never a guessable string; generation is the human's responsibility at the D-02 checkpoint, not something the app generates or defaults |

### Known Threat Patterns for This Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Consent-screen-only domain restriction bypassed by a misconfigured or externally-shared OAuth client | Elevation of Privilege | Server-side `hd`/email-domain check on every request (D-04), never relying on Google Workspace's "internal app" consent-screen setting alone |
| Secrets committed to git (recurrence of the DEPLOY-02/DEPLOY-03 defect class) | Information Disclosure | Standing AST/grep guard (`tests/test_no_committed_secrets.py`) asserting no email literal or secret-shaped string appears in tracked source, run on every commit |
| Weak or default `cookie_secret` allowing session forgery | Spoofing | Human-generated random secret at deployment time; document the requirement explicitly in README §"Deployment" rather than shipping a placeholder value anywhere in code |
| Auth bypass flag (`MLOS_AUTH_DISABLED`) accidentally left set on the production Space | Elevation of Privilege | Visible "authentication disabled" banner (D-03) makes the state undeniable on screen; AUTH-03's manual checklist explicitly checks its absence in Space secrets |
| Private-Space access-control assumption papering over a real gap (Open Question 1) | Elevation of Privilege / Denial of Service (legitimate officers locked out, or unintended parties let in) | Resolve Open Question 1 explicitly before deployment rather than assuming either shape |

## Sources

### Primary (HIGH confidence)
- PyPI registry (`pypi.org/pypi/<package>/json`), queried directly this session — versions and
  release history for `streamlit` (1.63.0), `Authlib` (1.8.0), `git-filter-repo` (2.47.0).
- Direct codebase reads this session: `app.py:1-40` (top-of-file import/config block),
  `app.py:260-320` (`send_qc_email`, `load_boundary_refs`), `tests/test_no_streamlit_in_qc.py`
  (AST-guard idiom to reuse), `.planning/config.json` (`nyquist_validation: true`,
  `security_enforcement: true`, `security_asvs_level: 1`), `requirements.txt`, `pytest.ini`.

### Secondary (MEDIUM confidence)
- `https://docs.streamlit.io/develop/api-reference/user/st.login` (WebFetch this session) —
  `[auth]` secrets.toml shape, `st.user.is_logged_in`, cookie 30-day expiry, `st.logout()`
  behavior, Authlib `>=1.3.2` requirement.
- `https://huggingface.co/docs/hub/en/spaces-oauth` (WebFetch this session) — native
  `hf_oauth` env vars, `SPACE_HOST`, redirect URL pattern, iframe/cookie `target="_blank"`
  warning (context for DEPLOY-04's rationale, not the chosen auth path per D-01).
- WebSearch this session — Streamlit `st.login`/`st.user`/Authlib secrets shape
  (cross-referenced against the WebFetch above); Hugging Face private Space access-control
  description ("only accessible to the owner and collaborators... 404 for others").
- `.planning/research/STACK.md` (2026-09-09, prior research pass) — the flat-env-var vs
  nested-TOML pitfall (Streamlit #10543), the `hf_oauth` vs `st.login` comparison (superseded
  for provider choice by D-01, still valid for the technical mechanics description), the
  `sdk: streamlit` vs `sdk: docker` XSRF/iframe distinction.

### Tertiary (LOW confidence / flagged for validation)
- The exact behavior of `st.user`'s `hd` claim exposure (Assumption A1, Open Question 2) —
  training-knowledge-consistent but not confirmed against a live token this session.
- Whether a private Space's page-render access control (as opposed to its API/git access
  control) blocks a non-collaborator browser visitor (Assumption A3, Open Question 1) — the
  single most important unresolved fact for this phase's planning.

## Metadata

**Confidence breakdown:**
- Standard stack (streamlit[auth], Authlib, git-filter-repo versions): HIGH — PyPI-verified this session
- `st.login`/`[auth]` secrets shape: MEDIUM — official docs fetched this session, but not exercised against a live Space
- HF Spaces private-access-vs-app-auth interaction: LOW — this is Open Question 1; do not plan around an assumed answer
- DEPLOY-02/DEPLOY-03 mechanics: HIGH — direct codebase reads for exact line numbers/literals, well-documented `git filter-repo` usage
- Testing strategy: MEDIUM — the unit-testable boundary follows this project's own established `qc/`-purity precedent; the manual-only items are inherent to OIDC/live-deployment verification, not a gap in this research

**Research date:** 2026-09-10
**Valid until:** ~14 days (Streamlit auth APIs and HF Spaces platform behavior have both changed within the last year; re-verify before executing if this research goes stale)
