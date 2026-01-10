'use client'

import { useEffect, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'

function OAuthCallbackContent() {
  const router = useRouter()
  const searchParams = useSearchParams()

  useEffect(() => {
    // Get code and state from GitHub OAuth callback
    const code = searchParams.get('code')
    const state = searchParams.get('state')

    if (code && state) {
      // Redirect to auth page with the callback params
      // The auth page will handle the OAuth flow
      router.push(`/auth?code=${code}&state=${state}`)
    } else {
      // No code/state, redirect to auth
      router.push('/auth')
    }
  }, [searchParams, router])

  // Show a loading message while redirecting
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 flex items-center justify-center">
      <div className="text-center">
        <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-cyan-400 via-blue-500 to-purple-600 rounded-2xl mb-4 shadow-lg shadow-blue-500/50 animate-spin">
          <div className="w-12 h-12 bg-slate-900 rounded-2xl"></div>
        </div>
        <p className="text-slate-300 font-medium">Completing authentication...</p>
      </div>
    </div>
  )
}

export default function OAuthCallbackPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 flex items-center justify-center">
        <div className="text-center">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-cyan-400 via-blue-500 to-purple-600 rounded-2xl mb-4 shadow-lg shadow-blue-500/50 animate-spin">
            <div className="w-12 h-12 bg-slate-900 rounded-2xl"></div>
          </div>
          <p className="text-slate-300 font-medium">Loading...</p>
        </div>
      </div>
    }>
      <OAuthCallbackContent />
    </Suspense>
  )
}
