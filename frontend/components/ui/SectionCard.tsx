import React from 'react'

interface SectionCardProps {
  title?: string
  children: React.ReactNode
  className?: string
}

export default function SectionCard({ title, children, className = '' }: SectionCardProps) {
  return (
    <div className={`rounded-lg border border-neutral-800 bg-neutral-900/60 p-4 ${className}`}>
      {title && (
        <h3 className="text-sm font-medium uppercase tracking-wide text-neutral-400 mb-2">
          {title}
        </h3>
      )}
      {children}
    </div>
  )
}
