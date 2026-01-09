'use client'

import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useEffect, useState } from 'react'
import { Button } from '@/components/ui'
import { Menu, X, LogOut, Home, FileText, Code2 } from 'lucide-react'

export function Header() {
  const router = useRouter()
  const [user, setUser] = useState<string | null>(null)
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

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

  return (
    <header className="sticky top-0 z-50 w-full bg-white border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          <div className="flex items-center gap-8">
            <Link href="/" className="flex items-center gap-2 hover:opacity-80 transition">
              <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
                <Code2 className="w-5 h-5 text-white" />
              </div>
              <span className="text-xl font-semibold text-gray-900">
                AGI Engineer
              </span>
            </Link>

            {user && (
              <nav className="hidden md:flex gap-6">
                <Link
                  href="/dashboard"
                  className="flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900 transition"
                >
                  <Home className="w-4 h-4" />
                  Dashboard
                </Link>
                <Link
                  href="/runs"
                  className="flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900 transition"
                >
                  <FileText className="w-4 h-4" />
                  Runs
                </Link>
              </nav>
            )}
          </div>

          <div className="hidden md:flex items-center gap-4">
            {user ? (
              <>
                <span className="text-sm text-gray-600">{user}</span>
                <Button
                  onClick={handleLogout}
                  variant="ghost"
                  className="text-gray-600 hover:text-gray-900"
                >
                  <LogOut className="w-4 h-4 mr-2" />
                  Logout
                </Button>
              </>
            ) : (
              <Link href="/auth">
                <Button className="bg-blue-600 hover:bg-blue-700 text-white">Sign In</Button>
              </Link>
            )}
          </div>

          {/* Mobile menu button */}
          <div className="md:hidden">
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-2 hover:bg-gray-100 rounded-md transition"
            >
              {mobileMenuOpen ? (
                <X className="w-6 h-6" />
              ) : (
                <Menu className="w-6 h-6" />
              )}
            </button>
          </div>
        </div>

        {/* Mobile menu */}
        {mobileMenuOpen && (
          <div className="md:hidden pb-4 border-t border-gray-200">
            {user ? (
              <>
                <Link
                  href="/dashboard"
                  className="block px-4 py-2 text-sm text-gray-600 hover:bg-gray-50 transition rounded"
                >
                  Dashboard
                </Link>
                <Link
                  href="/runs"
                  className="block px-4 py-2 text-sm text-gray-600 hover:bg-gray-50 transition rounded"
                >
                  Runs
                </Link>
                <button
                  onClick={handleLogout}
                  className="w-full text-left px-4 py-2 text-sm text-gray-600 hover:bg-gray-50 transition rounded mt-2"
                >
                  Logout
                </button>
              </>
            ) : (
              <Link href="/auth" className="block px-4 py-2">
                <Button className="w-full bg-blue-600 hover:bg-blue-700">Sign In</Button>
              </Link>
            )}
          </div>
        )}
      </div>
    </header>
  )
}

export function StatusBadge({ status }: { status: string }) {
  const colorMap: Record<string, { bg: string; text: string }> = {
    pending: { bg: 'bg-gray-100', text: 'text-gray-700' },
    in_progress: { bg: 'bg-blue-100', text: 'text-blue-700' },
    completed: { bg: 'bg-green-100', text: 'text-green-700' },
    failed: { bg: 'bg-red-100', text: 'text-red-700' },
  }

  const labelMap: Record<string, string> = {
    pending: '⏳ Pending',
    in_progress: '⚙️ In Progress',
    completed: '✅ Completed',
    failed: '❌ Failed',
  }

  const colors = colorMap[status] || colorMap.pending

  return (
    <div className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium ${colors.bg} ${colors.text}`}>
      <span>{labelMap[status] || status}</span>
    </div>
  )
}

export function CategoryBadge({ category }: { category: string }) {
  const colorMap: Record<string, { bg: string; text: string }> = {
    safe: { bg: 'bg-green-100', text: 'text-green-700' },
    review: { bg: 'bg-amber-100', text: 'text-amber-700' },
    suggestion: { bg: 'bg-blue-100', text: 'text-blue-700' },
  }

  const labelMap: Record<string, string> = {
    safe: '✅ Safe',
    review: '⚠️ Review',
    suggestion: '💡 Suggestion',
  }

  const colors = colorMap[category] || colorMap.suggestion

  return (
    <div className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium ${colors.bg} ${colors.text}`}>
      <span>{labelMap[category] || category}</span>
    </div>
  )
}

export function Loading() {
  return (
    <div className="flex justify-center items-center p-12">
      <div className="flex flex-col items-center gap-4">
        <div className="animate-spin rounded-full h-12 w-12 border-2 border-gray-200 border-t-blue-600"></div>
        <p className="text-gray-600">Loading...</p>
      </div>
    </div>
  )
}

export function ErrorAlert({ message }: { message: string }) {
  return (
    <div className="bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded-lg">
      <div className="flex items-center gap-2">
        <span className="text-lg">❌</span>
        <span>{message}</span>
      </div>
    </div>
  )
}

export function EmptyState({ message, icon = "📋" }: { message: string; icon?: string }) {
  return (
    <div className="text-center py-12">
      <div className="text-4xl mb-4">{icon}</div>
      <p className="text-gray-600 text-lg">{message}</p>
    </div>
  )
}

export function InfoAlert({ title, message }: { title: string; message: string }) {
  return (
    <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
      <div className="flex items-start gap-4">
        <div className="text-2xl">ℹ️</div>
        <div>
          <h3 className="font-semibold text-gray-900">{title}</h3>
          <p className="text-sm text-gray-600 mt-1">{message}</p>
        </div>
      </div>
    </div>
  )
}
