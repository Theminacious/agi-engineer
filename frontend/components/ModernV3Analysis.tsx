import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
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
  ChevronDown,
  ChevronUp,
  TrendingUp,
  Clock,
  Target,
  Activity
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

const agentConfig = {
  security: { 
    icon: Shield, 
    color: 'from-red-500 to-red-600',
    lightBg: 'bg-red-50',
    border: 'border-red-200',
    text: 'text-red-600',
    name: 'Security',
    description: 'Vulnerabilities & threats'
  },
  performance: { 
    icon: Zap, 
    color: 'from-yellow-500 to-orange-500',
    lightBg: 'bg-yellow-50',
    border: 'border-yellow-200',
    text: 'text-yellow-600',
    name: 'Performance',
    description: 'Speed & efficiency'
  },
  architecture: { 
    icon: Building, 
    color: 'from-blue-500 to-blue-600',
    lightBg: 'bg-blue-50',
    border: 'border-blue-200',
    text: 'text-blue-600',
    name: 'Architecture',
    description: 'Design patterns & structure'
  },
  test: { 
    icon: FileCheck, 
    color: 'from-green-500 to-green-600',
    lightBg: 'bg-green-50',
    border: 'border-green-200',
    text: 'text-green-600',
    name: 'Testing',
    description: 'Coverage & quality'
  },
  documentation: { 
    icon: FileText, 
    color: 'from-purple-500 to-purple-600',
    lightBg: 'bg-purple-50',
    border: 'border-purple-200',
    text: 'text-purple-600',
    name: 'Documentation',
    description: 'Completeness & clarity'
  },
};

const severityConfig = {
  CRITICAL: { 
    color: 'text-red-600', 
    bg: 'bg-red-100', 
    border: 'border-red-300',
    icon: XCircle, 
    label: 'Critical',
    weight: 4
  },
  HIGH: { 
    color: 'text-orange-600', 
    bg: 'bg-orange-100', 
    border: 'border-orange-300',
    icon: AlertTriangle, 
    label: 'High',
    weight: 2
  },
  MEDIUM: { 
    color: 'text-yellow-600', 
    bg: 'bg-yellow-100', 
    border: 'border-yellow-300',
    icon: Info, 
    label: 'Medium',
    weight: 1
  },
  LOW: { 
    color: 'text-blue-600', 
    bg: 'bg-blue-100', 
    border: 'border-blue-300',
    icon: Info, 
    label: 'Low',
    weight: 0.5
  },
  INFO: { 
    color: 'text-gray-600', 
    bg: 'bg-gray-100', 
    border: 'border-gray-300',
    icon: CheckCircle2, 
    label: 'Info',
    weight: 0.1
  },
};

export function ModernV3Analysis({ results }: { results: V3AnalysisResults }) {
  const [expandedAgent, setExpandedAgent] = useState<string | null>('security');
  const [expandedIssues, setExpandedIssues] = useState<Set<string>>(new Set());

  const agentResultsArray = Object.entries(results.agent_results || {}).map(([key, value]) => ({
    ...value,
    agent_type: value.agent_type || key.toUpperCase()
  }));

  // Calculate metrics
  const totalIssues = agentResultsArray.reduce((sum, r) => sum + (r.issues?.length || 0), 0);
  const criticalIssues = agentResultsArray.reduce((sum, r) => 
    sum + (r.issues?.filter(i => i.severity === 'CRITICAL').length || 0), 0);
  const highIssues = agentResultsArray.reduce((sum, r) => 
    sum + (r.issues?.filter(i => i.severity === 'HIGH').length || 0), 0);

  const overallScore = Math.round(
    agentResultsArray.reduce((sum, r) => {
      const score = r.metrics?.security_score || 
                    r.metrics?.performance_score || 
                    r.metrics?.architecture_score ||
                    r.metrics?.test_score ||
                    r.metrics?.documentation_score || 0;
      return sum + score;
    }, 0) / (agentResultsArray.length || 1)
  );

  const technicalDebt = Math.round(criticalIssues * 4 + highIssues * 2);

  const getScoreColor = (score: number) => {
    if (score >= 90) return 'text-green-600';
    if (score >= 70) return 'text-blue-600';
    if (score >= 50) return 'text-yellow-600';
    return 'text-red-600';
  };

  const toggleIssue = (issueId: string) => {
    const newExpanded = new Set(expandedIssues);
    if (newExpanded.has(issueId)) {
      newExpanded.delete(issueId);
    } else {
      newExpanded.add(issueId);
    }
    setExpandedIssues(newExpanded);
  };

  const exportToJSON = () => {
    const dataStr = JSON.stringify(results, null, 2);
    const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr);
    const link = document.createElement('a');
    link.setAttribute('href', dataUri);
    link.setAttribute('download', `analysis-${Date.now()}.json`);
    link.click();
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-slate-50">
      {/* Hero Section */}
      <div className="bg-gradient-to-r from-slate-900 via-slate-800 to-slate-900 text-white">
        <div className="max-w-7xl mx-auto px-6 py-12">
          <div className="flex items-center justify-between mb-8">
            <div>
              <h1 className="text-4xl font-bold mb-2">Code Analysis Report</h1>
              <p className="text-slate-300 text-lg">
                {results.repository?.name || 'Unknown Repository'} • {results.repository?.branch || 'main'}
              </p>
            </div>
            <Button 
              onClick={exportToJSON}
              variant="outline"
              className="bg-white/10 border-white/20 text-white hover:bg-white/20"
            >
              <Download className="w-4 h-4 mr-2" />
              Export
            </Button>
          </div>

          {/* Score Cards */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            <div className="bg-white/10 backdrop-blur rounded-xl p-6 border border-white/20">
              <div className="flex items-center gap-3 mb-2">
                <Activity className="w-5 h-5 text-blue-400" />
                <span className="text-sm text-slate-300">Quality Score</span>
              </div>
              <div className={`text-4xl font-bold ${getScoreColor(overallScore)}`}>
                {overallScore}
              </div>
              <Progress value={overallScore} className="mt-3 h-2" />
            </div>

            <div className="bg-white/10 backdrop-blur rounded-xl p-6 border border-white/20">
              <div className="flex items-center gap-3 mb-2">
                <AlertTriangle className="w-5 h-5 text-orange-400" />
                <span className="text-sm text-slate-300">Total Issues</span>
              </div>
              <div className="text-4xl font-bold text-orange-400">{totalIssues}</div>
              <div className="mt-3 text-sm text-slate-400">
                {criticalIssues} critical • {highIssues} high
              </div>
            </div>

            <div className="bg-white/10 backdrop-blur rounded-xl p-6 border border-white/20">
              <div className="flex items-center gap-3 mb-2">
                <Clock className="w-5 h-5 text-purple-400" />
                <span className="text-sm text-slate-300">Tech Debt</span>
              </div>
              <div className="text-4xl font-bold text-purple-400">{technicalDebt}h</div>
              <div className="mt-3 text-sm text-slate-400">
                ${technicalDebt * 75} estimated cost
              </div>
            </div>

            <div className="bg-white/10 backdrop-blur rounded-xl p-6 border border-white/20">
              <div className="flex items-center gap-3 mb-2">
                <Target className="w-5 h-5 text-green-400" />
                <span className="text-sm text-slate-300">Agents Run</span>
              </div>
              <div className="text-4xl font-bold text-green-400">{agentResultsArray.length}</div>
              <div className="mt-3 text-sm text-slate-400">
                Comprehensive scan
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Agents Section */}
      <div className="max-w-7xl mx-auto px-6 py-12">
        <h2 className="text-2xl font-bold text-slate-900 mb-6">Analysis by Agent</h2>
        
        <div className="space-y-4">
          {agentResultsArray.map((result) => {
            const agentKey = result.agent_type.toLowerCase();
            const config = agentConfig[agentKey as keyof typeof agentConfig];
            if (!config) return null;

            const Icon = config.icon;
            const isExpanded = expandedAgent === agentKey;
            const issueCount = result.issues?.length || 0;
            const score = result.metrics?.security_score || 
                         result.metrics?.performance_score || 
                         result.metrics?.architecture_score ||
                         result.metrics?.test_score ||
                         result.metrics?.documentation_score || 0;

            return (
              <Card key={agentKey} className={`overflow-hidden border-2 ${config.border} transition-all hover:shadow-lg`}>
                <div 
                  className="cursor-pointer"
                  onClick={() => setExpandedAgent(isExpanded ? null : agentKey)}
                >
                  <CardHeader className={`${config.lightBg} border-b ${config.border}`}>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-4">
                        <div className={`p-3 rounded-xl bg-gradient-to-br ${config.color} text-white shadow-lg`}>
                          <Icon className="w-6 h-6" />
                        </div>
                        <div>
                          <CardTitle className="text-xl font-bold text-slate-900">
                            {config.name}
                          </CardTitle>
                          <CardDescription className="text-slate-600">
                            {config.description}
                          </CardDescription>
                        </div>
                      </div>
                      
                      <div className="flex items-center gap-6">
                        <div className="text-center">
                          <div className={`text-3xl font-bold ${getScoreColor(score)}`}>
                            {score}
                          </div>
                          <div className="text-xs text-slate-500">score</div>
                        </div>
                        
                        <div className="text-center">
                          <div className={`text-3xl font-bold ${issueCount > 0 ? 'text-orange-600' : 'text-green-600'}`}>
                            {issueCount}
                          </div>
                          <div className="text-xs text-slate-500">issues</div>
                        </div>

                        <Button variant="ghost" size="sm">
                          {isExpanded ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
                        </Button>
                      </div>
                    </div>
                  </CardHeader>
                </div>

                {isExpanded && (
                  <CardContent className="pt-6">
                    {/* Metrics Summary Bar */}
                    {result.metrics && Object.keys(result.metrics).length > 0 && (
                      <div className="mb-6 p-4 bg-gradient-to-r from-slate-50 to-slate-100 rounded-xl border border-slate-200">
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                          {Object.entries(result.metrics).map(([key, value]) => {
                            if (key === 'execution_time_ms') return null;
                            // Skip objects and complex types, only show primitive values
                            if (typeof value === 'object' && value !== null) return null;
                            
                            return (
                              <div key={key} className="text-center">
                                <div className="text-2xl font-bold text-slate-900">
                                  {typeof value === 'number' ? Math.round(value) : String(value)}
                                </div>
                                <div className="text-xs text-slate-600 mt-1">
                                  {key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    )}

                    {/* Summary with Icon */}
                    {result.summary && (
                      <div className="mb-6 p-4 bg-blue-50 border-l-4 border-blue-400 rounded-lg">
                        <div className="flex items-start gap-3">
                          <Info className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
                          <div>
                            <h4 className="font-semibold text-blue-900 mb-1">Analysis Summary</h4>
                            <p className="text-sm text-blue-800">{result.summary}</p>
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Issues Stats */}
                    {issueCount > 0 && (
                      <div className="mb-4 p-4 bg-orange-50 border-l-4 border-orange-400 rounded-lg">
                        <div className="flex items-center gap-2">
                          <AlertTriangle className="w-5 h-5 text-orange-600" />
                          <span className="font-semibold text-orange-900">
                            ⚠️ {issueCount} {issueCount === 1 ? 'issue' : 'issues'} detected
                          </span>
                        </div>
                      </div>
                    )}

                    {/* Issues */}
                    {issueCount > 0 ? (
                      <div className="space-y-3">
                        <h3 className="font-semibold text-slate-900 mb-4">
                          Found {issueCount} Issue{issueCount !== 1 ? 's' : ''}
                        </h3>
                        {result.issues.map((issue, idx) => {
                          const issueId = `${agentKey}-${idx}`;
                          const isIssueExpanded = expandedIssues.has(issueId);
                          const sevConfig = severityConfig[issue.severity];
                          
                          // Skip if severity config not found
                          if (!sevConfig) {
                            console.warn(`Unknown severity: ${issue.severity}`);
                            return null;
                          }

                          return (
                            <div 
                              key={idx} 
                              className={`border-2 ${sevConfig.border} rounded-lg overflow-hidden hover:shadow-md transition-all`}
                            >
                              <div 
                                className={`${sevConfig.bg} p-4 cursor-pointer`}
                                onClick={() => toggleIssue(issueId)}
                              >
                                <div className="flex items-start justify-between">
                                  <div className="flex-1">
                                    <div className="flex items-center gap-3 mb-2">
                                      <Badge className={`${sevConfig.bg} ${sevConfig.color} border ${sevConfig.border}`}>
                                        {sevConfig.label}
                                      </Badge>
                                      <span className="text-xs text-slate-500">
                                        {issue.file_path}:{issue.line_number}
                                      </span>
                                    </div>
                                    <h4 className="font-semibold text-slate-900">{issue.title}</h4>
                                  </div>
                                  <Button variant="ghost" size="sm">
                                    {isIssueExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                                  </Button>
                                </div>
                              </div>

                              {isIssueExpanded && (
                                <div className="p-4 bg-white space-y-4">
                                  <div>
                                    <h5 className="text-sm font-semibold text-slate-700 mb-1">Description</h5>
                                    <p className="text-sm text-slate-600">{issue.description}</p>
                                  </div>
                                  <div>
                                    <h5 className="text-sm font-semibold text-slate-700 mb-1">Recommendation</h5>
                                    <p className="text-sm text-slate-600">{issue.recommendation}</p>
                                  </div>
                                  {issue.tags && issue.tags.length > 0 && (
                                    <div className="flex gap-2 flex-wrap">
                                      {issue.tags.map((tag, i) => (
                                        <Badge key={i} variant="outline" className="text-xs">
                                          {tag}
                                        </Badge>
                                      ))}
                                    </div>
                                  )}
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    ) : (
                      <div className="text-center py-12">
                        <CheckCircle2 className="w-16 h-16 text-green-500 mx-auto mb-4" />
                        <h3 className="text-xl font-semibold text-slate-900 mb-2">All Clear!</h3>
                        <p className="text-slate-600">No issues found by this agent</p>
                      </div>
                    )}
                  </CardContent>
                )}
              </Card>
            );
          })}
        </div>
      </div>
    </div>
  );
}
