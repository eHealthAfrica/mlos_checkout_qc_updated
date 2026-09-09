"""Pytest fixtures wrapping the plain builder functions in tests/fixtures.py.

Each fixture is a thin wrapper — the actual data construction lives in fixtures.py so that
tests/baseline/capture_baseline.py can import the same builders without depending on pytest.
"""

import pytest

from fixtures import build_mlos_fixture, build_takeoff_fixture, load_boundary_fixtures


@pytest.fixture
def mlos_df():
    """Function-scoped: a test that mutates this DataFrame must not leak state into the next."""
    return build_mlos_fixture()


@pytest.fixture
def takeoff_df():
    """Function-scoped: same isolation rationale as mlos_df."""
    return build_takeoff_fixture()


@pytest.fixture(scope="session")
def boundary_refs():
    """Session-scoped: reads 9,410 rows from disk, safe to share read-only across tests."""
    return load_boundary_fixtures()
