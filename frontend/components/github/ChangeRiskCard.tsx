"use client";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { AlertTriangle, ArrowDown, ShieldCheck } from "lucide-react";
import {
  affectedPath,
  behavioralStatusClassName,
  behavioralStatusLabel,
  factorSummary,
  proofIntegrityClassName,
  proofIntegrityLabel,
  recommendationLabel,
  requiresHumanReview,
  riskLevelClassName,
  riskLevelLabel,
  shortHash,
  verificationStateClassName,
  verificationStateLabel,
  type ChangeRisk,
} from "@/lib/prAnalyses";

interface ChangeRiskCardProps {
  prNumber: number;
  repository: string;
  changeRisk: ChangeRisk;
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-lg border p-3">
      <div className="text-xs uppercase tracking-wide text-muted-foreground">{label}</div>
      <div className="text-2xl font-semibold tabular-nums">{value}</div>
    </div>
  );
}

function EvidenceList({ label, values }: { label: string; values: string[] | null | undefined }) {
  return (
    <div>
      <div className="text-xs uppercase text-muted-foreground">{label}</div>
      {values === null || values === undefined ? (
        <div className="text-sm text-muted-foreground">Unknown / not available</div>
      ) : values.length === 0 ? (
        <div className="text-sm text-muted-foreground">None evidenced</div>
      ) : (
        <ul className="mt-1 space-y-1">
          {values.map((value) => (
            <li key={value} className="font-mono text-xs break-all">{value}</li>
          ))}
        </ul>
      )}
    </div>
  )
}

export function ChangeRiskCard({ prNumber, repository, changeRisk }: ChangeRiskCardProps) {
  if (!changeRisk?.available) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Change Risk</CardTitle>
          <CardDescription>
            {repository} #{prNumber}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div
            role="status"
            className="rounded-lg border border-dashed p-6 text-center text-sm text-muted-foreground"
          >
            <p className="font-medium text-foreground">Not assessed</p>
            <p className="mt-1">
              {changeRisk?.unavailable_reason ??
                "No change risk assessment was produced for this analysis."}
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  const {
    risk,
    impact,
    findings,
    risk_factors,
    caveats,
    evidence,
    decision,
    verification,
    baseline,
    regression,
    proof,
    governance,
  } = changeRisk;
  const level = risk?.level ?? null;
  const needsReview = requiresHumanReview(risk?.recommendation);
  const path = affectedPath(impact);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex flex-wrap items-center gap-3">
          <span>Change Risk</span>
          <Badge
            className={`border ${riskLevelClassName(level)}`}
            aria-label={`Change risk level ${riskLevelLabel(level)}`}
          >
            {riskLevelLabel(level)}
          </Badge>
          <span
            className={`inline-flex items-center gap-1 text-sm font-medium ${
              needsReview ? "text-red-700" : "text-emerald-700"
            }`}
          >
            {needsReview ? (
              <AlertTriangle className="h-4 w-4" aria-hidden="true" />
            ) : (
              <ShieldCheck className="h-4 w-4" aria-hidden="true" />
            )}
            {recommendationLabel(risk?.recommendation)}
          </span>
        </CardTitle>
        <CardDescription>
          {repository} #{prNumber} · confidence {risk?.confidence ?? "unknown"}
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-6">
        {risk?.summary && <p className="text-sm text-muted-foreground">{risk.summary}</p>}

        <section aria-labelledby={`blast-radius-${prNumber}`}>
          <h3 id={`blast-radius-${prNumber}`} className="mb-2 text-sm font-semibold">
            Blast radius
          </h3>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <Stat label="Symbols" value={impact?.blast_radius_size ?? 0} />
            <Stat label="Changed files" value={impact?.changed_file_count ?? 0} />
            <Stat label="Changed symbols" value={impact?.changed_symbol_count ?? 0} />
            <Stat label="Entry points" value={impact?.affected_entrypoints.length ?? 0} />
          </div>
        </section>

        {impact && impact.changed_symbols.length > 0 && (
          <section aria-labelledby={`changed-${prNumber}`}>
            <h3 id={`changed-${prNumber}`} className="mb-2 text-sm font-semibold">
              Changed
            </h3>
            <ul className="space-y-1">
              {impact.changed_symbols.map((symbol) => (
                <li key={symbol.node_id} className="font-mono text-sm break-all">
                  {symbol.node_id}
                  {symbol.change_kind && (
                    <span className="ml-2 font-sans text-xs text-muted-foreground">
                      {symbol.change_kind}
                    </span>
                  )}
                </li>
              ))}
            </ul>
          </section>
        )}

        {impact && (impact.unresolved_references.length > 0 || impact.changed_symbols.length === 0) && (
          <section aria-labelledby={`impact-evidence-${prNumber}`}>
            <h3 id={`impact-evidence-${prNumber}`} className="mb-2 text-sm font-semibold">
              Impact Evidence
            </h3>
            {impact.changed_symbols.length === 0 && (
              <p className="mb-3 text-sm text-muted-foreground">
                No changed symbol was resolved. Caller or downstream reachability was not inferred.
              </p>
            )}
            {impact.unresolved_references.length > 0 ? (
              <ul className="space-y-2">
                {impact.unresolved_references.map((reference, index) => (
                  <li key={`${reference.file_path}-${reference.detail}-${index}`} className="rounded-lg border p-3 text-sm">
                    <div className="font-mono break-all">
                      {reference.file_path ?? "Unknown file"}
                      {reference.detail ? ` · ${reference.detail}` : ""}
                    </div>
                    <div className="mt-1 text-muted-foreground">
                      {reference.reason ?? "Unresolved mapping reason unavailable."}
                    </div>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-muted-foreground">Unresolved mapping details are not available.</p>
            )}
          </section>
        )}

        {risk_factors.length > 0 && (
          <section aria-labelledby={`why-${prNumber}`}>
            <h3 id={`why-${prNumber}`} className="mb-2 text-sm font-semibold">
              Why?
            </h3>
            <ul className="space-y-2">
              {risk_factors.map((factor) => (
                <li key={`${factor.kind}-${factor.detail}`} className="flex gap-2 text-sm">
                  <Badge className={`border shrink-0 ${riskLevelClassName(factor.level)}`}>
                    {riskLevelLabel(factor.level)}
                  </Badge>
                  <div>
                    <div>{factorSummary(factor)}</div>
                    {factor.evidence.length > 0 && (
                      <ul className="mt-1 space-y-0.5">
                        {factor.evidence.map((item) => (
                          <li
                            key={item}
                            className="font-mono text-xs text-muted-foreground break-all"
                          >
                            {item}
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          </section>
        )}

        {path.length > 1 && (
          <section aria-labelledby={`path-${prNumber}`}>
            <h3 id={`path-${prNumber}`} className="mb-2 text-sm font-semibold">
              Affected path
            </h3>
            <ol className="space-y-1">
              {path.map((node, index) => (
                <li key={node} className="flex items-center gap-2 font-mono text-sm break-all">
                  {index > 0 && (
                    <ArrowDown
                      className="h-3 w-3 shrink-0 text-muted-foreground"
                      aria-hidden="true"
                    />
                  )}
                  <span className={index === 0 ? "ml-5" : ""}>{node}</span>
                </li>
              ))}
            </ol>
          </section>
        )}

        {findings && (
          <section aria-labelledby={`findings-${prNumber}`}>
            <h3 id={`findings-${prNumber}`} className="mb-2 text-sm font-semibold">
              Reliability findings evaluated
            </h3>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <Stat label="Evaluated" value={findings.evaluated} />
              <Stat label="Inside radius" value={findings.inside_radius} />
              <Stat label="Outside radius" value={findings.outside_radius} />
              <Stat label="Unresolved" value={findings.unresolved} />
            </div>
          </section>
        )}

        <section aria-labelledby={`decision-${prNumber}`}>
          <h3 id={`decision-${prNumber}`} className="mb-2 text-sm font-semibold">
            Change Decision
          </h3>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <Stat label="Score" value={decision?.score ?? "Unknown"} />
            <Stat label="Confidence" value={decision?.confidence ?? "Unknown"} />
            <Stat
              label="Review"
              value={decision?.human_review_required === null || decision?.human_review_required === undefined
                ? "Unknown"
                : decision.human_review_required ? "Required" : "Not required"}
            />
            <Stat label="Relationships" value={decision?.change_relationships.length ?? "Unknown"} />
          </div>
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <EvidenceList label="Decision reasons" values={decision?.reasons} />
            <EvidenceList label="Affected files" values={decision?.affected_files} />
          </div>
        </section>

        <section aria-labelledby={`verification-${prNumber}`}>
          <h3 id={`verification-${prNumber}`} className="mb-2 text-sm font-semibold">
            Verification
          </h3>
          <div className="flex flex-wrap items-center gap-2">
            <Badge
              className={`border ${verificationStateClassName(verification?.state)}`}
              aria-label={`Verification state ${verificationStateLabel(verification?.state)}`}
            >
              {verificationStateLabel(verification?.state)}
            </Badge>
            <span className="text-sm text-muted-foreground">
              confidence {verification?.confidence ?? "unknown"}
            </span>
            <Badge
              className={`border ${proofIntegrityClassName(verification?.proof_integrity?.status)}`}
              aria-label={`Proof integrity ${verification?.proof_integrity?.status ?? "INTEGRITY_UNAVAILABLE"}`}
            >
              {proofIntegrityLabel(verification?.proof_integrity?.status)}
            </Badge>
          </div>
          {verification?.proof_integrity?.status === "INTEGRITY_MISMATCH" && (
            <div
              role="alert"
              className="mt-2 rounded-lg border border-red-300 bg-red-50 p-3 text-sm text-red-900"
            >
              {verification.proof_integrity.reason ??
                "Persisted verification proof does not match the ledger-anchored hash."}{" "}
              This is an integrity failure, not a verification result — do not treat this
              analysis as verified.
            </div>
          )}
          <div className="mt-4 grid gap-4 sm:grid-cols-3">
            <EvidenceList label="Required checks" values={verification?.required_checks} />
            <EvidenceList label="Completed checks" values={verification?.completed_checks} />
            <EvidenceList label="Missing checks" values={verification?.missing_checks} />
          </div>
          <div className="mt-4 grid gap-2 text-sm sm:grid-cols-3">
            <div>Tests: {verification?.test_execution_result ?? "Unknown / not available"}</div>
            <div>Static analysis: {verification?.static_analysis_result ?? "Unknown / not available"}</div>
            <div>Selection: {verification?.relevant_test_selection ?? "Unknown / not available"}</div>
          </div>
          {verification?.reasons && verification.reasons.length > 0 && (
            <EvidenceList label="Verification reasons" values={verification.reasons} />
          )}
          {verification?.command_results && verification.command_results.length > 0 && (
            <div className="mt-4 space-y-2">
              <div className="text-xs uppercase text-muted-foreground">Verification commands</div>
              {verification.command_results.map((command, index) => {
                const output = command.stderr || command.stdout || command.reason
                return (
                  <div key={`${command.check}-${index}`} className="rounded-lg border p-3 text-sm">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-medium">{command.check ?? "Unknown check"}</span>
                      <Badge className="border">{command.status ?? "UNKNOWN"}</Badge>
                      {command.exit_code !== null && <span>exit {command.exit_code}</span>}
                      {command.duration_ms !== null && <span>{command.duration_ms} ms</span>}
                    </div>
                    {output && <pre className="mt-2 max-h-24 overflow-auto whitespace-pre-wrap text-xs text-muted-foreground">{output}</pre>}
                  </div>
                )
              })}
            </div>
          )}
        </section>

        <section aria-labelledby={`behavioral-${prNumber}`}>
          <h3 id={`behavioral-${prNumber}`} className="mb-2 text-sm font-semibold">
            Behavioral comparison
          </h3>
          {verification?.behavioral === null || verification?.behavioral === undefined ? (
            <p className="text-sm text-muted-foreground">
              Not available — no base-vs-target behavioral comparison was produced for this
              analysis.
            </p>
          ) : (
            <>
              <div className="flex flex-wrap items-center gap-2">
                <Badge
                  className={`border ${behavioralStatusClassName(
                    verification.behavioral.comparison_status,
                  )}`}
                >
                  {behavioralStatusLabel(verification.behavioral.comparison_status)}
                </Badge>
                <span className="text-xs text-muted-foreground">
                  base revision vs target revision, per selected test node
                </span>
              </div>
              {verification.behavioral.regressions === null ||
              verification.behavioral.regressions === undefined ? (
                <p className="mt-3 text-sm text-muted-foreground">
                  Per-node regression detail is not available.
                </p>
              ) : verification.behavioral.regressions.length === 0 ? (
                <p className="mt-3 text-sm text-muted-foreground">
                  No test node that passed on the base revision failed or timed out on the
                  target revision.
                </p>
              ) : (
                <ul className="mt-3 space-y-2">
                  {verification.behavioral.regressions.map((row, index) => (
                    <li
                      key={`${row.test_node_id ?? row.test_file ?? "node"}-${index}`}
                      className="rounded-lg border border-red-300 bg-red-50 p-3 text-sm"
                    >
                      <div className="font-mono text-xs break-all text-red-900">
                        {row.test_node_id ?? row.test_file ?? "Unknown test node"}
                      </div>
                      <div className="mt-1 flex flex-wrap items-center gap-2">
                        <Badge className="border">
                          {(row.baseline_status ?? "unknown")} → {(row.target_status ?? "unknown")}
                        </Badge>
                        {row.comparison_status && (
                          <span className="text-xs text-red-900">{row.comparison_status}</span>
                        )}
                        {row.timeout_attribution && (
                          <span className="font-mono text-xs text-muted-foreground">
                            {row.timeout_attribution}
                          </span>
                        )}
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </>
          )}
        </section>

        <section aria-labelledby={`regression-${prNumber}`}>
          <h3 id={`regression-${prNumber}`} className="mb-2 text-sm font-semibold">
            Regression Evidence
          </h3>
          <div className="grid gap-4 sm:grid-cols-3">
            <EvidenceList label="New findings" values={regression?.new_findings} />
            <EvidenceList label="Unchanged findings" values={regression?.unchanged_findings} />
            <EvidenceList label="Resolved findings" values={regression?.resolved_findings} />
          </div>
          {regression?.attribution_summary && regression.attribution_summary.total > 0 && (
            <div className="mt-4 rounded-lg border p-4 space-y-3" data-testid="attribution-summary">
              <div className="text-xs uppercase tracking-wide text-muted-foreground">
                Target-only finding attribution
              </div>
              <div className="text-sm">
                {regression.attribution_summary.total} target-only finding(s)
              </div>
              {regression.attribution_summary.change_related_count > 0 && (
                <div>
                  <div className="text-xs font-medium text-muted-foreground mb-1">
                    Related to change:
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(regression.attribution_summary.by_attribution)
                      .filter(([cat]) =>
                        ["DIRECT_CHANGE", "CHANGED_FILE", "CALLER_IMPACT", "DOWNSTREAM_IMPACT"].includes(cat)
                      )
                      .map(([cat, count]) => (
                        <Badge key={cat} className="border">
                          {count} {cat}
                        </Badge>
                      ))}
                  </div>
                </div>
              )}
              {regression.attribution_summary.outside_count > 0 && (
                <div>
                  <div className="text-xs font-medium text-muted-foreground mb-1">
                    Outside known impact:
                  </div>
                  <Badge className="border">
                    {regression.attribution_summary.outside_count} OUTSIDE_IMPACT
                  </Badge>
                </div>
              )}
              {regression.attribution_summary.unresolved_count > 0 && (
                <div>
                  <div className="text-xs font-medium text-muted-foreground mb-1">
                    Unresolved / unknown:
                  </div>
                  <Badge className="border">
                    {regression.attribution_summary.unresolved_count} unresolved
                  </Badge>
                </div>
              )}
            </div>
          )}
          {regression?.new_findings_attribution && regression.new_findings_attribution.length > 0 && (
            <div className="mt-4 space-y-2">
              <div className="text-xs uppercase text-muted-foreground">Finding attribution detail</div>
              {regression.new_findings_attribution.map((item, index) => (
                <div key={`${item.finding}-${index}`} className="rounded-lg border p-3 text-sm">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge className="border">{item.attribution}</Badge>
                    {item.file_path && <span className="font-mono text-xs">{item.file_path}</span>}
                    {item.symbol && <span className="font-mono text-xs">{item.symbol}</span>}
                  </div>
                  <div className="mt-1 text-xs text-muted-foreground">{item.relationship}</div>
                </div>
              ))}
            </div>
          )}
        </section>

        <section aria-labelledby={`baseline-${prNumber}`}>
          <h3 id={`baseline-${prNumber}`} className="mb-2 text-sm font-semibold">
            Baseline and Governance
          </h3>
          <dl className="grid gap-2 text-sm sm:grid-cols-2">
            <div><dt className="text-xs uppercase text-muted-foreground">Baseline status</dt><dd>{baseline?.status ?? "Unknown / not available"}</dd></div>
            <div><dt className="text-xs uppercase text-muted-foreground">Comparison status</dt><dd>{baseline?.comparison_status ?? "Unknown / not available"}</dd></div>
            <div><dt className="text-xs uppercase text-muted-foreground">Review requirement</dt><dd>{governance?.review_requirement ?? "Unknown / not available"}</dd></div>
            <div><dt className="text-xs uppercase text-muted-foreground">Approval state</dt><dd>{governance?.approval_state ?? "Unknown / not available"}</dd></div>
          </dl>
        </section>

        {caveats.length > 0 && (
          <section aria-labelledby={`caveats-${prNumber}`}>
            <h3 id={`caveats-${prNumber}`} className="mb-2 text-sm font-semibold">
              Caveats
            </h3>
            <ul className="list-disc space-y-1 pl-5 text-sm text-muted-foreground">
              {caveats.map((caveat) => (
                <li key={caveat}>{caveat}</li>
              ))}
            </ul>
          </section>
        )}

        <section aria-labelledby={`evidence-${prNumber}`}>
          <h3 id={`evidence-${prNumber}`} className="mb-2 text-sm font-semibold">
            Evidence
          </h3>
          <dl className="grid gap-2 text-sm sm:grid-cols-2">
            <div>
              <dt className="text-xs uppercase text-muted-foreground">Impact hash</dt>
              <dd className="font-mono" title={evidence?.impact_hash ?? undefined}>
                {shortHash(evidence?.impact_hash)}
              </dd>
            </div>
            <div>
              <dt className="text-xs uppercase text-muted-foreground">Risk hash</dt>
              <dd className="font-mono" title={evidence?.risk_hash ?? undefined}>
                {shortHash(evidence?.risk_hash)}
              </dd>
            </div>
            <div>
              <dt className="text-xs uppercase text-muted-foreground">Verification proof hash</dt>
              <dd className="font-mono" title={proof?.verification_hash ?? undefined}>
                {shortHash(proof?.verification_hash)}
              </dd>
            </div>
            <div>
              <dt className="text-xs uppercase text-muted-foreground">Base revision</dt>
              <dd className="font-mono">{shortHash(impact?.base_revision, 8)}</dd>
            </div>
            <div>
              <dt className="text-xs uppercase text-muted-foreground">Target revision</dt>
              <dd className="font-mono">{shortHash(impact?.target_revision, 8)}</dd>
            </div>
          </dl>
          <p className="mt-3 text-xs text-muted-foreground">
            Derived deterministically from the diff, the code graph, and already-reported
            reliability findings. Re-running on the same revisions reproduces these hashes.
            This describes what the change touches, not a prediction of production impact.
          </p>
        </section>
      </CardContent>
    </Card>
  );
}

export default ChangeRiskCard;
