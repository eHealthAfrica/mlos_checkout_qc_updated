"""Recipient-list parsing for the QC summary email, new for DEPLOY-02/D-07.

Pure module: no ``import streamlit``, no environment access (``os.environ``) and no address
validation beyond emptiness -- ``app.py::get_recipients`` reads the two comma-separated secrets
(``SMTP_TO``/``SMTP_CC``) through ``auth.secret`` and passes the raw strings in here; this module
only turns those raw strings into recipient lists and the message that explains why Send is
disabled, which is why it is unit-testable with plain string arguments and no live session --
matching ``qc/columns.py``'s purity discipline (no env access, no Streamlit import inside the
pure functions).

Two alternatives were offered during discussion and rejected (D-07):

- A single JSON-valued secret (e.g. ``SMTP_RECIPIENTS='{"to": [...], "cc": [...]}'``) was offered
  and not chosen: two comma-separated variables are what a person can edit in the Space UI
  without a deploy, and a later contributor must not "improve" this into a JSON parse -- that
  would reintroduce exactly the editability-without-a-deploy friction D-07 exists to avoid.
- A regex-validating address parser was offered and not chosen: D-07 asks for whitespace
  tolerance, not address validation, and a stricter parser would silently drop a valid but
  unusual address (a plus-addressed mailbox, an unusual TLD) that a human deliberately typed.
"""


def parse_address_list(raw):
    """Split ``raw`` on commas, strip each segment, drop empty segments, then de-duplicate
    case-insensitively keeping the FIRST occurrence's original spelling. Order is the input's
    order -- that is the specified, stable answer to "what happens when two entries compare
    equal" (a later, differently-cased repeat must not silently reorder or replace the first).

    Accepts ``None`` (the secret is unset) or a string; ``""``, an all-whitespace string, and a
    string containing only commas all normalise to ``[]``, since none of those name a single
    address.
    """
    if raw is None:
        return []
    seen = set()
    result = []
    for segment in str(raw).split(","):
        address = segment.strip()
        if not address:
            continue
        key = address.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(address)
    return result


def split_recipients(to_raw, cc_raw):
    """Parse both raw strings with ``parse_address_list``, then remove from the CC list every
    address whose case-folded form already appears in the TO list, preserving the remaining CC
    order. An address in both lists would otherwise be delivered twice on one message (T-04-14).

    Returns ``(to_list, cc_list)``. An empty ``to_raw`` does not empty the CC list -- the two
    lists are independent except for this one-directional de-duplication.
    """
    to_list = parse_address_list(to_raw)
    cc_list = parse_address_list(cc_raw)
    to_keys = {address.lower() for address in to_list}
    deduped_cc = [address for address in cc_list if address.lower() not in to_keys]
    return to_list, deduped_cc


def recipients_disabled_reason(to_list):
    """Returns ``None`` when ``to_list`` is non-empty. Returns a single sentence naming the
    ``SMTP_TO`` secret when it is empty -- this is the string the officer sees next to the
    disabled Send button, so it must name the variable: "Send is unavailable" with no cause is
    exactly the silent failure D-07 exists to prevent (T-04-13).
    """
    if to_list:
        return None
    return (
        "Send is disabled because the SMTP_TO secret is not set. Configure SMTP_TO in the "
        "Space's secrets to enable sending."
    )
