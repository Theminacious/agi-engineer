export default function Home() {
  return (
    <main className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-50">
      <div className="max-w-6xl mx-auto px-4 py-16">
        <div className="text-center">
          <h1 className="text-4xl font-bold text-slate-900 mb-4">
            AGI Engineer V2
          </h1>
          <p className="text-xl text-slate-600 mb-8">
            GitHub App for Automated Code Quality Analysis
          </p>
          <div className="space-y-4">
            <p className="text-slate-500">🚀 Coming Soon</p>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-12">
              <div className="bg-white p-6 rounded-lg shadow-sm border border-slate-200">
                <h3 className="font-semibold text-slate-900 mb-2">Dashboard</h3>
                <p className="text-slate-600 text-sm">View analysis results and metrics</p>
              </div>
              <div className="bg-white p-6 rounded-lg shadow-sm border border-slate-200">
                <h3 className="font-semibold text-slate-900 mb-2">Settings</h3>
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
