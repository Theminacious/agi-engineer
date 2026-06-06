/**
 * Reliability Insights Dashboard for Phase 18.
 * 
 * Displays repository-level reliability metrics, trends, and analytics.
 */

'use client';

import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'next/navigation';

interface ReliabilityScore {
  reliability_score: number;
  score_grade: string;
  score_change_7d: number | null;
  score_change_30d: number | null;
  last_score_update_at: string | null;
}

interface RiskBreakdown {
  critical_risks: number;
  high_risks: number;
  medium_risks: number;
  low_risks: number;
  total_risks: number;
  risk_trend_7d: string | null;
  risk_trend_30d: string | null;
}

interface RiskCategories {
  crash_risks: number;
  resource_leaks: number;
  reliability_antipatterns: number;
  scalability_risks: number;
  edge_case_vulnerabilities: number;
}

interface FixMetrics {
  total_fixes_proposed: number;
  total_fixes_approved: number;
  total_fixes_applied: number;
  total_fixes_failed: number;
  fix_adoption_rate: number;
  fix_success_rate: number;
}

interface PRMetrics {
  total_prs_analyzed: number;
  prs_with_critical_risks: number;
  prs_with_high_risks: number;
  prs_with_no_risks: number;
}

interface RepoInsights {
  repository_id: number;
  repository_name: string;
  score: ReliabilityScore;
  risk_breakdown: RiskBreakdown;
  risk_categories: RiskCategories;
  fix_metrics: FixMetrics;
  pr_metrics: PRMetrics;
  last_analysis_at: string | null;
  last_fix_applied_at: string | null;
}

interface TrendDataPoint {
  date: string;
  score: number;
  critical_risks: number;
  high_risks: number;
  total_risks: number;
}

function InsightsPageContent() {
  const searchParams = useSearchParams();
  const repoId = searchParams.get('repo_id');
  
  const [insights, setInsights] = useState<RepoInsights | null>(null);
  const [trends, setTrends] = useState<TrendDataPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedPeriod, setSelectedPeriod] = useState<number>(30);

  useEffect(() => {
    if (repoId) {
      loadInsights();
      loadTrends();
    }
  }, [repoId, selectedPeriod]);

  const loadInsights = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await fetch(`/api/insights/repo/${repoId}`);
      
      if (!response.ok) {
        throw new Error('Failed to load insights');
      }
      
      const data = await response.json();
      setInsights(data);
    } catch (err) {
      console.error('Error loading insights:', err);
      setError(err instanceof Error ? err.message : 'Failed to load insights');
    } finally {
      setLoading(false);
    }
  };

  const loadTrends = async () => {
    try {
      const response = await fetch(`/api/insights/repo/${repoId}/trends?days=${selectedPeriod}`);
      
      if (!response.ok) {
        throw new Error('Failed to load trends');
      }
      
      const data = await response.json();
      setTrends(data.data_points);
    } catch (err) {
      console.error('Error loading trends:', err);
    }
  };

  const getScoreColor = (score: number): string => {
    if (score >= 90) return 'text-green-600';
    if (score >= 80) return 'text-blue-600';
    if (score >= 70) return 'text-yellow-600';
    if (score >= 60) return 'text-orange-600';
    return 'text-red-600';
  };

  const getScoreBackgroundColor = (score: number): string => {
    if (score >= 90) return 'bg-green-50 border-green-200';
    if (score >= 80) return 'bg-blue-50 border-blue-200';
    if (score >= 70) return 'bg-yellow-50 border-yellow-200';
    if (score >= 60) return 'bg-orange-50 border-orange-200';
    return 'bg-red-50 border-red-200';
  };

  const getTrendIndicator = (change: number | null): JSX.Element => {
    if (change === null) return <span className="text-gray-400">—</span>;
    
    if (change > 0) {
      return (
        <span className="text-green-600">
          ↑ {change.toFixed(1)}
        </span>
      );
    } else if (change < 0) {
      return (
        <span className="text-red-600">
          ↓ {Math.abs(change).toFixed(1)}
        </span>
      );
    } else {
      return <span className="text-gray-600">— 0.0</span>;
    }
  };

  const getRiskTrendBadge = (trend: string | null): JSX.Element => {
    if (!trend) return <span className="text-gray-400">—</span>;
    
    const colors = {
      'increasing': 'bg-red-100 text-red-700',
      'stable': 'bg-blue-100 text-blue-700',
      'decreasing': 'bg-green-100 text-green-700'
    };
    
    return (
      <span className={`px-2 py-1 rounded text-xs font-medium ${colors[trend as keyof typeof colors]}`}>
        {trend}
      </span>
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading insights...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 max-w-md">
          <h2 className="text-red-800 font-semibold mb-2">Error Loading Insights</h2>
          <p className="text-red-600">{error}</p>
          <button
            onClick={loadInsights}
            className="mt-4 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!insights) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center text-gray-600">
          <p>No repository selected</p>
          <p className="text-sm mt-2">Please select a repository to view insights</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            Reliability Insights
          </h1>
          <p className="text-gray-600">
            {insights.repository_name}
          </p>
        </div>

        {/* Score Card */}
        <div className={`rounded-lg border-2 p-8 mb-8 ${getScoreBackgroundColor(insights.score.reliability_score)}`}>
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-gray-700 mb-2">
                Reliability Score
              </h2>
              <div className="flex items-baseline gap-4">
                <span className={`text-6xl font-bold ${getScoreColor(insights.score.reliability_score)}`}>
                  {insights.score.reliability_score.toFixed(1)}
                </span>
                <span className={`text-4xl font-bold ${getScoreColor(insights.score.reliability_score)}`}>
                  {insights.score.score_grade}
                </span>
              </div>
            </div>
            
            <div className="text-right">
              <div className="mb-2">
                <span className="text-sm text-gray-600">7-day change: </span>
                {getTrendIndicator(insights.score.score_change_7d)}
              </div>
              <div>
                <span className="text-sm text-gray-600">30-day change: </span>
                {getTrendIndicator(insights.score.score_change_30d)}
              </div>
            </div>
          </div>
          
          {insights.score.last_score_update_at && (
            <p className="text-sm text-gray-600 mt-4">
              Last updated: {new Date(insights.score.last_score_update_at).toLocaleString()}
            </p>
          )}
        </div>

        {/* Risk Breakdown */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          {/* Risk by Severity */}
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              Risks by Severity
            </h3>
            
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <span className="text-red-600 font-medium">Critical</span>
                <span className="text-2xl font-bold text-red-600">
                  {insights.risk_breakdown.critical_risks}
                </span>
              </div>
              
              <div className="flex justify-between items-center">
                <span className="text-orange-600 font-medium">High</span>
                <span className="text-2xl font-bold text-orange-600">
                  {insights.risk_breakdown.high_risks}
                </span>
              </div>
              
              <div className="flex justify-between items-center">
                <span className="text-yellow-600 font-medium">Medium</span>
                <span className="text-2xl font-bold text-yellow-600">
                  {insights.risk_breakdown.medium_risks}
                </span>
              </div>
              
              <div className="flex justify-between items-center">
                <span className="text-blue-600 font-medium">Low</span>
                <span className="text-2xl font-bold text-blue-600">
                  {insights.risk_breakdown.low_risks}
                </span>
              </div>
              
              <div className="border-t pt-4 flex justify-between items-center">
                <span className="text-gray-900 font-semibold">Total</span>
                <span className="text-2xl font-bold text-gray-900">
                  {insights.risk_breakdown.total_risks}
                </span>
              </div>
            </div>
            
            <div className="mt-6 pt-6 border-t">
              <div className="flex justify-between items-center mb-2">
                <span className="text-sm text-gray-600">7-day trend:</span>
                {getRiskTrendBadge(insights.risk_breakdown.risk_trend_7d)}
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">30-day trend:</span>
                {getRiskTrendBadge(insights.risk_breakdown.risk_trend_30d)}
              </div>
            </div>
          </div>

          {/* Risk by Category */}
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              Risks by Category
            </h3>
            
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-gray-700">Crash Risks</span>
                <span className="font-bold text-gray-900">
                  {insights.risk_categories.crash_risks}
                </span>
              </div>
              
              <div className="flex justify-between items-center">
                <span className="text-gray-700">Resource Leaks</span>
                <span className="font-bold text-gray-900">
                  {insights.risk_categories.resource_leaks}
                </span>
              </div>
              
              <div className="flex justify-between items-center">
                <span className="text-gray-700">Reliability Antipatterns</span>
                <span className="font-bold text-gray-900">
                  {insights.risk_categories.reliability_antipatterns}
                </span>
              </div>
              
              <div className="flex justify-between items-center">
                <span className="text-gray-700">Scalability Risks</span>
                <span className="font-bold text-gray-900">
                  {insights.risk_categories.scalability_risks}
                </span>
              </div>
              
              <div className="flex justify-between items-center">
                <span className="text-gray-700">Edge Case Vulnerabilities</span>
                <span className="font-bold text-gray-900">
                  {insights.risk_categories.edge_case_vulnerabilities}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Fix Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          {/* Fix Statistics */}
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              Fix Metrics
            </h3>
            
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-gray-700">Fixes Proposed</span>
                <span className="font-bold text-gray-900">
                  {insights.fix_metrics.total_fixes_proposed}
                </span>
              </div>
              
              <div className="flex justify-between items-center">
                <span className="text-gray-700">Fixes Approved</span>
                <span className="font-bold text-gray-900">
                  {insights.fix_metrics.total_fixes_approved}
                </span>
              </div>
              
              <div className="flex justify-between items-center">
                <span className="text-gray-700">Fixes Applied</span>
                <span className="font-bold text-green-600">
                  {insights.fix_metrics.total_fixes_applied}
                </span>
              </div>
              
              <div className="flex justify-between items-center">
                <span className="text-gray-700">Fixes Failed</span>
                <span className="font-bold text-red-600">
                  {insights.fix_metrics.total_fixes_failed}
                </span>
              </div>
            </div>
            
            <div className="mt-6 pt-6 border-t">
              <div className="flex justify-between items-center mb-2">
                <span className="text-sm text-gray-600">Adoption Rate:</span>
                <span className="text-lg font-bold text-blue-600">
                  {(insights.fix_metrics.fix_adoption_rate * 100).toFixed(1)}%
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">Success Rate:</span>
                <span className="text-lg font-bold text-green-600">
                  {(insights.fix_metrics.fix_success_rate * 100).toFixed(1)}%
                </span>
              </div>
            </div>
          </div>

          {/* PR Analysis Metrics */}
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              PR Analysis Metrics
            </h3>
            
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-gray-700">Total PRs Analyzed</span>
                <span className="font-bold text-gray-900">
                  {insights.pr_metrics.total_prs_analyzed}
                </span>
              </div>
              
              <div className="flex justify-between items-center">
                <span className="text-gray-700">PRs with Critical Risks</span>
                <span className="font-bold text-red-600">
                  {insights.pr_metrics.prs_with_critical_risks}
                </span>
              </div>
              
              <div className="flex justify-between items-center">
                <span className="text-gray-700">PRs with High Risks</span>
                <span className="font-bold text-orange-600">
                  {insights.pr_metrics.prs_with_high_risks}
                </span>
              </div>
              
              <div className="flex justify-between items-center">
                <span className="text-gray-700">PRs with No Risks</span>
                <span className="font-bold text-green-600">
                  {insights.pr_metrics.prs_with_no_risks}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Trend Chart Placeholder */}
        <div className="bg-white rounded-lg border border-gray-200 p-6 mb-8">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-semibold text-gray-900">
              Score Trend
            </h3>
            
            <div className="flex gap-2">
              <button
                onClick={() => setSelectedPeriod(7)}
                className={`px-3 py-1 rounded text-sm ${selectedPeriod === 7 ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-700'}`}
              >
                7 days
              </button>
              <button
                onClick={() => setSelectedPeriod(30)}
                className={`px-3 py-1 rounded text-sm ${selectedPeriod === 30 ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-700'}`}
              >
                30 days
              </button>
              <button
                onClick={() => setSelectedPeriod(90)}
                className={`px-3 py-1 rounded text-sm ${selectedPeriod === 90 ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-700'}`}
              >
                90 days
              </button>
            </div>
          </div>
          
          {trends.length > 0 ? (
            <div className="space-y-2">
              {trends.slice(0, 10).map((point, index) => (
                <div key={index} className="flex justify-between items-center text-sm border-b pb-2">
                  <span className="text-gray-600">
                    {new Date(point.date).toLocaleDateString()}
                  </span>
                  <span className={`font-semibold ${getScoreColor(point.score)}`}>
                    {point.score.toFixed(1)}
                  </span>
                  <span className="text-gray-600">
                    {point.total_risks} risks ({point.critical_risks}C / {point.high_risks}H)
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-600 text-center py-8">
              No trend data available yet. Trends will appear after multiple analyses.
            </p>
          )}
        </div>

        {/* Activity Summary */}
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Activity Summary
          </h3>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <span className="text-sm text-gray-600">Last Analysis:</span>
              <p className="font-medium text-gray-900">
                {insights.last_analysis_at 
                  ? new Date(insights.last_analysis_at).toLocaleString()
                  : 'Never'}
              </p>
            </div>
            
            <div>
              <span className="text-sm text-gray-600">Last Fix Applied:</span>
              <p className="font-medium text-gray-900">
                {insights.last_fix_applied_at 
                  ? new Date(insights.last_fix_applied_at).toLocaleString()
                  : 'Never'}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function InsightsPage() {
  return (
    <React.Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center">
          <div className="text-center">
            <div className="mx-auto mb-4 h-12 w-12 animate-spin rounded-full border-b-2 border-blue-600" />
            <p className="text-gray-600">Loading insights...</p>
          </div>
        </div>
      }
    >
      <InsightsPageContent />
    </React.Suspense>
  );
}
