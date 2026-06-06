import React from 'react'

interface StatusBadgeProps {
	status: string
	className?: string
}

const statusStyles: Record<string, string> = {
	proposed: 'bg-blue-500/10 text-blue-300 border-blue-500/20',
	approved: 'bg-emerald-500/10 text-emerald-300 border-emerald-500/20',
	rejected: 'bg-red-500/10 text-red-300 border-red-500/20',
	applied: 'bg-violet-500/10 text-violet-300 border-violet-500/20',
	failed: 'bg-amber-500/10 text-amber-300 border-amber-500/20',
}

export default function StatusBadge({ status, className = '' }: StatusBadgeProps) {
	const label = status.replace(/_/g, ' ')
	const style = statusStyles[status] || 'bg-neutral-500/10 text-neutral-300 border-neutral-500/20'

	return (
		<span className={`inline-flex items-center rounded border px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide ${style} ${className}`.trim()}>
			{label}
		</span>
	)
}
