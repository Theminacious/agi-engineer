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
