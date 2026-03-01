'use client'

/**
 * Phase 15.2: Combined Patch Preview
 * 
 * Displays unified diff for batch operations:
 * - Combined patch from multiple fixes
 * - Syntax highlighting for diff format
 * - Collapsible sections by file
 * - Copy to clipboard
 * - Download patch
 * 
 * Design: Dense code view, monospace font, diff colors
 */

import { useState } from 'react'
import { ChevronDown, ChevronRight, Copy, Download, Check } from 'lucide-react'

interface PreviewData {
  validation: {
    valid: boolean
    errors: string[]
    warnings: string[]
    fix_count: number
    files_affected: string[]
    conflicts: Array<{ file_path: string; fix_ids: number[] }>
    risk_level: 'low' | 'medium' | 'high'
  }
  combined_patch: string
  patch_hash: string
}

interface CombinedPatchPreviewProps {
  isOpen: boolean
  onClose: () => void
  preview: PreviewData | null
  loading?: boolean
}

export function CombinedPatchPreview({
  isOpen,
  onClose,
  preview,
  loading = false
}: CombinedPatchPreviewProps) {
  const [copied, setCopied] = useState(false)
  const [expandedFiles, setExpandedFiles] = useState<Set<string>>(new Set())

  if (!isOpen) return null

  const handleCopy = async () => {
    if (preview?.combined_patch) {
      await navigator.clipboard.writeText(preview.combined_patch)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  const handleDownload = () => {
    if (preview?.combined_patch) {
      const blob = new Blob([preview.combined_patch], { type: 'text/plain' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `batch-fix-${preview.patch_hash.slice(0, 8)}.patch`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    }
  }

  const toggleFile = (fileName: string) => {
    const newExpanded = new Set(expandedFiles)
    if (newExpanded.has(fileName)) {
      newExpanded.delete(fileName)
    } else {
      newExpanded.add(fileName)
    }
    setExpandedFiles(newExpanded)
  }

  const expandAll = () => {
    if (preview?.validation.files_affected) {
      setExpandedFiles(new Set(preview.validation.files_affected))
    }
  }

  const collapseAll = () => {
    setExpandedFiles(new Set())
  }

  // Parse patch into file sections
  const parsePatch = (patch: string): Array<{ file: string; content: string }> => {
    const sections: Array<{ file: string; content: string }> = []
    const lines = patch.split('\n')
    let currentFile = ''
    let currentContent: string[] = []

    for (const line of lines) {
      if (line.startsWith('diff --git')) {
        // Save previous section
        if (currentFile && currentContent.length > 0) {
          sections.push({ file: currentFile, content: currentContent.join('\n') })
        }
        // Extract file name
        const match = line.match(/diff --git a\/(.*?) b\//)
        currentFile = match ? match[1] : 'unknown'
        currentContent = [line]
      } else {
        currentContent.push(line)
      }
    }

    // Save last section
    if (currentFile && currentContent.length > 0) {
      sections.push({ file: currentFile, content: currentContent.join('\n') })
    }

    return sections
  }

  const renderDiffLine = (line: string, idx: number) => {
    let className = 'text-neutral-400'
    if (line.startsWith('+') && !line.startsWith('+++')) {
      className = 'text-green-400 bg-green-900/10'
    } else if (line.startsWith('-') && !line.startsWith('---')) {
      className = 'text-red-400 bg-red-900/10'
    } else if (line.startsWith('@@')) {
      className = 'text-blue-400 bg-blue-900/10'
    } else if (line.startsWith('diff') || line.startsWith('index') || line.startsWith('---') || line.startsWith('+++')) {
      className = 'text-neutral-500'
    }

    return (
      <div key={idx} className={`${className} px-4 py-0.5 text-xs font-mono leading-tight`}>
        {line || ' '}
      </div>
    )
  }

  const fileSections = preview?.combined_patch ? parsePatch(preview.combined_patch) : []

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
      <div className="bg-neutral-900 border border-neutral-800 rounded-lg shadow-xl max-w-6xl w-full mx-4 max-h-[90vh] overflow-hidden flex flex-col">
        
        {/* Header */}
        <div className="px-6 py-4 border-b border-neutral-800">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-medium text-neutral-100">
                Combined Patch Preview
              </h2>
              {preview && (
                <div className="text-xs text-neutral-500 mt-1">
                  {preview.validation.fix_count} fixes · {preview.validation.files_affected.length} files · 
                  <span className="font-mono ml-1">{preview.patch_hash.slice(0, 8)}</span>
                </div>
              )}
            </div>
            
            <div className="flex items-center gap-2">
              {preview && (
                <>
                  <button
                    onClick={expandAll}
                    className="px-2 py-1 text-xs text-neutral-400 hover:text-neutral-200 border border-neutral-800 rounded transition-colors"
                  >
                    Expand All
                  </button>
                  <button
                    onClick={collapseAll}
                    className="px-2 py-1 text-xs text-neutral-400 hover:text-neutral-200 border border-neutral-800 rounded transition-colors"
                  >
                    Collapse All
                  </button>
                  <button
                    onClick={handleCopy}
                    className="px-3 py-1 text-xs bg-neutral-800 hover:bg-neutral-750 text-neutral-200 rounded border border-neutral-700 transition-colors flex items-center gap-1"
                  >
                    {copied ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                    {copied ? 'Copied!' : 'Copy'}
                  </button>
                  <button
                    onClick={handleDownload}
                    className="px-3 py-1 text-xs bg-neutral-800 hover:bg-neutral-750 text-neutral-200 rounded border border-neutral-700 transition-colors flex items-center gap-1"
                  >
                    <Download className="w-3 h-3" />
                    Download
                  </button>
                </>
              )}
              <button
                onClick={onClose}
                className="text-neutral-500 hover:text-neutral-300 transition-colors"
              >
                ✕
              </button>
            </div>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto bg-neutral-950">
          {loading ? (
            <div className="flex items-center justify-center h-64">
              <div className="text-neutral-500 text-sm">Loading preview...</div>
            </div>
          ) : !preview ? (
            <div className="flex items-center justify-center h-64">
              <div className="text-neutral-500 text-sm">No preview available</div>
            </div>
          ) : (
            <div className="divide-y divide-neutral-800">
              {fileSections.map((section, idx) => {
                const isExpanded = expandedFiles.has(section.file)
                return (
                  <div key={idx} className="border-b border-neutral-800 last:border-b-0">
                    {/* File Header */}
                    <button
                      onClick={() => toggleFile(section.file)}
                      className="w-full px-4 py-2 flex items-center gap-2 hover:bg-neutral-900/50 transition-colors text-left"
                    >
                      {isExpanded ? (
                        <ChevronDown className="w-4 h-4 text-neutral-500" />
                      ) : (
                        <ChevronRight className="w-4 h-4 text-neutral-500" />
                      )}
                      <span className="text-sm font-mono text-neutral-300">{section.file}</span>
                    </button>
                    
                    {/* File Content */}
                    {isExpanded && (
                      <div className="bg-neutral-950">
                        {section.content.split('\n').map((line, lineIdx) => 
                          renderDiffLine(line, lineIdx)
                        )}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-neutral-800 flex items-center justify-between bg-neutral-900/50">
          <div className="text-xs text-neutral-500">
            Unified diff format · Lines starting with + are additions, - are deletions
          </div>
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm bg-neutral-800 hover:bg-neutral-750 text-neutral-300 rounded border border-neutral-700 transition-colors"
          >
            Close
          </button>
        </div>

      </div>
    </div>
  )
}
