"""H1/H2: authoritative lossless node-identity outcomes for behavioral comparison."""

import sys

from app.services.verification_execution import (
    NODE_RESULTS_SOURCE_LIFECYCLE,
    NODE_RESULTS_SOURCE_NONE,
    NODE_RESULTS_SOURCE_TEXT_SUMMARY,
    OUTCOME_SOURCE_EXECUTION_BOUNDARY,
    TARGET_STATUS_EXECUTION_TIMEOUT,
    _authoritative_node_results,
    _parse_node_events,
    behavioral_bundle_from_command_result,
    compare_behavioral_results,
    parse_pytest_node_results,
)


P1 = "tests/test_x.py::test_fn[a - x]"
P2 = "tests/test_x.py::test_fn[a - y]"


def _events(results, *, started=None, finished=None):
    started = list(started if started is not None else results.keys())
    finished = list(finished if finished is not None else results.keys())
    return {
        "source": "PYTEST_NODE_LIFECYCLE_EVENTS",
        "started": started,
        "finished": sorted(finished),
        "results": dict(results),
        "active": [n for n in started if n not in finished],
    }


def _cmd(*, node_events=None, node_results=None, status="PASSED", exit_code=0, reason=None):
    return {
        "check": "pytest",
        "command": [sys.executable, "-m", "pytest"],
        "revision": "r",
        "working_directory": "/repo",
        "discovered": True,
        "executed": True,
        "status": status,
        "exit_code": exit_code,
        "duration_ms": 1,
        "stdout": "",
        "stderr": "",
        "discovered_test_count": None,
        "executed_test_count": None,
        "reason": reason,
        "node_results": dict(node_results or {}),
        "node_events": node_events,
    }


def _bundle(**kw):
    return behavioral_bundle_from_command_result(_cmd(**kw), revision="r")


def _compare(base, target, files=("tests/test_x.py",)):
    return compare_behavioral_results(
        base,
        target,
        test_files=list(files),
        changed_files=["x/mod.py"],
        changed_symbols=["x/mod.py::fn"],
        selection_provenance="deterministic_changed_test_files",
    )


# --- The H1 defect the fix removes ----------------------------------------

def test_text_summary_collapses_dashed_param_ids():
    output = (
        "PASSED tests/test_x.py::test_fn[a - x]\n"
        "FAILED tests/test_x.py::test_fn[a - y] - AssertionError\n"
    )
    parsed = parse_pytest_node_results(output)
    assert len(parsed) == 1  # both truncate to the same key: the collision


def test_lifecycle_keeps_dashed_param_ids_distinct():
    events = _parse_node_events(
        f"START\t{P1}\nRESULT\t{P1}\tpassed\nFINISH\t{P1}\n"
        f"START\t{P2}\nRESULT\t{P2}\tfailed\nFINISH\t{P2}\n"
    )
    assert events["results"] == {P1: "passed", P2: "failed"}


def test_authoritative_prefers_lossless_lifecycle_results():
    results, source = _authoritative_node_results(
        _events({P1: "passed", P2: "failed"}),
        {"tests/test_x.py::test_fn[a": "failed"},  # truncated text (would collide)
    )
    assert source == NODE_RESULTS_SOURCE_LIFECYCLE
    assert results == {P1: "passed", P2: "failed"}


# --- Independent outcomes retained; no overwrite --------------------------

def test_two_previously_colliding_ids_retain_independent_outcomes():
    base = _bundle(node_events=_events({P1: "passed", P2: "passed"}))
    target = _bundle(node_events=_events({P1: "failed", P2: "passed"}), exit_code=1, status="FAILED")
    by_node = {c.test_node_id: c for c in _compare(base, target)}
    assert set(by_node) == {P1, P2}
    assert by_node[P1].comparison_status == "REGRESSION"
    assert by_node[P1].regression is True
    assert by_node[P2].comparison_status == "CONSISTENT"
    assert by_node[P2].regression is False


def test_failing_variant_not_overwritten_by_passing_variant():
    target = _bundle(node_events=_events({P1: "failed", P2: "passed"}), exit_code=1, status="FAILED")
    assert target["node_results"][P1] == "failed"
    assert target["node_results"][P2] == "passed"
    assert target["node_results_source"] == NODE_RESULTS_SOURCE_LIFECYCLE


def test_behavioral_comparison_uses_exact_node_ids():
    base = _bundle(node_events=_events({P1: "passed"}))
    target = _bundle(node_events=_events({P1: "failed"}), exit_code=1, status="FAILED")
    result = _compare(base, target)
    assert [c.test_node_id for c in result] == [P1]


# --- Outcome fidelity ------------------------------------------------------

def test_lifecycle_passed_remains_passed():
    base = _bundle(node_events=_events({P1: "passed"}))
    target = _bundle(node_events=_events({P1: "passed"}))
    assert base["node_results"][P1] == "passed"
    assert _compare(base, target)[0].comparison_status == "CONSISTENT"


def test_lifecycle_failed_remains_failed():
    base = _bundle(node_events=_events({P1: "passed"}))
    target = _bundle(node_events=_events({P1: "failed"}), exit_code=1, status="FAILED")
    assert target["node_results"][P1] == "failed"
    assert _compare(base, target)[0].comparison_status == "REGRESSION"


def test_error_outcome_retains_unknown_semantics():
    base = _bundle(node_events=_events({P1: "passed"}))
    target = _bundle(node_events=_events({P1: "error"}), exit_code=1, status="FAILED")
    assert target["node_results"][P1] == "error"
    assert _compare(base, target)[0].comparison_status == "UNKNOWN"


def test_skipped_result_events_are_dropped_like_before():
    events = _parse_node_events(
        f"START\t{P1}\nRESULT\t{P1}\tskipped\nFINISH\t{P1}\n"
    )
    assert P1 not in events["results"]
    base = _bundle(node_events=events, node_results={P1: "passed"})
    # No authoritative lifecycle result -> falls back to text, node stays known.
    assert base["node_results_source"] == NODE_RESULTS_SOURCE_TEXT_SUMMARY


# --- Never fabricate; conservative fallback --------------------------------

def test_missing_result_event_is_not_fabricated():
    events = _parse_node_events(f"START\t{P1}\n")  # started, never a RESULT
    assert events["results"] == {}
    results, source = _authoritative_node_results(events, None)
    assert results == {}
    assert source == NODE_RESULTS_SOURCE_NONE


def test_absent_tracker_falls_back_to_text_summary():
    results, source = _authoritative_node_results(None, {P1: "failed"})
    assert results == {P1: "failed"}
    assert source == NODE_RESULTS_SOURCE_TEXT_SUMMARY


def test_empty_lifecycle_results_falls_back_to_text_summary():
    results, source = _authoritative_node_results(_events({}), {P1: "passed"})
    assert results == {P1: "passed"}
    assert source == NODE_RESULTS_SOURCE_TEXT_SUMMARY


def test_malformed_tracker_falls_back_conservatively():
    for malformed in ({"results": "not-a-dict"}, {"results": None}, {}, "garbage", 42):
        results, source = _authoritative_node_results(malformed, {P1: "passed"})
        assert results == {P1: "passed"}
        assert source == NODE_RESULTS_SOURCE_TEXT_SUMMARY


def test_no_evidence_yields_none_source():
    results, source = _authoritative_node_results(None, None)
    assert results == {}
    assert source == NODE_RESULTS_SOURCE_NONE


# --- Timeout path unchanged: lifecycle-based, never fabricated FAILED ------

def test_timeout_uses_lifecycle_and_never_fabricates_failed():
    base = _bundle(node_events=_events({P1: "passed"}))
    target = behavioral_bundle_from_command_result(
        _cmd(
            node_events=_events({}, started=[P1], finished=[]),
            status="TIMEOUT",
            exit_code=None,
            reason="timeout after 5s",
        ),
        revision="r",
    )
    assert target["status"] == "TIMED_OUT"
    assert target["execution_outcome"]["source"] == OUTCOME_SOURCE_EXECUTION_BOUNDARY
    assert "failed" not in set(target["node_results"].values())

    result = _compare(base, target)
    assert len(result) == 1
    assert result[0].comparison_status == "REGRESSION"
    assert result[0].target_status == TARGET_STATUS_EXECUTION_TIMEOUT
    assert result[0].target_status != "failed"


def test_normal_completed_execution_marks_lifecycle_provenance():
    bundle = _bundle(node_events=_events({P1: "passed", P2: "failed"}), exit_code=1, status="FAILED")
    assert bundle["node_results_source"] == NODE_RESULTS_SOURCE_LIFECYCLE
    assert bundle["node_results"] == {P1: "passed", P2: "failed"}
