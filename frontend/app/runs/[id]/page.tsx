'use client'

import { useEffect, useMemo, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { getRunDetail, AnalysisRunDetail } from '@/lib/api'
import { Header, Loading, ErrorAlert, StatusBadge, CategoryBadge } from '@/components/layout'
import { Button, Badge, Table, TableHeader, TableRow, TableHead, TableBody, TableCell, Card, CardHeader, CardTitle, CardContent } from '@/components/ui'
import { ArrowLeft, RefreshCw, FileCode, GitBranch } from 'lucide-react'

export default function RunDetailPage() {
  const params = useParams()
  const router = useRouter()
  const runId = Number(params?.id)

  const [data, setData] = useState<AnalysisRunDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [refreshing, setRefreshing] = useState(false)

  const token = useMemo(() => (typeof window !== 'undefined' ? localStorage.getItem('jwt_token') : null), [])

  const fetchDetail = async () => {
    try {
      setRefreshing(true)
      const result = await getRunDetail(runId, token ?? undefined)
      setData(result)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch run')
    } finally {
      setRefreshing(false)
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!token) {
      router.push('/auth')
      return
    }
    fetchDetail()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [runId])

  if (loading) return (
    <>
      <Header />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8"><Loading /></main>
    </>
  )

  if (error) return (
    <>
      <Header />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex items-center gap-3 mb-6">
          <ArrowLeft className="w-5 h-5 text-gray-500" />
          <Link href="/runs" className="text-sm text-gray-600 hover:text-gray-900">Back to Runs</Link>
        </div>
        <ErrorAlert message={error} />
      </main>
    </>
  )

  return (
    <>
      <Header />
      <main className="min-h-screen bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
          {/* Header */}
          <div className="flex items-center justify-between mb-8">
            <div>
              <div className="flex items-center gap-3 mb-2">
                <FileCode className="w-6 h-6 text-gray-400" />
                <h1 className="text-3xl font-bold text-gray-900">Run #{data?.id}</h1>
              </div>
              <p className="text-gray-600">Detailed analysis results and metadata</p>
            </div>
            <div className="flex items-center gap-3">
              <Link href="/runs">
                <Button variant="ghost" className="flex items-center gap-2"><ArrowLeft className="w-4 h-4" />Back</Button>
              </Link>
              <Button onClick={fetchDetail} disabled={refreshing} className="flex items-center gap-2">
                <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
                Refresh
              </Button>
            </div>
          </div>

          {/* Summary cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            <Card>
              <CardHeader><CardTitle>Status</CardTitle></CardHeader>
              <CardContent>
                <div className="flex items-center justify-between">
                  <StatusBadge status={data!.status} />
                  <Badge className="bg-amber-100 text-amber-800">{data!.total_results} issues</Badge>
                </div>
                <div className="mt-3 text-sm text-gray-600">
                  <div>Created: {new Date(data!.created_at).toLocaleString()}</div>
                  {data!.started_at && <div>Started: {new Date(data!.started_at).toLocaleString()}</div>}
                  {data!.completed_at && <div>Completed: {new Date(data!.completed_at).toLocaleString()}</div>}
                </div>
                {data!.error && (
                  <div className="mt-3 text-sm text-red-700 bg-red-50 border border-red-200 rounded p-3">Error: {data!.error}</div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader><CardTitle>GitHub Context</CardTitle></CardHeader>
              <CardContent>
                <div className="space-y-2 text-sm">
                  <div className="flex items-center gap-2"><GitBranch className="w-4 h-4 text-gray-500" /><span className="text-gray-600">Branch</span><code className="bg-gray-100 px-2 py-1 rounded text-xs text-gray-700 border border-gray-200">{data!.branch}</code></div>
                  {data!.commit_sha && (
                    <div className="flex items-center gap-2"><span className="text-gray-600">Commit</span><code className="bg-gray-100 px-2 py-1 rounded text-xs text-gray-700 border border-gray-200">{data!.commit_sha.slice(0,7)}</code></div>
                  )}
                  {data!.pr_number && (
                    <div className="flex items-center gap-2"><span className="text-gray-600">PR</span><Badge className="bg-blue-100 text-blue-800">#{data!.pr_number}</Badge></div>
                  )}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader><CardTitle>Repository</CardTitle></CardHeader>
              <CardContent>
                <div className="text-sm text-gray-700">ID: {data!.repository_id}</div>
                <div className="mt-2 text-sm text-gray-600">Event: {data!.event}</div>
              </CardContent>
            </Card>
          </div>

          {/* Results table */}
          <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>File</TableHead>
                    <TableHead>Line</TableHead>
                    <TableHead>Code</TableHead>
                    <TableHead>Name</TableHead>
                    <TableHead>Category</TableHead>
                    <TableHead>Message</TableHead>
                    <TableHead>Fixed</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data!.results.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={7}>
                        <div className="py-8 text-center text-gray-600">No issues found</div>
                      </TableCell>
                    </TableRow>
                  ) : (
                    data!.results.map((r) => (
                      <TableRow key={r.id} className="hover:bg-gray-50">
                        <TableCell>
                          <code className="bg-gray-100 px-2 py-1 rounded text-xs text-gray-700 border border-gray-200">{r.file_path}</code>
                        </TableCell>
                        <TableCell>
                          <span className="text-sm text-gray-700">{r.line_number}</span>
                        </TableCell>
                        <TableCell>
                          <Badge className="bg-gray-100 text-gray-800">{r.code}</Badge>
                        </TableCell>
                        <TableCell>
                          <span className="text-sm text-gray-900">{r.name}</span>
                        </TableCell>
                        <TableCell>
                          <CategoryBadge category={r.category} />
                        </TableCell>
                        <TableCell>
                          <span className="text-sm text-gray-700">{r.message}</span>
                        </TableCell>
                        <TableCell>
                          <Badge className={r.is_fixed ? 'bg-green-100 text-green-800' : 'bg-amber-100 text-amber-800'}>
                            {r.is_fixed ? 'Yes' : 'No'}
                          </Badge>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </div>
          </div>
        </div>
      </main>
    </>
  )
}
