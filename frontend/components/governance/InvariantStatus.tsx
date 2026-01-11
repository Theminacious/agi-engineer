'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { CheckCircle2, XCircle, Shield } from 'lucide-react'

interface InvariantCheck {
  name: string
  passed: boolean
  description: string
}

interface InvariantStatusProps {
  checks: InvariantCheck[]
}

export default function InvariantStatus({ checks }: InvariantStatusProps) {
  const allPassed = checks.every(c => c.passed)

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Shield className="w-5 h-5" />
          Invariant Checks
          <Badge 
            variant={allPassed ? 'default' : 'destructive'}
            className={allPassed ? 'bg-green-100 text-green-700 ml-2' : 'ml-2'}
          >
            {checks.filter(c => c.passed).length} / {checks.length} Passed
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {checks.map((check, idx) => (
          <div 
            key={idx}
            className={`p-3 rounded-lg border ${
              check.passed 
                ? 'bg-green-50 border-green-200' 
                : 'bg-red-50 border-red-200'
            }`}
          >
            <div className="flex items-start gap-3">
              {check.passed ? (
                <CheckCircle2 className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
              ) : (
                <XCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
              )}
              
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <span className={`font-medium text-sm ${
                    check.passed ? 'text-green-900' : 'text-red-900'
                  }`}>
                    {check.name}
                  </span>
                  <Badge 
                    variant={check.passed ? 'default' : 'destructive'}
                    className={check.passed ? 'bg-green-100 text-green-700' : ''}
                  >
                    {check.passed ? 'PASS' : 'FAIL'}
                  </Badge>
                </div>
                <p className={`text-xs ${
                  check.passed ? 'text-green-700' : 'text-red-700'
                }`}>
                  {check.description}
                </p>
              </div>
            </div>
          </div>
        ))}

        {/* Overall Status */}
        <div className={`p-3 rounded-lg border-2 ${
          allPassed 
            ? 'bg-green-50 border-green-300' 
            : 'bg-red-50 border-red-300'
        }`}>
          <div className="flex items-center gap-2">
            {allPassed ? (
              <CheckCircle2 className="w-5 h-5 text-green-600" />
            ) : (
              <XCircle className="w-5 h-5 text-red-600" />
            )}
            <span className={`font-bold ${
              allPassed ? 'text-green-900' : 'text-red-900'
            }`}>
              {allPassed 
                ? 'All invariants satisfied ✓' 
                : 'Some invariants violated ✗'}
            </span>
          </div>
        </div>

        {/* Explanation */}
        <div className="text-xs text-gray-500 italic p-2 bg-gray-50 rounded">
          ℹ️ Invariants are mathematical properties that MUST hold true for every valid run.
          Violations indicate bugs in the execution system or corrupted ledger data.
        </div>
      </CardContent>
    </Card>
  )
}
