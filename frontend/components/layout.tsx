'use client'

import Link from 'next/link'
import { useRouter, usePathname } from 'next/navigation'
import { useEffect, useState } from 'react'
import { Button } from '@/components/ui'
import { LogOut, Home, BarChart3, FileText, Zap, Code2 } from 'lucide-react'

export function Header() {
  const router = useRouter()
  const pathname = usePathname()
  const [user, setUser] = useState<string | null>(null)

  useEffect(() => {
    const token = localStorage.getItem('jwt_token')
    const savedUser = localStorage.getItem('user')
    if (token && savedUser) {
      setUser(savedUser)
    }
  }, [])

  const handleLogout = () => {
    localStorage.removeItem('jwt_token')
    localStorage.removeItem('user')
    setUser(null)
    router.push('/')
  }

  const isActive = (path: string) => pathname === path

  const navItems = [
    { href: '/dashboard', label: 'Dashboard', icon: Home },
    { href: '/analytics', label: 'Analytics', icon: BarChart3 },
    { href: '/runs', label: 'Runs', icon: FileText },
    { href: '/v3-analysis', label: 'V3 Analysis', icon: Zap },
  ]

  if (!user) {
    return null
  }

  return (
    <aside className="fixed left-0 top-0 h-screen w-60 bg-card border-r border-border flex flex-col z-40">
      {/* Logo Section */}
      <div className="h-14 px-4 flex items-center border-b border-border">
        <Link href="/dashboard" className="flex items-center gap-2 hover:opacity-80 transition">
          <div className="w-6 h-6 bg-primary rounded flex items-center justify-center flex-shrink-0">
            <Code2 className="w-4 h-4 text-primary-foreground" />
          </div>
          <span className="text-sm font-semibold text-foreground truncate">
            AGI Engineer
          </span>
        </Link>
      </div>

      {/* Navigation Items */}
      <nav className="flex-1 px-2 py-4 space-y-1 overflow-y-auto">
        {navItems.map((item) => {
          const Icon = item.icon
          const active = isActive(item.href)
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`
                flex items-center gap-3 px-3 py-2.5 rounded text-sm font-medium
                transition-colors border-l-2
                ${active
                  ? 'bg-muted border-l-primary text-primary'
                  : 'border-l-transparent text-muted-foreground hover:text-foreground hover:bg-muted'
                }
              `}
            >
              <Icon className="w-4 h-4 flex-shrink-0" />
              <span className="truncate">{item.label}</span>
            </Link>
          )
        })}
      </nav>

      {/* User Section */}
      <div className="border-t border-border px-2 py-4 space-y-3">
        <div className="px-3 py-2 text-xs">
          <p className="text-muted-foreground truncate">{user}</p>
        </div>
        <Button
          onClick={handleLogout}
          variant="ghost"
          className="w-full justify-start text-muted-foreground hover:text-foreground text-xs"
          size="sm"
        >
          <LogOut className="w-4 h-4 mr-2 flex-shrink-0" />
          Logout
        </Button>
      </div>
    </aside>
  )
}

export function StatusBadge({ status }: { status: string }) {
  const colorMap: Record<string, { text: string }> = {
    pending: { text: 'text-muted-foreground' },
    in_progress: { text: 'text-primary' },
    completed: { text: 'text-foreground' },
    failed: { text: 'text-destructive' },
  }

  const labelMap: Record<string, string> = {
    pending: 'Pending',
    in_progress: 'In Progress',
    completed: 'Completed',
    failed: 'Failed',
  }

  const colors = colorMap[status] || colorMap.pending

  return (
    <div className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-muted border border-border ${colors.text}`}>
      <span>{labelMap[status] || status}</span>
    </div>
  )
}

export function CategoryBadge({ category }: { category: string }) {
  const labelMap: Record<string, string> = {
    safe: 'Safe',
    review: 'Review',
    suggestion: 'Suggestion',
  }

  return (
    <div className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-muted border border-border text-foreground">
      <span>{labelMap[category] || category}</span>
    </div>
  )
}

export function Loading() {
  return (
    <div className="flex justify-center items-center p-12">
      <div className="flex flex-col items-center gap-4">
        <div className="animate-spin rounded-full h-12 w-12 border-2 border-muted border-t-primary"></div>
        <p className="text-muted-foreground text-sm">Loading...</p>
      </div>
    </div>
  )
}

export function ErrorAlert({ message }: { message: string }) {
  return (
    <div className="bg-card border border-destructive text-destructive px-4 py-3 rounded">
      <div className="flex items-center gap-2">
        <span>{message}</span>
      </div>
    </div>
  )
}

export function EmptyState({ message }: { message: string }) {
  return (
    <div className="text-center py-8">
      <p className="text-muted-foreground text-sm">{message}</p>
    </div>
  )
}

export function InfoAlert({ title, message }: { title: string; message: string }) {
  return (
    <div className="bg-card border border-primary rounded p-4">
      <div className="flex items-start gap-3">
        <div>
          <h3 className="font-medium text-foreground text-sm">{title}</h3>
          <p className="text-xs text-muted-foreground mt-1">{message}</p>
        </div>
      </div>
    </div>
  )
}
