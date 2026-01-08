'use client'

import { useRouter, useParams } from 'next/navigation'
import { useEffect, useState } from 'react'
import { getRunDetail, AnalysisRunDetail } from '@/lib/api'
import { Header, Loading, Error, StatusBadge, CategoryBadge } from '@/components/ui'

export default function RunDetailPage() {
  const router = useRouter()
  const params = useParams()
  const runId = params.id as string
  const [run, setRun] = useState<AnalysisRunDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [autoRefresh, setAutoRefresh] = useState(true)

  useEffect(() => {
    // Check authentication
    const token = localStorage.getItem('jwt_token')
    if (!token) {
      router.push('/auth')
      return
    }

    fetchRun(token)

    // Auto-refresh if pending or in_progress
    if (autoRefresh) {
      const interval = setInterval(() => {
        fetchRun(token)
      }, 5000)
      return () => clearInterval(interval)
    }
  }, [runId, autoRefresh, router])

  const fetchRun = async (token: string) => {
    try {
      setLoading(true)
      const data = await getRunDetail(parseInt(runId), token)
      setRun(data)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch run')
    } finally {
      setLoading(false)
    }
  }

  const handleRefresh = () => {
    const token = localStorage.getItem('jwt_token')
    if (token) fetchRun(token)
  }

  return (
    <>
      <Header />
      <div className="max-w-7xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
        <div className="mb-8">
          <button
            onClick={() => router.back()}
            className="text-blue-600 hover:text-blue-900 mb-4"
          >
            ← Back
          </button>
          <div className="flex justify-between items-center">
            <h1 className="text-3xl font-bold text-gray-900">Analysis Run #{runId}</h1>
            <button
              onClick={handleRefresh}
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
            >
              Refresh
            </button>
          </div>
        </div>

        {error && <Error message={error} />}

        {loading ? (
          <Loading />
        ) : run ? (
          <>
            {/* Run Details */}
            <div className="bg-white rounded-lg shadow p-6 mb-8">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div>
                  <p className="text-gray-600 text-sm">Event</p>
                  <p className="text-lg font-semibold">{run.event}</p>
                </div>
                <div>
                  <p className="text-gray-600 text-sm">Branch</p>
                  <p className="text-lg font-semibold">{run.branch}</p>
                </div>
                <div>
                  <p className="text-gray-600 text-sm">Status</p>
                  <div className="mt-1">
                    <StatusBadge status={run.status} />
                  </div>
                </div>
                <div>
                  <p className="text-gray-600 text-sm">Total Issues</p>
                  <p className="text-lg font-semibold">{run.total_results}</p>
                </div>
              </div>

              {run.error && (
                <div className="mt-4 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
                  <p className="font-semibold">Error:</p>
                  <p>{run.error}</p>
                </div>
              )}

              <div className="mt-4 text-sm text-gray-600">
                <p>Created: {new Date(run.created_at).toLocaleString()}</p>
                {run.started_at && <p>Started: {new Date(run.started_at).toLocaleString()}</p>}
                {run.completed_at && (
                  <p>Completed: {new Date(run.completed_at).toLocaleString()}</p>
                )}
              </div>
            </div>

            {/* Auto-refresh toggle */}
            <div className="mb-6">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={autoRefresh && ['pending', 'in_progress'].includes(run.status)}
                  onChange={(e) => setAutoRefresh(e.target.checked)}
                  className="w-4 h-4"
                />
                <span className="text-gray-700">
                  Auto-refresh every 5 seconds (for pending/in-progress runs)
                </span>
              </label>
            </div>

            {/* Results */}
            <div className="bg-white rounded-lg shadow overflow-hidden">
              <div className="px-6 py-4 border-b border-gray-200">
                <h2 className="text-xl font-bold text-gray-900">Analysis Results</h2>
              </div>

              {run.results.length === 0 ? (
                <div className="px-6 py-8 text-center text-gray-500">
                  No issues found
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">
                          File
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">
                          Line
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">
                          Code
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">
                          Category
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">
                          Message
                        </th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200">
                      {run.results.map((result) => (
                        <tr key={result.id} className="hover:bg-gray-50">
                          <td className="px-6 py-4 text-sm text-gray-900 font-mono">
                            {result.file_path}
                          </td>
                          <td className="px-6 py-4 text-sm text-gray-600">
                            {result.line_number}
                          </td>
                          <td className="px-6 py-4 text-sm text-gray-600 font-semibold">
                            {result.code}
                          </td>
                          <td className="px-6 py-4 text-sm">
                            <CategoryBadge category={result.category} />
                          </td>
                          <td className="px-6 py-4 text-sm text-gray-700 max-w-md">
                            {result.message}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </>
        ) : null}
      </div>
    </>
  )
}
