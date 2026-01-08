'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'

export default function Home() {
  const router = useRouter()

  useEffect(() => {
    // Redirect to dashboard if logged in, otherwise to auth
    const token = localStorage.getItem('jwt_token')
    if (token) {
      router.push('/dashboard')
    } else {
      router.push('/auth')
    }
  }, [router])

  // This page redirects, so we never actually render
  return null
}
                <p className="text-slate-600 text-sm">Configure per-repository analysis rules</p>
              </div>
              <div className="bg-white p-6 rounded-lg shadow-sm border border-slate-200">
                <h3 className="font-semibold text-slate-900 mb-2">History</h3>
                <p className="text-slate-600 text-sm">Track analysis runs and improvements</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>
  )
}
