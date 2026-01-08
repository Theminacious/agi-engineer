'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { getOAuthUrl, oauthCallback } from '@/lib/api'
import { Header } from '@/components/ui'

export default function AuthPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Handle OAuth callback
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const code = params.get('code')
    const state = params.get('state')

    if (code && state) {
      handleCallback(code, state)
    }
  }, [])

  const handleCallback = async (code: string, state: string) => {
    try {
      setLoading(true)
      const response = await oauthCallback(code, state)

      // Store token and user
      localStorage.setItem('jwt_token', response.token)
      localStorage.setItem('user', response.user)

      // Redirect to dashboard
      router.push('/dashboard')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Authentication failed')
      setLoading(false)
    }
  }

  const handleLogin = async () => {
    try {
      setLoading(true)
      const { authorization_url } = await getOAuthUrl()
      window.location.href = authorization_url
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start login')
      setLoading(false)
    }
  }

  return (
    <>
      <Header />
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
        <div className="bg-white rounded-lg shadow-xl p-8 max-w-md w-full">
          <h1 className="text-3xl font-bold text-center mb-2 text-gray-900">AGI Engineer</h1>
          <p className="text-center text-gray-600 mb-8">
            Automated Code Quality Analysis
          </p>

          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-6">
              {error}
            </div>
          )}

          {loading ? (
            <div className="text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
            </div>
          ) : (
            <button
              onClick={handleLogin}
              className="w-full bg-blue-600 text-white py-3 rounded-lg font-semibold hover:bg-blue-700 transition"
            >
              Login with GitHub
            </button>
          )}
        </div>
      </div>
    </>
  )
}
