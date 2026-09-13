"""Standing tests that the resolved Python environment matches the pins declared in
``requirements.txt``.

These tests exist so that a drift between the *declared* dependency constraints and the
*actually installed* environment is caught by the test suite instead of surfacing later as an
unexplained QC-engine discrepancy (ENGINE-07). ``requirements.txt`` is resolved relative to
this file's own parent directory (the repository root) rather than the process working
directory, so the suite passes regardless of where ``pytest`` is invoked from.
"""

from pathlib import Path

import huggingface_hub
import numpy
import pandas

REQUIREMENTS_PATH = Path(__file__).resolve().parent.parent / "requirements.txt"


def _read_requirement_lines():
    """Return the non-empty, non-comment lines of requirements.txt as a list of strings."""
    text = REQUIREMENTS_PATH.read_text()
    lines = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        lines.append(line)
    return lines


def test_pandas_is_pinned_to_an_exact_version():
    """The pandas line in requirements.txt must be exactly ``pandas==3.0.5``.

    Asserting the literal line (rather than "starts with pandas") is what makes the boundary
    real: ``pandas==3.0.4`` and ``pandas==3.0.6`` both fail this assertion, just as a bare
    ``pandas>=2.0.0`` would.
    """
    lines = _read_requirement_lines()
    pandas_lines = [line for line in lines if line.split("=")[0].split(">")[0].split("<")[0] == "pandas"]
    assert pandas_lines, "requirements.txt does not declare a pandas dependency at all"
    assert len(pandas_lines) == 1, f"expected exactly one pandas line, found: {pandas_lines}"
    assert pandas_lines[0] == "pandas==3.0.5", (
        f"pandas line must be exactly 'pandas==3.0.5', found {pandas_lines[0]!r} instead"
    )


def test_pandas_installed_version_matches_the_pin():
    """The pandas actually importable in this interpreter must equal the declared pin.

    Deliberately a string ``==`` comparison, not a parsed-version or lexicographic comparison —
    a future ``3.0.10`` release must not be able to satisfy a ``3.0.5`` assertion by ordering
    accident.
    """
    assert pandas.__version__ == "3.0.5", (
        f"installed pandas is {pandas.__version__!r}, but requirements.txt pins '3.0.5'"
    )


def test_numpy_is_declared_with_both_bounds():
    """requirements.txt must declare numpy with both a lower and an upper bound, and numpy
    must actually be importable in this environment."""
    lines = _read_requirement_lines()
    numpy_lines = [line for line in lines if line.split(">")[0].split("<")[0].split("=")[0] == "numpy"]
    assert numpy_lines, "requirements.txt does not declare a numpy dependency at all"
    assert len(numpy_lines) == 1, f"expected exactly one numpy line, found: {numpy_lines}"
    numpy_line = numpy_lines[0]
    assert ">=2.0.0" in numpy_line, f"numpy line {numpy_line!r} is missing the '>=2.0.0' lower bound"
    assert "<3.0.0" in numpy_line, f"numpy line {numpy_line!r} is missing the '<3.0.0' upper bound"

    # numpy must actually be importable — a declared-but-uninstalled dependency is not caught
    # by the string checks above.
    assert numpy.__version__, "numpy did not report a __version__ after import"


def test_streamlit_floor_supports_the_login_api():
    """The streamlit line must declare both a >=1.42.0 lower bound (where st.login/st.user were
    introduced, AUTH-01/D-01) and the existing <2.0.0 upper bound -- a bare version-ordering
    comparison could be fooled by string sort order, so this asserts the exact substrings."""
    lines = _read_requirement_lines()
    streamlit_lines = [
        line for line in lines
        if line.split(">")[0].split("<")[0].split("=")[0].split("[")[0] == "streamlit"
    ]
    assert streamlit_lines, "requirements.txt does not declare a streamlit dependency at all"
    assert len(streamlit_lines) == 1, f"expected exactly one streamlit line, found: {streamlit_lines}"
    streamlit_line = streamlit_lines[0]
    assert ">=1.42.0" in streamlit_line, (
        f"streamlit line {streamlit_line!r} is missing the '>=1.42.0' lower bound st.login/st.user need"
    )
    assert "<2.0.0" in streamlit_line, f"streamlit line {streamlit_line!r} is missing the '<2.0.0' upper bound"


def test_authlib_is_declared_with_both_bounds():
    """Authlib is the OIDC client streamlit[auth] pulls in for st.login (AUTH-01/D-01) and must
    carry both bounds, matching test_every_runtime_dependency_is_bounded's requirement that no
    dependency line may drift into an untested major version silently."""
    lines = _read_requirement_lines()
    authlib_lines = [line for line in lines if line.split(">")[0].split("<")[0].split("=")[0] == "Authlib"]
    assert authlib_lines, "requirements.txt does not declare an Authlib dependency at all"
    assert len(authlib_lines) == 1, f"expected exactly one Authlib line, found: {authlib_lines}"
    authlib_line = authlib_lines[0]
    assert ">=1.3.2" in authlib_line, f"Authlib line {authlib_line!r} is missing the '>=1.3.2' lower bound"
    assert "<2.0.0" in authlib_line, f"Authlib line {authlib_line!r} is missing the '<2.0.0' upper bound"


def test_huggingface_hub_is_declared_with_both_bounds():
    """huggingface_hub writes the submission log to a private HF Dataset repo (AUDIT-02/D-05)
    and must carry both bounds, matching test_every_runtime_dependency_is_bounded's requirement
    that no dependency line may drift into an untested major version silently."""
    lines = _read_requirement_lines()
    hf_lines = [line for line in lines if line.split(">")[0].split("<")[0].split("=")[0] == "huggingface_hub"]
    assert hf_lines, "requirements.txt does not declare a huggingface_hub dependency at all"
    assert len(hf_lines) == 1, f"expected exactly one huggingface_hub line, found: {hf_lines}"
    hf_line = hf_lines[0]
    assert ">=1.30.0" in hf_line, f"huggingface_hub line {hf_line!r} is missing the '>=1.30.0' lower bound"
    assert "<2.0.0" in hf_line, f"huggingface_hub line {hf_line!r} is missing the '<2.0.0' upper bound"


def test_huggingface_hub_installed_version_satisfies_the_pin():
    """The huggingface_hub actually importable in this interpreter must fall inside the
    declared >=1.30.0,<2.0.0 range -- a declared-but-uninstalled or drifted-major dependency is
    not caught by the string checks above."""
    version = huggingface_hub.__version__
    parts = version.split(".")
    major, minor = int(parts[0]), int(parts[1])
    assert (major, minor) >= (1, 30), f"installed huggingface_hub {version!r} is older than 1.30.0"
    assert major < 2, f"installed huggingface_hub {version!r} does not satisfy the <2.0.0 upper bound"


def test_every_runtime_dependency_is_bounded():
    """Every non-comment, non-empty line of requirements.txt must declare either an exact pin
    (``==``) or an explicit upper bound (``<``) — no dependency may drift into a new major
    version silently.

    A minimum-count assertion guards against a vacuous pass: a loop over an empty (or
    mis-parsed) list of dependency lines would otherwise satisfy this test having examined
    nothing, which reports confidence that was never earned.
    """
    lines = _read_requirement_lines()
    assert len(lines) >= 5, (
        f"expected requirements.txt to declare at least 5 dependency lines, found {len(lines)}: {lines}"
    )

    unbounded = [line for line in lines if "==" not in line and "<" not in line]
    assert not unbounded, (
        "the following requirements.txt line(s) declare no exact pin and no upper bound, "
        f"so they can drift into an untested major version silently: {unbounded}"
    )
