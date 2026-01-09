'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { Header, Loading, ErrorAlert } from '@/components/layout'
import { Badge, Card, CardHeader, CardTitle, CardContent, Button, Table, TableHeader, TableRow, TableHead, TableBody, TableCell } from '@/components/ui'
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

        // Backend health
        try {
          const res = await healthCheck()
          setBackend({ ok: true, status: res.status, version: (res as any).version })
        } catch (e) {
          setBackend({ ok: false })
        }

        // Frontend routes
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

  if (loading) return (
    <div>
      <Header />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Loading />
      </main>
    </div>
  )

  return (
    <div>
      <Header />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-semibold text-gray-900">System Status</h1>
          <Link href="/">
            <Button variant="ghost">Back to Home</Button>
          </Link>
        </div>

        {error && <ErrorAlert message={error} />}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Card>
            <CardHeader>
              <CardTitle>Backend</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-3">
                <Badge className={backend?.ok ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}>
                  {backend?.ok ? 'Healthy' : 'Unavailable'}
                </Badge>
                <span className="text-sm text-gray-600">API URL: {apiUrl}</span>
              </div>
              {backend?.ok && (
                <p className="mt-2 text-sm text-gray-600">Version: {backend.version || 'unknown'}</p>
              )}
              <div className="mt-4">
                <Link href="/docs">
                  <Button variant="outline">Open API Docs</Button>
                </Link>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Frontend Routes</CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Route</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>HTTP</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {routes.map((r) => (
                    <TableRow key={r.path}>
                      <TableCell>
                        <Link href={r.path} className="text-blue-600 hover:underline">{r.path}</Link>
                      </TableCell>
                      <TableCell>
                        <Badge className={r.ok ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}>
                          {r.ok ? 'OK' : 'Error'}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <span className="text-sm text-gray-600">{r.status ?? '—'}</span>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </div>

        <div className="mt-6">
          <Card>
            <CardHeader>
              <CardTitle>Notes</CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="list-disc pl-5 text-sm text-gray-700 space-y-2">
                <li>If a route shows Error, clear the Next.js cache: `rm -rf .next` and restart dev server.</li>
                <li>Ensure backend is running on {apiUrl}. You can start it via Uvicorn.</li>
                <li>Set `NEXT_PUBLIC_API_URL` in `.env.local` if your backend URL differs.</li>
              </ul>
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  )
}
