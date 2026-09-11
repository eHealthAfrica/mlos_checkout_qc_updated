"""Standing assertions on the Hugging Face Space front-matter block at the top of README.md,
new for DEPLOY-01.

The Space supervisor reads a `---`-delimited YAML block at the very start of README.md to
decide the SDK, the Python floor and the entry point it launches. This file proves the block
is genuinely there (byte offset 0, not merely present somewhere in the document) and that it
declares the right values -- but its more important job is the two *absent*-key assertions:

- ``sdk_version`` must NEVER appear here. Declaring it would give the Streamlit version two
  independent sources of truth (this file and requirements.txt's bounded pin) -- exactly the
  defect class this project's own 2026-09-09 audit found and Phase 1 closed (ENGINE-07). A
  reader who does not know that history could reasonably "improve" this file by adding
  ``sdk_version`` back in; this test exists so that improvement fails loudly instead of
  silently reintroducing a two-sources-of-truth bug.
- ``hf_oauth`` must NEVER appear here. Native Hugging Face OAuth was the researcher's own
  recommendation (04-RESEARCH.md) and was explicitly declined in favour of the officers' work
  Google identity (D-01). Setting this key would sign officers in with Hugging Face accounts
  instead, silently reversing a locked decision.

``parse_front_matter()`` is a small top-level ``key: value`` line reader, not a YAML parser --
the front-matter block is flat by construction (no nesting, no lists), so a real YAML
dependency would be a new runtime dependency for eight lines of metadata, which is not
warranted (per this task's own instruction).
"""

from pathlib import Path

FRONT_MATTER_PATH = Path(__file__).resolve().parent.parent / "README.md"


def parse_front_matter():
    """Parse the leading ``---``-delimited block at the very top of README.md into a flat dict
    of ``key -> value`` strings.

    Deliberately not a YAML parser: values are returned as plain strings (``"false"`` stays the
    three-letter string, never Python's ``False``), since every assertion this suite makes is a
    string comparison and a booleanized value would just have to be re-stringified to compare.
    Returns an empty dict (not an exception) if the file does not open with the delimiter --
    the byte-offset test below is what turns that into a loud, specific failure instead of a
    quiet ``KeyError`` deep inside some other test.
    """
    text = FRONT_MATTER_PATH.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    result = {}
    for line in lines[1:]:
        stripped = line.strip()
        if stripped == "---":
            break
        if not stripped or ":" not in stripped:
            continue
        key, _, value = stripped.partition(":")
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        result[key] = value
    return result


def test_readme_opens_with_the_front_matter_delimiter_at_byte_zero():
    """A front-matter block anywhere else in the file is invisible to the Space supervisor --
    it only reads a block that starts at the literal first three bytes."""
    raw = FRONT_MATTER_PATH.read_bytes()
    assert raw[:3] == b"---", (
        "README.md must open with the '---' front-matter delimiter as its first three bytes, "
        f"found {raw[:3]!r} instead"
    )


def test_sdk_is_the_native_streamlit_sdk():
    """Must be exactly 'streamlit', not 'docker' -- the Docker SDK does not receive the
    XSRF/cookie workaround st.file_uploader needs inside the platform's iframe
    (.planning/research/STACK.md line 71)."""
    fm = parse_front_matter()
    assert fm.get("sdk") == "streamlit", (
        f"front matter 'sdk' must be exactly 'streamlit', found {fm.get('sdk')!r}"
    )


def test_python_version_is_the_311_floor_as_a_string():
    """Must be the string '3.11', not the YAML float 3.11 -- pandas==3.0.5 declares
    requires-python >=3.11, and a numeric front-matter value risks the platform's own YAML
    parser silently normalising it (e.g. dropping a trailing zero) in a way a quoted string
    cannot."""
    fm = parse_front_matter()
    assert fm.get("python_version") == "3.11", (
        f"front matter 'python_version' must be exactly '3.11', found {fm.get('python_version')!r}"
    )


def test_app_file_points_at_the_real_entry_point():
    fm = parse_front_matter()
    assert fm.get("app_file") == "app.py", (
        f"front matter 'app_file' must be exactly 'app.py', found {fm.get('app_file')!r}"
    )


def test_pinned_is_false():
    fm = parse_front_matter()
    assert fm.get("pinned") == "false", (
        f"front matter 'pinned' must be exactly 'false', found {fm.get('pinned')!r}"
    )


def test_title_and_short_description_are_present():
    """A blank title or description would still satisfy 'the key exists' -- assert non-empty
    content, not just key presence."""
    fm = parse_front_matter()
    assert fm.get("title"), "front matter 'title' must be non-empty"
    assert fm.get("short_description"), "front matter 'short_description' must be non-empty"


def test_sdk_version_is_not_declared():
    """Absence is the point: declaring sdk_version would let the platform install a Streamlit
    version chosen here while requirements.txt declares a bounded range -- one dependency, two
    sources of truth, the exact defect class Phase 1's audit closed (ENGINE-07). A future
    contributor who does not know this history could reasonably add this key back as an
    apparent improvement; this test is what makes that regression fail loudly."""
    fm = parse_front_matter()
    assert "sdk_version" not in fm, (
        f"'sdk_version' must not appear in the front matter (requirements.txt is the single "
        f"source of truth for the Streamlit version); found keys: {sorted(fm)}"
    )


def test_hf_oauth_is_not_declared():
    """Absence is the point: hf_oauth was the researcher's own recommendation and was
    explicitly declined (D-01) -- officers sign in with their work Google identity via
    st.login, not a Hugging Face account. Setting this key would silently reverse that locked
    decision."""
    fm = parse_front_matter()
    assert "hf_oauth" not in fm, (
        f"'hf_oauth' must not appear in the front matter (native HF OAuth was declined per "
        f"D-01); found keys: {sorted(fm)}"
    )


def test_parser_found_a_nonzero_number_of_keys():
    """A guard that greens because the parser resolved an empty or mis-delimited block reports
    confidence it never earned -- assert a real minimum count of parsed keys."""
    fm = parse_front_matter()
    assert len(fm) >= 6, f"expected at least 6 front-matter keys, parsed {len(fm)}: {sorted(fm)}"
