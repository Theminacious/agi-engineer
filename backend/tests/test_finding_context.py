"""Phase 21 — Finding Context / Relevance layer."""

import pytest

from app.services.finding_context import (
    FileClass,
    Recommendation,
    Relevance,
    build_finding_contexts,
    classify_file,
    relative_path,
    rule_semantics,
    summarize_contexts,
)


class FakeNode:
    def __init__(self, node_id, name, file_path, line_number, end_line=None):
        self.id = node_id
        self.name = name
        self.file_path = file_path
        self.line_number = line_number
        self.metadata = {"end_line": end_line} if end_line else {}


class FakeGraph:
    def __init__(self, nodes, callers=None, impact=None):
        self.nodes = {n.id: n for n in nodes}
        self._callers = callers or {}
        self._impact = impact or {}

    def get_callers(self, node_id):
        return self._callers.get(node_id, [])

    def get_impact_set(self, node_id, max_depth=3):
        return self._impact.get(node_id, {node_id})


class FakeFindingImpact:
    def __init__(
        self,
        finding_ref,
        relation,
        resolved_node_id="",
        severity="unknown",
        file_path=None,
    ):
        self.finding_ref = finding_ref
        self.relation = relation
        self.resolved_node_id = resolved_node_id
        self.severity = severity
        self.file_path = file_path


class FakeImpactReport:
    def __init__(self, finding_impacts):
        self.finding_impacts = finding_impacts


def finding(path, line=1, code="F811", message="Redefinition of unused `x` from line 1", severity="warning"):
    return {
        "file_path": path,
        "line_number": line,
        "issue_code": code,
        "issue_name": message,
        "message": message,
        "severity": severity,
    }


class TestFileClassification:
    def test_pyi_extension_is_type_stub(self):
        result = classify_file("mypkg/_socket.pyi")
        assert result.file_class is FileClass.TYPE_STUB
        assert any(".pyi" in reason for reason in result.reasons)

    def test_d_ts_is_type_stub(self):
        assert classify_file("types/express.d.ts").file_class is FileClass.TYPE_STUB

    def test_typeshed_stdlib_tree_is_type_stub_even_without_pyi(self):
        assert classify_file("stdlib/socket.py").file_class is FileClass.TYPE_STUB

    def test_typeshed_stubs_tree_is_type_stub(self):
        assert classify_file("stubs/psutil/psutil/_pswindows.pyi").file_class is FileClass.TYPE_STUB

    def test_plain_application_file(self):
        result = classify_file("app/services/billing.py")
        assert result.file_class is FileClass.APPLICATION
        assert result.also == ()

    def test_unknown_path_defaults_to_application(self):
        assert classify_file("weird/path/thing.py").file_class is FileClass.APPLICATION

    def test_node_modules_is_vendored(self):
        assert classify_file("node_modules/lodash/index.js").file_class is FileClass.VENDORED

    def test_site_packages_is_vendored(self):
        assert classify_file(".venv/lib/site-packages/requests/api.py").file_class is FileClass.VENDORED

    def test_protobuf_stem_is_generated(self):
        assert classify_file("app/rpc/user_pb2.py").file_class is FileClass.GENERATED

    def test_minified_js_is_generated(self):
        assert classify_file("static/app.min.js").file_class is FileClass.GENERATED

    def test_test_directory_is_test(self):
        assert classify_file("tests/test_billing.py").file_class is FileClass.TEST

    def test_test_filename_outside_test_dir_is_test(self):
        assert classify_file("app/test_helpers.py").file_class is FileClass.TEST

    def test_fixtures_dir_outranks_test_dir(self):
        assert classify_file("tests/fixtures/sample.py").file_class is FileClass.TEST_FIXTURE

    def test_docs_dir_is_documentation(self):
        assert classify_file("docs/examples/quickstart.py").file_class is FileClass.DOCUMENTATION

    def test_markdown_is_documentation(self):
        assert classify_file("README.md").file_class is FileClass.DOCUMENTATION

    def test_setup_py_is_build_config(self):
        assert classify_file("setup.py").file_class is FileClass.BUILD_CONFIG

    def test_vendored_outranks_generated_and_stub(self):
        result = classify_file("vendor/thing/generated/mod_pb2.pyi")
        assert result.file_class is FileClass.VENDORED
        assert FileClass.GENERATED in result.also
        assert FileClass.TYPE_STUB in result.also

    def test_segment_matching_is_whole_segment_not_substring(self):
        assert classify_file("app/vendored_api/client.py").file_class is FileClass.APPLICATION

    def test_windows_separators_are_normalized(self):
        assert classify_file(r"stubs\psutil\_pswindows.pyi").file_class is FileClass.TYPE_STUB

    def test_empty_path_is_application(self):
        assert classify_file("").file_class is FileClass.APPLICATION

    def test_classification_is_deterministic(self):
        path = "vendor/x/generated/y_pb2.pyi"
        assert classify_file(path) == classify_file(path)


class TestRelativePath:
    def test_strips_repo_root(self):
        assert relative_path("/tmp/agi-abc/stdlib/_socket.pyi", "/tmp/agi-abc") == "stdlib/_socket.pyi"

    def test_strips_repo_root_with_trailing_slash(self):
        assert relative_path("/tmp/agi-abc/a.py", "/tmp/agi-abc/") == "a.py"

    def test_leaves_unrelated_path_alone(self):
        assert relative_path("/other/a.py", "/tmp/agi-abc") == "/other/a.py"

    def test_no_root_returns_normalized(self):
        assert relative_path(r"a\b.py", "") == "a/b.py"


class TestStubFindingsAreContextualizedNotDropped:
    def test_f811_in_pyi_is_informational_but_retained(self):
        contexts = build_finding_contexts([finding("stdlib/_socket.pyi", 846)])
        assert len(contexts) == 1
        context = contexts[0]
        assert context.file_class is FileClass.TYPE_STUB
        assert context.relevance is Relevance.INFORMATIONAL
        assert context.recommendation is Recommendation.SUPPRESS_CANDIDATE
        assert any("type_stub" in reason for reason in context.relevance_reasons)

    def test_f811_in_application_code_is_actionable(self):
        contexts = build_finding_contexts([finding("app/services/billing.py", 12)])
        context = contexts[0]
        assert context.file_class is FileClass.APPLICATION
        assert context.relevance is Relevance.ACTIONABLE
        assert context.recommendation is Recommendation.FIX

    def test_stub_confidence_is_lower_than_application_confidence(self):
        stub = build_finding_contexts([finding("stdlib/_socket.pyi")])[0]
        app = build_finding_contexts([finding("app/svc.py")])[0]
        assert stub.confidence < app.confidence

    def test_no_finding_is_ever_removed(self):
        findings = [
            finding("stdlib/_socket.pyi", 846),
            finding("node_modules/x/index.js", 3, code="no-undef"),
            finding("app/svc.py", 10),
            finding("docs/example.py", 4),
        ]
        contexts = build_finding_contexts(findings)
        assert len(contexts) == len(findings)

    def test_input_order_is_preserved(self):
        findings = [finding("a.py", 1), finding("stdlib/b.pyi", 2), finding("c.py", 3)]
        contexts = build_finding_contexts(findings)
        assert [c.file_path for c in contexts] == ["a.py", "stdlib/b.pyi", "c.py"]

    def test_vendored_finding_is_review_not_actionable(self):
        context = build_finding_contexts([finding("node_modules/lodash/index.js", code="no-console")])[0]
        assert context.file_class is FileClass.VENDORED
        assert context.relevance is Relevance.REVIEW

    def test_unknown_rule_in_application_code_is_actionable(self):
        context = build_finding_contexts([finding("app/svc.py", code="XYZ999")])[0]
        assert context.relevance is Relevance.ACTIONABLE

    def test_unknown_rule_in_vendored_code_is_downgraded(self):
        context = build_finding_contexts([finding("vendor/x/y.py", code="XYZ999")])[0]
        assert context.relevance is Relevance.REVIEW


class TestSymbolExtraction:
    def test_symbol_pulled_from_backticked_message(self):
        context = build_finding_contexts([
            finding("app/svc.py", message="Redefinition of unused `timeout` from line 4")
        ])[0]
        assert context.symbol == "timeout"

    def test_missing_symbol_stays_none(self):
        context = build_finding_contexts([finding("app/svc.py", message="Line too long")])[0]
        assert context.symbol is None


class TestCorrelation:
    def test_same_rule_same_file_is_grouped(self):
        findings = [finding("stubs/psutil/_pswindows.pyi", line, message=f"Redefinition of unused `C{line}`")
                    for line in range(48, 54)]
        contexts = build_finding_contexts(findings)
        assert all(c.correlated_count == 6 for c in contexts)
        assert len({c.correlation_id for c in contexts}) == 1

    def test_different_files_are_not_grouped(self):
        contexts = build_finding_contexts([finding("a.pyi"), finding("b.pyi")])
        assert all(c.correlation_id is None for c in contexts)
        assert all(c.correlated_count == 1 for c in contexts)

    def test_different_rules_same_file_are_not_grouped(self):
        contexts = build_finding_contexts([
            finding("app/svc.py", code="F811"),
            finding("app/svc.py", code="E501"),
        ])
        assert all(c.correlation_id is None for c in contexts)

    def test_correlation_lowers_confidence(self):
        single = build_finding_contexts([finding("app/svc.py", 1)])[0]
        grouped = build_finding_contexts([finding("app/svc.py", 1), finding("app/svc.py", 2)])[0]
        assert grouped.confidence < single.confidence


class TestGraphEnrichment:
    def test_no_graph_leaves_reachability_unknown(self):
        context = build_finding_contexts([finding("app/svc.py", 10)])[0]
        assert context.production_reachable is None
        assert context.caller_count is None

    def test_file_absent_from_graph_states_the_reason(self):
        graph = FakeGraph([FakeNode("other.py::f", "f", "other.py", 1, 5)])
        context = build_finding_contexts([finding("app/svc.py", 10)], graph=graph)[0]
        assert context.production_reachable is None
        assert "not present in code graph" in context.reachability_reason

    def test_enclosing_symbol_resolved_and_callers_counted(self):
        node = FakeNode("app/svc.py::charge", "charge", "app/svc.py", 5, 20)
        caller = FakeNode("app/api.py::post", "post", "app/api.py", 1, 10)
        graph = FakeGraph(
            [node, caller],
            callers={"app/svc.py::charge": [caller]},
            impact={"app/svc.py::charge": {"app/api.py::post"}},
        )
        context = build_finding_contexts([finding("app/svc.py", 10)], graph=graph)[0]
        assert context.symbol == "charge"
        assert context.symbol_node_id == "app/svc.py::charge"
        assert context.caller_count == 1
        assert context.downstream_count == 1
        assert context.production_reachable is None
        assert "runtime/production reachability is not established" in context.reachability_reason

    def test_no_callers_does_not_claim_runtime_unreachability(self):
        node = FakeNode("app/svc.py::orphan", "orphan", "app/svc.py", 5, 20)
        graph = FakeGraph([node], callers={"app/svc.py::orphan": []})
        with_graph = build_finding_contexts([finding("app/svc.py", 10)], graph=graph)[0]
        without_graph = build_finding_contexts([finding("app/svc.py", 10)])[0]
        assert with_graph.caller_count == 0
        assert with_graph.production_reachable is None
        assert with_graph.confidence == without_graph.confidence

    def test_narrowest_enclosing_symbol_wins(self):
        outer = FakeNode("app/svc.py::Outer", "Outer", "app/svc.py", 1, 50)
        inner = FakeNode("app/svc.py::Outer.method", "method", "app/svc.py", 10, 20)
        graph = FakeGraph([outer, inner])
        context = build_finding_contexts([finding("app/svc.py", 15)], graph=graph)[0]
        assert context.symbol == "method"

    def test_line_outside_every_symbol_is_reported(self):
        node = FakeNode("app/svc.py::f", "f", "app/svc.py", 100, 120)
        graph = FakeGraph([node])
        context = build_finding_contexts([finding("app/svc.py", 5)], graph=graph)[0]
        assert context.symbol_node_id is None
        assert "no symbol in graph encloses" in context.reachability_reason

    def test_call_graph_does_not_promote_vendored_code_as_production_reachable(self):
        node = FakeNode("vendor/x/y.py::f", "f", "vendor/x/y.py", 1, 20)
        caller = FakeNode("app/a.py::g", "g", "app/a.py", 1, 5)
        graph = FakeGraph([node, caller], callers={"vendor/x/y.py::f": [caller]})
        context = build_finding_contexts(
            [finding("vendor/x/y.py", 10, code="XYZ999")], graph=graph
        )[0]
        assert context.production_reachable is None
        assert context.relevance is Relevance.REVIEW

    def test_reachability_does_not_promote_broken_premise_stub_finding(self):
        node = FakeNode("stdlib/_socket.pyi::timeout", "timeout", "stdlib/_socket.pyi", 840, 850)
        caller = FakeNode("app/a.py::g", "g", "app/a.py", 1, 5)
        graph = FakeGraph([node, caller], callers={"stdlib/_socket.pyi::timeout": [caller]})
        context = build_finding_contexts([finding("stdlib/_socket.pyi", 846)], graph=graph)[0]
        assert context.relevance is Relevance.INFORMATIONAL

    def test_broken_graph_does_not_raise(self):
        class Broken:
            @property
            def nodes(self):
                raise RuntimeError("boom")

        context = build_finding_contexts([finding("app/svc.py")], graph=Broken())[0]
        assert context.reachability_reason == "graph unavailable"


class TestChangeImpactEnrichment:
    def test_direct_relation_is_attached(self):
        contexts = build_finding_contexts([finding("app/svc.py", 10)])
        ref = contexts[0].finding_ref
        impact = FakeImpactReport([FakeFindingImpact(ref, "direct", "app/svc.py::charge", "high")])
        enriched = build_finding_contexts([finding("app/svc.py", 10)], impact=impact)[0]
        assert enriched.change_relation == "direct"
        assert enriched.symbol_node_id == "app/svc.py::charge"
        assert enriched.severity == "high"

    def test_outside_relation_is_recorded_as_preexisting(self):
        ref = build_finding_contexts([finding("app/svc.py", 10)])[0].finding_ref
        impact = FakeImpactReport([FakeFindingImpact(ref, "outside")])
        context = build_finding_contexts([finding("app/svc.py", 10)], impact=impact)[0]
        assert context.change_relation == "outside"
        assert any("outside the change" in reason for reason in context.relevance_reasons)

    def test_direct_relation_promotes_review_to_actionable(self):
        ref = build_finding_contexts([finding("vendor/x/y.py", 10, code="XYZ999")])[0].finding_ref
        impact = FakeImpactReport([FakeFindingImpact(ref, "direct")])
        context = build_finding_contexts(
            [finding("vendor/x/y.py", 10, code="XYZ999")], impact=impact
        )[0]
        assert context.relevance is Relevance.ACTIONABLE

    def test_unmatched_finding_ref_leaves_relation_none(self):
        impact = FakeImpactReport([FakeFindingImpact("nope", "direct")])
        context = build_finding_contexts([finding("app/svc.py", 10)], impact=impact)[0]
        assert context.change_relation is None

    def test_unknown_severity_from_impact_does_not_overwrite(self):
        ref = build_finding_contexts([finding("app/svc.py", 10, severity="error")])[0].finding_ref
        impact = FakeImpactReport([FakeFindingImpact(ref, "direct", severity="unknown")])
        context = build_finding_contexts(
            [finding("app/svc.py", 10, severity="error")], impact=impact
        )[0]
        assert context.severity == "error"

    def test_multi_file_finding_uses_evidence_for_the_context_file(self):
        ref = build_finding_contexts([finding("app/svc.py", 10)])[0].finding_ref
        impact = FakeImpactReport([
            FakeFindingImpact(ref, "direct", file_path="app/other.py"),
            FakeFindingImpact(ref, "outside", file_path="app/svc.py"),
        ])
        context = build_finding_contexts([finding("app/svc.py", 10)], impact=impact)[0]
        assert context.change_relation == "outside"


class TestDeterminism:
    def test_same_input_gives_identical_hash(self):
        findings = [finding("stdlib/_socket.pyi", 846), finding("app/svc.py", 10)]
        first = build_finding_contexts(findings)
        second = build_finding_contexts(findings)
        assert [c.context_hash() for c in first] == [c.context_hash() for c in second]

    def test_finding_ref_is_stable_across_calls(self):
        row = finding("app/svc.py", 10)
        assert build_finding_contexts([row])[0].finding_ref == build_finding_contexts([row])[0].finding_ref

    def test_explicit_finding_ref_is_respected(self):
        row = finding("app/svc.py", 10)
        row["finding_ref"] = "prop-123"
        assert build_finding_contexts([row])[0].finding_ref == "prop-123"

    def test_repo_root_stripping_changes_classification(self):
        row = finding("/tmp/agi-xyz/stdlib/_socket.pyi", 846)
        without = build_finding_contexts([row])[0]
        with_root = build_finding_contexts([row], repo_root="/tmp/agi-xyz")[0]
        assert without.file_path.startswith("/tmp/")
        assert with_root.file_path == "stdlib/_socket.pyi"
        assert with_root.file_class is FileClass.TYPE_STUB

    def test_confidence_stays_in_range(self):
        node = FakeNode("stdlib/a.pyi::x", "x", "stdlib/a.pyi", 1, 10)
        graph = FakeGraph([node], callers={"stdlib/a.pyi::x": []})
        findings = [finding("stdlib/a.pyi", 5) for _ in range(10)]
        for context in build_finding_contexts(findings, graph=graph):
            assert 1 <= context.confidence <= 100

    def test_confidence_never_collapses_to_zero(self):
        context = build_finding_contexts([finding("stdlib/a.pyi", 5)])[0]
        assert context.confidence >= 1

    def test_broken_premise_is_a_ceiling_not_an_extra_penalty(self):
        stub = build_finding_contexts([finding("stdlib/a.pyi", 5)])[0]
        assert stub.confidence <= 20
        assert any("capped at" in reason for reason in stub.confidence_reasons)

    def test_stub_confidences_stay_distinguishable(self):
        single = build_finding_contexts([finding("stdlib/a.pyi", 5)])[0]
        vendored_stub = build_finding_contexts([finding("vendor/x/a.pyi", 5, code="E501")])[0]
        assert single.confidence != vendored_stub.confidence

    def test_every_context_carries_reasons(self):
        contexts = build_finding_contexts([
            finding("stdlib/a.pyi"), finding("app/b.py"), finding("node_modules/c.js"),
        ])
        for context in contexts:
            assert context.classification_reasons
            assert context.relevance_reasons
            assert context.confidence_reasons


class TestRuleSemantics:
    def test_known_rule_returns_its_entry(self):
        assert rule_semantics("F811").code == "F811"
        assert FileClass.TYPE_STUB in rule_semantics("F811").premise_broken_in

    def test_unknown_rule_gets_generic_weakening(self):
        semantics = rule_semantics("ZZZ111")
        assert semantics.premise_broken_in == ()
        assert FileClass.VENDORED in semantics.premise_weakened_in


class TestSummary:
    def test_typeshed_shaped_run_summarizes_as_informational(self):
        findings = (
            [finding("stdlib/_socket.pyi", line) for line in (846, 949)]
            + [finding("stubs/psutil/psutil/_pswindows.pyi", line) for line in range(48, 54)]
            + [finding("stubs/pywin32/win32/win32ras.pyi", 24)]
        )
        contexts = build_finding_contexts(findings)
        summary = summarize_contexts(contexts)

        assert summary["total_findings"] == 9
        assert summary["informational_count"] == 9
        assert summary["actionable_count"] == 0
        assert summary["by_file_class"] == {"type_stub": 9}
        assert summary["by_recommendation"][Recommendation.SUPPRESS_CANDIDATE.value] == 9
        assert summary["correlation_group_count"] == 2
        assert summary["distinct_issues"] == 3

    def test_mixed_run_counts_each_bucket(self):
        contexts = build_finding_contexts([
            finding("app/a.py", 1),
            finding("stdlib/b.pyi", 2),
            finding("node_modules/c.js", 3, code="no-console"),
        ])
        summary = summarize_contexts(contexts)
        assert summary["actionable_count"] == 1
        assert summary["informational_count"] == 1
        assert summary["by_relevance"][Relevance.REVIEW.value] == 1

    def test_empty_run_summarizes_cleanly(self):
        summary = summarize_contexts([])
        assert summary["total_findings"] == 0
        assert summary["actionable_count"] == 0
        assert summary["distinct_issues"] == 0
