'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { getOAuthUrl, oauthCallback } from '@/lib/api'
import { Button } from '@/components/ui'
import { Github, Code2, AlertCircle, ArrowRight } from 'lucide-react'
import Link from 'next/link'

export default function AuthPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Handle OAuth callback
  const handleCallback = async (code: string, state: string) => {
    try {
      setLoading(true)
      const response = await oauthCallback(code, state)

      // Store token and user
      localStorage.setItem('jwt_token', response.token)
      localStorage.setItem('user', JSON.stringify(response.user))

      // Redirect to dashboard
      router.push('/dashboard')
    } catch (err) {
      const message = (err as Error).message || 'Authentication failed'
      setError(message)
      setLoading(false)
    }
  }

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const code = params.get('code')
    const state = params.get('state')

    if (code && state) {
      handleCallback(code, state)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const handleLogin = async () => {
    try {
      setError(null)
      setLoading(true)
      const { authorization_url } = await getOAuthUrl()
      window.location.href = authorization_url
    } catch (err) {
      const message = (err as Error).message || 'Failed to get authorization URL'
      setError(message)
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-white flex flex-col">
      {/* Navigation */}
      <nav className="border-b border-gray-200 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2 hover:opacity-80 transition">
            <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
              <Code2 className="w-5 h-5 text-white" />
            </div>
            <span className="text-xl font-semibold text-gray-900">AGI Engineer</span>
          </Link>
          <Link href="/">
            <Button variant="ghost" className="text-gray-600 hover:text-gray-900">
              Back to Home
            </Button>
          </Link>
        </div>
      </nav>

      {/* Main Content */}
      <div className="flex-1 flex items-center justify-center px-4 py-12">
        <div className="w-full max-w-md">
          {/* Header */}
          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center w-12 h-12 bg-blue-50 rounded-lg mb-4">
              <Code2 className="w-6 h-6 text-blue-600" />
            </div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">Welcome to AGI Engineer</h1>
            <p className="text-gray-600">Sign in with GitHub to start analyzing your code today</p>
          </div>

          {/* Login Card */}
          <div className="bg-white border border-gray-200 rounded-lg p-8 mb-6">
            {/* Error Message */}
            {error && (
              <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex gap-3">
                <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
                <div className="flex-1">
                  <p className="text-sm text-red-800 font-medium">{error}</p>
                  <p className="text-xs text-red-600 mt-1">Please ensure the backend service is running</p>
                </div>
              </div>
            )}

            {/* Login Button */}
            {loading ? (
              <div className="flex flex-col items-center justify-center py-6">
                <div className="w-8 h-8 border-3 border-blue-200 border-t-blue-600 rounded-full animate-spin mb-3"></div>
                <p className="text-sm text-gray-600">Authenticating...</p>
              </div>
            ) : (
              <Button
                onClick={handleLogin}
                className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-3 h-auto flex items-center justify-center gap-2 rounded-lg transition"
              >
                <Github className="w-5 h-5" />
                Sign in with GitHub
              </Button>
            )}

            {/* Footer */}
            <p className="text-xs text-gray-500 text-center mt-4">
              We only request access to public repositories
            </p>
          </div>

          {/* Benefits */}
          <div className="space-y-3">
            <div className="flex items-start gap-3">
              <div className="w-5 h-5 bg-blue-100 rounded flex items-center justify-center flex-shrink-0 mt-0.5">
                <span className="text-xs font-semibold text-blue-600">✓</span>
              </div>
              <div>
                <p className="text-sm font-medium text-gray-900">Free to start</p>
                <p className="text-xs text-gray-600">Begin analyzing immediately</p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <div className="w-5 h-5 bg-blue-100 rounded flex items-center justify-center flex-shrink-0 mt-0.5">
                <span className="text-xs font-semibold text-blue-600">✓</span>
              </div>
              <div>
                <p className="text-sm font-medium text-gray-900">Secure</p>
                <p className="text-xs text-gray-600">OAuth 2.0 authentication</p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <div className="w-5 h-5 bg-blue-100 rounded flex items-center justify-center flex-shrink-0 mt-0.5">
                <span className="text-xs font-semibold text-blue-600">✓</span>
              </div>
              <div>
                <p className="text-sm font-medium text-gray-900">Quick setup</p>
                <p className="text-xs text-gray-600">3 clicks to get started</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <footer className="border-t border-gray-200 bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            <p className="text-center md:text-left text-gray-600 text-sm">
              © 2026 AGI Engineer. All rights reserved.
            </p>
            <div className="flex gap-6 text-gray-600 text-sm">
              <a href="/" className="hover:text-gray-900 transition">Home</a>
              <a href="https://github.com" className="hover:text-gray-900 transition">GitHub</a>
              <a href="/" className="hover:text-gray-900 transition">Contact</a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}
