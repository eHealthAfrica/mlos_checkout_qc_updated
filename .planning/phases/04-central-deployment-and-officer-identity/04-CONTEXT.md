# Phase 4: Central Deployment and Officer Identity - Context

**Gathered:** 2026-09-10
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase puts the M1 verdict in officers' hands: one private Hugging Face Space at a direct
`*.hf.space` URL, sign-in required before any check runs, SMTP credentials and the recipient
list read from Space secrets, and the organisational addresses committed in `app.py` removed
from git history, not only from the working tree.

It delivers **no new checks, no report or scoring changes, and no submission log**. The
submission record is Phase 5 (AUDIT-*); role-based or per-state access segregation is v2
(ACL-01) and is not smuggled in as an allow-list rule. Threshold configuration and new QC
layers are Phases 6 and 7.

Requirements closed: DEPLOY-01, DEPLOY-02, DEPLOY-03, DEPLOY-04, AUTH-01, AUTH-02, AUTH-03.

</domain>

<decisions>
## Implementation Decisions

### Identity Provider (AUTH-01, AUTH-02)

- **D-01:** Officers sign in with their **Google Workspace identity via Streamlit's `st.login`
  / `st.user`**, not with Hugging Face accounts. The research recommendation (native
  `hf_oauth: true`) was presented and **not chosen**: the user wants officers to keep their
  existing work identity. — **Reversibility:** costly — the identity provider decides what the
  Phase 5 submission log records as "who"; switching providers later changes the identity
  string on every logged submission and every officer's sign-in instructions.

  *Recorded deviation:* native Hugging Face OAuth was the recommended option and was not
  chosen. The planner must not revert to it as a "simpler" path.

  **Consequence the planner must handle:** Space secrets surface as **flat environment
  variables**, and `st.login` reads only the nested `[auth]` table of an actual
  `.streamlit/secrets.toml` (Streamlit issue #10543, per `.planning/research/STACK.md`). A
  startup step must render `.streamlit/secrets.toml` from the flat env vars **before any
  `st.*` call triggers secrets loading**. `streamlit>=1.42.0` and `Authlib>=1.3.2` (the
  `streamlit[auth]` extra) become declared dependencies; Streamlit 1.63.0 is installed and
  already exposes `st.login` and `st.user`.

- **D-02:** The Google OAuth client **already exists**; only the Space host's redirect URI needs
  adding to it. The plan therefore carries **one `checkpoint:human-action`**, gated
  `blocking-human`: the user adds the redirect URI and pastes the client id, client secret and
  a cookie secret into Space secrets; Claude then verifies sign-in against the deployed URL
  (AUTH-03). No plan task may fabricate or commit these values.

- **D-03:** When the app runs **with no `[auth]` configuration** (developer laptop, pytest),
  the login gate is bypassed **only when an explicit opt-out environment variable is set**
  (name is the planner's choice, e.g. `MLOS_AUTH_DISABLED=1`), and the page shows a visible
  "authentication disabled" banner. Missing auth configuration **without** the flag stops the
  app with a clear message rather than running open. Automatic bypass on absent secrets was
  offered and rejected: a misconfigured Space would silently violate success criterion 2.

### Who Is Allowed In (AUTH-01)

- **D-04:** Sign-in is accepted **only for the `ehealthnigeria.org` Google Workspace domain**,
  enforced on the token's hosted-domain / email-domain claim after authentication, not by
  trusting the Google consent screen alone. A domain allow-list, an explicit email
  allow-list, and "any Google account" were offered and not chosen. State officers must have
  Workspace accounts. — **Reversibility:** reversible — widening to an allow-list later is a
  configuration and a small code change; nothing filed depends on it.
- **D-05:** An authenticated user outside the domain sees a **refusal page**: a plain
  statement that the account is not authorised for this tool, the data-team contact address
  read from Space secrets (not hard-coded), and a sign-out button. No uploader, no tabs, no
  QC can run. Bouncing them back to the sign-in page with no explanation was rejected.

### Data-Governance Sign-Off (DEPLOY-01)

- **D-06:** The sign-off for hosting settlement coordinates and population figures on a
  third-party free tier **has not yet been obtained**. The plan **must gate the first
  deployment of the private Space on it** with a `checkpoint:human-action` rated
  `blocking-human`, naming the approver and recording the decision in this file's
  `<decisions>` and in STATE.md when it arrives. All code and configuration work proceeds
  without waiting; only the act of creating or making reachable the Space that holds real
  data waits. A deploy against synthetic fixture data for AUTH-03's login verification is
  acceptable before sign-off, provided no real settlement file is uploaded to it.

### Secrets and History Scrub (DEPLOY-02, DEPLOY-03)

- **D-07:** SMTP recipients live in Space secrets as **two comma-separated variables**,
  `SMTP_TO` and `SMTP_CC`, whitespace-tolerant, editable in the Space UI without a deploy. A
  single JSON variable was offered and not chosen. If `SMTP_TO` is missing or empty the Send
  button is **disabled with a visible reason**, never silently emailing nobody. The existing
  `smtp_host`, `smtp_port`, `smtp_user`, `smtp_pass` keys stay as secrets; the hard-coded
  `TO` and `CC` lists in `send_qc_email` (`app.py:286-289` at the time of discussion) are
  deleted.
- **D-08:** The committed addresses are removed from history with **`git filter-repo`, run
  once, after `feature/qc-rules` has merged to `main`**, so the branch and `main` are not
  rewritten separately. Rewriting the branch now (two disruptions) and BFG Repo-Cleaner were
  offered and not chosen. — **Reversibility:** one-way — a history rewrite plus force-push
  invalidates every existing clone and cannot be undone once collaborators have re-cloned.
  The plan must therefore carry the rewrite as a `blocking-human` checkpoint with a
  checklist: notify collaborators, confirm no unpushed work, run filter-repo with the exact
  address literals, force-push all branches and tags, everyone re-clones, verify with
  `git log -S` on each address across all refs. "Removed from the working tree" (DEPLOY-02)
  and "removed from history" (DEPLOY-03) are separate tasks and separate acceptance criteria.

### Claude's Discretion

- **Where auth code lives.** ROADMAP names an `auth.py` boundary; the planner chooses the
  module and its shape (a `require_login()` gate called before the uploader; a domain check
  helper; the secrets.toml materialiser). It must be importable and unit-testable without a
  live Streamlit session where possible, following `qc/` and `qc/report.py` precedent, while
  the `st.login` / `st.user` calls themselves stay in `app.py` or a thin Streamlit-only module.
- **Space metadata.** `sdk: streamlit` in the Space README front matter (research: Docker SDK
  loses the XSRF/iframe workaround `st.file_uploader` needs); Python 3.11 floor for
  `pandas==3.0.5`; free CPU basic hardware. Whether the Space README lives in this repo or
  the Space repo is the planner's call; the app must not depend on it either way.
- **Cookie lifetime and sign-out.** Streamlit's `[auth]` `cookie_secret` and its default
  expiry are acceptable; a sign-out button is required on the refusal page (D-05) and
  reasonable on the main page.
- **Officer instructions.** DEPLOY-04 requires officers be given the direct `*.hf.space` URL.
  README §"Deployment" should be rewritten from Streamlit Community Cloud to Hugging Face
  Spaces, including the direct-URL note and the secrets list. Required, not optional.
- **Free-tier sleep.** A free Space sleeps after 48 hours idle and cold-starts on the next
  visit. Accepted as-is (paid hosting is out of scope); the README may mention the wait.
- **Structural guard.** A standing test that no email address literal and no secret value
  appears in tracked source (the AST/grep idiom Phases 1 to 3 established) is strongly
  recommended so DEPLOY-02 cannot silently regress.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope and requirements
- `.planning/ROADMAP.md` — Phase 4 section: goal, four success criteria, the Notes paragraph
  on the two open items and on keeping DEPLOY-02 and DEPLOY-03 separately scoped
- `.planning/REQUIREMENTS.md` — DEPLOY-01 to DEPLOY-04, AUTH-01 to AUTH-03; the Out of Scope
  rows on password storage and role-based segregation; Open Items rows on the OIDC provider
  and the governance sign-off (both now answered above)
- `.planning/PROJECT.md` — Hosting, Storage, Security and Privacy constraints; Key Decisions
  on HF Spaces and OIDC; Open Items on the Python 3.11 floor
- `.planning/STATE.md` — the two Phase 4 blockers (OIDC provider; governance sign-off)

### Technical grounding
- `.planning/research/STACK.md` — the `hf_oauth` vs `st.login` comparison, the flat-env-var
  vs nested-TOML pitfall (Streamlit #10543), the `streamlit[auth]` / `Authlib>=1.3.2`
  dependency, the `sdk: streamlit` recommendation and the XSRF/iframe pitfall
- `.planning/research/FEATURES.md` — login gate as a precondition for the Phase 5 log; the
  explicit deferral of RBAC
- `https://huggingface.co/docs/hub/en/spaces-oauth` and Streamlit's `st.login` / `st.user`
  documentation — fetch current versions during research; behaviour has changed across
  Streamlit releases

### Subject code
- `app.py` — `send_qc_email` (hard-coded `TO`/`CC` lists and `st.secrets` reads); the top of
  the file, where the secrets.toml materialiser and the login gate must run before the first
  `st.*` call; the sidebar/uploader entry point that the gate must precede
- `qc/report.py` — the pure email subject/body builder Phase 3 created; the thin sender in
  `app.py` is the only place that reads SMTP secrets
- `requirements.txt` — `streamlit>=1.32.0,<2.0.0` floor must rise to `>=1.42.0`; add
  `Authlib`; keep `pandas==3.0.5`
- `README.md` — §"Deployment" and the SMTP secrets section (currently Streamlit Community
  Cloud instructions) to rewrite for Hugging Face Spaces and the direct URL
- `tests/test_no_streamlit_in_qc.py` — the import-boundary and AST idiom to reuse for the
  no-literal-addresses guard

**No external ADRs or specs exist** for this project.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `send_qc_email` already reads host, port, user and password from `st.secrets`; only the
  recipient lists are literals. DEPLOY-02 is a small edit at one site.
- Phase 3 split email composition (`qc/report.py`) from sending (`app.py`), so the sender is
  the single place secrets are read.
- The AST-over-`app.py` standing-test idiom (Phases 1 to 3) fits a "no address literals in
  tracked source" guard directly.

### Established Patterns
- `qc/` stays Streamlit-free; Streamlit-touching code lives in `app.py` or a thin module.
- Configuration that must be tunable without a deploy lives in secrets or config, never in
  code (PROJECT.md Configuration constraint; D-07 follows it).
- Blocking-human gates for one-way decisions and for facts only a human can establish
  (Phase 2 D-12 precedent; D-02, D-06 and D-08 here).

### Integration Points
- The login gate must run before the file uploader renders; everything below the sidebar in
  `app.py` is conditional on an authenticated, in-domain user or the explicit dev bypass.
- The refusal page (D-05) reads its contact address from the same secrets surface as D-07.
- Phase 5 will read the signed-in identity from `st.user` for the submission log; expose it
  cleanly (a small accessor) rather than reaching into `st.user` from many sites.

</code_context>

<specifics>
## Specific Ideas

- Sign-in must be with the officer's work Google account; Hugging Face accounts were
  explicitly declined.
- Only `ehealthnigeria.org` may run a check; anyone else sees a polite refusal with a contact.
- Nothing about the deployment may quietly run without authentication: local bypass needs an
  explicit flag and shows a banner.
- The governance sign-off and the history rewrite are both human gates the plan must stop at.

</specifics>

<deferred>
## Deferred Ideas

- **Domain or email allow-list beyond the Workspace domain** — offered, not chosen; revisit if
  state officers outside `ehealthnigeria.org` need access. A configuration change, not a
  redesign.
- **Native Hugging Face OAuth** — the research recommendation, declined for identity reasons;
  remains the fallback if the Google OAuth client cannot be reused.
- **Always-on hosting** to avoid the 48-hour idle sleep — paid tier, out of scope by
  constraint.
- **Role-based / per-state access segregation** — already v2 (ACL-01); D-04 is authentication
  scope, not authorization.

</deferred>

---

*Phase: 4-Central Deployment and Officer Identity*
*Context gathered: 2026-09-10*
