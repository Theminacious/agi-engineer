/**
 * Analyzer Registry (Frontend Mirror)
 * 
 * This mirrors the backend registry at agent/intelligence/registry.py
 * Used for UI display of analyzer metadata and plan requirements.
 * 
 * Phase 13.4: Read-only subscription-aware transparency
 */

export type PlanType = 'developer' | 'team' | 'enterprise'
export type AnalyzerCategory = 
  | 'architecture' 
  | 'performance' 
  | 'concurrency' 
  | 'security' 
  | 'testing' 
  | 'configuration'

export interface AnalyzerMetadata {
  id: string
  category: AnalyzerCategory
  min_plan: PlanType
  default_enabled: boolean
  description: string
}

export const ANALYZER_REGISTRY: Record<string, AnalyzerMetadata> = {
  // Architecture
  architectural: {
    id: 'architectural',
    category: 'architecture',
    min_plan: 'developer',
    default_enabled: true,
    description: 'Detects architectural violations and circular dependencies (baseline)',
  },
  enhanced_architectural: {
    id: 'enhanced_architectural',
    category: 'architecture',
    min_plan: 'team',
    default_enabled: true,
    description: 'Detects architectural violations, multi-hop cycles, domain leakage, coupling',
  },
  abstraction: {
    id: 'abstraction',
    category: 'architecture',
    min_plan: 'developer',
    default_enabled: true,
    description: 'Detects abstraction leakage and boundary problems',
  },
  api_contracts: {
    id: 'api_contracts',
    category: 'architecture',
    min_plan: 'developer',
    default_enabled: true,
    description: 'Detects API contract violations across modules/services',
  },
  god_objects: {
    id: 'god_objects',
    category: 'architecture',
    min_plan: 'developer',
    default_enabled: true,
    description: 'Detects large, do-everything classes/modules (god objects)',
  },

  // Performance
  performance: {
    id: 'performance',
    category: 'performance',
    min_plan: 'developer',
    default_enabled: true,
    description: 'Detects performance anti-patterns (baseline)',
  },
  enhanced_performance: {
    id: 'enhanced_performance',
    category: 'performance',
    min_plan: 'team',
    default_enabled: true,
    description: 'Detects N+1 queries, blocking I/O, memory growth, inefficient algorithms',
  },

  // Concurrency
  concurrency: {
    id: 'concurrency',
    category: 'concurrency',
    min_plan: 'developer',
    default_enabled: true,
    description: 'Detects basic concurrency hazards (baseline)',
  },
  enhanced_concurrency: {
    id: 'enhanced_concurrency',
    category: 'concurrency',
    min_plan: 'team',
    default_enabled: true,
    description: 'Detects shared state, thread-safety issues, async anti-patterns, lock risks',
  },

  // Security
  security: {
    id: 'security',
    category: 'security',
    min_plan: 'developer',
    default_enabled: true,
    description: 'Detects security misconfigurations and risks',
  },

  // Testing
  test_coverage: {
    id: 'test_coverage',
    category: 'testing',
    min_plan: 'developer',
    default_enabled: true,
    description: 'Detects test coverage blind spots and testing risks',
  },
  broken_invariants: {
    id: 'broken_invariants',
    category: 'testing',
    min_plan: 'developer',
    default_enabled: true,
    description: 'Detects broken invariants and incorrect assumptions',
  },

  // Configuration
  configuration: {
    id: 'configuration',
    category: 'configuration',
    min_plan: 'developer',
    default_enabled: true,
    description: 'Detects configuration drift and misalignment',
  },
  dependencies: {
    id: 'dependencies',
    category: 'configuration',
    min_plan: 'developer',
    default_enabled: true,
    description: 'Detects dependency misuse and version conflicts',
  },
}

/**
 * Plan tier ordering for comparison
 */
export const PLAN_ORDER: Record<PlanType, number> = {
  developer: 0,
  team: 1,
  enterprise: 2,
}

/**
 * Get all analyzers sorted deterministically by ID
 */
export function getAllAnalyzers(): AnalyzerMetadata[] {
  return Object.values(ANALYZER_REGISTRY).sort((a, b) => a.id.localeCompare(b.id))
}

/**
 * Get analyzers available for a specific plan
 */
export function getAnalyzersForPlan(plan: PlanType): AnalyzerMetadata[] {
  const planLevel = PLAN_ORDER[plan]
  return getAllAnalyzers().filter(analyzer => PLAN_ORDER[analyzer.min_plan] <= planLevel)
}

/**
 * Check if analyzer is available for plan
 */
export function isAnalyzerAvailableForPlan(analyzerId: string, plan: PlanType): boolean {
  const analyzer = ANALYZER_REGISTRY[analyzerId]
  if (!analyzer) return false
  return PLAN_ORDER[analyzer.min_plan] <= PLAN_ORDER[plan]
}

/**
 * Get analyzer by ID
 */
export function getAnalyzer(analyzerId: string): AnalyzerMetadata | null {
  return ANALYZER_REGISTRY[analyzerId] || null
}

/**
 * Group analyzers by category
 */
export function groupAnalyzersByCategory(): Record<AnalyzerCategory, AnalyzerMetadata[]> {
  const grouped: Record<AnalyzerCategory, AnalyzerMetadata[]> = {
    architecture: [],
    performance: [],
    concurrency: [],
    security: [],
    testing: [],
    configuration: [],
  }

  getAllAnalyzers().forEach(analyzer => {
    grouped[analyzer.category].push(analyzer)
  })

  return grouped
}

/**
 * Get category display name
 */
export function getCategoryLabel(category: AnalyzerCategory): string {
  const labels: Record<AnalyzerCategory, string> = {
    architecture: 'Architecture',
    performance: 'Performance',
    concurrency: 'Concurrency',
    security: 'Security',
    testing: 'Testing',
    configuration: 'Configuration',
  }
  return labels[category]
}

/**
 * Get plan display name
 */
export function getPlanLabel(plan: PlanType): string {
  const labels: Record<PlanType, string> = {
    developer: 'Developer',
    team: 'Team',
    enterprise: 'Enterprise',
  }
  return labels[plan]
}
