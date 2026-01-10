'use client'

import { useEffect, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { Loader2, ShieldCheck } from 'lucide-react'

// --- SHARED UI COMPONENT ---
// We extract this so the Suspense fallback looks identical to the active loading state
function LoadingState({ label = "Authenticating..." }: { label?: string }) {
  return (
    <div className="min-h-screen bg-[#050505] flex items-center justify-center relative overflow-hidden font-sans text-white">
      
      {/* 1. Background Texture (Noise & Glow) */}
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute inset-0 opacity-[0.03]" style={{ backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E")` }}></div>
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] bg-blue-500/5 blur-[120px] rounded-full" />
      </div>

      {/* 2. Glass Card */}
      <div className="relative z-10 w-full max-w-[320px] mx-4">
        <div className="bg-[#0A0A0A]/90 backdrop-blur-xl border border-white/10 rounded-2xl p-8 shadow-2xl flex flex-col items-center text-center ring-1 ring-white/5">
          
          {/* Animated Loader Icon */}
          <div className="relative w-12 h-12 mb-6 flex items-center justify-center">
             <div className="absolute inset-0 rounded-full border-t-2 border-r-2 border-white/20 animate-[spin_1s_linear_infinite]" />
             <div className="absolute inset-1 rounded-full border-t-2 border-l-2 border-white/60 animate-[spin_1.5s_ease-in-out_infinite_reverse]" />
             <Loader2 className="w-5 h-5 text-white/80 animate-pulse" />
          </div>

          {/* Text Content */}
          <h2 className="text-sm font-semibold tracking-wide text-white mb-2">
            {label}
          </h2>
          <p className="text-[11px] text-gray-500 font-medium">
            Verifying credentials...
          </p>

          {/* Security Badge */}
          <div className="mt-6 flex items-center gap-2 text-[10px] text-green-500/80 bg-green-500/5 px-3 py-1.5 rounded-full border border-green-500/10">
            <ShieldCheck className="w-3 h-3" />
            <span>Secure Connection</span>
          </div>

        </div>
      </div>
    </div>
  )
}

// --- LOGIC COMPONENT ---
function OAuthCallbackContent() {
  const router = useRouter()
  const searchParams = useSearchParams()

  useEffect(() => {
    const code = searchParams.get('code')
    const state = searchParams.get('state')

    // Small timeout to prevent a jarring flash, gives it a "processing" feel
    const timer = setTimeout(() => {
      if (code && state) {
        router.push(`/auth?code=${code}&state=${state}`)
      } else {
        router.push('/auth')
      }
    }, 800)

    return () => clearTimeout(timer)
  }, [searchParams, router])

  return <LoadingState label="Finalizing Handshake..." />
}

// --- MAIN EXPORT ---
export default function OAuthCallbackPage() {
  return (
    <Suspense fallback={<LoadingState label="Initializing..." />}>
      <OAuthCallbackContent />
    </Suspense>
  )
}