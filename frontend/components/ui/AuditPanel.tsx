import type { ReactNode } from 'react'

interface AuditPanelProps {
	children: ReactNode
	className?: string
}

export default function AuditPanel({ children, className = '' }: AuditPanelProps) {
	return (
		<div className={`rounded border border-neutral-800 bg-neutral-950/60 p-3 ${className}`.trim()}>
			{children}
		</div>
	)
}
