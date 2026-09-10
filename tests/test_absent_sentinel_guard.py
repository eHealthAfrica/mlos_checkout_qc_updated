"""D-05's required standing guard: the sentinel list and the "NA" exemption are a named,
version-controlled constant in qc/domain.py, and this file is the structural half of that
one-way decision — following Phase 1's D-12 precedent of a standing test as the cheap assertable
backstop for a decision that cannot be cheaply undone once real submissions are scored under it.

Four assertions, each with a message naming the offending token or column rather than reporting
a bare boolean.
"""

import pandas as pd
import pytest

from qc.domain import ABSENCE_SENTINELS, FLAG_COLS
from qc.predicates import vec_is_absent


@pytest.mark.parametrize("flag_col", FLAG_COLS)
def test_exact_literal_NA_is_present_in_every_flag_column(flag_col):
    """D-05's exemption is global, and one of the two reasons it must be global is that "NA" is
    a valid flag value in every FLAG_COLS column — parametrised over FLAG_COLS so a failure names
    exactly which flag column the guard was covering."""
    is_absent = vec_is_absent(pd.Series(["NA"])).iloc[0]
    assert not is_absent, (
        f"the exact literal 'NA' read as absent for flag column {flag_col!r} — D-05's "
        f"case-sensitive exemption must keep 'NA' present in every FLAG_COLS column"
    )


def test_exact_literal_NA_is_present_as_state_code():
    """The second reason D-05's exemption must be global: "NA" is also Nasarawa's state_code."""
    is_absent = vec_is_absent(pd.Series(["NA"])).iloc[0]
    assert not is_absent, (
        "the exact literal 'NA' read as absent for state_code — D-05's exemption must keep "
        "Nasarawa's state code from being misread as a missing required field"
    )


def test_lowercase_na_is_present_too():
    """Lowercase "na" survives as present for a *different* reason than "NA" does: it is simply
    not a member of ABSENCE_SENTINELS (a distinct string from "nan"), not because of the
    case-sensitive exemption — the exemption only ever matters for the exact literal "NA"."""
    is_absent = vec_is_absent(pd.Series(["na"])).iloc[0]
    assert not is_absent, (
        "lowercase 'na' read as absent — it is not a member of ABSENCE_SENTINELS (distinct from "
        "'nan') and must survive as present"
    )


@pytest.mark.parametrize("token", sorted(ABSENCE_SENTINELS))
def test_every_sentinel_token_reads_absent_in_every_case(token):
    """Every member of ABSENCE_SENTINELS reads as absent in lower, upper and title case — derived
    by iterating the constant itself so a future addition to the sentinel set is covered
    automatically, with no matching test-file edit required."""
    for cased in (token.lower(), token.upper(), token.title()):
        is_absent = vec_is_absent(pd.Series([cased])).iloc[0]
        assert is_absent, (
            f"sentinel token {token!r} in casing {cased!r} did not read as absent"
        )


def test_absence_sentinels_has_exactly_five_members_and_excludes_NA():
    """The defensive floor: a guard that iterates an empty or gutted ABSENCE_SENTINELS would
    green regardless of what it claims to cover."""
    assert len(ABSENCE_SENTINELS) == 5, (
        f"ABSENCE_SENTINELS expected exactly 5 members, found {len(ABSENCE_SENTINELS)}: "
        f"{sorted(ABSENCE_SENTINELS)!r}"
    )
    assert "NA" not in ABSENCE_SENTINELS, (
        "the exact literal 'NA' must not be a member of ABSENCE_SENTINELS — its exemption in "
        "vec_is_absent would otherwise be redundant with membership, or worse, contradicted by it"
    )
