'use client'

import { useEffect, useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui'
import { Badge, Button } from '@/components/ui'
import { TrendingUp, AlertCircle, CheckCircle, BarChart3 } from 'lucide-react'

interface AnalyticsDashboardProps {
  repositoryId?: number
  days?: number
}

export function AnalyticsDashboard({ repositoryId, days = 30 }: AnalyticsDashboardProps) {
  const [stats, setStats] = useState<any>(null)
  const [categories, setCategories] = useState<any>(null)
  const [topIssues, setTopIssues] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchAnalytics = async () => {
      const token = localStorage.getItem('jwt_token')
      
      try {
        // Fetch all analytics in parallel
        const [statsRes, categoriesRes, topRes] = await Promise.all([
          fetch(`/api/analytics/runs/stats?days=${days}`, {
            headers: { 'Authorization': `Bearer ${token}` }
          }),
          fetch(`/api/analytics/issues/categories?days=${days}`, {
            headers: { 'Authorization': `Bearer ${token}` }
          }),
          fetch(`/api/analytics/top-issues?days=${days}`, {
            headers: { 'Authorization': `Bearer ${token}` }
          })
        ])

        if (statsRes.ok) setStats(await statsRes.json())
        if (categoriesRes.ok) setCategories(await categoriesRes.json())
        if (topRes.ok) setTopIssues(await topRes.json())
      } catch (error) {
        console.error('Error fetching analytics:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchAnalytics()
  }, [days])

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="text-gray-600">Loading analytics...</div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">Total Runs</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-gray-900">
              {stats?.summary?.total_runs || 0}
            </div>
            <p className="text-xs text-gray-500 mt-1">Last {days} days</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">Success Rate</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-green-600">
              {stats?.summary?.total_runs > 0 
                ? ((stats.summary.completed / stats.summary.total_runs) * 100).toFixed(0)
                : 0}%
            </div>
            <p className="text-xs text-gray-500 mt-1">{stats?.summary?.completed || 0} completed</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">Total Issues Found</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-amber-600">
              {stats?.summary?.total_issues || 0}
            </div>
            <p className="text-xs text-gray-500 mt-1">
              Avg: {stats?.summary?.average_issues_per_run?.toFixed(1) || 0}/run
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">Failed Runs</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-red-600">
              {stats?.summary?.failed || 0}
            </div>
            <p className="text-xs text-gray-500 mt-1">Requires attention</p>
          </CardContent>
        </Card>
      </div>

      {/* Issue Categories */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-blue-600" />
            Issues by Category
          </CardTitle>
          <CardDescription>Breakdown of detected issues</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {categories?.categories?.map((cat: any) => (
              <div key={cat.name} className="flex items-center justify-between">
                <div className="flex-1">
                  <p className="font-medium text-gray-900 text-sm">{cat.name}</p>
                  <div className="flex gap-2 mt-1">
                    {Object.entries(cat.severity_breakdown).map(([sev, count]: [string, any]) => (
                      <Badge key={sev} variant="secondary" className="text-xs">
                        {sev}: {count}
                      </Badge>
                    ))}
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-2xl font-bold text-gray-900">{cat.count}</p>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Top Issues */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <AlertCircle className="w-5 h-5 text-amber-600" />
            Most Common Issues
          </CardTitle>
          <CardDescription>Issues appearing most frequently</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {topIssues?.top_issues?.map((issue: any, idx: number) => (
              <div key={issue.rule_id} className="flex items-center gap-3 p-2 border border-gray-200 rounded">
                <div className="flex-shrink-0 w-8 h-8 flex items-center justify-center bg-gray-100 rounded font-semibold text-sm text-gray-700">
                  {idx + 1}
                </div>
                <div className="flex-1">
                  <p className="font-medium text-gray-900 text-sm">{issue.name}</p>
                  <p className="text-xs text-gray-500">{issue.rule_id}</p>
                </div>
                <Badge className="bg-red-100 text-red-800">
                  {issue.occurrence_count} times
                </Badge>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Insights */}
      <Card className="bg-blue-50 border-blue-200">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-blue-900">
            <TrendingUp className="w-5 h-5" />
            Insights
          </CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="space-y-2 text-sm text-blue-900">
            <li>✅ Analysis success rate: {stats?.summary?.total_runs > 0 
              ? ((stats.summary.completed / stats.summary.total_runs) * 100).toFixed(0)
              : 0}%</li>
            <li>🔍 Most common category: {categories?.categories?.[0]?.name || 'N/A'}</li>
            <li>⚠️ Average issues per run: {stats?.summary?.average_issues_per_run?.toFixed(1) || 0}</li>
            <li>📈 Total unique issue types: {topIssues?.total_unique_issues || 0}</li>
          </ul>
        </CardContent>
      </Card>
    </div>
  )
}
