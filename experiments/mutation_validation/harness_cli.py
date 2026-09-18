import sys
import os
import json
import argparse
from pathlib import Path

# Add AGI Engineer backend to path
# We run this from experiments/mutation_validation, so backend is at ../../backend
backend_path = Path(__file__).resolve().parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))
sys.path.insert(0, str(backend_path.parent))

from app.services.change_impact_service import ChangeImpactService
from app.services.change_risk_service import ChangeRiskService
from agent.intelligence import IntelligenceOrchestrator
from agent.intelligence.selection import AnalyzerSelection
from agent.run_ledger import RunLedgerWriter
from app.services.change_risk_engine import ChangeRiskEngine
from app.services.verification_engine import VerificationEngine
from app.services.verification_execution import VerificationExecutor
from app.services.baseline_comparison import BaselineComparisonService
from app.services.finding_context import build_finding_contexts
from app.v1_engine import V1AnalysisEngine
from app.models.change_impact import ChangeRiskReport
from agent.intelligence.proposal import IntelligenceProposal
from agent.intelligence.registry import ANALYZER_REGISTRY
import dataclasses

def _run_baseline_analyzers(repo_path: str, branch: str = "main") -> list:
    engine = V1AnalysisEngine(groq_api_key=os.environ.get("GROQ_API_KEY", ""))
    ruff_results = engine._run_ruff_analysis(repo_path)
    eslint_results = engine._run_eslint_analysis(repo_path)
    all_issues = ruff_results + eslint_results

    finding_rows = []
    for issue in all_issues:
        finding_rows.append({
            "proposal_id": f"baseline-{len(finding_rows)}",
            "file_path": issue.get("file_path", ""),
            "line_number": issue.get("line_number", 0),
            "issue_code": issue.get("issue_code", "unknown"),
            "issue_name": issue.get("issue_name", ""),
            "message": issue.get("message", ""),
            "severity": issue.get("severity", "medium"),
        })
    return finding_rows

def main():
    parser = argparse.ArgumentParser(description="AGI Engineer Local Wrapper")
    parser.add_argument("--repo-path", required=True, help="Path to local repository")
    parser.add_argument("--base-revision", required=True, help="Base revision (commit sha)")
    parser.add_argument("--target-revision", required=True, help="Target revision (commit sha)")

    args = parser.parse_args()

    # Run intelligence orchestrator
    orchestrator = IntelligenceOrchestrator()
    enabled_analyzers = [
        aid for aid, config in ANALYZER_REGISTRY.items()
        if config.get("category") == "reliability"
    ]
    if not enabled_analyzers:
        enabled_analyzers = ["ruff_analyzer"] # Fallback

    selection = AnalyzerSelection(
        plan="team",
        enabled_analyzers=enabled_analyzers
    )

    ledger = RunLedgerWriter(run_id="local-harness", repo_id="local-repo", environment="TEST", initiated_by="HARNESS")
    ledger.create_ledger()

    proposals = orchestrator.analyze(
        repository_path=args.repo_path,
        repository_url="local",
        branch="main",
        ledger=ledger,
        run_id="local-harness",
        selection=selection,
    )

    # Change Impact
    impact_service = ChangeImpactService()
    try:
        impact_analysis = impact_service.compute_change_impact_with_graph(
            repo_path=args.repo_path,
            base_revision=args.base_revision,
            target_revision=args.target_revision,
            max_impact_depth=6,
            repository_label="local-repo",
        )
    except Exception as e:
        print(json.dumps({"error": f"Change impact failed: {e}"}))
        sys.exit(1)

    # Change Risk Assessment
    risk_service = ChangeRiskService(impact_service=impact_service)
    try:
        risk_report = risk_service.assess(
            repo_path=args.repo_path,
            base_revision=args.base_revision,
            target_revision=args.target_revision,
            findings=proposals,
            ledger=ledger,
            max_impact_depth=6,
            repository_label="local-repo",
            precomputed_analysis=impact_analysis
        )
    except Exception as e:
        print(json.dumps({"error": f"Risk assessment failed: {e}"}))
        sys.exit(1)

    # Verification Engine
    # Build finding contexts first
    finding_rows = []
    for proposal in proposals:
        if proposal.affected_files:
            primary = proposal.affected_files[0]
            line_start = 0
            if primary.line_range:
                try:
                    line_start = int(str(primary.line_range).split("-")[0])
                except:
                    pass
            finding_rows.append({
                "proposal_id": proposal.proposal_id,
                "file_path": primary.path,
                "line_number": line_start,
                "issue_code": (proposal.bug_class.value if proposal.bug_class else "unknown"),
                "issue_name": proposal.problem_statement or "",
                "message": proposal.problem_statement or "",
                "severity": (proposal.severity.value if proposal.severity else "medium")
            })

    contexts = build_finding_contexts(
        finding_rows,
        graph=impact_analysis.graph,
        impact=impact_analysis.report,
        repo_root=args.repo_path
    )

    assessment = ChangeRiskEngine().assess(
        impact_analysis.report,
        contexts,
        existing_report=risk_report
    )

    execution_evidence = VerificationExecutor().execute(
        repo_path=args.repo_path,
        revision=args.target_revision,
        impact=impact_analysis.report,
        risk=assessment,
        contexts=contexts
    )

    baseline = BaselineComparisonService().compare(
        repo_path=args.repo_path,
        base_revision=args.base_revision,
        target_revision=args.target_revision,
        target_findings=finding_rows,
        analyze=lambda path: _run_baseline_analyzers(path),
        normalize=lambda x: x
    )

    execution_evidence = dataclasses.replace(
        execution_evidence,
        findings_before=baseline.findings_before,
        baseline_status=baseline.baseline_status,
        comparison_status=baseline.comparison_status,
        baseline_error=baseline.error,
        comparison_findings_before=baseline.findings_before,
        comparison_findings_after=finding_rows,
    )

    proof = VerificationEngine().assess(
        impact_analysis.report,
        contexts,
        assessment,
        evidence=execution_evidence
    )

    final_report = risk_report.to_dict()
    final_report["decision"] = assessment.to_dict()
    final_report["verification"] = proof.to_dict()

    final_report["harness_findings"] = []
    for row, ctx in zip(finding_rows, contexts):
        final_report["harness_findings"].append({
            "finding": row,
            "context": ctx.to_dict()
        })

    print(json.dumps(final_report, indent=2))

if __name__ == "__main__":
    main()
