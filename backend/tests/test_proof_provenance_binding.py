"""Bind test-selection and node-results-source provenance into the proof hash."""

import json
import os
import subprocess
import sys

from app.models.change_impact import ChangeImpactReport, Confidence
from app.services.change_risk_engine import ChangeRiskAssessment, RiskLevel
from app.services.verification_engine import (
    PROOF_HASH_VERSION,
    BehavioralTestComparison,
    VerificationEngine,
    VerificationEvidence,
)


def _impact():
    return ChangeImpactReport(
        repository="r", base_revision="base", target_revision="target",
        changed_files=["x/mod.py"], confidence=Confidence.HIGH,
    )


def _risk():
    return ChangeRiskAssessment(risk_level=RiskLevel.LOW, score=10, confidence="high")


REC_A = {
    "test_file": "tests/test_x.py", "changed_file": "x/mod.py",
    "changed_module": "x.mod", "evidence": "DIRECT_IMPORT",
    "name_mirror": True, "symbols": ["fn"],
}
REC_B = {
    "test_file": "tests/test_y.py", "changed_file": "x/mod.py",
    "changed_module": "x.mod", "evidence": "REEXPORT_IMPORT",
    "name_mirror": False, "symbols": [],
}


def _prov(records):
    return json.dumps(records, sort_keys=True, separators=(",", ":"))


def _beh(base_src="PYTEST_NODE_LIFECYCLE_EVENTS", tgt_src="PYTEST_NODE_LIFECYCLE_EVENTS",
         *, volatile=0):
    def _exec(src):
        return {
            "node_results_source": src,
            "node_results": {"tests/test_x.py::t": "passed"},
            "status": "EXECUTED",
            "duration_ms": volatile,
            "stdout": "x" * volatile,
            "stderr": "",
            "working_directory": f"/tmp/agi-{volatile}/repo",
        }
    return BehavioralTestComparison(
        test_file="tests/test_x.py", test_node_id="tests/test_x.py::t",
        baseline_status="passed", target_status="passed", regression=False,
        comparison_status="CONSISTENT",
        baseline_execution=_exec(base_src), target_execution=_exec(tgt_src),
    )


def _proof(*, provenance=None, behavioral=None):
    ev = VerificationEvidence(
        test_selection_provenance=provenance,
        behavioral=behavioral,
    )
    return VerificationEngine().assess(_impact(), [], _risk(), ev)


# --- presence ---------------------------------------------------------------

def test_selection_provenance_present_in_proof():
    proof = _proof(provenance=_prov([REC_A]))
    payload = proof.to_dict()
    assert payload["test_selection_provenance"] == [REC_A]


def test_node_results_source_present_in_proof():
    proof = _proof(behavioral=[_beh()])
    payload = proof.to_dict()
    assert payload["node_results_source"] == {
        "baseline": ["PYTEST_NODE_LIFECYCLE_EVENTS"],
        "target": ["PYTEST_NODE_LIFECYCLE_EVENTS"],
    }


def test_both_present_in_canonical_hash_payload():
    proof = _proof(provenance=_prov([REC_A]), behavioral=[_beh()])
    canonical = proof.canonical_hash_payload()
    assert canonical["version"] == PROOF_HASH_VERSION
    inner = canonical["proof"]
    assert inner["test_selection_provenance"] == [REC_A]
    assert inner["node_results_source"]["baseline"] == ["PYTEST_NODE_LIFECYCLE_EVENTS"]


# --- deterministic ordering -------------------------------------------------

def test_selection_provenance_order_independent_hash():
    a = _proof(provenance=_prov([REC_A, REC_B]))
    b = _proof(provenance=_prov([REC_B, REC_A]))
    assert a.deterministic_hash == b.deterministic_hash
    assert a.test_selection_provenance == b.test_selection_provenance


# --- volatile exclusion -----------------------------------------------------

def test_volatile_behavioral_fields_excluded_from_hash():
    a = _proof(behavioral=[_beh(volatile=1)])
    b = _proof(behavioral=[_beh(volatile=99999)])
    assert a.deterministic_hash == b.deterministic_hash


# --- meaningful changes change the hash -------------------------------------

def test_different_selection_provenance_changes_hash():
    a = _proof(provenance=_prov([REC_A]))
    b = _proof(provenance=_prov([REC_B]))
    assert a.deterministic_hash != b.deterministic_hash


def test_node_source_lifecycle_differs_from_text_summary():
    lifecycle = _proof(behavioral=[_beh("PYTEST_NODE_LIFECYCLE_EVENTS", "PYTEST_NODE_LIFECYCLE_EVENTS")])
    text = _proof(behavioral=[_beh("PYTEST_RA_SUMMARY_TEXT", "PYTEST_RA_SUMMARY_TEXT")])
    assert lifecycle.deterministic_hash != text.deterministic_hash


def test_evidence_tier_change_changes_hash():
    upgraded = dict(REC_A, evidence="DIRECT_IMPORT_AND_SYMBOL")
    a = _proof(provenance=_prov([REC_A]))
    b = _proof(provenance=_prov([upgraded]))
    assert a.deterministic_hash != b.deterministic_hash


# --- absence stays None, no false binding -----------------------------------

def test_absent_provenance_is_none():
    proof = _proof()
    assert proof.test_selection_provenance is None
    assert proof.node_results_source is None
    unavailable = _proof(provenance="unavailable")
    assert unavailable.test_selection_provenance is None


# --- stable across PYTHONHASHSEED -------------------------------------------

def test_hash_stable_across_python_hash_seeds():
    script = (
        "import json\n"
        "from app.models.change_impact import ChangeImpactReport, Confidence\n"
        "from app.services.change_risk_engine import ChangeRiskAssessment, RiskLevel\n"
        "from app.services.verification_engine import (VerificationEngine, VerificationEvidence, BehavioralTestComparison)\n"
        "impact = ChangeImpactReport(repository='r', base_revision='base', target_revision='target', changed_files=['x/mod.py'], confidence=Confidence.HIGH)\n"
        "risk = ChangeRiskAssessment(risk_level=RiskLevel.LOW, score=10, confidence='high')\n"
        "prov = json.dumps([{'test_file':'tests/test_y.py','changed_file':'x/mod.py','changed_module':'x.mod','evidence':'REEXPORT_IMPORT','name_mirror':False,'symbols':[]},"
        "{'test_file':'tests/test_x.py','changed_file':'x/mod.py','changed_module':'x.mod','evidence':'DIRECT_IMPORT','name_mirror':True,'symbols':['fn']}])\n"
        "b = BehavioralTestComparison(test_file='tests/test_x.py', test_node_id='tests/test_x.py::t', baseline_status='passed', target_status='passed', regression=False, comparison_status='CONSISTENT',"
        " baseline_execution={'node_results_source':'PYTEST_NODE_LIFECYCLE_EVENTS','node_results':{'tests/test_x.py::t':'passed'},'status':'EXECUTED'},"
        " target_execution={'node_results_source':'PYTEST_NODE_LIFECYCLE_EVENTS','node_results':{'tests/test_x.py::t':'passed'},'status':'EXECUTED'})\n"
        "ev = VerificationEvidence(test_selection_provenance=prov, behavioral=[b])\n"
        "print(VerificationEngine().assess(impact, [], risk, ev).deterministic_hash)\n"
    )
    env = dict(os.environ, PYTHONPATH="backend", PYTHONHASHSEED="5")
    first = subprocess.check_output([sys.executable, "-c", script], env=env, text=True).strip()
    env["PYTHONHASHSEED"] = "104729"
    second = subprocess.check_output([sys.executable, "-c", script], env=env, text=True).strip()
    assert first == second
