import { useState } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { 
  Shield, 
  Zap, 
  Building, 
  FileCheck, 
  FileText,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Info,
  Download,
  ChevronRight,
  Clock,
  Activity,
  TrendingUp,
  BarChart3,
  ArrowLeft
} from 'lucide-react';

interface AgentIssue {
  file_path: string;
  line_number: number;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INFO';
  title: string;
  description: string;
  recommendation: string;
  confidence: number;
  tags?: string[];
}

interface AgentResult {
  agent_type: string;
  issues: AgentIssue[];
  metrics: Record<string, any>;
  summary: string;
  execution_time_ms: number;
}

interface V3AnalysisResults {
  repository: {
    name: string;
    branch: string;
    url: string;
  };
  agent_results: Record<string, AgentResult>;
  total_issues: number;
}

interface PiecesStyleAnalysisProps {
  results: V3AnalysisResults;
  onBack?: () => void;
}

const agentConfig = {
  security: { 
    icon: Shield, 
    color: 'text-red-600',
    bg: 'bg-red-50',
    border: 'border-red-200',
    name: 'Security',
  },
  performance: { 
    icon: Zap, 
    color: 'text-yellow-600',
    bg: 'bg-yellow-50',
    border: 'border-yellow-200',
    name: 'Performance',
  },
  architecture: { 
    icon: Building, 
    color: 'text-blue-600',
    bg: 'bg-blue-50',
    border: 'border-blue-200',
    name: 'Architecture',
  },
  test: { 
    icon: FileCheck, 
    color: 'text-green-600',
    bg: 'bg-green-50',
    border: 'border-green-200',
    name: 'Testing',
  },
  documentation: { 
    icon: FileText, 
    color: 'text-purple-600',
    bg: 'bg-purple-50',
    border: 'border-purple-200',
    name: 'Documentation',
  },
};

const severityConfig = {
  CRITICAL: { icon: XCircle, label: 'Critical', color: 'text-red-600' },
  HIGH: { icon: AlertTriangle, label: 'High', color: 'text-orange-600' },
  MEDIUM: { icon: Info, label: 'Medium', color: 'text-yellow-600' },
  LOW: { icon: Info, label: 'Low', color: 'text-blue-600' },
  INFO: { icon: CheckCircle2, label: 'Info', color: 'text-gray-600' },
};

export function PiecesStyleAnalysis({ results, onBack }: PiecesStyleAnalysisProps) {
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null);
  const [selectedIssue, setSelectedIssue] = useState<string | null>(null);

  const agentResultsArray = Object.entries(results.agent_results || {}).map(
    ([key, value]) => ({
      ...value,
      agent_type: value.agent_type || key.toUpperCase(),
    })
  );

  const totalIssues = agentResultsArray.reduce(
    (sum, r) => sum + (r.issues?.length || 0),
    0
  );
  const exportToJSON = () => {
  const blob = new Blob(
    [JSON.stringify(results, null, 2)],
    { type: 'application/json' }
  );

  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `analysis-${Date.now()}.json`;
  a.click();
  URL.revokeObjectURL(url);
};


  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="mx-auto max-w-7xl px-6 py-6">

        {/* Header */}
        <div className="mb-6 flex items-center justify-between">
          <div>
            {onBack && (
              <Button
                variant="ghost"
                size="sm"
                onClick={onBack}
                className="mb-2 -ml-2 text-muted-foreground"
              >
                <ArrowLeft className="w-4 h-4 mr-1" />
                Back
              </Button>
            )}
            <h1 className="text-xl font-semibold">Analysis Results</h1>
            <p className="text-sm text-muted-foreground">
              {results.repository?.name} · {results.repository?.branch} · {totalIssues} issues
            </p>
          </div>

        <Button
  variant="outline"
  size="sm"
  onClick={() => exportToJSON()}
>
  <Download className="w-4 h-4 mr-2" />
  Export JSON
</Button>

        </div>

        <div className="grid grid-cols-12 gap-4">

          {/* Sidebar */}
          <div className="col-span-3">
            <div className="border border-border bg-card">
              <div className="px-4 py-3 border-b border-border text-xs font-medium text-muted-foreground">
                ANALYSIS AGENTS
              </div>

              <div className="divide-y divide-border">
                {agentResultsArray.map(result => {
                  const key = result.agent_type.toLowerCase();
                  const config = agentConfig[key as keyof typeof agentConfig];
                  if (!config) return null;

                  const score =
                    result.metrics?.security_score ??
                    result.metrics?.performance_score ??
                    result.metrics?.architecture_score ??
                    0;

                  const issues = result.issues?.length || 0;
                  const active = selectedAgent === key;

                  return (
                    <button
                      key={key}
                      onClick={() => setSelectedAgent(key)}
                      className={`w-full px-4 py-3 text-left transition
                        ${active
                          ? 'bg-muted border-l-2 border-l-primary'
                          : 'hover:bg-muted/50 border-l-2 border-l-transparent'}
                      `}
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium">{config.name}</span>
                        <ChevronRight className="w-4 h-4 text-muted-foreground" />
                      </div>
                      <div className="mt-1 flex gap-2 text-xs text-muted-foreground">
                        <span>{score}/100</span>
                        <span>•</span>
                        <span>{issues} issues</span>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Main */}
          <div className="col-span-9">
            {selectedAgent ? (
              <div className="border border-border bg-card">

                {/* Agent Header */}
                <div className="px-6 py-4 border-b border-border">
                  <h2 className="text-lg font-semibold">
                    {agentConfig[selectedAgent as keyof typeof agentConfig]?.name} Analysis
                  </h2>
                </div>

                {/* Issues */}
                <div className="divide-y divide-border">
                  {agentResultsArray
                    .find(r => r.agent_type.toLowerCase() === selectedAgent)
                    ?.issues?.map((issue, idx) => {
                      const id = `${selectedAgent}-${idx}`;
                      const open = selectedIssue === id;
                      const sev = severityConfig[issue.severity];
                      if (!sev) return null;

                      const SevIcon = sev.icon;

                      return (
                        <div key={id} className="px-6 py-4">
                          <button
                            onClick={() => setSelectedIssue(open ? null : id)}
                            className="flex w-full items-start gap-3 text-left"
                          >
                            <SevIcon className={`w-4 h-4 mt-1 ${sev.color}`} />
                            <div className="flex-1">
                              <div className="flex items-center gap-2">
                                <Badge variant="outline" className="text-xs">
                                  {sev.label}
                                </Badge>
                                <span className="text-xs text-muted-foreground">
                                  {issue.file_path}:{issue.line_number}
                                </span>
                              </div>
                              <p className="mt-1 text-sm font-medium">
                                {issue.title}
                              </p>
                              {!open && (
                                <p className="mt-1 text-xs text-muted-foreground line-clamp-1">
                                  {issue.description}
                                </p>
                              )}
                            </div>
                            <ChevronRight
                              className={`w-4 h-4 transition ${
                                open ? 'rotate-90' : ''
                              }`}
                            />
                          </button>

                          {open && (
                            <div className="mt-3 ml-7 text-sm text-muted-foreground space-y-2">
                              <p>{issue.description}</p>
                              <p className="text-foreground">
                                Recommendation: {issue.recommendation}
                              </p>
                              <p className="text-xs">
                                Confidence: {Math.round(issue.confidence * 100)}%
                              </p>
                            </div>
                          )}
                        </div>
                      );
                    })}
                </div>
              </div>
            ) : (
              <div className="border border-border bg-card p-12 text-center">
                <Activity className="w-10 h-10 text-muted-foreground mx-auto mb-4" />
                <p className="text-muted-foreground">
                  Select an agent to inspect results
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

