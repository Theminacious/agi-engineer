'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { AppShell, Loading, ErrorAlert } from '@/components/layout'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { healthCheck } from '@/lib/api'

type RouteStatus = {
  path: string
  ok: boolean
  status: number | null
}

export default function StatusPage() {
  const [backend, setBackend] = useState<{ ok: boolean; status?: string; version?: string } | null>(null)
  const [routes, setRoutes] = useState<RouteStatus[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const FRONTEND_ROUTES = ['/', '/auth', '/dashboard', '/runs']
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  useEffect(() => {
    const runChecks = async () => {
      try {
        setLoading(true)

        try {
          const res = await healthCheck()
          setBackend({ ok: true, status: res.status, version: (res as any).version })
        } catch (e) {
          setBackend({ ok: false })
        }

        const routeChecks: RouteStatus[] = []
        for (const path of FRONTEND_ROUTES) {
          try {
            const resp = await fetch(path, { method: 'GET' })
            routeChecks.push({ path, ok: resp.ok, status: resp.status })
          } catch {
            routeChecks.push({ path, ok: false, status: null })
          }
        }
        setRoutes(routeChecks)
        setError(null)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Status check failed')
      } finally {
        setLoading(false)
      }
    }

    runChecks()
  }, [])

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
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">System Status</h1>
            <p className="text-sm text-muted-foreground mt-1">Health check for backend and frontend routes</p>
          </div>
          <Link href="/">
            <Button variant="outline">Back to Home</Button>
          </Link>
        </div>

        {error && <ErrorAlert message={error} />}

        <div className="grid grid-cols-2 gap-6">
          {/* Backend */}
          <div className="border border-border rounded p-6 space-y-4">
            <h2 className="text-lg font-semibold">Backend</h2>
            <div className="flex items-center gap-3">
              <Badge variant={backend?.ok ? 'default' : 'destructive'}>
                {backend?.ok ? 'Healthy' : 'Unavailable'}
              </Badge>
              <span className="text-sm text-muted-foreground">API URL: {apiUrl}</span>
            </div>
            {backend?.ok && (
              <p className="text-sm text-muted-foreground">Version: {backend.version || 'unknown'}</p>
            )}
            <div>
              <Link href="/docs">
                <Button variant="outline" size="sm">Open API Docs</Button>
              </Link>
            </div>
          </div>

          {/* Frontend Routes */}
          <div className="border border-border rounded p-6 space-y-4">
            <h2 className="text-lg font-semibold">Frontend Routes</h2>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Route</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">HTTP</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {routes.map((r) => (
                  <TableRow key={r.path}>
                    <TableCell>
                      <Link href={r.path} className="text-primary hover:underline text-sm">
                        {r.path}
                      </Link>
                    </TableCell>
                    <TableCell>
                      <Badge variant={r.ok ? 'default' : 'destructive'} className="text-xs">
                        {r.ok ? 'OK' : 'Error'}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right text-sm text-muted-foreground">
                      {r.status ?? '—'}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </div>

        {/* Notes */}
        <div className="border border-border rounded p-6 space-y-4">
          <h2 className="text-lg font-semibold">Notes</h2>
          <ul className="list-disc pl-5 text-sm text-muted-foreground space-y-2">
            <li>If a route shows Error, clear the Next.js cache: <code className="text-xs">rm -rf .next</code> and restart dev server</li>
            <li>Ensure backend is running on {apiUrl}. Start it via Uvicorn</li>
            <li>Set <code className="text-xs">NEXT_PUBLIC_API_URL</code> in <code className="text-xs">.env.local</code> if your backend URL differs</li>
          </ul>
        </div>
      </div>
    </AppShell>
  )
}
