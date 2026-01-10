'use client'

import { useEffect, useState } from 'react'
import { usePathname } from 'next/navigation'
import { motion, AnimatePresence } from 'framer-motion'

/* --- AMBIENT BACKGROUND COMPONENT --- */
function CinematicBackground() {
  return (
    <div className="fixed inset-0 z-0 pointer-events-none overflow-hidden bg-[#030303]">
      
      {/* 1. Deep Space Gradients (Breathing Animation) */}
      <div className="absolute top-[-20%] left-[-10%] w-[50vw] h-[50vw] bg-indigo-900/10 blur-[120px] rounded-full mix-blend-screen animate-pulse duration-[10000ms]" />
      <div className="absolute bottom-[-20%] right-[-10%] w-[50vw] h-[50vw] bg-blue-900/10 blur-[120px] rounded-full mix-blend-screen animate-pulse duration-[8000ms]" />
      
      {/* 2. Technical Grid Overlay */}
      <div 
        className="absolute inset-0 opacity-[0.08]"
        style={{
          backgroundImage: `
            linear-gradient(to right, #333 1px, transparent 1px),
            linear-gradient(to bottom, #333 1px, transparent 1px)
          `,
          backgroundSize: '64px 64px',
          maskImage: 'radial-gradient(circle at 50% 50%, black, transparent 80%)'
        }}
      />

      {/* 3. Film Grain Texture (Texture & Grip) */}
      <div 
        className="absolute inset-0 opacity-[0.035] mix-blend-overlay"
        style={{ backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.7' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E")` }} 
      />

      {/* 4. Vignette (Focus Center) */}
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,transparent_0%,#030303_100%)]" />
    </div>
  )
}

/* --- MAIN WRAPPER --- */
export default function ContentWrapper({
  children,
}: {
  children: React.ReactNode
}) {
  const pathname = usePathname()
  const [mounted, setMounted] = useState(false)
  const [hasSidebar, setHasSidebar] = useState(false)

  useEffect(() => {
    // 1. Check Authentication
    const token = localStorage.getItem('jwt_token')

    // 2. Define Public Routes (No Sidebar)
    const isPublicPage = pathname === '/' || pathname.startsWith('/auth')

    // 3. Determine Layout State
    const shouldShowSidebar = !!token && !isPublicPage
    setHasSidebar(shouldShowSidebar)

    // 4. Mark as Mounted to enable transitions
    setMounted(true)
  }, [pathname])

  return (
    <div className="min-h-screen bg-[#030303] text-white selection:bg-blue-500/30 selection:text-white relative font-sans antialiased">
      
      {/* Background Layer */}
      <CinematicBackground />

      {/* Main Content Layout */}
      <AnimatePresence mode="wait">
        {mounted && (
          <motion.main
            initial={{ opacity: 0 }}
            animate={{ 
              opacity: 1,
              // Smooth spring animation for layout shifts instead of linear CSS
              paddingLeft: hasSidebar ? 280 : 0 
            }}
            transition={{ 
              duration: 0.5, 
              ease: [0.22, 1, 0.36, 1], // Custom Bézier for "Apple-like" smoothness
              opacity: { duration: 0.3 }
            }}
            className="relative z-10 min-h-screen flex flex-col"
          >
            {/* We wrap children in another motion div to handle page-transition effects 
              if you want them later, but for now it acts as a clean container 
            */}
            <div className="flex-1 w-full max-w-[100vw] overflow-x-hidden">
               {children}
            </div>

          </motion.main>
        )}
      </AnimatePresence>

      {/* Loading State (Pre-hydration flicker prevention) */}
      {!mounted && (
        <div className="fixed inset-0 bg-[#030303] z-50 pointer-events-none opacity-100 transition-opacity duration-500" />
      )}

    </div>
  )
}