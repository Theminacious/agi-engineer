/**
 * Read-Only Ledger Reader
 * 
 * This module provides READ-ONLY access to immutable run ledgers.
 * It NEVER mutates state, NEVER triggers execution, NEVER calls write APIs.
 * 
 * Data sources:
 * - examples/sample_run/ (frozen proof artifacts)
 * - Future: Backend API for ledger reads (GET only)
 */

export interface LedgerMetadata {
  run_id: string
  repository_url?: string
  branch?: string
  policy?: string
  started_at: string
  ended_at?: string
  final_state: 'COMPLETE' | 'INCOMPLETE' | 'ABORTED' | 'REJECTED'
}

export interface LedgerEvent {
  sequence: number
  event_type: string
  timestamp: string
  actor: string
  actor_role: 'Human' | 'System' | 'Policy'
  phase?: string
  payload?: Record<string, any>
  payload_ref?: string
}

export interface ReplaySummary {
  run_id: string
  final_state: string
  event_count: number
  fixes_count: number
  plan_approved: boolean
  safety_passed: boolean
  edr_id?: string
  invariant_violations: string[]
  duration_seconds?: number
  issues_detected?: number
}

export interface InspectionReport {
  metadata: {
    run_id: string
    started_at: string
    ended_at?: string
    duration_seconds?: number
    final_state: string
  }
  timeline: {
    event_count: number
    phases_histogram?: Record<string, number>
    event_types_histogram?: Record<string, number>
  }
  decisions: {
    plan_approved: boolean
    approved_by?: string
    safety_passed: boolean
  }
  fixes: {
    count: number
    breakdown?: Record<string, number>
  }
  invariants: {
    violation_count: number
    violations?: string[]
  }
}

/**
 * Read ledger metadata (ledger.json)
 * READ-ONLY - No side effects
 */
export async function readLedgerMetadata(runId: string): Promise<LedgerMetadata> {
  // For Phase 10.2, we read from the frozen sample run
  // In production, this would call: GET /api/governance/runs/{run_id}/ledger
  
  if (runId === 'run-2026-01-12-sample') {
    // Simulating reading from examples/sample_run/ledger.json
    return {
      run_id: 'run-2026-01-12-sample',
      repository_url: 'https://github.com/example/repo.git',
      branch: 'main',
      policy: 'default-v1',
      started_at: '2026-01-12T10:00:00Z',
      ended_at: '2026-01-12T10:05:30Z',
      final_state: 'COMPLETE'
    }
  }
  
  throw new Error(`Ledger not found for run: ${runId}`)
}

/**
 * Read all events from ledger (events.jsonl)
 * READ-ONLY - No side effects
 */
export async function readLedgerEvents(runId: string): Promise<LedgerEvent[]> {
  // For Phase 10.2, we read from the frozen sample run
  // In production, this would call: GET /api/governance/runs/{run_id}/events
  
  if (runId === 'run-2026-01-12-sample') {
    // Simulating reading from examples/sample_run/events.jsonl
    return [
      {
        sequence: 0,
        event_type: 'RUN_CREATED',
        timestamp: '2026-01-12T10:00:00Z',
        actor: 'system',
        actor_role: 'System',
        phase: 'initialization',
        payload: {}
      },
      {
        sequence: 1,
        event_type: 'RUN_STARTED',
        timestamp: '2026-01-12T10:00:05Z',
        actor: 'orchestrator',
        actor_role: 'System',
        phase: 'initialization',
        payload: {}
      },
      {
        sequence: 2,
        event_type: 'ISSUE_DETECTED',
        timestamp: '2026-01-12T10:00:45Z',
        actor: 'scanner',
        actor_role: 'System',
        phase: 'scanning',
        payload: { count: 18, categories: { F401: 5, F541: 8, W291: 5 } }
      },
      {
        sequence: 3,
        event_type: 'POLICY_RESOLVED',
        timestamp: '2026-01-12T10:01:00Z',
        actor: 'classifier',
        actor_role: 'System',
        phase: 'planning',
        payload: { policy: 'default-v1', safe_count: 18 }
      },
      {
        sequence: 4,
        event_type: 'PLAN_CREATED',
        timestamp: '2026-01-12T10:01:15Z',
        actor: 'planner',
        actor_role: 'System',
        phase: 'planning',
        payload: { fixes_count: 18, requires_approval: true }
      },
      {
        sequence: 5,
        event_type: 'PLAN_APPROVED',
        timestamp: '2026-01-12T10:01:30Z',
        actor: 'alice@company.com',
        actor_role: 'Human',
        phase: 'approval',
        payload: { approved_by: 'alice@company.com', approval_type: 'manual' }
      },
      {
        sequence: 6,
        event_type: 'SAFETY_CHECK_STARTED',
        timestamp: '2026-01-12T10:01:45Z',
        actor: 'safety_checker',
        actor_role: 'System',
        phase: 'safety',
        payload: {}
      },
      {
        sequence: 7,
        event_type: 'SAFETY_CHECK_PASSED',
        timestamp: '2026-01-12T10:02:00Z',
        actor: 'safety_checker',
        actor_role: 'System',
        phase: 'safety',
        payload: { checks_passed: ['syntax', 'imports', 'tests'] }
      },
      {
        sequence: 8,
        event_type: 'FIX_APPLIED',
        timestamp: '2026-01-12T10:02:15Z',
        actor: 'fixer',
        actor_role: 'System',
        phase: 'fixing',
        payload: { file: 'main.py', rule: 'F401', line: 1 }
      },
      {
        sequence: 9,
        event_type: 'FIX_APPLIED',
        timestamp: '2026-01-12T10:02:30Z',
        actor: 'fixer',
        actor_role: 'System',
        phase: 'fixing',
        payload: { file: 'utils.py', rule: 'F541', line: 15 }
      },
      {
        sequence: 10,
        event_type: 'FIX_APPLIED',
        timestamp: '2026-01-12T10:02:45Z',
        actor: 'fixer',
        actor_role: 'System',
        phase: 'fixing',
        payload: { file: 'helpers.py', rule: 'W291', line: 42 }
      },
      {
        sequence: 11,
        event_type: 'FIX_APPLIED',
        timestamp: '2026-01-12T10:03:00Z',
        actor: 'fixer',
        actor_role: 'System',
        phase: 'fixing',
        payload: { file: 'config.py', rule: 'F401', line: 3 }
      },
      {
        sequence: 12,
        event_type: 'FIX_APPLIED',
        timestamp: '2026-01-12T10:03:15Z',
        actor: 'fixer',
        actor_role: 'System',
        phase: 'fixing',
        payload: { file: 'api.py', rule: 'F541', line: 88 }
      },
      {
        sequence: 13,
        event_type: 'TEST_VALIDATION_STARTED',
        timestamp: '2026-01-12T10:04:00Z',
        actor: 'validator',
        actor_role: 'System',
        phase: 'validation',
        payload: {}
      },
      {
        sequence: 14,
        event_type: 'TEST_VALIDATION_PASSED',
        timestamp: '2026-01-12T10:04:30Z',
        actor: 'validator',
        actor_role: 'System',
        phase: 'validation',
        payload: { tests_passed: 42, tests_failed: 0 }
      },
      {
        sequence: 15,
        event_type: 'EDR_GENERATION_STARTED',
        timestamp: '2026-01-12T10:04:45Z',
        actor: 'edr_generator',
        actor_role: 'System',
        phase: 'reporting',
        payload: {}
      },
      {
        sequence: 16,
        event_type: 'EDR_FINALIZED',
        timestamp: '2026-01-12T10:05:00Z',
        actor: 'edr_generator',
        actor_role: 'System',
        phase: 'reporting',
        payload: { edr_id: 'edr-2026-01-12-sample' },
        payload_ref: 'edr-2026-01-12-sample'
      },
      {
        sequence: 17,
        event_type: 'RUN_COMPLETED',
        timestamp: '2026-01-12T10:05:30Z',
        actor: 'orchestrator',
        actor_role: 'System',
        phase: 'completion',
        payload: { final_state: 'COMPLETE', duration_seconds: 330 }
      }
    ]
  }
  
  throw new Error(`Events not found for run: ${runId}`)
}

/**
 * Read replay summary (replay_summary.json)
 * READ-ONLY - No side effects
 */
export async function readReplaySummary(runId: string): Promise<ReplaySummary> {
  // For Phase 10.2, we read from the frozen sample run
  // In production, this would call: GET /api/governance/runs/{run_id}/replay
  
  if (runId === 'run-2026-01-12-sample') {
    return {
      run_id: 'run-2026-01-12-sample',
      final_state: 'COMPLETE',
      event_count: 18,
      fixes_count: 5,
      plan_approved: true,
      safety_passed: true,
      edr_id: 'edr-2026-01-12-sample',
      invariant_violations: [],
      duration_seconds: 330,
      issues_detected: 18
    }
  }
  
  throw new Error(`Replay summary not found for run: ${runId}`)
}

/**
 * Read inspection report (inspect_run.json)
 * READ-ONLY - No side effects
 */
export async function readInspectionReport(runId: string): Promise<InspectionReport> {
  // For Phase 10.2, we read from the frozen sample run
  // In production, this would call: GET /api/governance/runs/{run_id}/inspect
  
  if (runId === 'run-2026-01-12-sample') {
    return {
      metadata: {
        run_id: 'run-2026-01-12-sample',
        started_at: '2026-01-12T10:00:00Z',
        ended_at: '2026-01-12T10:05:30Z',
        duration_seconds: 330,
        final_state: 'COMPLETE'
      },
      timeline: {
        event_count: 18,
        phases_histogram: {
          initialization: 2,
          scanning: 1,
          planning: 2,
          approval: 1,
          safety: 2,
          fixing: 5,
          validation: 2,
          reporting: 2,
          completion: 1
        },
        event_types_histogram: {
          RUN_CREATED: 1,
          RUN_STARTED: 1,
          ISSUE_DETECTED: 1,
          POLICY_RESOLVED: 1,
          PLAN_CREATED: 1,
          PLAN_APPROVED: 1,
          SAFETY_CHECK_STARTED: 1,
          SAFETY_CHECK_PASSED: 1,
          FIX_APPLIED: 5,
          TEST_VALIDATION_STARTED: 1,
          TEST_VALIDATION_PASSED: 1,
          EDR_GENERATION_STARTED: 1,
          EDR_FINALIZED: 1,
          RUN_COMPLETED: 1
        }
      },
      decisions: {
        plan_approved: true,
        approved_by: 'alice@company.com',
        safety_passed: true
      },
      fixes: {
        count: 5,
        breakdown: {
          F401: 2,
          F541: 2,
          W291: 1
        }
      },
      invariants: {
        violation_count: 0,
        violations: []
      }
    }
  }
  
  throw new Error(`Inspection report not found for run: ${runId}`)
}

/**
 * List all available runs (for governance landing page)
 * READ-ONLY - No side effects
 */
export async function listAvailableRuns(): Promise<LedgerMetadata[]> {
  // For Phase 10.2, we only have the sample run
  // In production, this would call: GET /api/governance/runs
  
  return [
    {
      run_id: 'run-2026-01-12-sample',
      repository_url: 'https://github.com/example/repo.git',
      branch: 'main',
      policy: 'default-v1',
      started_at: '2026-01-12T10:00:00Z',
      ended_at: '2026-01-12T10:05:30Z',
      final_state: 'COMPLETE'
    }
  ]
}

/**
 * Check invariants for a run
 * READ-ONLY - No side effects
 */
export function checkInvariants(
  events: LedgerEvent[],
  metadata: LedgerMetadata
): {
  sequenceContiguous: boolean
  terminalEventPresent: boolean
  approvalBeforeFix: boolean
  safetyBeforeFix: boolean
  terminalMatches: boolean
} {
  // Check sequence contiguity
  const sequences = events.map(e => e.sequence).sort((a, b) => a - b)
  const sequenceContiguous = sequences.every((seq, idx) => seq === idx)
  
  // Check terminal event
  const lastEvent = events[events.length - 1]
  const terminalEvents = ['RUN_COMPLETED', 'RUN_ABORTED', 'RUN_REJECTED']
  const terminalEventPresent = terminalEvents.includes(lastEvent?.event_type || '')
  
  // Check approval before fix
  const approvalIndex = events.findIndex(e => e.event_type === 'PLAN_APPROVED')
  const firstFixIndex = events.findIndex(e => e.event_type === 'FIX_APPLIED')
  const approvalBeforeFix = approvalIndex === -1 || firstFixIndex === -1 || approvalIndex < firstFixIndex
  
  // Check safety before fix
  const safetyIndex = events.findIndex(e => e.event_type === 'SAFETY_CHECK_PASSED')
  const safetyBeforeFix = safetyIndex === -1 || firstFixIndex === -1 || safetyIndex < firstFixIndex
  
  // Check terminal event matches metadata
  const terminalStateMap: Record<string, string> = {
    'RUN_COMPLETED': 'COMPLETE',
    'RUN_ABORTED': 'ABORTED',
    'RUN_REJECTED': 'REJECTED'
  }
  const expectedState = terminalStateMap[lastEvent?.event_type || '']
  const terminalMatches = expectedState === metadata.final_state
  
  return {
    sequenceContiguous,
    terminalEventPresent,
    approvalBeforeFix,
    safetyBeforeFix,
    terminalMatches
  }
}
