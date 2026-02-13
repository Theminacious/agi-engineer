'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { AppShell, Loading, ErrorAlert } from '@/components/layout'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Clock, Plus, Trash2, Play } from 'lucide-react'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface Schedule {
  repository_id: number
  repository_name: string
  interval_hours: number
  enabled: boolean
  next_run: string
}

export default function SchedulingPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [schedules, setSchedules] = useState<Schedule[]>([])
  const [showForm, setShowForm] = useState(false)
  const [formData, setFormData] = useState({ interval_hours: 24 })

  const token = typeof window !== 'undefined' ? localStorage.getItem('jwt_token') : null

  const getHeaders = (): Record<string, string> => {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' }
    if (token) headers['Authorization'] = `Bearer ${token}`
    return headers
  }

  const fetchSchedules = async () => {
    try {
      const headers = getHeaders()
      const res = await fetch(`${API_BASE}/api/schedule/schedules?enabled_only=false`, { headers })
      
      if (!res.ok) throw new Error('Failed to fetch schedules')
      
      const data = await res.json()
      setSchedules(data.schedules || [])
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch schedules')
    } finally {
      setLoading(false)
    }
  }

  const handleRemoveSchedule = async (repoId: number) => {
    try {
      const headers = getHeaders()
      const res = await fetch(
        `${API_BASE}/api/schedule/repositories/${repoId}/schedule/disable`,
        { method: 'POST', headers }
      )
      
      if (!res.ok) throw new Error('Failed to remove schedule')
      
      await fetchSchedules()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to remove schedule')
    }
  }

  const handleRunNow = async () => {
    try {
      const headers = getHeaders()
      const res = await fetch(
        `${API_BASE}/api/schedule/run-due-analyses`,
        { method: 'POST', headers }
      )
      
      if (!res.ok) throw new Error('Failed to run analyses')
      
      const data = await res.json()
      alert(`Queued ${data.count} analysis runs`)
      await fetchSchedules()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to run analyses')
    }
  }

  useEffect(() => {
    if (!token) {
      router.push('/auth')
      return
    }
    fetchSchedules()
  }, [token, router])

  if (loading) {
    return (
      <AppShell>
        <Loading />
      </AppShell>
    )
  }

  return (
    <AppShell>
      <div className="max-w-7xl mx-auto px-6 py-8 space-y-8">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Analysis Scheduling</h1>
            <p className="text-sm text-muted-foreground mt-1">Set up recurring code analysis for your repositories</p>
          </div>
          <div className="flex gap-2">
            <Button onClick={handleRunNow} variant="outline">
              <Play className="w-4 h-4 mr-2" />
              Run Due Now
            </Button>
            <Button onClick={() => setShowForm(!showForm)}>
              <Plus className="w-4 h-4 mr-2" />
              Add Schedule
            </Button>
          </div>
        </div>

        {error && <ErrorAlert message={error} />}

        {/* Schedules Table */}
        <div className="space-y-4">
          <h2 className="text-lg font-semibold">Active Schedules</h2>
          {schedules.length === 0 ? (
            <div className="border border-border rounded p-12 text-center">
              <Clock className="w-12 h-12 mx-auto mb-4 text-muted-foreground opacity-50" />
              <p className="text-sm text-muted-foreground">No schedules configured yet</p>
              <p className="text-xs text-muted-foreground mt-1">Add a schedule to automate analysis runs</p>
            </div>
          ) : (
            <div className="border border-border rounded">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Repository</TableHead>
                    <TableHead>Interval</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Next Run</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {schedules.map((schedule) => (
                    <TableRow key={schedule.repository_id}>
                      <TableCell className="font-medium">{schedule.repository_name}</TableCell>
                      <TableCell className="text-sm text-muted-foreground">Every {schedule.interval_hours}h</TableCell>
                      <TableCell>
                        <Badge variant={schedule.enabled ? 'default' : 'secondary'}>
                          {schedule.enabled ? 'Enabled' : 'Disabled'}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {new Date(schedule.next_run).toLocaleString()}
                      </TableCell>
                      <TableCell className="text-right">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleRemoveSchedule(schedule.repository_id)}
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </div>
      </div>
    </AppShell>
  )
}

          {error && <div className="mb-6"><ErrorAlert message={error} /></div>}

          {/* Info Card */}
          <Card className="mb-8 bg-blue-50 border-blue-200">
            <CardContent className="pt-6">
              <p className="text-sm text-blue-900">
                📋 <strong>Recurring Analysis:</strong> Set up automatic code analysis at regular intervals for any repository.
                The system will run Ruff and ESLint, apply AGI Engineer v3 auto-fixes for safe issues, and track results over time.
              </p>
            </CardContent>
          </Card>

          {/* Schedules List */}
          <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
            <div className="p-6 border-b border-gray-200">
              <h2 className="text-lg font-semibold text-gray-900">Active Schedules</h2>
              <p className="text-sm text-gray-600 mt-1">{schedules.length} schedule(s) configured</p>
            </div>

            {schedules.length === 0 ? (
              <div className="p-12 text-center">
                <Clock className="w-12 h-12 text-gray-300 mx-auto mb-4" />
                <h3 className="text-lg font-semibold text-gray-900 mb-2">No schedules yet</h3>
                <p className="text-gray-600 mb-6">Create your first schedule to enable recurring analysis</p>
                <Button
                  onClick={() => setShowForm(true)}
                  className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white"
                >
                  <Plus className="w-4 h-4" />
                  Create Schedule
                </Button>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-gray-200 bg-gray-50">
                      <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase">Repository</th>
                      <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase">Frequency</th>
                      <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase">Next Run</th>
                      <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase">Status</th>
                      <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200">
                    {schedules.map((schedule) => (
                      <tr key={schedule.repository_id} className="hover:bg-gray-50">
                        <td className="px-6 py-4 text-sm font-medium text-gray-900">{schedule.repository_name}</td>
                        <td className="px-6 py-4 text-sm text-gray-600">Every {schedule.interval_hours}h</td>
                        <td className="px-6 py-4 text-sm text-gray-600">
                          {schedule.next_run ? new Date(schedule.next_run).toLocaleString() : 'N/A'}
                        </td>
                        <td className="px-6 py-4 text-sm">
                          <Badge className={schedule.enabled ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}>
                            {schedule.enabled ? 'Active' : 'Disabled'}
                          </Badge>
                        </td>
                        <td className="px-6 py-4 text-sm">
                          <button
                            onClick={() => handleRemoveSchedule(schedule.repository_id)}
                            className="inline-flex items-center gap-1 px-3 py-1 rounded-lg bg-red-50 hover:bg-red-100 border border-red-200 text-red-600 text-xs font-semibold transition-all"
                          >
                            <Trash2 className="w-3 h-3" />
                            Remove
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Active Schedules Summary */}
          {schedules.length > 0 && (
            <div className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-6">
              <Card>
                <CardHeader><CardTitle className="text-sm">Total Schedules</CardTitle></CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold text-gray-900">{schedules.length}</div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader><CardTitle className="text-sm">Active</CardTitle></CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold text-green-600">{schedules.filter(s => s.enabled).length}</div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader><CardTitle className="text-sm">Avg. Frequency</CardTitle></CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold text-blue-600">
                    {(schedules.reduce((sum, s) => sum + s.interval_hours, 0) / schedules.length).toFixed(0)}h
                  </div>
                </CardContent>
              </Card>
            </div>
          )}
        </div>
      </main>
    </>
  )
}
