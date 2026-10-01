/**
 * Data layer for PR analyses and Change Risk: URLs, failure handling, and the
 * formatting the UI depends on.
 *
 * tests/integrations-page.test.tsx covers what the user actually sees.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { API_BASE } from '@/lib/api'
import {
  affectedPath,
  behavioralStatusClassName,
  behavioralStatusLabel,
  factorSummary,
  fetchPRAnalyses,
  fetchPRAnalysis,
  prAnalysesPath,
  prAnalysisPath,
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
} from '@/lib/prAnalyses'

const originalFetch = global.fetch

function mockJson(body: unknown, ok = true, status = 200) {
  const spy = vi.fn().mockResolvedValue({
    ok,
    status,
    json: async () => body,
  })
  global.fetch = spy as unknown as typeof fetch
  return spy
}

afterEach(() => {
  global.fetch = originalFetch
  vi.restoreAllMocks()
})

describe('request paths', () => {
  it('lists analyses with a limit and no repository filter by default', () => {
    expect(prAnalysesPath()).toBe('/api/github/pr-analyses?limit=25')
  })

  it('encodes the repository filter', () => {
    expect(prAnalysesPath('acme/widgets', 5)).toBe(
      '/api/github/pr-analyses?repository=acme%2Fwidgets&limit=5',
    )
  })

  it('addresses a single analysis by id', () => {
    expect(prAnalysisPath(42)).toBe('/api/github/pr-analyses/42')
  })

  it('requests the absolute backend URL, not a relative one', async () => {
    const spy = mockJson({ analyses: [], count: 0, repositories: [] })
    await fetchPRAnalyses()
    expect(spy).toHaveBeenCalledWith(`${API_BASE}/api/github/pr-analyses?limit=25`)
  })

  it('requests the absolute backend URL for one analysis', async () => {
    const spy = mockJson({ id: 7 })
    await fetchPRAnalysis(7)
    expect(spy).toHaveBeenCalledWith(`${API_BASE}/api/github/pr-analyses/7`)
  })
})

describe('failure handling', () => {
  it('rejects with the status when the list request is not ok', async () => {
    mockJson({}, false, 503)
    await expect(fetchPRAnalyses()).rejects.toThrow(/503/)
  })

  it('rejects with the status when the detail request is not ok', async () => {
    mockJson({}, false, 404)
    await expect(fetchPRAnalysis(9)).rejects.toThrow(/404/)
  })

  it('names what failed so the UI can show it verbatim', async () => {
    mockJson({}, false, 500)
    await expect(fetchPRAnalysis(9)).rejects.toThrow(/PR analysis 9/)
  })
})

describe('risk level presentation', () => {
  it('labels a known level in upper case', () => {
    expect(riskLevelLabel('critical')).toBe('CRITICAL')
    expect(riskLevelLabel('low')).toBe('LOW')
  })

  it('says a missing level is not assessed rather than implying safety', () => {
    expect(riskLevelLabel(null)).toBe('NOT ASSESSED')
    expect(riskLevelLabel(undefined)).toBe('NOT ASSESSED')
  })

  it('gives each level a distinct class', () => {
    const classes = ['none', 'low', 'medium', 'high', 'critical'].map(riskLevelClassName)
    expect(new Set(classes).size).toBe(5)
  })

  it('does not style an unknown level as low risk', () => {
    expect(riskLevelClassName('banana')).not.toBe(riskLevelClassName('low'))
    expect(riskLevelClassName(null)).not.toBe(riskLevelClassName('low'))
  })
})

describe('recommendation presentation', () => {
  it('labels each recommendation', () => {
    expect(recommendationLabel('no_review_required')).toBe('No review required')
    expect(recommendationLabel('review_recommended')).toBe('Review recommended')
    expect(recommendationLabel('requires_human_review')).toBe('Human review required')
  })

  it('falls back to the raw value rather than dropping an unknown recommendation', () => {
    expect(recommendationLabel('something_new')).toBe('something_new')
  })

  it('reports no recommendation when there is none', () => {
    expect(recommendationLabel(null)).toBe('No recommendation')
  })

  it('flags only requires_human_review as needing review', () => {
    expect(requiresHumanReview('requires_human_review')).toBe(true)
    expect(requiresHumanReview('review_recommended')).toBe(false)
    expect(requiresHumanReview(null)).toBe(false)
  })
})

describe('factor and hash formatting', () => {
  it('prefers the factor detail over its kind', () => {
    expect(
      factorSummary({ kind: 'wide_blast_radius', level: 'medium', detail: '11 symbols', evidence: [] }),
    ).toBe('11 symbols')
  })

  it('falls back to the kind when there is no detail', () => {
    expect(
      factorSummary({ kind: 'wide_blast_radius', level: 'medium', detail: '', evidence: [] }),
    ).toBe('wide_blast_radius')
  })

  it('truncates a long hash and leaves a short one alone', () => {
    expect(shortHash('a'.repeat(64), 8)).toBe('aaaaaaaa…')
    expect(shortHash('abc', 8)).toBe('abc')
  })

  it('renders a missing hash as an em dash, never as an empty string', () => {
    expect(shortHash(null)).toBe('—')
  })
})

const IMPACT: NonNullable<ChangeRisk['impact']> = {
  repository: 'acme/payments',
  base_revision: 'b'.repeat(40),
  target_revision: 't'.repeat(40),
  changed_file_count: 1,
  changed_symbol_count: 1,
  blast_radius_size: 6,
  changed_files: ['user_repo.py'],
  changed_symbols: [
    {
      node_id: 'user_repo.py::UserRepository.get_user',
      node_type: 'method',
      file_path: 'user_repo.py',
      name: 'get_user',
      change_kind: 'modified',
    },
  ],
  affected_callers: ['auth_service.py::AuthorizationService.authorize'],
  downstream_symbols: [
    'user_repo.py',
    'user_repo.py::UserRepository',
    'payments.py::PaymentService.process_payment',
    'auth_service.py::AuthorizationService.authorize',
  ],
  affected_entrypoints: ['api.py::create_payment'],
  affected_api_surfaces: ['create_payment (app.post)'],
  unresolved_references: [],
}

describe('affectedPath', () => {
  it('orders the path from the entry point down to the changed symbol', () => {
    expect(affectedPath(IMPACT)).toEqual([
      'api.py::create_payment',
      'payments.py::PaymentService.process_payment',
      'auth_service.py::AuthorizationService.authorize',
      'user_repo.py::UserRepository.get_user',
    ])
  })

  it('lists each node once', () => {
    const path = affectedPath(IMPACT)
    expect(new Set(path).size).toBe(path.length)
  })

  it('omits file-level graph nodes, which are not call steps', () => {
    expect(affectedPath(IMPACT)).not.toContain('user_repo.py')
  })

  it('omits the class containing the changed method, which contains rather than calls it', () => {
    expect(affectedPath(IMPACT)).not.toContain('user_repo.py::UserRepository')
  })

  it('returns nothing when there is no impact to draw a path from', () => {
    expect(affectedPath(null)).toEqual([])
  })

  it('lists a node once when it is both an entry point and a caller', () => {
    const path = affectedPath({
      ...IMPACT,
      affected_callers: ['api.py::create_payment'],
      downstream_symbols: [],
    })
    expect(path).toEqual([
      'api.py::create_payment',
      'user_repo.py::UserRepository.get_user',
    ])
  })

  it('returns nothing when no symbol changed', () => {
    expect(affectedPath({ ...IMPACT, changed_symbols: [] })).toEqual([])
  })

  it('still returns the changed symbol when no entry point is reached', () => {
    expect(
      affectedPath({
        ...IMPACT,
        affected_entrypoints: [],
        affected_callers: [],
        downstream_symbols: [],
      }),
    ).toEqual(['user_repo.py::UserRepository.get_user'])
  })
})

describe('verificationStateLabel', () => {
  it('uppercases a known state', () => {
    expect(verificationStateLabel('verified')).toBe('VERIFIED')
    expect(verificationStateLabel('partially_verified')).toBe('PARTIALLY_VERIFIED')
    expect(verificationStateLabel('blocked')).toBe('BLOCKED')
  })

  it('reports UNKNOWN when the state is missing', () => {
    expect(verificationStateLabel(null)).toBe('UNKNOWN')
    expect(verificationStateLabel(undefined)).toBe('UNKNOWN')
  })
})

describe('verificationStateClassName', () => {
  it('gives each state a distinct style so VERIFIED is not confused with the rest', () => {
    const verified = verificationStateClassName('verified')
    const partial = verificationStateClassName('partially_verified')
    const unverified = verificationStateClassName('unverified')
    const blocked = verificationStateClassName('blocked')
    const distinct = new Set([verified, partial, unverified, blocked])
    expect(distinct.size).toBe(4)
    expect(verified).not.toBe(partial)
    expect(blocked).toContain('red')
  })

  it('marks an unknown or missing state as unresolved rather than passing', () => {
    expect(verificationStateClassName(null)).toContain('dashed')
    expect(verificationStateClassName('mystery')).toContain('dashed')
  })
})

describe('behavioralStatusLabel', () => {
  it('labels known comparison statuses', () => {
    expect(behavioralStatusLabel('REGRESSIONS_FOUND')).toBe('Regressions found')
    expect(behavioralStatusLabel('NO_REGRESSIONS')).toBe('No regressions')
    expect(behavioralStatusLabel('UNKNOWN')).toBe('Inconclusive')
  })

  it('reports not available when the status is missing', () => {
    expect(behavioralStatusLabel(null)).toBe('Not available')
    expect(behavioralStatusLabel(undefined)).toBe('Not available')
  })
})

describe('behavioralStatusClassName', () => {
  it('flags regressions in red and no-regressions distinctly', () => {
    expect(behavioralStatusClassName('REGRESSIONS_FOUND')).toContain('red')
    expect(behavioralStatusClassName('NO_REGRESSIONS')).not.toContain('red')
  })

  it('marks a missing status as unresolved', () => {
    expect(behavioralStatusClassName(null)).toContain('dashed')
  })
})

describe('proofIntegrityLabel', () => {
  it('labels known integrity statuses', () => {
    expect(proofIntegrityLabel('INTEGRITY_VERIFIED')).toBe('Proof integrity verified')
    expect(proofIntegrityLabel('INTEGRITY_MISMATCH')).toBe('Proof integrity MISMATCH')
    expect(proofIntegrityLabel('INTEGRITY_UNAVAILABLE')).toBe('Proof integrity not checkable')
  })

  it('reports not checkable when the status is missing', () => {
    expect(proofIntegrityLabel(null)).toBe('Proof integrity not checkable')
    expect(proofIntegrityLabel(undefined)).toBe('Proof integrity not checkable')
  })
})

describe('proofIntegrityClassName', () => {
  it('flags a mismatch in red and a verified proof distinctly', () => {
    expect(proofIntegrityClassName('INTEGRITY_MISMATCH')).toContain('red')
    expect(proofIntegrityClassName('INTEGRITY_VERIFIED')).not.toContain('red')
  })

  it('marks unavailable or missing integrity as unresolved rather than passing', () => {
    expect(proofIntegrityClassName('INTEGRITY_UNAVAILABLE')).toContain('dashed')
    expect(proofIntegrityClassName(null)).toContain('dashed')
  })
})

