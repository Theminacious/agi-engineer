'use client'

import { Badge } from '@/components/ui/badge'
import { Lock, Eye, Archive } from 'lucide-react'

interface ReadOnlyBadgeProps {
  variant?: 'lock' | 'eye' | 'archive'
  text?: string
  className?: string
}

export default function ReadOnlyBadge({ 
  variant = 'lock', 
  text,
  className = ''
}: ReadOnlyBadgeProps) {
  const variants = {
    lock: {
      icon: Lock,
      defaultText: 'Read-Only',
      className: 'bg-blue-100 text-blue-700 border-blue-300'
    },
    eye: {
      icon: Eye,
      defaultText: 'View Only',
      className: 'bg-gray-100 text-gray-700 border-gray-300'
    },
    archive: {
      icon: Archive,
      defaultText: 'Frozen',
      className: 'bg-purple-100 text-purple-700 border-purple-300'
    }
  }

  const config = variants[variant]
  const Icon = config.icon
  const displayText = text || config.defaultText

  return (
    <Badge 
      variant="outline" 
      className={`flex items-center gap-1 ${config.className} ${className}`}
    >
      <Icon className="w-3 h-3" />
      {displayText}
    </Badge>
  )
}
