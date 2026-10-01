/**
 * Data layer for PR analyses and Change Risk.
 *
 * Everything decidable — which URL is requested, what happens on a non-ok
 * response, how a risk level or factor is presented — lives here so it is
 * testable without a browser. The page and card keep the JSX.
 *
 * Covered by frontend/tests/prAnalyses.test.ts.
 */

import { apiUrl } from './api'

export type RiskLevel = 'none' | 'low' | 'medium' | 'high' | 'critical'

export type Recommendation =
  | 'no_review_required'
  | 'review_recommended'
  | 'requires_human_review'

export interface ChangedSymbol {
  node_id: string
  node_type: string | null
  file_path: string | null
  name: string | null
  change_kind: string | null
}

export interface RiskFactor {
  kind: string
  level: RiskLevel | string
  detail: string
  evidence: string[]
}

export interface ReviewTarget {
  kind: string
  location: string
  detail: string
}

export interface FindingImpact {
  finding_ref: string
  file_path: string
  line_range: string
  severity: string
  relation: string
  resolved_node_id: string
  overlapping_symbol_count: number
  reason: string
}

export interface UnresolvedReference {
  file_path: string | null
  detail: string | null
  reason: string | null
}

export interface VerificationCommandSummary {
  check: string | null
  command: string[] | null
  status: string | null
  exit_code: number | null
  duration_ms: number | null
  reason: string | null
  stdout: string
  stderr: string
}

export interface ChangeDecision {
  risk_level: RiskLevel | string | null
  score: number | null
  confidence: string | null
  reasons: string[]
  human_review_required: boolean | null
  affected_files: string[]
  affected_symbols: string[]
  caller_count: number | null
  downstream_count: number | null
  change_relationships: string[]
}

export interface BehavioralRegressionRow {
  test_file: string | null
  test_node_id: string | null
  baseline_status: string | null
  target_status: string | null
  comparison_status: string | null
  timeout_attribution: string | null
  timeout_attribution_source: string | null
  selection_provenance: string | null
}

export interface BehavioralRecord {
  comparison_status: string | null
  regressions: BehavioralRegressionRow[] | null
}

export interface ProofIntegrityRecord {
  status: 'INTEGRITY_VERIFIED' | 'INTEGRITY_MISMATCH' | 'INTEGRITY_UNAVAILABLE' | string
  reason: string | null
  expected_hash: string | null
  actual_hash: string | null
}

export interface VerificationRecord {
  state: 'verified' | 'partially_verified' | 'unverified' | 'blocked' | string | null
  confidence: string | null
  required_checks: string[]
  completed_checks: string[]
  missing_checks: string[]
  tests_discovered: string[] | null
  tests_executed: string[] | null
  test_execution_result: string | null
  static_analysis_executed: boolean | null
  static_analysis_result: string | null
  command_results: VerificationCommandSummary[] | null
  relevant_test_selection: string | null
  reasons: string[]
  behavioral?: BehavioralRecord | null
  proof_integrity?: ProofIntegrityRecord | null
}

export interface BaselineRecord {
  base_revision: string | null
  status: string | null
  comparison_status: string | null
  error: string | null
  findings_before: string[] | null
}

export interface AttributionSummary {
  total: number
  by_attribution: Record<string, number>
  change_related_count: number
  outside_count: number
  unresolved_count: number
}

export interface RegressionRecord {
  new_findings: string[] | null
  new_findings_attribution: Array<{
    finding: string
    attribution: string
    file_path: string | null
    symbol: string | null
    relationship: string
  }> | null
  attribution_summary: AttributionSummary | null
  unchanged_findings: string[] | null
  resolved_findings: string[] | null
}

export interface ProofRecord {
  verification_hash: string | null
  risk_hash: string | null
  impact_hash: string | null
  base_revision: string | null
  target_revision: string | null
}

export interface GovernanceRecord {
  review_requirement: string | null
  acknowledgement_required: boolean | null
  acknowledged: boolean | null
  approval_state: string | null
  rejection_state: string | null
  application_state: string | null
}

export interface ChangeRisk {
  available: boolean
  unavailable_reason: string | null
  risk: {
    level: RiskLevel | string | null
    recommendation: Recommendation | string | null
    recommendation_label: string | null
    confidence: string | null
    summary: string | null
  } | null
  impact: {
    repository: string | null
    base_revision: string | null
    target_revision: string | null
    changed_file_count: number
    changed_symbol_count: number
    blast_radius_size: number
    changed_files: string[]
    changed_symbols: ChangedSymbol[]
    affected_callers: string[]
    downstream_symbols: string[]
    affected_entrypoints: string[]
    affected_api_surfaces: string[]
    unresolved_references: UnresolvedReference[]
  } | null
  findings: {
    evaluated: number
    inside_radius: number
    outside_radius: number
    unresolved: number
  } | null
  risk_factors: RiskFactor[]
  review_targets: ReviewTarget[]
  finding_impacts: FindingImpact[]
  caveats: string[]
  evidence: { impact_hash: string | null; risk_hash: string | null } | null
  decision: ChangeDecision | null
  verification: VerificationRecord | null
  baseline: BaselineRecord | null
  regression: RegressionRecord | null
  proof: ProofRecord | null
  governance: GovernanceRecord | null
}

export interface PRAnalysisSummary {
  id: number
  repository: string
  pr_number: number
  head_sha: string
  base_branch: string | null
  status: string | null
  reliability_score: string | null
  critical_risks_count: number
  high_risks_count: number
  medium_risks_count: number
  fix_candidates_count: number
  comment_posted: boolean
  status_check_posted: boolean
  status_check_conclusion: string | null
  change_risk_level: string | null
  change_risk_recommendation: string | null
  change_risk_hash: string | null
  change_risk_available: boolean
  ledger_run_id: string | null
  created_at: string | null
  completed_at: string | null
}

export interface PRAnalysisListResponse {
  analyses: PRAnalysisSummary[]
  count: number
  repositories: string[]
}

export interface PRAnalysisDetail extends PRAnalysisSummary {
  change_risk: ChangeRisk
  change_risk_base_revision: string | null
  change_risk_error: string | null
  analysis_error: string | null
}

async function getJson<T>(path: string, what: string): Promise<T> {
  const response = await fetch(apiUrl(path))
  if (!response.ok) {
    throw new Error(`Failed to load ${what} (${response.status})`)
  }
  return response.json()
}

export function prAnalysesPath(repository?: string, limit = 25): string {
  const params = new URLSearchParams()
  if (repository) params.set('repository', repository)
  params.set('limit', String(limit))
  return `/api/github/pr-analyses?${params.toString()}`
}

export function prAnalysisPath(id: number): string {
  return `/api/github/pr-analyses/${id}`
}

export async function fetchPRAnalyses(
  repository?: string,
  limit = 25,
): Promise<PRAnalysisListResponse> {
  return getJson<PRAnalysisListResponse>(
    prAnalysesPath(repository, limit),
    'PR analyses',
  )
}

export async function fetchPRAnalysis(id: number): Promise<PRAnalysisDetail> {
  return getJson<PRAnalysisDetail>(prAnalysisPath(id), `PR analysis ${id}`)
}

const RISK_STYLES: Record<string, string> = {
  none: 'bg-slate-100 text-slate-700 border-slate-300',
  low: 'bg-emerald-100 text-emerald-800 border-emerald-300',
  medium: 'bg-amber-100 text-amber-900 border-amber-300',
  high: 'bg-orange-100 text-orange-900 border-orange-300',
  critical: 'bg-red-100 text-red-900 border-red-300',
}

export function riskLevelClassName(level: string | null | undefined): string {
  if (!level) return 'bg-slate-100 text-slate-600 border-slate-300'
  return RISK_STYLES[level.toLowerCase()] ?? RISK_STYLES.medium
}

export function riskLevelLabel(level: string | null | undefined): string {
  return level ? level.toUpperCase() : 'NOT ASSESSED'
}

const VERIFICATION_STATE_STYLES: Record<string, string> = {
  verified: 'bg-emerald-100 text-emerald-800 border-emerald-300',
  partially_verified: 'bg-amber-100 text-amber-900 border-amber-300',
  unverified: 'bg-slate-100 text-slate-700 border-slate-300',
  blocked: 'bg-red-100 text-red-900 border-red-300',
}

export function verificationStateClassName(state: string | null | undefined): string {
  if (!state) return 'bg-slate-100 text-slate-600 border-slate-300 border-dashed'
  return (
    VERIFICATION_STATE_STYLES[state.toLowerCase()] ??
    'bg-slate-100 text-slate-600 border-slate-300 border-dashed'
  )
}

export function verificationStateLabel(state: string | null | undefined): string {
  return state ? state.toUpperCase() : 'UNKNOWN'
}

const BEHAVIORAL_STATUS_LABELS: Record<string, string> = {
  REGRESSIONS_FOUND: 'Regressions found',
  NO_REGRESSIONS: 'No regressions',
  UNKNOWN: 'Inconclusive',
}

export function behavioralStatusLabel(status: string | null | undefined): string {
  if (!status) return 'Not available'
  return BEHAVIORAL_STATUS_LABELS[status] ?? status
}

const BEHAVIORAL_STATUS_STYLES: Record<string, string> = {
  REGRESSIONS_FOUND: 'bg-red-100 text-red-900 border-red-300',
  NO_REGRESSIONS: 'bg-emerald-100 text-emerald-800 border-emerald-300',
  UNKNOWN: 'bg-slate-100 text-slate-700 border-slate-300',
}

export function behavioralStatusClassName(status: string | null | undefined): string {
  if (!status) return 'bg-slate-100 text-slate-600 border-slate-300 border-dashed'
  return (
    BEHAVIORAL_STATUS_STYLES[status] ??
    'bg-slate-100 text-slate-600 border-slate-300 border-dashed'
  )
}

const PROOF_INTEGRITY_LABELS: Record<string, string> = {
  INTEGRITY_VERIFIED: 'Proof integrity verified',
  INTEGRITY_MISMATCH: 'Proof integrity MISMATCH',
  INTEGRITY_UNAVAILABLE: 'Proof integrity not checkable',
}

export function proofIntegrityLabel(status: string | null | undefined): string {
  if (!status) return 'Proof integrity not checkable'
  return PROOF_INTEGRITY_LABELS[status] ?? status
}

const PROOF_INTEGRITY_STYLES: Record<string, string> = {
  INTEGRITY_VERIFIED: 'bg-emerald-100 text-emerald-800 border-emerald-300',
  INTEGRITY_MISMATCH: 'bg-red-100 text-red-900 border-red-300',
  INTEGRITY_UNAVAILABLE: 'bg-slate-100 text-slate-700 border-slate-300 border-dashed',
}

export function proofIntegrityClassName(status: string | null | undefined): string {
  if (!status) return 'bg-slate-100 text-slate-600 border-slate-300 border-dashed'
  return (
    PROOF_INTEGRITY_STYLES[status] ??
    'bg-slate-100 text-slate-600 border-slate-300 border-dashed'
  )
}

const RECOMMENDATION_LABELS: Record<string, string> = {
  no_review_required: 'No review required',
  review_recommended: 'Review recommended',
  requires_human_review: 'Human review required',
}

export function recommendationLabel(
  recommendation: string | null | undefined,
): string {
  if (!recommendation) return 'No recommendation'
  return RECOMMENDATION_LABELS[recommendation] ?? recommendation
}

export function requiresHumanReview(
  recommendation: string | null | undefined,
): boolean {
  return recommendation === 'requires_human_review'
}

export function factorSummary(factor: RiskFactor): string {
  return factor.detail || factor.kind
}

/**
 * Ordered call path from an entry point down to the changed symbol.
 *
 * Built only from data the report already carries: the entry points, the
 * downstream and caller symbols, and the changed symbols. The graph also holds
 * file and class nodes that contain those symbols rather than calling them, so
 * containers are dropped — a node is a container when another node in the set
 * begins with it. An empty array means the report does not evidence a path.
 */
export function affectedPath(impact: ChangeRisk['impact']): string[] {
  if (!impact) return []
  const changed = impact.changed_symbols.map((s) => s.node_id).filter(Boolean)
  if (changed.length === 0) return []

  const entrypoints = impact.affected_entrypoints
  const callers = impact.affected_callers.filter(
    (c) => !changed.includes(c) && !entrypoints.includes(c),
  )
  const downstream = impact.downstream_symbols.filter(
    (s) =>
      !changed.includes(s) &&
      !callers.includes(s) &&
      !entrypoints.includes(s) &&
      s.includes('::'),
  )

  const ordered = Array.from(new Set([...entrypoints, ...downstream, ...callers, ...changed]))
  return ordered.filter(
    (node) => !ordered.some((other) => other !== node && other.startsWith(node)),
  )
}

export function shortHash(hash: string | null | undefined, length = 12): string {
  if (!hash) return '—'
  return hash.length <= length ? hash : `${hash.slice(0, length)}…`
}
