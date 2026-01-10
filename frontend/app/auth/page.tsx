'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { getOAuthUrl, oauthCallback } from '@/lib/api'
import { Github, AlertCircle, ShieldCheck, Zap, Terminal, Command, CheckCircle2 } from 'lucide-react'
import { motion } from 'framer-motion'

/* --- COMPONENTS --- */

// 1. Moving 3D Grid Background
function RetroGrid() {
  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none [perspective:1000px]">
      <div className="absolute inset-0 bg-gradient-to-t from-[#050505] via-transparent to-[#050505] z-10" />
      <div 
        className="absolute inset-0 opacity-20"
        style={{
          transform: 'rotateX(60deg)',
          backgroundImage: 'linear-gradient(to right, #333 1px, transparent 1px), linear-gradient(to bottom, #333 1px, transparent 1px)',
          backgroundSize: '40px 40px',
          animation: 'gridMove 20s linear infinite',
        }}
      />
      {/* Horizon Glow */}
      <div className="absolute top-0 left-0 right-0 h-[50vh] bg-gradient-to-b from-blue-900/10 to-transparent blur-3xl" />
    </div>
  )
}

// 2. Typing Code Background (Visual Context)
function CodeBackground() {
  return (
    <div className="absolute right-[-10%] top-[20%] w-[400px] h-[400px] opacity-10 pointer-events-none select-none font-mono text-xs text-blue-300 hidden lg:block rotate-12 blur-[2px]">
      <div className="space-y-1">
        <p>{"> initializing auth_sequence..."}</p>
        <p>{"> checking_integrity: OK"}</p>
        <p>{"> establishing_secure_link..."}</p>
        <p className="text-blue-500">{"> handshake_protocol: ACTIVE"}</p>
        {Array.from({ length: 10 }).map((_, i) => (
          <p key={i} className="opacity-50">{`0x7F${i}4A... [encrypted]`}</p>
        ))}
      </div>
    </div>
  )
}

/* --- MAIN PAGE --- */

export default function AuthPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // --- LOGIC ---
  const handleCallback = async (code: string, state: string) => {
    try {
      setLoading(true)
      const response = await oauthCallback(code, state)
      localStorage.setItem('jwt_token', response.token)
      localStorage.setItem('user', JSON.stringify(response.user))
      router.push('/dashboard')
    } catch (err) {
      setError((err as Error).message || 'Authentication failed')
      setLoading(false)
    }
  }

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const code = params.get('code')
    const state = params.get('state')
    if (code && state) handleCallback(code, state)
  }, [])

  const handleLogin = async () => {
    try {
      setError(null)
      setLoading(true)
      const { authorization_url } = await getOAuthUrl()
      window.location.href = authorization_url
    } catch (err) {
      setError((err as Error).message || 'Failed to start authentication')
      setLoading(false)
    }
  }

  // --- UI ---
  return (
    <div className="relative min-h-screen bg-[#050505] flex items-center justify-center overflow-hidden font-sans text-white selection:bg-blue-500/30">
      
      {/* LAYER 1: Background FX */}
      <RetroGrid />
      <CodeBackground />
      
      {/* LAYER 2: Main Card */}
      <motion.div 
        initial={{ opacity: 0, scale: 0.95, y: 10 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
        className="relative z-20 w-full max-w-[400px] mx-4"
      >
        {/* Glow behind card */}
        <div className="absolute -inset-1 bg-gradient-to-r from-blue-500 to-purple-600 rounded-2xl blur-lg opacity-20" />

        <div className="relative bg-[#0A0A0A]/90 backdrop-blur-2xl border border-white/10 rounded-2xl p-8 shadow-2xl ring-1 ring-white/5 overflow-hidden group">
            
            {/* Top Shine */}
            <div className="absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-white/20 to-transparent" />

            {/* Header */}
            <div className="flex flex-col items-center mb-8">
                <div className="w-14 h-14 bg-[#111] rounded-2xl flex items-center justify-center border border-white/10 shadow-inner mb-5 relative overflow-hidden">
                    <div className="absolute inset-0 bg-blue-500/10 blur-xl" />
                    <Zap className="w-6 h-6 text-white relative z-10" fill="currentColor" />
                </div>
                
                <h1 className="text-2xl font-bold tracking-tight text-center mb-2">
                    Initialize Workspace
                </h1>
                <p className="text-sm text-gray-500 text-center px-4">
                    Connect your GitHub to start the automated analysis engine.
                </p>
            </div>

            {/* Content Area */}
            <div className="space-y-6 relative">
                
                {/* Error Banner */}
                {error && (
                    <motion.div 
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        className="bg-red-500/10 border border-red-500/20 rounded-lg p-3 flex items-start gap-3"
                    >
                        <AlertCircle className="w-4 h-4 text-red-400 mt-0.5" />
                        <p className="text-xs text-red-200 font-medium">{error}</p>
                    </motion.div>
                )}

                {/* Loading State */}
                {loading ? (
                    <div className="flex flex-col items-center justify-center py-6 space-y-4">
                        <div className="relative w-16 h-16">
                            <div className="absolute inset-0 rounded-full border-t-2 border-r-2 border-blue-500 animate-spin" />
                            <div className="absolute inset-2 rounded-full border-t-2 border-l-2 border-purple-500 animate-spin-reverse" />
                            <div className="absolute inset-0 flex items-center justify-center">
                                <Github className="w-6 h-6 text-white/20" />
                            </div>
                        </div>
                        <div className="text-center space-y-1">
                            <p className="text-sm font-medium text-white">Authenticating...</p>
                            <p className="text-[10px] text-gray-500 font-mono">negotiating_token_exchange</p>
                        </div>
                    </div>
                ) : (
                    /* The "Hero" Button */
                    <button
                        onClick={handleLogin}
                        className="group relative w-full h-12 bg-white hover:bg-gray-100 text-black font-bold rounded-xl transition-all duration-300 flex items-center justify-center gap-3 overflow-hidden shadow-[0_0_20px_-5px_rgba(255,255,255,0.3)] hover:shadow-[0_0_30px_-5px_rgba(255,255,255,0.5)] hover:scale-[1.02]"
                    >
                        {/* Shimmer Effect */}
                        <div className="absolute top-0 -left-[100%] w-[50%] h-full bg-gradient-to-r from-transparent via-white/50 to-transparent transform -skew-x-12 group-hover:animate-shine" />
                        
                        <Github className="w-5 h-5 transition-transform group-hover:scale-110" />
                        <span className="relative z-10">Continue with GitHub</span>
                    </button>
                )}

                {/* Security Badge */}
                <div className="flex items-center justify-center gap-6 pt-2 opacity-60">
                    <div className="flex items-center gap-2 text-[10px] text-gray-400">
                        <ShieldCheck className="w-3 h-3 text-green-500" />
                        <span>SOC2 Compliant</span>
                    </div>
                    <div className="h-3 w-[1px] bg-gray-700" />
                    <div className="flex items-center gap-2 text-[10px] text-gray-400">
                        <div className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
                        <span>System Online</span>
                    </div>
                </div>

            </div>
        </div>

        {/* Footer Links */}
        <div className="flex justify-center gap-4 mt-8 text-[11px] text-gray-600 font-medium">
            <span className="hover:text-gray-400 cursor-pointer transition-colors">Privacy Policy</span>
            <span>•</span>
            <span className="hover:text-gray-400 cursor-pointer transition-colors">Terms of Service</span>
            <span>•</span>
            <span className="hover:text-gray-400 cursor-pointer transition-colors">Help</span>
        </div>

      </motion.div>

      {/* CSS Animations */}
      <style jsx global>{`
        @keyframes gridMove {
            0% { transform: rotateX(60deg) translateY(0); }
            100% { transform: rotateX(60deg) translateY(40px); }
        }
        @keyframes shine {
            0% { left: -100%; }
            100% { left: 200%; }
        }
        .animate-shine {
            animation: shine 1.5s ease-out infinite;
        }
        .animate-spin-reverse {
            animation: spin 1s linear infinite reverse;
        }
        @keyframes spin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  )
}