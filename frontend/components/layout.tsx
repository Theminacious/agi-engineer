'use client'

import Link from 'next/link'
import { useRouter, usePathname } from 'next/navigation'
import { useEffect, useState } from 'react'
import { Button } from '@/components/ui'
import { 
  LogOut, 
  Home, 
  BarChart3, 
  FileText, 
  Zap, 
  ChevronDown, 
  Settings, 
  HelpCircle,
  AlertCircle,
  CheckCircle2,
  Clock,
  Loader2,
  Info,
  Layers
} from 'lucide-react'

// --- CUSTOM "NEURAL CONSTRUCT" LOGO ---
const AGILogo = ({ className }: { className?: string }) => (
  <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" className={className}>
    {/* The Core: A diamond representing the 'Singularity' or AI Core */}
    <path 
      d="M12 8L15 12L12 16L9 12L12 8Z" 
      fill="currentColor" 
      className="text-white"
    />
    
    {/* The Shell: Abstract brackets representing Code/Engineering */}
    {/* Left Bracket */}
    <path 
      d="M7 6L3 12L7 18" 
      stroke="currentColor" 
      strokeWidth="2" 
      strokeLinecap="round" 
      strokeLinejoin="round" 
      className="text-gray-400"
    />
    {/* Right Bracket */}
    <path 
      d="M17 6L21 12L17 18" 
      stroke="currentColor" 
      strokeWidth="2" 
      strokeLinecap="round" 
      strokeLinejoin="round" 
      className="text-gray-400"
    />
    
    {/* Connection Lines: Tying logic to the core */}
    <path d="M7 12H9" stroke="currentColor" strokeWidth="2" className="text-gray-500/50" />
    <path d="M15 12H17" stroke="currentColor" strokeWidth="2" className="text-gray-500/50" />
  </svg>
)

// --- SIDEBAR COMPONENT ---

export function Header() {
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

  const isActive = (path: string) => pathname === path

  const navItems = [
    { href: '/dashboard', label: 'Dashboard', icon: Home },
    { href: '/analytics', label: 'Analytics', icon: BarChart3 },
    { href: '/runs', label: 'Runs & Logs', icon: Layers },
    { href: '/v3-analysis', label: 'AGI Engine', icon: Zap },
  ]

  if (!user) return null

  return (
    <aside className="fixed left-0 top-0 bottom-0 z-50 w-[260px] flex flex-col bg-[#050505] border-r border-[#1F1F1F]">
      
      {/* 1. Header: Workspace Dropdown (Cursor Style) */}
      <div className="px-3 pt-4 pb-2">
        <button className="w-full flex items-center justify-between p-2 rounded-md hover:bg-[#1A1A1A] transition-colors group">
          <div className="flex items-center gap-2.5">
             {/* New Premium Logo */}
             <div className="w-6 h-6 flex items-center justify-center">
                <AGILogo className="w-6 h-6" />
             </div>
             <span className="text-[13px] font-semibold text-white tracking-tight">AGI Engineer</span>
          </div>
          <ChevronDown className="w-3.5 h-3.5 text-gray-500 group-hover:text-white transition-colors" />
        </button>
      </div>

      {/* 2. Navigation (Compact & Minimal) */}
      <nav className="flex-1 px-2 py-4 space-y-0.5">
        <div className="px-2 mb-2">
          <p className="text-[10px] font-medium text-[#444] uppercase tracking-wider">Workspace</p>
        </div>

        {navItems.map((item) => {
          const Icon = item.icon
          const active = isActive(item.href)
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`
                flex items-center gap-2.5 px-2 py-1.5 rounded-md text-[13px] font-medium transition-all group
                ${active 
                  ? 'bg-[#1A1A1A] text-white' 
                  : 'text-[#888] hover:text-white hover:bg-[#111]'
                }
              `}
            >
              <Icon className={`w-4 h-4 ${active ? 'text-white' : 'text-[#666] group-hover:text-[#999]'}`} />
              <span className="truncate">{item.label}</span>
              
              {/* Subtle Active Dot */}
              {active && <div className="ml-auto w-1 h-1 rounded-full bg-blue-500/80 shadow-[0_0_8px_rgba(59,130,246,0.8)]" />}
            </Link>
          )
        })}

        <div className="mt-6 px-2 mb-2">
          <p className="text-[10px] font-medium text-[#444] uppercase tracking-wider">Preferences</p>
        </div>
        <button className="w-full flex items-center gap-2.5 px-2 py-1.5 rounded-md text-[13px] font-medium text-[#888] hover:text-white hover:bg-[#111] transition-colors">
            <Settings className="w-4 h-4 text-[#666]" />
            <span>Settings</span>
        </button>
        <button className="w-full flex items-center gap-2.5 px-2 py-1.5 rounded-md text-[13px] font-medium text-[#888] hover:text-white hover:bg-[#111] transition-colors">
            <HelpCircle className="w-4 h-4 text-[#666]" />
            <span>Documentation</span>
        </button>
      </nav>

      {/* 3. Footer: User Profile (Pieces Style - Minimal) */}
      <div className="p-3 border-t border-[#1F1F1F]">
        <div className="flex items-center gap-3 p-2 rounded-md hover:bg-[#111] transition-colors cursor-default">
          <div className="w-6 h-6 rounded bg-gradient-to-b from-[#333] to-[#222] border border-[#333] flex items-center justify-center shrink-0">
             <span className="text-[10px] font-bold text-gray-300">
                {user ? user.charAt(0).toUpperCase() : 'U'}
             </span>
          </div>
          
          <div className="flex-1 min-w-0 flex flex-col justify-center">
            <p className="text-[12px] font-medium text-gray-200 truncate leading-none mb-0.5">{user?.split('@')[0]}</p>
            <p className="text-[10px] text-gray-600 truncate leading-none">Free Plan</p>
          </div>

          <button
            onClick={handleLogout}
            className="text-gray-600 hover:text-gray-300 transition-colors"
            title="Sign out"
          >
            <LogOut className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </aside>
  )
}

// --- UTILITY COMPONENTS (Badges & Alerts) ---

export function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    pending: 'bg-[#1A1A1A] text-gray-400 border-[#333]',
    in_progress: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
    completed: 'bg-green-500/10 text-green-400 border-green-500/20',
    failed: 'bg-red-500/10 text-red-400 border-red-500/20',
  }
  const icons: Record<string, any> = {
    pending: Clock,
    in_progress: Loader2,
    completed: CheckCircle2,
    failed: AlertCircle
  }

  const style = styles[status] || styles.pending
  const Icon = icons[status] || Clock
  const label = status.replace('_', ' ')

  return (
    <div className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-medium border ${style}`}>
      <Icon className={`w-3 h-3 ${status === 'in_progress' ? 'animate-spin' : ''}`} />
      <span className="capitalize">{label}</span>
    </div>
  )
}

export function CategoryBadge({ category }: { category: string }) {
  // Monochromatic/Technical look
  const styles: Record<string, string> = {
    safe: 'bg-[#111] text-gray-300 border-[#333]',
    review: 'bg-[#1A1A00] text-yellow-500/80 border-yellow-900/30',
    suggestion: 'bg-[#00111A] text-blue-400/80 border-blue-900/30',
  }
  const style = styles[category.toLowerCase()] || 'bg-[#111] text-gray-400 border-[#333]'

  return (
    <div className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium uppercase tracking-wider border ${style}`}>
      {category}
    </div>
  )
}

export function Loading() {
  return (
    <div className="flex h-32 w-full items-center justify-center rounded-lg border border-dashed border-[#222] bg-[#0A0A0A]">
      <div className="flex flex-col items-center gap-2">
         <Loader2 className="w-5 h-5 animate-spin text-gray-500" />
         <p className="text-[11px] font-medium text-gray-600">Syncing...</p>
      </div>
    </div>
  )
}

export function ErrorAlert({ message }: { message: string }) {
  return (
    <div className="flex items-center gap-3 rounded-md border border-red-900/30 bg-red-950/10 p-3">
      <AlertCircle className="w-4 h-4 text-red-500 shrink-0" />
      <p className="text-xs text-red-300">{message}</p>
    </div>
  )
}

export function EmptyState({ message }: { message: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-10 rounded-lg border border-dashed border-[#222] bg-[#0A0A0A]">
      <div className="h-8 w-8 rounded bg-[#111] flex items-center justify-center mb-3 text-gray-600">
        <FileText className="w-4 h-4" />
      </div>
      <p className="text-xs text-gray-500">{message}</p>
    </div>
  )
}

export function InfoAlert({ title, message }: { title: string; message: string }) {
  return (
    <div className="flex items-start gap-3 rounded-lg border border-blue-500/20 bg-blue-500/5 p-4">
      <Info className="w-5 h-5 text-blue-500 shrink-0 mt-0.5" />
      <div>
        <h3 className="text-sm font-bold text-blue-400 mb-1">{title}</h3>
        <p className="text-xs text-blue-300/70 leading-relaxed">{message}</p>
      </div>
    </div>
  )
}