"""Read-model observability for unresolved impact and verification evidence."""

from app.services.change_risk_view import change_risk_view


def test_module_level_unresolved_mapping_is_exposed_without_fake_symbol():
    view = change_risk_view({
        "repository": "pallets/flask",
        "base_revision": "base",
        "target_revision": "target",
        "risk_level": "medium",
        "recommendation": "review_recommended",
        "confidence": "low",
        "impact": {
            "changed_files": ["src/flask/views.py"],
            "changed_symbols": [],
            "unresolved_references": [{
                "file_path": "src/flask/views.py",
                "detail": "lines 12-12",
                "reason": "changed range does not fall inside any known symbol (likely module-level code)",
            }],
        },
        "decision": {"risk_level": "medium", "score": 45},
        "verification": {
            "state": "blocked",
            "verification_confidence": "low",
            "reasons": ["impact confidence is low"],
            "command_results": [{
                "check": "ruff",
                "command": ["python", "-m", "ruff"],
                "status": "FAILED",
                "exit_code": 1,
                "duration_ms": 12,
                "stdout": "",
                "stderr": "E402" * 500,
            }],
        },
    })

    assert view["impact"]["changed_symbols"] == []
    assert view["impact"]["unresolved_references"] == [{
        "file_path": "src/flask/views.py",
        "detail": "lines 12-12",
        "reason": "changed range does not fall inside any known symbol (likely module-level code)",
    }]
    assert view["verification"]["reasons"] == ["impact confidence is low"]
    command = view["verification"]["command_results"][0]
    assert command["status"] == "FAILED"
    assert command["exit_code"] == 1
    assert len(command["stderr"]) <= 1015


def test_missing_and_empty_observability_evidence_keep_distinct_semantics():
    view = change_risk_view({
        "risk_level": "low",
        "recommendation": "no_review_required",
        "impact": {"changed_symbols": [], "unresolved_references": []},
        "verification": {
            "reasons": [],
            "command_results": None,
        },
    })

    assert view["impact"]["changed_symbols"] == []
    assert view["impact"]["unresolved_references"] == []
    assert view["verification"]["reasons"] == []
    assert view["verification"]["command_results"] is None


def test_attribution_summary_is_exposed_in_regression_view():
    view = change_risk_view({
        "risk_level": "medium",
        "verification": {
            "new_findings_attribution": [
                {"attribution": "DIRECT_CHANGE"},
                {"attribution": "DIRECT_CHANGE"},
                {"attribution": "CALLER_IMPACT"},
                {"attribution": "OUTSIDE_IMPACT"},
                {"attribution": "UNRESOLVED"},
                {"attribution": "UNKNOWN"},
            ]
        },
    })

    summary = view["regression"]["attribution_summary"]
    assert summary is not None
    assert summary["total"] == 6
    assert summary["change_related_count"] == 3  # 2 DIRECT_CHANGE + 1 CALLER_IMPACT
    assert summary["outside_count"] == 1
    assert summary["unresolved_count"] == 2  # 1 UNRESOLVED + 1 UNKNOWN
    assert summary["by_attribution"]["DIRECT_CHANGE"] == 2


def test_attribution_summary_is_none_when_unavailable():
    view = change_risk_view({
        "risk_level": "low",
        "verification": {
            "new_findings_attribution": None
        }
    })

    assert view["regression"]["attribution_summary"] is None
