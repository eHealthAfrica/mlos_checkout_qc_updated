# Phase 4: Central Deployment and Officer Identity - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-10
**Phase:** 4-Central Deployment and Officer Identity
**Areas discussed:** Identity provider, Who is allowed in, Data-governance sign-off, Secrets and history scrub

---

## Identity provider

**Q1. Who should officers sign in as?**

| Option | Description | Selected |
|--------|-------------|----------|
| Hugging Face accounts (Recommended by research) | hf_oauth: true, flat env vars injected, nothing to provision | |
| Google Workspace via st.login | Existing work identity; OAuth app, redirect URI, Authlib, secrets.toml startup step | ✓ |
| Microsoft Entra via st.login | Same machinery against an Entra tenant | |
| Decide later | Leave AUTH-01/02 unplannable | |

**User's choice:** Google Workspace via st.login.

**Q2. Registering the Google OAuth client — where does it stand?**

| Option | Description | Selected |
|--------|-------------|----------|
| I can create it myself when the plan reaches that task | One blocking human-action checkpoint | |
| IT or another team must create it | Sequence other work first | |
| Already exists | Only the redirect URI needs adding | ✓ |

**User's choice:** Already exists.

**Q3. Local runs with no [auth] secrets?**

| Option | Description | Selected |
|--------|-------------|----------|
| Bypass login only with an explicit opt-out (Recommended) | Env flag plus visible banner; missing secrets without the flag stops the app | ✓ |
| Never bypass | Every contributor needs OAuth credentials | |
| Bypass automatically when secrets are absent | Misconfigured Space would silently run open | |

**User's choice:** Bypass only with an explicit opt-out.

---

## Who is allowed in

**Q1. Which accounts may run a check?**

| Option | Description | Selected |
|--------|-------------|----------|
| Only the ehealthnigeria.org Workspace domain (Recommended) | Hosted-domain claim enforced; others refused | ✓ |
| A domain allow-list in Space secrets | Multiple domains, editable without deploy | |
| An explicit email allow-list in Space secrets | Named officers only | |
| Any Google account | Identity for the log, no restriction | |

**User's choice:** Only the ehealthnigeria.org domain.

**Q2. What should an authenticated but not-allowed user see?**

| Option | Description | Selected |
|--------|-------------|----------|
| Refusal page with a contact (Recommended) | Clear statement, contact from secrets, sign-out button | ✓ |
| Same as signed-out | Back to sign-in with no explanation | |

**User's choice:** Refusal page with a contact.

---

## Data-governance sign-off

**Q1. Where does the sign-off stand?**

| Option | Description | Selected |
|--------|-------------|----------|
| Not yet obtained; plan must gate on it | Blocking human gate before first deploy; code work proceeds | ✓ |
| Already obtained | Record approver and date | |
| Obtained on condition uploads are not retained | Add non-retention invariant | |

**User's choice:** Not yet obtained; plan must gate on it.

---

## Secrets and history scrub

**Q1. How should the recipient list live in Space secrets?**

| Option | Description | Selected |
|--------|-------------|----------|
| Two variables, comma-separated (Recommended) | SMTP_TO and SMTP_CC; missing SMTP_TO disables Send visibly | ✓ |
| One JSON variable | Stricter shape, harder to hand-edit | |

**User's choice:** Two variables, comma-separated.

**Q2. When and how to remove the committed addresses from history?**

| Option | Description | Selected |
|--------|-------------|----------|
| git filter-repo, after feature/qc-rules merges to main (Recommended) | One rewrite, checklist, force-push, re-clone, verify | ✓ |
| git filter-repo, on this branch now | Two disruptions | |
| BFG Repo-Cleaner | Java tool, same outcome | |

**User's choice:** git filter-repo after the merge.

---

## Claude's Discretion

- Module layout for the auth gate, domain check and secrets.toml materialiser.
- Space README metadata (`sdk: streamlit`, Python 3.11) and where it lives.
- Cookie lifetime; sign-out placement.
- README Deployment section rewrite (required).
- Free-tier idle sleep accepted; no-address-literal standing test recommended.

## Deferred Ideas

- Domain/email allow-list beyond the Workspace domain.
- Native Hugging Face OAuth as fallback.
- Always-on hosting (paid tier, out of scope).
- Role-based access segregation (v2, ACL-01).
