'use client'

import React, { useState, useEffect, useRef } from 'react'
import { motion, useScroll, useTransform, useMotionTemplate, useMotionValue } from 'framer-motion'
import Link from 'next/link'

/* ---------------- 0. ASSETS & ICONS ---------------- */

// THE LOGO COMPONENT (Reused consistently)
const AppLogo = ({ className = "" }: { className?: string }) => (
  <div className={`relative group ${className}`}>
    <div className="absolute -inset-1 bg-gradient-to-r from-blue-600 to-indigo-600 rounded-xl blur opacity-25 group-hover:opacity-75 transition duration-500"></div>
    <div className="relative w-8 h-8 bg-gradient-to-tr from-[#2563EB] to-[#4F46E5] rounded-lg flex items-center justify-center shadow-2xl border border-white/10">
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4 text-white">
        <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" />
      </svg>
    </div>
  </div>
)

const Icons = {
  // Navigation / UI
  Github: ({ className }: { className?: string }) => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}><path d="M15 22v-4a4.8 5 0 0 0-1-3.5c3 0 6-2 6-5.5.08-1.25-.27-2.48-1-3.5.28-1.15.28-2.35 0-3.5 0 0-1 4 1 4 5.5-.9 3.5.3 4 .5 1.38-.27 2.8-.27 4.2 0 .5-.2 2.5-1.4 4-.5.28 1.15.28 2.35 0 3.5-.73 1.02-1.08 2.25-1 3.5.12 3.8 3.2 5.5 6 5.5a5 5 0 0 0-1 3.5v4" /></svg>
  ),
  ArrowRight: ({ className }: { className?: string }) => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}><path d="M5 12h14" /><path d="m12 5 7 7-7 7" /></svg>
  ),
  Play: ({ className }: { className?: string }) => (
    <svg viewBox="0 0 24 24" fill="currentColor" stroke="none" className={className}><polygon points="5 3 19 12 5 21 5 3" /></svg>
  ),
  
  // Dashboard Specific
  Terminal: ({ className }: { className?: string }) => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}><polyline points="4 17 10 11 4 5" /><line x1="12" x2="20" y1="19" y2="19" /></svg>
  ),
  ShieldCheck: ({ className }: { className?: string }) => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}><path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z" /><path d="m9 12 2 2 4-4" /></svg>
  ),
  GitPullRequest: ({ className }: { className?: string }) => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}><circle cx="18" cy="18" r="3" /><circle cx="6" cy="6" r="3" /><path d="M13 6h3a2 2 0 0 1 2 2v7" /><line x1="6" x2="6" y1="9" y2="21" /></svg>
  ),
  Zap: ({ className }: { className?: string }) => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" /></svg>
  ),
  Cpu: ({ className }: { className?: string }) => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}><rect width="16" height="16" x="4" y="4" rx="2" /><rect width="6" height="6" x="9" y="9" rx="1" /><path d="M15 2v2" /><path d="M15 20v2" /><path d="M2 15h2" /><path d="M2 9h2" /><path d="M20 15h2" /><path d="M20 9h2" /><path d="M9 2v2" /><path d="M9 20v2" /></svg>
  ),
  Sparkles: ({ className }: { className?: string }) => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}><path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z" /></svg>
  ),
  CheckCircle2: ({ className }: { className?: string }) => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}><circle cx="12" cy="12" r="10" /><path d="m9 12 2 2 4-4" /></svg>
  ),
  Activity: ({ className }: { className?: string }) => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}><path d="M22 12h-4l-3 9L9 3l-3 9H2" /></svg>
  ),
  Command: ({ className }: { className?: string }) => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}><rect width="18" height="18" x="3" y="3" rx="2" ry="2" /><line x1="12" x2="12" y1="8" y2="16" /><line x1="8" x2="16" y1="12" y2="12" /></svg>
  ),

  // Feature Section Specific
  Brain: ({ className }: { className?: string }) => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
       <path d="M9.5 2A2.5 2.5 0 0 1 12 4.5v15a2.5 2.5 0 0 1-4.96.44 2.5 2.5 0 0 1-2.96-3.08 3 3 0 0 1-.34-5.58 2.5 2.5 0 0 1 1.32-4.24 2.5 2.5 0 0 1 1.98-3A2.5 2.5 0 0 1 9.5 2Z" />
       <path d="M14.5 2A2.5 2.5 0 0 0 12 4.5v15a2.5 2.5 0 0 0 4.96.44 2.5 2.5 0 0 0 2.96-3.08 3 3 0 0 0 .34-5.58 2.5 2.5 0 0 0-1.32-4.24 2.5 2.5 0 0 0-1.98-3A2.5 2.5 0 0 0 14.5 2Z" />
    </svg>
  ),
  Lock: ({ className }: { className?: string }) => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}><rect width="18" height="11" x="3" y="11" rx="2" ry="2" /><path d="M7 11V7a5 5 0 0 1 10 0v4" /></svg>
  ),
  Quote: ({ className }: { className?: string }) => (
     <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="currentColor" className={className}>
       <path d="M14.017 21L14.017 18C14.017 16.8954 14.9124 16 16.017 16H19.017C19.5693 16 20.017 15.5523 20.017 15V9C20.017 8.44772 19.5693 8 19.017 8H15.017C14.4647 8 14.017 8.44772 14.017 9V11C14.017 11.5523 13.5693 12 13.017 12H12.017V5H22.017V15C22.017 18.3137 19.3307 21 16.017 21H14.017ZM5.01691 21L5.01691 18C5.01691 16.8954 5.91234 16 7.01691 16H10.0169C10.5692 16 11.0169 15.5523 11.0169 15V9C11.0169 8.44772 10.5692 8 10.0169 8H6.01691C5.46462 8 5.01691 8.44772 5.01691 9V11C5.01691 11.5523 4.56919 12 4.01691 12H3.01691V5H13.0169V15C13.0169 18.3137 10.3306 21 7.01691 21H5.01691Z" />
     </svg>
  )
}

/* ---------------- 1. COMPONENTS ---------------- */

// Spotlight Card for Feature Grid
function SpotlightCard({ children, className = "" }: { children: React.ReactNode, className?: string }) {
    const mouseX = useMotionValue(0);
    const mouseY = useMotionValue(0);

    function handleMouseMove({ currentTarget, clientX, clientY }: React.MouseEvent) {
        const { left, top } = currentTarget.getBoundingClientRect();
        mouseX.set(clientX - left);
        mouseY.set(clientY - top);
    }

    return (
        <div
            className={`group relative border border-white/10 bg-[#0A0A0B] overflow-hidden ${className}`}
            onMouseMove={handleMouseMove}
        >
            <motion.div
                className="pointer-events-none absolute -inset-px rounded-xl opacity-0 transition duration-300 group-hover:opacity-100"
                style={{
                    background: useMotionTemplate`
            radial-gradient(
              650px circle at ${mouseX}px ${mouseY}px,
              rgba(59, 130, 246, 0.1),
              transparent 80%
            )
          `,
                }}
            />
            <div className="relative h-full">{children}</div>
        </div>
    );
}

// Background Grid Animation
function BackgroundGrid() {
    return (
        <div className="absolute inset-0 pointer-events-none opacity-[0.2]" 
             style={{ 
                 backgroundImage: 'linear-gradient(rgba(255, 255, 255, 0.05) 1px, transparent 1px), linear-gradient(90deg, rgba(255, 255, 255, 0.05) 1px, transparent 1px)', 
                 backgroundSize: '40px 40px' 
             }}>
             <motion.div 
                animate={{ y: [0, 40] }} 
                transition={{ duration: 4, repeat: Infinity, ease: "linear" }}
                className="absolute inset-0"
             />
        </div>
    )
}

// Live Terminal (No changes to logic, just styling)
function LiveTerminal() {
  const [lines, setLines] = useState<string[]>([])
  
  useEffect(() => {
    const script = [
        { text: "> initializing agi-engine v2.0...", delay: 200, color: "text-gray-400" },
        { text: "> scanning target: /src/backend...", delay: 1000, color: "text-blue-300" },
        { text: "  ⎿ found 24 files (py, tsx)", delay: 1400, color: "text-gray-500" },
        { text: "⚠ issue found: unused_dependency (auth.py:12)", delay: 2200, color: "text-amber-400" },
        { text: "⚠ issue found: memory_leak_risk (worker.ts:45)", delay: 2800, color: "text-amber-400" },
        { text: "> querying Groq LPU™ for context...", delay: 3500, color: "text-purple-300" },
        { text: "✓ fix strategy generated (98% confidence)", delay: 4500, color: "text-green-400" },
        { text: "> creating pull request...", delay: 5200, color: "text-blue-300" },
        { text: "✓ PR #1042 created successfully", delay: 6000, color: "text-green-400 font-bold" },
    ]

    let timeouts: NodeJS.Timeout[] = []
    const runScript = () => {
        setLines([])
        script.forEach(({ text, delay, color }, index) => {
            const timeout = setTimeout(() => {
                setLines(prev => [...prev, `<span class="${color} font-mono">${text}</span>`])
            }, delay)
            timeouts.push(timeout)
        })
    }
    runScript()
    const interval = setInterval(runScript, 8000)
    return () => {
        timeouts.forEach(clearTimeout)
        clearInterval(interval)
    }
  }, [])

  return (
    <div className="w-full bg-[#0F0F10] rounded-xl border border-white/10 shadow-2xl overflow-hidden font-mono text-[10px] md:text-[11px] leading-relaxed relative group h-[240px]">
      <div className="flex items-center justify-between px-3 py-2 bg-white/5 border-b border-white/5">
        <div className="flex gap-1.5">
            <div className="w-2.5 h-2.5 rounded-full bg-[#FF5F56] opacity-80" />
            <div className="w-2.5 h-2.5 rounded-full bg-[#FFBD2E] opacity-80" />
            <div className="w-2.5 h-2.5 rounded-full bg-[#27C93F] opacity-80" />
        </div>
        <div className="text-gray-500 flex items-center gap-1">
             <Icons.Terminal className="w-3 h-3" />
             <span>analysis_worker_01</span>
        </div>
      </div>
      <div className="p-4 flex flex-col justify-end h-[200px] overflow-hidden">
        <div className="flex flex-col gap-1.5">
            {lines.map((html, i) => (
                <motion.div key={i} initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} dangerouslySetInnerHTML={{ __html: html }} />
            ))}
            <motion.span animate={{ opacity: [0, 1, 0] }} transition={{ repeat: Infinity, duration: 0.8 }} className="w-1.5 h-3 bg-gray-500 inline-block mt-1" />
        </div>
      </div>
      <div className="absolute bottom-0 right-0 w-40 h-40 bg-blue-500/10 blur-[60px] pointer-events-none" />
    </div>
  )
}

function StatCard({ icon: Icon, label, value, color }: { icon: any, label: string, value: string, color: string }) {
    return (
        <div className="bg-white/50 backdrop-blur-sm border border-white/40 p-3 rounded-xl flex items-center gap-3 shadow-sm hover:scale-[1.02] transition-transform cursor-default">
            <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${color}`}>
                <Icon className="w-4 h-4 text-white" />
            </div>
            <div>
                <p className="text-[10px] uppercase font-bold text-gray-400 tracking-wider">{label}</p>
                <p className="text-sm font-bold text-gray-800">{value}</p>
            </div>
        </div>
    )
}

function FeatureItem({ title, desc, icon: Icon }: { title: string, desc: string, icon: any }) {
    return (
        <div className="flex gap-4 p-4 rounded-xl hover:bg-gray-50 transition-colors border border-transparent hover:border-gray-100 group">
            <div className="w-10 h-10 rounded-full bg-blue-50 flex items-center justify-center text-blue-600 shrink-0 group-hover:scale-110 transition-transform">
                <Icon className="w-5 h-5" />
            </div>
            <div>
                <h3 className="text-sm font-bold text-gray-900 mb-1">{title}</h3>
                <p className="text-xs text-gray-500 leading-relaxed">{desc}</p>
            </div>
        </div>
    )
}

/* ---------------- 2. MAIN PAGE ---------------- */

export default function HomePage() {
  return (
    <div className="min-h-screen bg-[#050505] text-white font-sans selection:bg-blue-500/30 overflow-x-hidden relative">
      
      {/* Background & Atmosphere */}
      <div className="fixed inset-0 pointer-events-none z-0">
         <BackgroundGrid />
         {/* Deep Glows */}
         <div className="absolute top-[-20%] left-[20%] w-[600px] h-[600px] bg-indigo-600/10 blur-[130px] rounded-full mix-blend-screen" />
         <div className="absolute bottom-[-10%] right-[10%] w-[800px] h-[800px] bg-blue-600/10 blur-[130px] rounded-full mix-blend-screen" />
      </div>

      <div className="relative z-10 max-w-[1600px] mx-auto p-4 md:p-6 flex flex-col gap-32">
        
        {/* =========================================================================
            SECTION 1: THE DASHBOARD (HERO) - Preserved Exact Design
           ========================================================================= */}
        <section className="flex flex-col min-h-screen pb-10">
            {/* Header */}
            <header className="sticky top-4 z-50 flex items-center justify-between mb-8 px-4 py-3 bg-[#121214]/70 backdrop-blur-xl border border-white/10 rounded-2xl shadow-2xl">
                <div className="flex items-center gap-3">
                    <AppLogo />
                    <span className="text-lg font-bold tracking-tight text-white">AGI Engineer <span className="text-white/30 font-normal ml-1 text-sm">v2.0</span></span>
                </div>
                
                <div className="flex items-center gap-4">
                    <Link href="https://github.com/Theminacious/agi-engineer" target="_blank" className="hidden md:flex text-xs font-medium text-gray-400 hover:text-white items-center gap-2 transition-colors">
                        <Icons.Github className="w-4 h-4" /> GitHub
                    </Link>
                    <div className="h-4 w-[1px] bg-white/10 hidden md:block"></div>
                    <Link href="/auth" className="bg-white text-black px-4 py-2 rounded-full text-xs font-bold hover:bg-gray-200 transition-colors flex items-center gap-2">
                      Start Analysis <Icons.ArrowRight className="w-3 h-3" />
                    </Link>
                </div>
            </header>

            {/* Dashboard Interface */}
            <main className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-6 pb-4">
                
                {/* Sidebar Panel */}
                <motion.aside initial={{ x: -20, opacity: 0 }} animate={{ x: 0, opacity: 1 }} className="lg:col-span-3 hidden lg:flex flex-col gap-4">
                    <div className="bg-[#121214]/60 backdrop-blur-md border border-white/5 p-4 rounded-2xl">
                        <div className="flex items-center gap-3 mb-4">
                            <div className="w-8 h-8 rounded-full bg-gradient-to-r from-gray-700 to-gray-600 border border-white/10" />
                            <div>
                                <div className="text-xs font-bold text-white">Engineer_Workspace</div>
                                <div className="text-[10px] text-green-400 flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" /> Online</div>
                            </div>
                        </div>
                        <div className="space-y-1">
                            {['Dashboard', 'Active Issues', 'Pull Requests', 'Configuration'].map((item, i) => (
                                <div key={item} className={`p-2 rounded-lg text-xs cursor-pointer ${i===0 ? 'bg-white/10 text-white font-medium' : 'text-gray-400 hover:text-white hover:bg-white/5'}`}>{item}</div>
                            ))}
                        </div>
                    </div>
                    {/* Auto Fix Card */}
                    <div className="bg-gradient-to-br from-indigo-900/20 to-blue-900/20 border border-blue-500/20 p-5 rounded-2xl flex-1 relative overflow-hidden group">
                        <div className="absolute inset-0 bg-blue-500/5 group-hover:bg-blue-500/10 transition-colors" />
                        <div className="relative z-10">
                            <div className="flex items-center gap-2 mb-3 text-blue-300 font-bold text-xs"><Icons.Sparkles className="w-3 h-3" /> NEW FEATURE</div>
                            <h3 className="text-xl font-bold text-white mb-2">Auto-Fix V2</h3>
                            <p className="text-xs text-gray-400 leading-relaxed mb-4">Now powered by parallel processing. Runs Ruff & ESLint simultaneously for 3x speed.</p>
                            <div className="w-full bg-blue-500/20 h-1 rounded-full overflow-hidden"><div className="h-full bg-blue-500 w-2/3 animate-[shimmer_2s_infinite]" /></div>
                            <p className="text-[10px] text-blue-300 mt-2 text-right">Updated 2m ago</p>
                        </div>
                    </div>
                </motion.aside>

                {/* Main Content */}
                <motion.div initial={{ y: 20, opacity: 0 }} animate={{ y: 0, opacity: 1 }} transition={{ delay: 0.1 }} className="lg:col-span-9 bg-[#F5F5F7] rounded-[32px] overflow-hidden flex flex-col relative shadow-2xl">
                    <div className="flex-1 p-8 lg:p-10 overflow-hidden">
                        <div className="grid lg:grid-cols-2 gap-12 mb-12">
                            <div className="flex flex-col justify-center">
                                <div className="inline-block px-3 py-1 rounded-full bg-blue-100 text-blue-700 text-[10px] font-bold uppercase tracking-wide mb-4 w-fit">⚡️ System Status: Operational</div>
                                <h1 className="text-4xl lg:text-5xl font-bold text-gray-900 mb-5 tracking-tight leading-[1.1]">Code Intelligence <br/><span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-indigo-600">on Autopilot.</span></h1>
                                <p className="text-gray-500 text-sm leading-relaxed mb-8 max-w-md">AGI Engineer V2 analyzes your repo, detects architectural drift, and automatically creates Pull Requests to fix issues safely.</p>
                                <div className="flex gap-3">
                                    <button className="bg-[#111] text-white px-6 py-3 rounded-xl text-xs font-bold shadow-xl hover:shadow-2xl hover:scale-105 transition-all flex items-center gap-2"><Icons.Play className="w-3 h-3 text-white" /> Run Analysis</button>
                                    <button className="bg-white border border-gray-200 text-gray-700 px-6 py-3 rounded-xl text-xs font-bold hover:bg-gray-50 transition-colors">View Demo</button>
                                </div>
                            </div>
                            <div className="relative pt-6">
                                <LiveTerminal />
                                <motion.div initial={{ y: 20, opacity: 0 }} animate={{ y: 0, opacity: 1 }} transition={{ delay: 1.5, type: "spring" }} className="absolute -bottom-5 -left-5 bg-white p-3 rounded-xl shadow-[0_10px_40px_-10px_rgba(0,0,0,0.2)] border border-gray-100 flex items-center gap-3 pr-6">
                                    <div className="w-10 h-10 rounded-full bg-green-50 flex items-center justify-center text-green-600"><Icons.CheckCircle2 className="w-5 h-5" /></div>
                                    <div><p className="text-xs font-bold text-gray-900">PR Created</p><p className="text-[10px] text-gray-500">fix/optimize-imports (#1042)</p></div>
                                </motion.div>
                            </div>
                        </div>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-12">
                            <StatCard icon={Icons.Zap} label="Speed" value="0.05s" color="bg-amber-500" />
                            <StatCard icon={Icons.ShieldCheck} label="Safety" value="100%" color="bg-green-500" />
                            <StatCard icon={Icons.GitPullRequest} label="PRs Built" value="1,204" color="bg-purple-500" />
                            <StatCard icon={Icons.Cpu} label="Cores" value="Parallel" color="bg-blue-500" />
                        </div>
                        <div className="border-t border-gray-200 pt-8">
                            <h2 className="text-sm font-bold text-gray-900 mb-6 uppercase tracking-wider">System Capabilities</h2>
                            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
                                <FeatureItem icon={Icons.Cpu} title="Parallel Analysis" desc="Executes Ruff and ESLint on separate threads for immediate feedback." />
                                <FeatureItem icon={Icons.Command} title="One-Click Fix" desc="Don't just find bugs. Fix them and push to GitHub instantly." />
                                <FeatureItem icon={Icons.Activity} title="Context Awareness" desc="Understands project structure to avoid breaking changes." />
                            </div>
                        </div>
                    </div>
                </motion.div>
            </main>
        </section>

        {/* =========================================================================
            SECTION 2: CONTEXT AWARENESS (Graph & Code)
           ========================================================================= */}
        <section className="relative">
            <div className="flex flex-col md:flex-row justify-between items-end mb-16 border-b border-white/10 pb-8">
                <div>
                     <h2 className="text-4xl md:text-6xl font-bold tracking-tight mb-4">
                        It starts with memory—<br/>at the <span className="text-blue-500">OS-Level</span>
                     </h2>
                     <p className="text-gray-400 max-w-lg text-lg">
                        We don't just grep text. AGI Engineer builds a persistent knowledge graph of your entire architecture.
                     </p>
                </div>
                <div className="hidden md:flex gap-2">
                    <div className="px-4 py-2 rounded-full border border-white/10 text-xs font-mono text-gray-400 bg-white/5">Graph Theory</div>
                    <div className="px-4 py-2 rounded-full border border-white/10 text-xs font-mono text-gray-400 bg-white/5">AST Parsing</div>
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 md:h-[550px]">
                 {/* Card 1: The Visualizer */}
                 <SpotlightCard className="col-span-1 rounded-3xl p-8 flex flex-col justify-between group">
                     <div className="relative h-40 w-full mb-6 flex items-center justify-center">
                         {/* SVG Visual */}
                         <div className="absolute inset-0 flex items-center justify-center opacity-60">
                             <div className="w-32 h-32 rounded-full border border-blue-500/30 flex items-center justify-center relative">
                                 <div className="absolute inset-0 border border-blue-500/20 rounded-full animate-ping" />
                                 <div className="w-20 h-20 rounded-full border border-indigo-500/50 flex items-center justify-center">
                                     <div className="w-2 h-2 bg-white rounded-full shadow-[0_0_10px_rgba(255,255,255,0.8)]" />
                                 </div>
                             </div>
                         </div>
                         <div className="relative z-10 w-16 h-16 bg-blue-500/10 rounded-2xl flex items-center justify-center backdrop-blur-md border border-blue-500/30">
                            <Icons.Brain className="w-8 h-8 text-blue-400" />
                        </div>
                     </div>
                     <div>
                        <h3 className="text-2xl font-bold mb-2">Neural Architecture</h3>
                        <p className="text-gray-400 leading-relaxed">Visualize dependencies and data flow across your entire codebase instantly. We map the unknown.</p>
                     </div>
                 </SpotlightCard>

                 {/* Card 2: Deep Code Analysis */}
                 <SpotlightCard className="col-span-1 md:col-span-2 rounded-3xl p-10 relative overflow-hidden">
                     <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-blue-600/10 blur-[120px] rounded-full pointer-events-none" />
                     
                     <div className="grid md:grid-cols-2 gap-12 h-full items-center relative z-10">
                         <div>
                             <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-500/10 text-blue-400 text-xs font-bold mb-6 border border-blue-500/20">
                                 <div className="w-2 h-2 rounded-full bg-blue-400 animate-pulse" /> Live Context
                             </div>
                             <h3 className="text-3xl font-bold mb-4">Deep Semantic Understanding</h3>
                             <p className="text-gray-400 leading-relaxed mb-8">
                                 Most tools only see text. We see logic. Our engine parses ASTs to understand variable scope, import chains, and type definitions before suggesting a single line of code.
                             </p>
                             <div className="flex flex-wrap gap-2">
                                 {['TypeScript', 'Python', 'Rust', 'Go'].map(lang => (
                                     <span key={lang} className="px-3 py-1 rounded-lg bg-white/5 text-xs text-gray-300 border border-white/10 hover:border-white/20 transition-colors cursor-default">{lang}</span>
                                 ))}
                             </div>
                         </div>

                         {/* Code Snippet */}
                         <div className="bg-[#050505] rounded-xl border border-white/10 font-mono text-[11px] text-gray-400 shadow-2xl relative overflow-hidden">
                             {/* Mac Window Header */}
                             <div className="flex items-center gap-2 px-4 py-3 bg-white/5 border-b border-white/5">
                                 <div className="w-2.5 h-2.5 rounded-full bg-red-500/20" />
                                 <div className="w-2.5 h-2.5 rounded-full bg-yellow-500/20" />
                                 <div className="w-2.5 h-2.5 rounded-full bg-green-500/20" />
                                 <div className="ml-auto text-[10px] text-gray-600">context_loader.py</div>
                             </div>
                             
                             <div className="p-5 space-y-2">
                                <div className="flex"><span className="w-6 text-gray-700 select-none">1</span><span className="text-purple-400">class</span>&nbsp;<span className="text-yellow-200">ContextLoader</span>:</div>
                                <div className="flex"><span className="w-6 text-gray-700 select-none">2</span>&nbsp;&nbsp;&nbsp;&nbsp;<span className="text-gray-500"># Mapping semantics...</span></div>
                                <div className="flex"><span className="w-6 text-gray-700 select-none">3</span>&nbsp;&nbsp;&nbsp;&nbsp;<span className="text-purple-400">def</span>&nbsp;<span className="text-blue-300">__init__</span>(self, root):</div>
                                <div className="flex"><span className="w-6 text-gray-700 select-none">4</span>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;self.graph =&nbsp;<span className="text-green-400">nx.DiGraph()</span></div>
                                <div className="flex"><span className="w-6 text-gray-700 select-none">5</span>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;self.parser =&nbsp;<span className="text-yellow-200">TreeSitter</span>.load()</div>
                                <div className="flex"><span className="w-6 text-gray-700 select-none">6</span></div>
                                <div className="flex"><span className="w-6 text-gray-700 select-none">7</span>&nbsp;&nbsp;&nbsp;&nbsp;<span className="text-purple-400">async def</span>&nbsp;<span className="text-blue-300">index_nodes</span>(self):</div>
                                <div className="flex bg-blue-500/10 -mx-5 px-5 py-1 border-l-2 border-blue-500"><span className="w-6 text-gray-700 select-none">8</span>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span className="text-white">await self.build_edges()</span></div>
                             </div>
                         </div>
                     </div>
                 </SpotlightCard>
            </div>
        </section>

        {/* =========================================================================
            SECTION 3: INTEGRATIONS (Light Mode Contrast)
           ========================================================================= */}
        <section className="py-10">
            <div className="bg-gradient-to-b from-white to-gray-200 rounded-[48px] p-12 md:p-24 text-center relative overflow-hidden">
                <div className="absolute inset-0 opacity-[0.4]" style={{ backgroundImage: 'radial-gradient(#94a3b8 1px, transparent 1px)', backgroundSize: '32px 32px' }}></div>
                
                <div className="relative z-10 max-w-4xl mx-auto">
                    <h2 className="text-4xl md:text-6xl font-bold text-gray-900 mb-8 tracking-tight">
                        Analyze and fix code right—<br/>from your <span className="text-blue-600">favorite tools</span>
                    </h2>
                    
                    <div className="grid md:grid-cols-2 gap-6 mt-16">
                        {/* VS Code */}
                        <div className="bg-white p-8 rounded-3xl shadow-[0_20px_40px_-15px_rgba(0,0,0,0.1)] border border-gray-100 flex flex-col items-center text-center hover:translate-y-[-5px] transition-transform duration-300 group">
                            <div className="w-16 h-16 bg-[#007ACC] rounded-2xl flex items-center justify-center mb-6 shadow-lg shadow-blue-500/20 group-hover:scale-110 transition-transform">
                                <Icons.Terminal className="w-8 h-8 text-white" />
                            </div>
                            <h3 className="text-xl font-bold text-gray-900 mb-2">VS Code Extension</h3>
                            <p className="text-gray-500 leading-relaxed">Real-time linting, auto-fix suggestions, and chat directly in your editor sidebar.</p>
                        </div>

                        {/* GitHub */}
                        <div className="bg-white p-8 rounded-3xl shadow-[0_20px_40px_-15px_rgba(0,0,0,0.1)] border border-gray-100 flex flex-col items-center text-center hover:translate-y-[-5px] transition-transform duration-300 group">
                            <div className="w-16 h-16 bg-[#181717] rounded-2xl flex items-center justify-center mb-6 shadow-lg shadow-black/20 group-hover:scale-110 transition-transform">
                                <Icons.Github className="w-8 h-8 text-white" />
                            </div>
                            <h3 className="text-xl font-bold text-gray-900 mb-2">GitHub Actions</h3>
                            <p className="text-gray-500 leading-relaxed">Block bad PRs before merge. Automated review bot that acts like a senior engineer.</p>
                        </div>
                    </div>
                </div>
            </div>
        </section>

        {/* =========================================================================
            SECTION 4: PRIVACY & TESTIMONIALS
           ========================================================================= */}
        <section className="grid md:grid-cols-2 gap-6">
             {/* Privacy */}
             <div className="bg-[#121214] border border-white/10 p-10 rounded-3xl flex flex-col justify-center relative overflow-hidden group">
                 <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-green-500 to-emerald-500" />
                 <Icons.Lock className="w-10 h-10 text-green-400 mb-6" />
                 <h3 className="text-2xl font-bold mb-3">Local-First Security</h3>
                 <p className="text-gray-400 leading-relaxed mb-6">Your code never leaves your machine. We run entirely on your hardware using optimized small language models.</p>
                 <div className="flex items-center gap-4 text-xs font-mono text-gray-500">
                     <span className="flex items-center gap-2"><div className="w-2 h-2 bg-green-500 rounded-full" /> Air-gapped capable</span>
                 </div>
             </div>

             {/* Testimonial */}
             <div className="bg-[#121214] border border-white/10 p-10 rounded-3xl flex flex-col justify-center relative overflow-hidden">
                 <Icons.Quote className="w-10 h-10 text-gray-600 mb-6" />
                 <p className="text-xl font-medium text-gray-200 mb-6 leading-relaxed">
                    "It caught a race condition I missed for weeks. AGI Engineer is like having a senior developer who never sleeps."
                 </p>
                 <div className="flex items-center gap-4">
                     <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-purple-500 to-blue-500" />
                     <div>
                         <div className="font-bold text-white">Alex Chen</div>
                         <div className="text-xs text-gray-500">Staff Engineer @ Vercel</div>
                     </div>
                 </div>
             </div>
        </section>

        {/* =========================================================================
            SECTION 5: FOOTER & CTA
           ========================================================================= */}
        <section className="pb-20">
             <div className="w-full bg-[#0A0A0B] border border-white/10 rounded-[48px] p-12 md:p-32 text-center relative overflow-hidden group">
                 {/* Footer Glow */}
                 <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[600px] h-[400px] bg-blue-600/20 blur-[150px] rounded-full pointer-events-none group-hover:bg-blue-600/30 transition-colors duration-700" />
                 
                 <div className="relative z-10 flex flex-col items-center">
                    <AppLogo className="mb-8 scale-150" />
                    <h2 className="text-4xl md:text-7xl font-bold mb-8 tracking-tight">
                        "It's like I'm building my own<br/>
                        <span className="text-transparent bg-clip-text bg-gradient-to-b from-white to-gray-500">private internet</span>"
                    </h2>
                    <p className="text-gray-400 text-lg mb-10">Join 10,000+ engineers shipping safer code today.</p>
                    
                    <Link href="/auth" className="bg-white text-black px-10 py-5 rounded-full font-bold text-lg hover:scale-105 transition-transform shadow-[0_0_40px_-10px_rgba(255,255,255,0.3)] inline-block">
                        Start Analysis Now
                    </Link>
                 </div>
             </div>
             
             {/* Simple Footer Links */}
             <div className="flex justify-between items-center px-6 pt-10 text-xs text-gray-600">
                 <p>© 2026 AGI Engineer Inc.</p>
                 <div className="flex gap-6">
                     <a href="#" className="hover:text-gray-400">Twitter</a>
                     <a href="#" className="hover:text-gray-400">GitHub</a>
                     <a href="#" className="hover:text-gray-400">Privacy</a>
                 </div>
             </div>
        </section>

      </div>

      <style jsx global>{`
        .custom-scrollbar::-webkit-scrollbar {
          width: 0px;
          background: transparent;
        }
        @keyframes shimmer {
            0% { transform: translateX(-100%); }
            100% { transform: translateX(100%); }
        }
      `}</style>
    </div>
  )
}