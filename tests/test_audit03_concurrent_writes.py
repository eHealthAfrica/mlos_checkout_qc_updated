"""AUDIT-03's launch-gate proof, new for D-08: many concurrent writers against a disposable
private Dataset repo, each minting its path through the shipped
``qc.submission_record.mint_record_id_and_path``, proving every write lands and the count is
exact. Skips cleanly, with a reason naming both required environment variables, whenever a live
Hub credential is absent -- so the suite stays green on a developer laptop and in CI, and the one
live-capable test in this file is the evidence AUDIT-03's M2 launch gate is recorded against.

No test in this file makes a network call by default. Only ``test_twenty_concurrent_uploads_...``
touches the real Hub, and only when both ``MLOS_TEST_HF_TOKEN`` and ``MLOS_TEST_HF_NAMESPACE`` are
set in the environment -- run once, live, at this plan's `checkpoint:human-action` (Task 3).

This file is one of the two paths ``tests/test_no_delete_in_submission_log.py`` excludes from its
standing append-only guard: the lifecycle below is this test's own disposable repo, created and
removed by the test itself, never a path the shipped application can reach.
"""

import concurrent.futures
import json
import os
import uuid

import pytest

import submission_log
from qc.submission_record import mint_record_id_and_path

# Separate from the production MLOS_LOG_TOKEN/MLOS_LOG_REPO pair (submission_log.LOG_TOKEN_VAR /
# submission_log.LOG_REPO_VAR, D-15): the production token is fine-grained and scoped to write on
# one already-existing Dataset repo. Creating a brand-new disposable repo for this test's own
# lifecycle is an account-or-organisation-level permission a per-repo scope cannot express.
# Reusing the production token here would mean widening it just to make a test pass -- the
# opposite of what D-15 chose (05-RESEARCH.md Common Pitfalls, pitfall 3).
TEST_TOKEN_VAR = "MLOS_TEST_HF_TOKEN"
TEST_NAMESPACE_VAR = "MLOS_TEST_HF_NAMESPACE"

CONCURRENT_WRITERS = 20

_MISSING_LIVE_VARS = [v for v in (TEST_TOKEN_VAR, TEST_NAMESPACE_VAR) if not os.environ.get(v)]
_LIVE_SKIP_REASON = (
    f"{TEST_TOKEN_VAR} and/or {TEST_NAMESPACE_VAR} not set -- AUDIT-03's live concurrency proof "
    "needs a Hub token permitted to create and delete repos, plus the namespace to create them "
    "under (Task 2 of 05-04-PLAN.md mints both)."
)

# A skip condition scoped to only the live test below -- deliberately NOT stored under the
# module attribute literally named ``pytestmark``, which pytest auto-applies to every test
# collected from this file regardless of how it is otherwise referenced. Doing that would skip
# the always-on constant-comparison test too, and a file that is entirely skipped everywhere is a
# file nobody would notice had rotted.
_requires_live_hub_credentials = pytest.mark.skipif(
    bool(_MISSING_LIVE_VARS), reason=_LIVE_SKIP_REASON
)


def test_test_credentials_are_distinct_from_production_credentials():
    """Runs unconditionally -- with no live credentials configured, this is the assertion that
    keeps this file from being a no-op nobody would notice had rotted. Without it, a future edit
    could quietly repoint the test-token variable at the production secret name and nothing would
    catch it until the widened-scope credential actually reused the production one (D-15,
    05-RESEARCH.md pitfall 3)."""
    assert TEST_TOKEN_VAR == "MLOS_TEST_HF_TOKEN"
    assert TEST_NAMESPACE_VAR == "MLOS_TEST_HF_NAMESPACE"
    assert TEST_TOKEN_VAR != submission_log.LOG_TOKEN_VAR
    assert TEST_NAMESPACE_VAR != submission_log.LOG_REPO_VAR


def test_concurrent_writers_is_at_least_twenty():
    """AUDIT-03 requires 'many concurrent writers' -- without a floor on this constant, a future
    edit could quietly shrink it to 2 and still claim to prove concurrency."""
    assert CONCURRENT_WRITERS >= 20


@_requires_live_hub_credentials
def test_twenty_concurrent_uploads_all_land_at_distinct_paths_with_none_missing():
    """The core AUDIT-03 proof. A test that only asserted 'no exception was raised' would pass
    while half the records were silently lost -- exactly the subtle failure ROADMAP's launch-gate
    note warns about. This asserts two separate things: every minted path was actually written
    (catches a lost write), and the landed count is exactly ``CONCURRENT_WRITERS`` (catches a
    surprise -- a merge, a duplicate, or an extra file neither of the first two checks would
    catch alone).
    """
    from huggingface_hub import HfApi

    token = os.environ[TEST_TOKEN_VAR]
    namespace = os.environ[TEST_NAMESPACE_VAR]
    api = HfApi(token=token)
    repo_id = f"{namespace}/mlos-audit03-{uuid.uuid4().hex[:8]}"
    api.create_repo(repo_id=repo_id, repo_type="dataset", private=True)
    try:
        # Mint through the shipped production function -- not a test-local path generator -- so
        # this proves the shape records actually land at, not a convenient approximation of it.
        minted = [mint_record_id_and_path() for _ in range(CONCURRENT_WRITERS)]
        paths = [path for (_record_id, path, _ts) in minted]

        # Assert distinctness *before* any upload begins, so a minting collision and a Hub-side
        # loss produce two distinguishable failures rather than one ambiguous one.
        assert len(set(paths)) == CONCURRENT_WRITERS, "minting collision before any upload began"

        def upload_one(index, path):
            payload = json.dumps({"marker": "audit03-synthetic", "index": index}).encode("utf-8")
            # Same keyword set submission_log.py's upload call uses, and -- as there -- no
            # optimistic-concurrency keyword: every path here has never existed before, so there
            # is nothing for that keyword to guard against, and supplying a stale value would
            # only manufacture a false rejection between two unrelated concurrent writers.
            api.upload_file(
                path_or_fileobj=payload,
                path_in_repo=path,
                repo_id=repo_id,
                repo_type="dataset",
                commit_message=f"audit03 concurrency proof writer {index}",
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENT_WRITERS) as pool:
            futures = {
                pool.submit(upload_one, index, path): (index, path)
                for index, path in enumerate(paths)
            }
            failures = []
            for future in concurrent.futures.as_completed(futures):
                exc = future.exception()
                if exc is not None:
                    index, path = futures[future]
                    failures.append(f"writer {index} ({path}) raised {type(exc).__name__}: {exc}")
            assert not failures, "\n".join(failures)

        landed = set(api.list_repo_files(repo_id=repo_id, repo_type="dataset"))
        missing = [p for p in paths if p not in landed]
        assert not missing, f"missing paths (lost writes): {missing}"

        records_paths = [p for p in landed if p.startswith("records/")]
        assert len(records_paths) == CONCURRENT_WRITERS, (
            f"expected exactly {CONCURRENT_WRITERS} paths under records/, found "
            f"{len(records_paths)}: {sorted(records_paths)}"
        )
    finally:
        # Removes only the repo id this test itself built and created above -- this test's own
        # disposable-repo lifecycle, not an application delete path (D-16's exclusion for this
        # file in tests/test_no_delete_in_submission_log.py).
        api.delete_repo(repo_id=repo_id, repo_type="dataset")
