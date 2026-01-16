/**
 * Plan Selection Hook
 * 
 * Phase 14.4: Plan Selection Finalization (Pre-Billing)
 * 
 * Manages mock user plan state using localStorage.
 * No billing integration - purely demo/preview functionality.
 * 
 * Flow:
 * 1. User selects plan on /plans page
 * 2. Selection persisted to localStorage
 * 3. All pages read current plan from localStorage
 * 4. Shows "Active Plan" indicators
 * 5. Trust messaging: "Upgrades only affect future runs"
 * 
 * Default: 'developer' (Core Engineer) - free tier
 */

'use client'

import { useState, useEffect } from 'react'
import type { PlanType } from '@/lib/analyzerRegistry'

const PLAN_STORAGE_KEY = 'agi_engineer_selected_plan'
const DEFAULT_PLAN: PlanType = 'developer'

export interface PlanSelectionState {
  plan: PlanType
  selectedAt: string | null
  isLoading: boolean
}

export interface PlanSelectionActions {
  selectPlan: (plan: PlanType) => void
  resetToDefault: () => void
}

/**
 * Hook for managing user's selected plan (mock state)
 * 
 * @returns Current plan state and selection actions
 */
export function usePlanSelection(): PlanSelectionState & PlanSelectionActions {
  const [state, setState] = useState<PlanSelectionState>({
    plan: DEFAULT_PLAN,
    selectedAt: null,
    isLoading: true,
  })

  // Load plan from localStorage on mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem(PLAN_STORAGE_KEY)
      if (stored) {
        const parsed = JSON.parse(stored)
        setState({
          plan: parsed.plan || DEFAULT_PLAN,
          selectedAt: parsed.selectedAt || null,
          isLoading: false,
        })
      } else {
        setState(prev => ({ ...prev, isLoading: false }))
      }
    } catch (error) {
      console.error('Failed to load plan selection:', error)
      setState(prev => ({ ...prev, isLoading: false }))
    }
  }, [])

  // Select a plan (mock upgrade/downgrade)
  const selectPlan = (plan: PlanType) => {
    const newState = {
      plan,
      selectedAt: new Date().toISOString(),
    }
    
    try {
      localStorage.setItem(PLAN_STORAGE_KEY, JSON.stringify(newState))
      setState({
        ...newState,
        isLoading: false,
      })
    } catch (error) {
      console.error('Failed to save plan selection:', error)
    }
  }

  // Reset to default (free tier)
  const resetToDefault = () => {
    try {
      localStorage.removeItem(PLAN_STORAGE_KEY)
      setState({
        plan: DEFAULT_PLAN,
        selectedAt: null,
        isLoading: false,
      })
    } catch (error) {
      console.error('Failed to reset plan selection:', error)
    }
  }

  return {
    ...state,
    selectPlan,
    resetToDefault,
  }
}

/**
 * Get experience name for a plan tier
 */
export function getPlanExperienceName(plan: PlanType): string {
  const names: Record<PlanType, string> = {
    developer: 'Core Engineer',
    team: 'Advanced Engineer',
    enterprise: 'Autonomous Engineer',
  }
  return names[plan]
}

/**
 * Get plan price display
 */
export function getPlanPrice(plan: PlanType): string {
  const prices: Record<PlanType, string> = {
    developer: 'Free',
    team: '$99/mo',
    enterprise: 'Custom',
  }
  return prices[plan]
}

/**
 * Check if plan is upgraded (not free tier)
 */
export function isUpgradedPlan(plan: PlanType): boolean {
  return plan !== 'developer'
}
