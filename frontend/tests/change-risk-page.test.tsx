// @vitest-environment jsdom
/**
 * Change Risk rendered through the real integrations page.
 *
 * Renders the shipping component. Only global.fetch is substituted — the tab
 * navigation, the effects, the loading/error/empty branches, the Retry buttons
 * and the repository filter are all the real code.
 *
 * tests/prAnalyses.test.ts covers the data layer; this file covers what a user
 * sees. Every payload here matches the backend DTO asserted in
 * backend/tests/test_pr_change_risk_integration.py.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'

import IntegrationsPage from '@/app/integrations/page'
import type { BehavioralRecord, ChangeRisk, ProofIntegrityRecord } from '@/lib/prAnalyses'

const BASE_SHA = 'b'.repeat(40)
const HEAD_SHA = '3e36ac6b1d33fbec851347622e9ba5d9f55efd49'

function summary(overrides: Record<string, unknown> = {}) {
  return {
    id: 1,
    repository: 'acme/payments',
    pr_number: 481,
    head_sha: HEAD_SHA,
    base_branch: 'main',
    status: 'completed',
    reliability_score: 'concerning',
    critical_risks_count: 1,
    high_risks_count: 0,
    medium_risks_count: 0,
    fix_candidates_count: 2,
    comment_posted: true,
    status_check_posted: true,
    status_check_conclusion: 'failure',
    change_risk_level: 'critical',
    change_risk_recommendation: 'requires_human_review',
    change_risk_hash: 'r'.repeat(64),
    change_risk_available: true,
    ledger_run_id: 'pr-acme-payments-481-3e36ac6',
    created_at: '2026-08-20T10:00:00Z',
    completed_at: '2026-08-20T10:02:00Z',
    ...overrides,
  }
}

function changeRisk(level: string, recommendation: string) {
  return {
    available: true,
    unavailable_reason: null,
    risk: {
      level,
      recommendation,
      recommendation_label:
        recommendation === 'requires_human_review'
          ? 'Human review required'
          : recommendation === 'review_recommended'
            ? 'Review recommended'
            : 'No review required',
      confidence: 'high',
      summary: `${level.toUpperCase()} risk: 1 changed symbol(s), 6 symbol(s) in the blast radius.`,
    },
    impact: {
      repository: 'acme/payments',
      base_revision: BASE_SHA,
      target_revision: HEAD_SHA,
      changed_file_count: 1,
      changed_symbol_count: 1,
      blast_radius_size: 6,
      changed_files: ['payments.py'],
      changed_symbols: [
        {
          node_id: 'payments.py::PaymentService.authorize',
          node_type: 'method',
          file_path: 'payments.py',
          name: 'authorize',
          change_kind: 'modified',
        },
      ],
      affected_callers: ['api.py::create_payment'],
      downstream_symbols: ['transactions.py::TransactionService.commit'],
      affected_entrypoints: ['api.py::create_payment'],
      affected_api_surfaces: ['create_payment (app.post)'],
      unresolved_references: [],
    },
    findings: { evaluated: 3, inside_radius: 2, outside_radius: 1, unresolved: 0 },
    risk_factors: [
      {
        kind: 'reliability_finding_in_blast_radius',
        level,
        detail: `1 ${level}-severity reliability finding(s) resolve to symbols inside the affected area`,
        evidence: ['payments.py:9-12 -> payments.py::PaymentService.authorize (direct)'],
      },
      {
        kind: 'entrypoint_reachable',
        level: 'medium',
        detail: '1 API entry point(s) reach the changed code',
        evidence: ['create_payment (app.post)'],
      },
    ],
    review_targets: [],
    finding_impacts: [
      {
        finding_ref: 'abc123',
        file_path: 'payments.py',
        line_range: '9-12',
        severity: level,
        relation: 'direct',
        resolved_node_id: 'payments.py::PaymentService.authorize',
        overlapping_symbol_count: 2,
        reason: '',
      },
    ],
    caveats: ['1 reliability finding location(s) resolved outside the blast radius.'],
    evidence: { impact_hash: 'i'.repeat(64), risk_hash: 'r'.repeat(64) },
    decision: {
      risk_level: level,
      score: level === 'critical' ? 100 : 75,
      confidence: 'high',
      reasons: ['A direct finding affects a changed symbol.'],
      human_review_required: recommendation === 'requires_human_review',
      affected_files: ['payments.py'],
      affected_symbols: ['payments.py::PaymentService.authorize'],
      caller_count: 1,
      downstream_count: 1,
      change_relationships: ['direct', 'caller'],
    },
    verification: {
      state: 'partially_verified',
      confidence: 'medium',
      required_checks: ['static_analysis_execution', 'test_execution'],
      completed_checks: ['static_analysis_execution'],
      missing_checks: ['test_execution'],
      tests_discovered: null,
      tests_executed: null,
      test_execution_result: null,
      static_analysis_executed: true,
      static_analysis_result: 'passed',
      command_results: [
        {
          check: 'ruff',
          command: ['python', '-m', 'ruff'],
          status: 'FAILED',
          exit_code: 1,
          duration_ms: 12,
          reason: null,
          stdout: '',
          stderr: 'E402: module level import not at top of file',
        },
      ],
      relevant_test_selection: 'unavailable',
      reasons: ['Static analysis failed.', 'Tests were not executed.'],
      behavioral: null as BehavioralRecord | null,
      proof_integrity: null as ProofIntegrityRecord | null,
    },
    baseline: {
      base_revision: BASE_SHA,
      status: 'COMPLETED',
      comparison_status: 'COMPLETED',
      error: null,
      findings_before: ['before-finding'],
    },
    regression: {
      new_findings: [] as string[],
      new_findings_attribution: [] as Array<{
        finding: string
        attribution: string
        file_path: string | null
        symbol: string | null
        relationship: string
      }>,
      attribution_summary: {
        total: 0,
        by_attribution: {},
        change_related_count: 0,
        outside_count: 0,
        unresolved_count: 0,
      },
      unchanged_findings: ['before-finding'],
      resolved_findings: ['resolved-finding'],
    },
    proof: {
      verification_hash: 'v'.repeat(64),
      risk_hash: 'r'.repeat(64),
      impact_hash: 'i'.repeat(64),
      base_revision: BASE_SHA,
      target_revision: HEAD_SHA,
    },
    governance: {
      review_requirement: 'explicit_approval_required',
      acknowledgement_required: true,
      acknowledged: null,
      approval_state: null,
      rejection_state: null,
      application_state: null,
    },
  }
}

function detail(level: string, recommendation: string, overrides: Record<string, unknown> = {}) {
  return {
    ...summary({ change_risk_level: level, change_risk_recommendation: recommendation }),
    change_risk: changeRisk(level, recommendation),
    change_risk_base_revision: BASE_SHA,
    change_risk_error: null,
    analysis_error: null,
    ...overrides,
  }
}

interface RouteMap {
  list?: unknown
  listOk?: boolean
  detail?: unknown
  detailOk?: boolean
}

function mockRoutes({ list, listOk = true, detail: detailBody, detailOk = true }: RouteMap) {
  global.fetch = vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input)
    if (url.includes('/api/installations')) {
      return { ok: true, status: 200, json: async () => ({ installations: [] }) }
    }
    if (url.includes('/api/github/webhook-events')) {
      return { ok: true, status: 200, json: async () => ({ events: [] }) }
    }
    if (url.match(/\/api\/github\/pr-analyses\/\d+$/)) {
      return { ok: detailOk, status: detailOk ? 200 : 500, json: async () => detailBody }
    }
    if (url.includes('/api/github/pr-analyses')) {
      return { ok: listOk, status: listOk ? 200 : 503, json: async () => list }
    }
    throw new Error(`Unexpected fetch: ${url}`)
  }) as unknown as typeof fetch
}

async function openRiskTab() {
  render(<IntegrationsPage />)
  await waitFor(() => expect(screen.getByText('GitHub Integrations')).toBeTruthy())
  fireEvent.click(screen.getByRole('button', { name: 'Change Risk' }))
}

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
})

describe('Change Risk tab', () => {
  it('renders a CRITICAL assessment with its recommendation and reasoning', async () => {
    mockRoutes({
      list: { analyses: [summary()], count: 1, repositories: ['acme/payments'] },
      detail: detail('critical', 'requires_human_review'),
    })

    await openRiskTab()

    await waitFor(() => expect(screen.getAllByText('CRITICAL').length).toBeGreaterThan(0))
    expect(screen.getAllByText('Human review required').length).toBeGreaterThan(0)
    expect(screen.getByText('Why?')).toBeTruthy()
    expect(
      screen.getByText(/1 critical-severity reliability finding\(s\)/),
    ).toBeTruthy()
    expect(screen.getByText('1 API entry point(s) reach the changed code')).toBeTruthy()
  })

  it('shows blast radius counts from the report', async () => {
    mockRoutes({
      list: { analyses: [summary()], count: 1, repositories: ['acme/payments'] },
      detail: detail('critical', 'requires_human_review'),
    })

    await openRiskTab()
    await waitFor(() => expect(screen.getByText('Blast radius')).toBeTruthy())

    const section = screen.getByText('Blast radius').closest('section')!
    expect(within(section).getByText('6')).toBeTruthy()
    expect(within(section).getAllByText('1').length).toBeGreaterThan(0)
  })

  it('renders the affected path from entry point to changed symbol', async () => {
    mockRoutes({
      list: { analyses: [summary()], count: 1, repositories: ['acme/payments'] },
      detail: detail('critical', 'requires_human_review'),
    })

    await openRiskTab()
    await waitFor(() => expect(screen.getByText('Affected path')).toBeTruthy())

    const section = screen.getByText('Affected path').closest('section')!
    const steps = within(section)
      .getAllByRole('listitem')
      .map((li) => li.textContent?.trim())
    expect(steps).toEqual([
      'api.py::create_payment',
      'transactions.py::TransactionService.commit',
      'payments.py::PaymentService.authorize',
    ])
  })

  it('renders the deterministic evidence hashes', async () => {
    mockRoutes({
      list: { analyses: [summary()], count: 1, repositories: ['acme/payments'] },
      detail: detail('critical', 'requires_human_review'),
    })

    await openRiskTab()
    await waitFor(() => expect(screen.getByText('Evidence')).toBeTruthy())

    const section = screen.getByText('Evidence').closest('section')!
    expect(within(section).getByText('iiiiiiiiiiii…')).toBeTruthy()
    expect(within(section).getByText('rrrrrrrrrrrr…')).toBeTruthy()
    expect(
      within(section).getByText(/not a prediction of production impact/),
    ).toBeTruthy()
  })

  it('renders the complete decision, verification, regression, baseline, and governance evidence', async () => {
    mockRoutes({
      list: { analyses: [summary()], count: 1, repositories: ['acme/payments'] },
      detail: detail('critical', 'requires_human_review'),
    })

    await openRiskTab()

    await waitFor(() => expect(screen.getByText('Change Decision')).toBeTruthy())
    expect(screen.getByText('100')).toBeTruthy()
    expect(screen.getByText('Verification')).toBeTruthy()
    expect(screen.getByText('PARTIALLY_VERIFIED')).toBeTruthy()
    expect(screen.getAllByText('static_analysis_execution')).toHaveLength(2)
    expect(screen.getAllByText('test_execution')).toHaveLength(2)
    expect(screen.getByText('Regression Evidence')).toBeTruthy()
    expect(screen.getByText('resolved-finding')).toBeTruthy()
    expect(screen.getByText('Baseline and Governance')).toBeTruthy()
    expect(screen.getAllByText('COMPLETED')).toHaveLength(2)
    expect(screen.getByText('explicit_approval_required')).toBeTruthy()
    expect(screen.getByText('Verification proof hash')).toBeTruthy()
    expect(screen.getByText('Verification reasons')).toBeTruthy()
    expect(screen.getByText('Verification commands')).toBeTruthy()
    expect(screen.getByText('E402: module level import not at top of file')).toBeTruthy()
  })

  it('renders target-only finding attribution without claiming causality', async () => {
    const body = detail('medium', 'review_recommended')
    body.change_risk.regression.new_findings = ['finding-1', 'finding-2', 'finding-3']
    body.change_risk.regression.new_findings_attribution = [
      {
        finding: 'finding-1',
        attribution: 'OUTSIDE_IMPACT',
        file_path: 'docs/conf.py',
        symbol: null,
        relationship: 'outside changed files and known impact relationships',
      },
      {
        finding: 'finding-2',
        attribution: 'DIRECT_CHANGE',
        file_path: 'payments.py',
        symbol: 'authorize',
        relationship: 'changed symbol',
      },
      {
        finding: 'finding-3',
        attribution: 'CALLER_IMPACT',
        file_path: 'api.py',
        symbol: 'create_payment',
        relationship: 'caller of changed symbol',
      },
    ]
    body.change_risk.regression.attribution_summary = {
      total: 3,
      by_attribution: {
        DIRECT_CHANGE: 1,
        CALLER_IMPACT: 1,
        OUTSIDE_IMPACT: 1,
      },
      change_related_count: 2,
      outside_count: 1,
      unresolved_count: 0,
    }

    mockRoutes({
      list: { analyses: [summary({ change_risk_level: 'medium' })], count: 1, repositories: ['acme/payments'] },
      detail: body,
    })

    await openRiskTab()

    await waitFor(() => expect(screen.getByText('Target-only finding attribution')).toBeTruthy())
    expect(screen.getByText('3 target-only finding(s)')).toBeTruthy()
    expect(screen.getByText('Related to change:')).toBeTruthy()
    expect(screen.getByText('1 DIRECT_CHANGE')).toBeTruthy()
    expect(screen.getByText('1 CALLER_IMPACT')).toBeTruthy()
    expect(screen.getByText('Outside known impact:')).toBeTruthy()
    expect(screen.getByText('1 OUTSIDE_IMPACT')).toBeTruthy()

    expect(screen.getByText(/outside changed files and known impact relationships/)).toBeTruthy()
    expect(screen.queryByText(/caused by change/i)).toBeNull()
  })

  it('explains unresolved impact without presenting it as a clean change', async () => {
    const body = detail('medium', 'review_recommended')
    body.change_risk.impact.changed_symbols = []
    const impact = body.change_risk.impact as ChangeRisk['impact']
    if (!impact) throw new Error('expected impact evidence')
    impact.unresolved_references = [{
      file_path: 'src/flask/views.py',
      detail: 'lines 12-12',
      reason: 'changed range does not fall inside any known symbol (likely module-level code)',
    }]
    mockRoutes({
      list: { analyses: [summary({ change_risk_level: 'medium' })], count: 1, repositories: ['acme/payments'] },
      detail: body,
    })

    await openRiskTab()

    await waitFor(() => expect(screen.getByText('Impact Evidence')).toBeTruthy())
    expect(screen.getByText(/No changed symbol was resolved/)).toBeTruthy()
    expect(screen.getByText(/src\/flask\/views\.py.*lines 12-12/)).toBeTruthy()
    expect(screen.getByText(/likely module-level code/)).toBeTruthy()
    expect(screen.getByText(/Caller or downstream reachability was not inferred/)).toBeTruthy()
  })

  it('renders a HIGH assessment as requiring human review', async () => {
    mockRoutes({
      list: {
        analyses: [summary({ change_risk_level: 'high' })],
        count: 1,
        repositories: ['acme/payments'],
      },
      detail: detail('high', 'requires_human_review'),
    })

    await openRiskTab()

    await waitFor(() => expect(screen.getAllByText('HIGH').length).toBeGreaterThan(0))
    expect(screen.getAllByText('Human review required').length).toBeGreaterThan(0)
    expect(screen.queryByText('CRITICAL')).toBeNull()
  })

  it('renders a LOW assessment as needing no review', async () => {
    mockRoutes({
      list: {
        analyses: [
          summary({
            change_risk_level: 'low',
            change_risk_recommendation: 'no_review_required',
          }),
        ],
        count: 1,
        repositories: ['acme/payments'],
      },
      detail: detail('low', 'no_review_required'),
    })

    await openRiskTab()

    await waitFor(() => expect(screen.getAllByText('LOW').length).toBeGreaterThan(0))
    expect(screen.getAllByText('No review required').length).toBeGreaterThan(0)
    expect(screen.queryByText('Human review required')).toBeNull()
  })

  it('reports why an assessment is unavailable instead of implying it is safe', async () => {
    mockRoutes({
      list: {
        analyses: [
          summary({
            change_risk_level: null,
            change_risk_recommendation: null,
            change_risk_available: false,
          }),
        ],
        count: 1,
        repositories: ['acme/payments'],
      },
      detail: {
        ...summary({ change_risk_level: null, change_risk_recommendation: null }),
        change_risk: {
          available: false,
          unavailable_reason: 'git diff failed: base revision not found',
          risk: null,
          impact: null,
          findings: null,
          risk_factors: [],
          review_targets: [],
          finding_impacts: [],
          caveats: [],
          evidence: null,
        },
        change_risk_base_revision: null,
        change_risk_error: 'git diff failed: base revision not found',
        analysis_error: null,
      },
    })

    await openRiskTab()

    await waitFor(() => expect(screen.getByText('Not assessed')).toBeTruthy())
    expect(screen.getByText(/base revision not found/)).toBeTruthy()
    expect(screen.getAllByText('NOT ASSESSED').length).toBeGreaterThan(0)
    expect(screen.queryByText('Why?')).toBeNull()
  })

  it('shows an empty state when no PR has been analysed', async () => {
    mockRoutes({ list: { analyses: [], count: 0, repositories: [] } })

    await openRiskTab()

    await waitFor(() => expect(screen.getByText('No PR analyses yet')).toBeTruthy())
    expect(screen.getByText(/will appear here/)).toBeTruthy()
  })

  it('shows an error state with a working Retry when the list request fails', async () => {
    mockRoutes({ list: {}, listOk: false })

    await openRiskTab()

    await waitFor(() => expect(screen.getByRole('alert')).toBeTruthy())
    expect(screen.getByText(/503/)).toBeTruthy()

    mockRoutes({
      list: { analyses: [summary()], count: 1, repositories: ['acme/payments'] },
      detail: detail('critical', 'requires_human_review'),
    })
    fireEvent.click(screen.getByRole('button', { name: 'Retry' }))

    await waitFor(() => expect(screen.queryByRole('alert')).toBeNull())
    expect(screen.getAllByText('CRITICAL').length).toBeGreaterThan(0)
  })

  it('shows an error state when the detail request fails while the list succeeds', async () => {
    mockRoutes({
      list: { analyses: [summary()], count: 1, repositories: ['acme/payments'] },
      detail: {},
      detailOk: false,
    })

    await openRiskTab()

    await waitFor(() => expect(screen.getByRole('alert')).toBeTruthy())
    expect(screen.getByText(/PR analysis 1/)).toBeTruthy()
    expect(screen.getByText('acme/payments #481')).toBeTruthy()
  })

  it('filters by repository through the select', async () => {
    mockRoutes({
      list: { analyses: [summary()], count: 1, repositories: ['acme/payments', 'acme/web'] },
      detail: detail('critical', 'requires_human_review'),
    })

    await openRiskTab()
    await waitFor(() => expect(screen.getByLabelText('Repository')).toBeTruthy())

    fireEvent.change(screen.getByLabelText('Repository'), {
      target: { value: 'acme/web' },
    })

    await waitFor(() => {
      const calls = (global.fetch as unknown as { mock: { calls: unknown[][] } }).mock.calls
      expect(
        calls.some((call) => String(call[0]).includes('repository=acme%2Fweb')),
      ).toBe(true)
    })
  })

  it('labels the risk badge for assistive technology', async () => {
    mockRoutes({
      list: { analyses: [summary()], count: 1, repositories: ['acme/payments'] },
      detail: detail('critical', 'requires_human_review'),
    })

    await openRiskTab()

    await waitFor(() =>
      expect(screen.getByLabelText('Change risk level CRITICAL')).toBeTruthy(),
    )
  })

  it('renders VERIFIED with a distinct verification badge', async () => {
    const body = detail('low', 'no_review_required')
    body.change_risk.verification.state = 'verified'
    body.change_risk.verification.confidence = 'high'
    mockRoutes({
      list: {
        analyses: [summary({ change_risk_level: 'low' })],
        count: 1,
        repositories: ['acme/payments'],
      },
      detail: body,
    })

    await openRiskTab()

    await waitFor(() =>
      expect(screen.getByLabelText('Verification state VERIFIED')).toBeTruthy(),
    )
    expect(screen.queryByLabelText('Verification state PARTIALLY_VERIFIED')).toBeNull()
  })

  it('renders UNVERIFIED without implying it passed', async () => {
    const body = detail('medium', 'review_recommended')
    body.change_risk.verification.state = 'unverified'
    mockRoutes({
      list: {
        analyses: [summary({ change_risk_level: 'medium' })],
        count: 1,
        repositories: ['acme/payments'],
      },
      detail: body,
    })

    await openRiskTab()

    await waitFor(() =>
      expect(screen.getByLabelText('Verification state UNVERIFIED')).toBeTruthy(),
    )
  })

  it('renders BLOCKED as a distinct, non-passing state', async () => {
    const body = detail('critical', 'requires_human_review')
    body.change_risk.verification.state = 'blocked'
    mockRoutes({
      list: { analyses: [summary()], count: 1, repositories: ['acme/payments'] },
      detail: body,
    })

    await openRiskTab()

    await waitFor(() =>
      expect(screen.getByLabelText('Verification state BLOCKED')).toBeTruthy(),
    )
  })

  it('renders a behavioral regression as passed-to-failed evidence', async () => {
    const body = detail('critical', 'requires_human_review')
    body.change_risk.verification.behavioral = {
      comparison_status: 'REGRESSIONS_FOUND',
      regressions: [
        {
          test_file: 'tests/test_payments.py',
          test_node_id: 'tests/test_payments.py::test_authorize',
          baseline_status: 'passed',
          target_status: 'failed',
          comparison_status: 'REGRESSION',
          timeout_attribution: null,
          timeout_attribution_source: null,
          selection_provenance: 'deterministic_changed_test_files',
        },
      ],
    }
    mockRoutes({
      list: { analyses: [summary()], count: 1, repositories: ['acme/payments'] },
      detail: body,
    })

    await openRiskTab()

    await waitFor(() => expect(screen.getByText('Behavioral comparison')).toBeTruthy())
    expect(screen.getByText('Regressions found')).toBeTruthy()
    expect(screen.getByText('tests/test_payments.py::test_authorize')).toBeTruthy()
    expect(screen.getByText('passed → failed')).toBeTruthy()
  })

  it('renders a clean behavioral comparison without inventing a regression', async () => {
    const body = detail('low', 'no_review_required')
    body.change_risk.verification.behavioral = {
      comparison_status: 'NO_REGRESSIONS',
      regressions: [],
    }
    mockRoutes({
      list: {
        analyses: [summary({ change_risk_level: 'low' })],
        count: 1,
        repositories: ['acme/payments'],
      },
      detail: body,
    })

    await openRiskTab()

    await waitFor(() => expect(screen.getByText('Behavioral comparison')).toBeTruthy())
    expect(screen.getByText('No regressions')).toBeTruthy()
    expect(
      screen.getByText(/passed on the base revision failed or timed out/),
    ).toBeTruthy()
  })

  it('shows behavioral comparison as unavailable for an older response missing the field', async () => {
    mockRoutes({
      list: { analyses: [summary()], count: 1, repositories: ['acme/payments'] },
      detail: detail('critical', 'requires_human_review'),
    })

    await openRiskTab()

    await waitFor(() => expect(screen.getByText('Behavioral comparison')).toBeTruthy())
    expect(
      screen.getByText(/no base-vs-target behavioral comparison was produced/),
    ).toBeTruthy()
  })

  it('surfaces a proof-integrity mismatch as an integrity failure, not a verified result', async () => {
    const body = detail('critical', 'requires_human_review')
    body.change_risk.verification.proof_integrity = {
      status: 'INTEGRITY_MISMATCH',
      reason: 'persisted proof does not match the ledger-anchored hash',
      expected_hash: 'e'.repeat(64),
      actual_hash: 'a'.repeat(64),
    }
    mockRoutes({
      list: { analyses: [summary()], count: 1, repositories: ['acme/payments'] },
      detail: body,
    })

    await openRiskTab()

    await waitFor(() =>
      expect(screen.getByLabelText('Proof integrity INTEGRITY_MISMATCH')).toBeTruthy(),
    )
    expect(screen.getByRole('alert')).toBeTruthy()
    expect(screen.getByText(/do not treat this analysis as verified/)).toBeTruthy()
  })

  it('shows proof-integrity verified without altering the verification state', async () => {
    const body = detail('low', 'no_review_required')
    body.change_risk.verification.state = 'verified'
    body.change_risk.verification.proof_integrity = {
      status: 'INTEGRITY_VERIFIED',
      reason: null,
      expected_hash: 'v'.repeat(64),
      actual_hash: 'v'.repeat(64),
    }
    mockRoutes({
      list: {
        analyses: [summary({ change_risk_level: 'low' })],
        count: 1,
        repositories: ['acme/payments'],
      },
      detail: body,
    })

    await openRiskTab()

    await waitFor(() =>
      expect(screen.getByLabelText('Proof integrity INTEGRITY_VERIFIED')).toBeTruthy(),
    )
    expect(screen.queryByRole('alert')).toBeNull()
  })
})
