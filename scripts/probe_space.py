#!/usr/bin/env python3
"""Reachability and unauthenticated-leak probe for the deployed MLoS Checkout QC Space.

Standard-library only (``urllib.request``, ``urllib.parse``, ``argparse``, ``sys``). This is an
operator tool run by hand against a deployed Hugging Face Space host -- it is not part of the
shipped app and is deliberately absent from ``requirements.txt``.

What this probe CAN establish, against the direct ``*.hf.space`` host, with no browser and no
platform credentials:

- The direct host answers over HTTPS at all (reachability).
- A request carrying no platform credentials is not redirected to a platform sign-in page --
  the observable form of D-09's public-visibility choice. This is checked by comparing the
  final URL's host, after following redirects, against the requested host.
- The Streamlit health endpoint (``HEALTH_PATH``) reports healthy, proving the app process
  actually started rather than the Space merely existing in a build-failed or crashed state.
- The unauthenticated root response body contains none of ``GATED_CONTENT_MARKERS`` -- strings
  drawn verbatim from gated regions of ``app.py`` (the sidebar uploader label, the QC rules
  reference heading, the auto-correct rules expander label, the MLoS required-columns heading,
  and the boundary reference CSV filename).

What this probe CANNOT establish: that the sign-in screen is what actually renders in a
browser. Streamlit ships a JavaScript shell and paints the real page over a websocket
connection after the initial HTML loads, so the initial HTML this probe reads is not what a
human eventually sees. The absence of gated markers from that initial HTML is therefore a leak
check that can only fail meaningfully -- finding a marker proves a real leak -- it is not proof
that the login gate rendered correctly. That proof is plan 04-01's structural
statement-ordering test plus the human checklist run in Task 3. A green run of this script is
not an AUTH-01 pass; it is a narrower, still-useful reachability and leak check.
"""

import argparse
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import namedtuple

# Streamlit's own health endpoint. See Flagged Assumptions in the plan: this path is assumed
# stable across the Streamlit versions this project pins; if the health check fails while the
# root request succeeds, confirm the path against the installed Streamlit version before
# treating it as a deployment fault.
HEALTH_PATH = "/_stcore/health"

# Five strings drawn verbatim from gated regions of app.py. Each occurs exactly once in app.py
# today (proven by tests/test_space_probe_logic.py's non-vacuity check), which is what makes a
# hit here mean something: the MLoS required-columns heading, the boundary reference CSV
# filename, the auto-correct rules expander label, the MLoS file uploader label, and the QC
# rules reference heading.
GATED_CONTENT_MARKERS = (
    "**MLoS required columns:**",
    "ward_boundary_ref.csv",
    "🔧 Auto Correct Rules",
    "Upload MLoS file",
    "📋 QC Rules Reference",
)

# A small result carrying a boolean verdict and a named reason, so every failure prints a cause
# rather than a bare exit code. Comparable to a plain 2-tuple for convenience in tests.
ClassificationResult = namedtuple("ClassificationResult", ["ok", "reason"])


def find_gated_markers(text):
    """Return every marker in GATED_CONTENT_MARKERS present in ``text``, or ``[]`` if none are."""
    return [marker for marker in GATED_CONTENT_MARKERS if marker in text]


def classify_response(status, final_url, body, host):
    """Classify one HTTP response against the expected host.

    Returns an ``ok`` ClassificationResult only when ``status`` is 200, the final URL's host
    (after redirects) equals ``host``, and ``body`` is non-empty. Each failure mode gets its own
    named reason: a non-200 status, a final URL on a different host (the platform-bounce
    failure this whole probe exists to catch), and an empty body.
    """
    if status != 200:
        return ClassificationResult(False, f"non_200_status:{status}")

    final_host = urllib.parse.urlparse(final_url).hostname or ""
    if final_host != host:
        return ClassificationResult(
            False, f"host_mismatch:expected={host}:got={final_host or '(none)'}"
        )

    if not body or not body.strip():
        return ClassificationResult(False, "empty_body")

    return ClassificationResult(True, "ok")


def _fetch(url):
    """Perform a GET request, following redirects, and return (status, final_url, body_text).

    An HTTP error response (4xx/5xx) is captured and returned rather than raised, since a
    non-200 status is a classification outcome this probe is designed to report, not a network
    failure. A ``urllib.error.URLError`` that is not an ``HTTPError`` (DNS failure, connection
    refused, TLS failure) is not caught here and propagates to the caller.
    """
    req = urllib.request.Request(url, headers={"User-Agent": "mlos-space-probe/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            status = resp.status
            final_url = resp.geturl()
            raw = resp.read()
    except urllib.error.HTTPError as exc:
        status = exc.code
        final_url = exc.geturl() if hasattr(exc, "geturl") else url
        raw = exc.read() if hasattr(exc, "read") else b""
    body = raw.decode("utf-8", errors="replace") if raw else ""
    return status, final_url, body


def main(argv=None):
    """Probe a deployed Space host. Returns a process exit code (0 = every check passed)."""
    argv = sys.argv[1:] if argv is None else argv

    parser = argparse.ArgumentParser(
        prog="probe_space.py",
        description=(
            "Probe a deployed MLoS Checkout QC Hugging Face Space for reachability, "
            "no-platform-bounce, app health, and unauthenticated content leakage."
        ),
    )
    parser.add_argument(
        "url",
        nargs="?",
        default=None,
        help="Direct *.hf.space host or URL. Falls back to the MLOS_SPACE_URL env var.",
    )
    args = parser.parse_args(argv)

    url = args.url or os.environ.get("MLOS_SPACE_URL")
    if not url:
        print(
            "usage: probe_space.py <space-url>\n"
            "No target URL was given and MLOS_SPACE_URL is not set in the environment.\n"
            "Pass the direct *.hf.space host as an argument, or export MLOS_SPACE_URL.",
            file=sys.stderr,
        )
        return 2

    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url

    host = urllib.parse.urlparse(url).hostname or ""
    checks_failed = 0

    try:
        status, final_url, body = _fetch(url)
    except urllib.error.URLError as exc:
        print(f"FAIL root_reachable: could not reach {url}: {exc}")
        return 1

    root_result = classify_response(status, final_url, body, host)
    if root_result.ok:
        print(f"OK root_reachable: {url} -> {final_url} (status {status}, no platform bounce)")
    else:
        print(f"FAIL root_reachable: {root_result.reason}")
        checks_failed += 1

    leaked_markers = find_gated_markers(body)
    if not leaked_markers:
        print("OK no_gated_content: unauthenticated response carries none of the gated-content markers")
    else:
        print(f"FAIL no_gated_content: markers leaked in unauthenticated response: {leaked_markers}")
        checks_failed += 1

    health_url = url.rstrip("/") + HEALTH_PATH
    try:
        h_status, h_final_url, h_body = _fetch(health_url)
        health_result = classify_response(h_status, h_final_url, h_body, host)
        if health_result.ok:
            print(f"OK health_endpoint: {health_url} reports healthy (status {h_status})")
        else:
            print(f"FAIL health_endpoint: {health_result.reason}")
            checks_failed += 1
    except urllib.error.URLError as exc:
        print(f"FAIL health_endpoint: could not reach {health_url}: {exc}")
        checks_failed += 1

    if checks_failed:
        print(f"\n{checks_failed} check(s) failed.")
        return 1

    print("\nAll checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
