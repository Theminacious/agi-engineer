'use client'

import Link from 'next/link'
import { useRouter, usePathname } from 'next/navigation'
import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { 
  LogOut, 
  Home, 
  BarChart3, 
  Activity,
  Wrench,
  Shield,
  Settings, 
  AlertCircle,
  CheckCircle2,
  Clock,
  Loader2,
  XCircle
} from 'lucide-react'
import { cn } from '@/lib/utils'

export function AppShell({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const pathname = usePathname()
  const [user, setUser] = useState<string | null>(null)

  useEffect(() => {
    const token = localStorage.getItem('jwt_token')
    const savedUser = localStorage.getItem('user')
    if (token && savedUser) {
      try {
        const parsed = JSON.parse(savedUser)
        setUser(parsed.email || parsed) 
      } catch {
        setUser(savedUser)
      }
    }
  }, [])

  const handleLogout = () => {
    localStorage.removeItem('jwt_token')
    localStorage.removeItem('user')
    setUser(null)
    router.push('/')
  }

  const isActive = (path: string) => {
    if (path === '/governance') {
      return pathname === path || pathname?.startsWith('/governance/')
    }
    return pathname === path
  }

  const primaryNav = [
    { href: '/dashboard', label: 'Dashboard', icon: Home },
    { href: '/runs', label: 'Runs', icon: Activity },
    { href: '/governance', label: 'Governance', icon: Shield },
  ]

  const secondaryNav = [
    { href: '/analytics', label: 'Analytics', icon: BarChart3 },
    { href: '/plans', label: 'Plans', icon: Settings },
  ]

  if (!user) return null

  return (
    <div className="flex h-screen bg-background">
      {/* Sidebar */}
      <aside className="w-64 border-r border-border flex flex-col">
        {/* Logo */}
        <div className="h-14 flex items-center px-6 border-b border-border">
          <Link href="/dashboard" className="flex items-center gap-2">
            <div className="w-6 h-6 rounded bg-primary" />
            <span className="text-sm font-semibold">AGI Engineer</span>
          </Link>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-4 py-6 space-y-12">
          {/* Primary */}
          <div className="space-y-1">
            <div className="px-2 mb-2">
              <span className="text-xs text-muted-foreground uppercase tracking-wider font-semibold">Primary</span>
            </div>
            {primaryNav.map((item) => {
              const Icon = item.icon
              const active = isActive(item.href)
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "flex items-center gap-2 px-2 py-1.5 rounded text-sm font-medium transition-colors",
                    active 
                      ? "bg-secondary text-foreground" 
                      : "text-muted-foreground hover:bg-secondary/50 hover:text-foreground"
                  )}
                >
                  <Icon className="w-4 h-4" />
                  {item.label}
                </Link>
              )
            })}
          </div>

          {/* Secondary */}
          <div className="space-y-1">
            <div className="px-2 mb-2">
              <span className="text-xs text-muted-foreground uppercase tracking-wider font-semibold">Secondary</span>
            </div>
            {secondaryNav.map((item) => {
              const Icon = item.icon
              const active = isActive(item.href)
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "flex items-center gap-2 px-2 py-1.5 rounded text-sm font-medium transition-colors",
                    active 
                      ? "bg-secondary text-foreground" 
                      : "text-muted-foreground hover:bg-secondary/50 hover:text-foreground"
                  )}
                >
                  <Icon className="w-4 h-4" />
                  {item.label}
                </Link>
              )
            })}
          </div>
        </nav>

        {/* User */}
        <div className="p-4 border-t border-border">
          <div className="flex items-center gap-2 text-sm">
            <div className="w-7 h-7 rounded-full bg-secondary flex items-center justify-center text-xs font-semibold">
              {user ? user.charAt(0).toUpperCase() : 'U'}
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium truncate">{user?.split('@')[0]}</div>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleLogout}
              className="h-7 w-7 p-0"
            >
              <LogOut className="h-3.5 w-3.5" />
            </Button>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-y-auto">
        {children}
      </main>
    </div>
  )
}

// Utility Components
export function StatusBadge({ status }: { status: string }) {
  const config: Record<string, { icon: any; className: string }> = {
    pending: { icon: Clock, className: 'bg-muted text-muted-foreground' },
    in_progress: { icon: Loader2, className: 'bg-primary/10 text-primary' },
    completed: { icon: CheckCircle2, className: 'bg-green-500/10 text-green-400' },
    failed: { icon: XCircle, className: 'bg-destructive/10 text-destructive' },
  }

  const { icon: Icon, className } = config[status] || config.pending
  const label = status.replace('_', ' ')

  return (
    <div className={cn("inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-medium", className)}>
      <Icon className={cn("w-3 h-3", status === 'in_progress' && 'animate-spin')} />
      <span className="capitalize">{label}</span>
    </div>
  )
}

export function Loading({ text = "Loading..." }: { text?: string }) {
  return (
    <div className="flex h-64 w-full items-center justify-center">
      <div className="flex flex-col items-center gap-4">
         <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
         <p className="text-sm text-muted-foreground">{text}</p>
      </div>
    </div>
  )
}

export function ErrorAlert({ title, message }: { title?: string; message: string }) {
  return (
    <div className="flex items-start gap-3 rounded border border-destructive/20 bg-destructive/5 px-4 py-3">
      <AlertCircle className="w-4 h-4 text-destructive shrink-0 mt-0.5" />
      <div className="flex-1 space-y-1">
        {title && <h3 className="text-sm font-semibold text-destructive">{title}</h3>}
        <p className="text-sm text-destructive/80">{message}</p>
      </div>
    </div>
  )
}

export function EmptyState({ message }: { message: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <p className="text-sm text-muted-foreground">{message}</p>
    </div>
  )
}