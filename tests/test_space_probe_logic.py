"""Network-free unit tests for scripts/probe_space.py.

Covers the classifier logic (``classify_response``), the marker finder (``find_gated_markers``),
the usage-guard exit behaviour of ``main`` when no target URL is available, and a non-vacuity
check that every string in ``GATED_CONTENT_MARKERS`` is a real substring of ``app.py`` -- the
guard-of-the-guard idiom from ``tests/test_no_streamlit_in_qc.py``, applied here so the leak
check can never silently go vacuous if a future phase rewords the gated sidebar content. No test
in this file performs any network access: every case feeds synthetic strings or synthetic
status/URL/body tuples directly to the probe's pure functions.
"""

import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
APP_PY_PATH = Path(__file__).resolve().parent.parent / "app.py"

sys.path.insert(0, str(SCRIPTS_DIR))
import probe_space as p  # noqa: E402

SYNTHETIC_GATED_HTML = "<html><body>\n" + "\n".join(p.GATED_CONTENT_MARKERS) + "\n</body></html>"

SYNTHETIC_STREAMLIT_SHELL = (
    "<html><head><title>Streamlit</title></head>"
    '<body><div id="root"></div><script src="/static/js/main.js"></script></body></html>'
)


def test_find_gated_markers_returns_all_markers_present():
    found = p.find_gated_markers(SYNTHETIC_GATED_HTML)
    assert sorted(found) == sorted(p.GATED_CONTENT_MARKERS)


def test_find_gated_markers_returns_empty_for_clean_streamlit_shell():
    assert p.find_gated_markers(SYNTHETIC_STREAMLIT_SHELL) == []


def test_classify_response_ok_for_200_on_matching_host_with_body():
    result = p.classify_response(200, "https://myspace.hf.space/", "some body", "myspace.hf.space")
    assert result.ok is True
    assert result.reason == "ok"


def test_classify_response_fails_on_non_200_status():
    result = p.classify_response(503, "https://myspace.hf.space/", "some body", "myspace.hf.space")
    assert result.ok is False
    assert "non_200_status" in result.reason


def test_classify_response_fails_on_final_url_host_mismatch():
    # The platform-bounce failure this probe exists to catch: the request landed somewhere
    # other than the requested Space host (e.g. a huggingface.co sign-in redirect).
    result = p.classify_response(200, "https://huggingface.co/login", "some body", "myspace.hf.space")
    assert result.ok is False
    assert "host_mismatch" in result.reason


def test_classify_response_fails_on_empty_body():
    result = p.classify_response(200, "https://myspace.hf.space/", "", "myspace.hf.space")
    assert result.ok is False
    assert "empty_body" in result.reason


def test_classify_response_also_fails_on_whitespace_only_body():
    result = p.classify_response(200, "https://myspace.hf.space/", "   \n\t  ", "myspace.hf.space")
    assert result.ok is False
    assert "empty_body" in result.reason


def test_classify_response_failure_reasons_are_distinct_across_modes():
    non_200 = p.classify_response(500, "https://myspace.hf.space/", "body", "myspace.hf.space")
    mismatch = p.classify_response(200, "https://evil.example/", "body", "myspace.hf.space")
    empty = p.classify_response(200, "https://myspace.hf.space/", "", "myspace.hf.space")
    reasons = {non_200.reason, mismatch.reason, empty.reason}
    assert len(reasons) == 3


def test_main_exits_nonzero_with_no_url_argument_and_no_env_var(monkeypatch):
    monkeypatch.delenv("MLOS_SPACE_URL", raising=False)
    exit_code = p.main([])
    assert exit_code != 0


def test_main_usage_message_names_the_environment_variable(monkeypatch, capsys):
    monkeypatch.delenv("MLOS_SPACE_URL", raising=False)
    p.main([])
    captured = capsys.readouterr()
    assert "MLOS_SPACE_URL" in captured.err


def test_every_gated_marker_is_a_real_substring_of_app_py():
    """Guard-of-the-guard: if a marker were not really present in app.py, the leak check it
    powers could never fire against a real leak, which is worse than having no check at all."""
    src = APP_PY_PATH.read_text(encoding="utf-8", errors="replace")
    missing = [marker for marker in p.GATED_CONTENT_MARKERS if marker not in src]
    assert not missing, f"markers absent from app.py: {missing}"


def test_gated_content_markers_has_at_least_five_entries():
    assert len(p.GATED_CONTENT_MARKERS) >= 5
