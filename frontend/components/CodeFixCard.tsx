'use client'

import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui'
import { Button, Badge } from '@/components/ui'
import { Copy, Check, Loader } from 'lucide-react'

interface CodeFixProps {
  result_id: number
  originalCode: string
  issue: {
    rule_id: string
    name: string
    message: string
    severity: string
  }
}

export function CodeFixCard({ result_id, originalCode, issue }: CodeFixProps) {
  const [fix, setFix] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [copied, setCopied] = useState(false)
  const [provider, setProvider] = useState('groq')

  const generateFix = async () => {
    setLoading(true)
    try {
      const response = await fetch(`/api/fixes/generate/${result_id}?provider=${provider}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('jwt_token')}`,
        },
      })

      if (response.ok) {
        const data = await response.json()
        
        // Poll for result
        let attempts = 0
        const pollInterval = setInterval(async () => {
          attempts++
          const checkResponse = await fetch(`/api/fixes/${result_id}`, {
            headers: {
              'Authorization': `Bearer ${localStorage.getItem('jwt_token')}`,
            },
          })
          
          if (checkResponse.ok) {
            const fixData = await checkResponse.json()
            if (fixData.fixed_code) {
              setFix(fixData)
              clearInterval(pollInterval)
            }
          }
          
          if (attempts > 30) clearInterval(pollInterval) // 30 second timeout
        }, 1000)
      }
    } catch (error) {
      console.error('Error generating fix:', error)
    } finally {
      setLoading(false)
    }
  }

  const copyCode = () => {
    if (fix?.fixed_code) {
      navigator.clipboard.writeText(fix.fixed_code)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  return (
    <div className="space-y-4">
      <Card className="border-blue-200 bg-blue-50">
        <CardHeader>
          <CardTitle className="text-lg">🤖 AI-Powered Fix</CardTitle>
          <CardDescription>Generate an automatic fix for this issue</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {!fix ? (
            <div className="space-y-3">
              <div className="flex gap-2">
                <select
                  value={provider}
                  onChange={(e) => setProvider(e.target.value)}
                  className="px-3 py-2 border border-gray-300 rounded text-sm"
                >
                  <option value="groq">Groq (Free)</option>
                  <option value="claude">Claude (Paid)</option>
                </select>
                <Button
                  onClick={generateFix}
                  disabled={loading}
                  className="bg-blue-600 hover:bg-blue-700 text-white"
                >
                  {loading ? (
                    <>
                      <Loader className="w-4 h-4 mr-2 animate-spin" />
                      Generating...
                    </>
                  ) : (
                    '✨ Generate Fix'
                  )}
                </Button>
              </div>
              <p className="text-xs text-gray-600">
                Using AI to generate a code fix for: <span className="font-semibold">{issue.name}</span>
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              <div>
                <p className="text-sm font-semibold text-gray-700 mb-2">📝 Explanation:</p>
                <p className="text-sm text-gray-600 bg-white p-3 rounded border border-gray-200">
                  {fix.explanation}
                </p>
              </div>

              <div>
                <div className="flex items-center justify-between mb-2">
                  <p className="text-sm font-semibold text-gray-700">💚 Fixed Code:</p>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={copyCode}
                    className="h-8"
                  >
                    {copied ? (
                      <>
                        <Check className="w-4 h-4 mr-1 text-green-600" />
                        Copied!
                      </>
                    ) : (
                      <>
                        <Copy className="w-4 h-4 mr-1" />
                        Copy
                      </>
                    )}
                  </Button>
                </div>
                <div className="bg-white border border-gray-300 rounded p-3 overflow-x-auto">
                  <pre className="text-xs font-mono text-gray-700 whitespace-pre-wrap">
                    {fix.fixed_code}
                  </pre>
                </div>
              </div>

              <div className="flex gap-2">
                <Button
                  onClick={() => setFix(null)}
                  variant="ghost"
                  className="text-blue-600"
                >
                  Generate Another
                </Button>
                <Button
                  className="bg-green-600 hover:bg-green-700 text-white"
                >
                  📤 Create PR
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
