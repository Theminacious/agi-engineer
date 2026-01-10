import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Progress } from '@/components/ui/progress';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { EnterpriseMetrics } from '@/components/EnterpriseMetrics';
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
  TrendingUp,
  TrendingDown,
  Clock,
  Target,
  DollarSign,
  Users
} from 'lucide-react';

interface AgentIssue {
  file_path: string;
  line_number: number;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INFO';
  title: string;
  description: string;
  recommendation: string;
  confidence: number;
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
  execution_time_ms?: number;
  agents_run: string[];
  severity_breakdown?: Record<string, number>;
}

const severityConfig = {
  CRITICAL: { color: 'bg-red-500', icon: XCircle, label: 'Critical' },
  HIGH: { color: 'bg-orange-500', icon: AlertTriangle, label: 'High' },
  MEDIUM: { color: 'bg-yellow-500', icon: Info, label: 'Medium' },
  LOW: { color: 'bg-blue-500', icon: Info, label: 'Low' },
  INFO: { color: 'bg-gray-500', icon: CheckCircle2, label: 'Info' },
};

const agentConfig = {
  security: { 
    icon: Shield, 
    color: 'text-red-600',
    bgColor: 'bg-red-50',
    name: 'Security Analysis' 
  },
  performance: { 
    icon: Zap, 
    color: 'text-yellow-600',
    bgColor: 'bg-yellow-50',
    name: 'Performance Analysis' 
  },
  architecture: { 
    icon: Building, 
    color: 'text-blue-600',
    bgColor: 'bg-blue-50',
    name: 'Architecture Analysis' 
  },
  test: { 
    icon: FileCheck, 
    color: 'text-green-600',
    bgColor: 'bg-green-50',
    name: 'Test Quality Analysis' 
  },
  documentation: { 
    icon: FileText, 
    color: 'text-purple-600',
    bgColor: 'bg-purple-50',
    name: 'Documentation Analysis' 
  },
};

function getSeverityBadge(severity: string) {
  const config = severityConfig[severity as keyof typeof severityConfig];
  const Icon = config.icon;
  
  return (
    <Badge className={`${config.color} text-white`}>
      <Icon className="w-3 h-3 mr-1" />
      {config.label}
    </Badge>
  );
}

function IssueCard({ issue }: { issue: AgentIssue }) {
  return (
    <Card className="mb-4">
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <CardTitle className="text-lg">{issue.title}</CardTitle>
            <CardDescription className="mt-1">
              {issue.file_path}:{issue.line_number}
            </CardDescription>
          </div>
          <div className="flex gap-2">
            {getSeverityBadge(issue.severity)}
            <Badge variant="outline">{Math.round(issue.confidence * 100)}% confident</Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          <div>
            <p className="text-sm font-medium text-gray-700">Description:</p>
            <p className="text-sm text-gray-600">{issue.description}</p>
          </div>
          <div>
            <p className="text-sm font-medium text-gray-700">Recommendation:</p>
            <p className="text-sm text-gray-600">{issue.recommendation}</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function AgentResultPanel({ result }: { result: AgentResult }) {
  const agentKey = result.agent_type.toLowerCase();
  const config = agentConfig[agentKey as keyof typeof agentConfig];
  const Icon = config?.icon || FileText;
  
  // Group issues by severity
  const issuesBySeverity = (result.issues || []).reduce((acc, issue) => {
    acc[issue.severity] = (acc[issue.severity] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);
  
  // Extract key metrics for display
  const score = result.metrics?.security_score || 
                result.metrics?.performance_score || 
                result.metrics?.architecture_score ||
                result.metrics?.test_score ||
                result.metrics?.documentation_score ||
                null;
  
  const filesAnalyzed = result.metrics?.files_analyzed || 
                        result.metrics?.total_test_files ||
                        result.metrics?.total_modules ||
                        0;
  
  const criticalCount = result.metrics?.critical_issues || 0;
  const highCount = result.metrics?.high_priority_issues || 0;
  
  // Calculate score color
  const getScoreColor = (score: number | null) => {
    if (score === null) return 'text-gray-600';
    if (score >= 90) return 'text-green-600';
    if (score >= 70) return 'text-yellow-600';
    if (score >= 50) return 'text-orange-600';
    return 'text-red-600';
  };
  
  const getScoreBg = (score: number | null) => {
    if (score === null) return 'bg-gray-100';
    if (score >= 90) return 'bg-green-100';
    if (score >= 70) return 'bg-yellow-100';
    if (score >= 50) return 'bg-orange-100';
    return 'bg-red-100';
  };
  
  return (
    <div className="space-y-4">
      {/* Agent Summary */}
      <Card className={config?.bgColor}>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Icon className={`w-6 h-6 ${config?.color}`} />
              <div>
                <CardTitle>{config?.name || result.agent_type}</CardTitle>
                <CardDescription>{result.summary}</CardDescription>
              </div>
            </div>
            <Badge variant="outline">
              {result.execution_time_ms ? `${Math.round(result.execution_time_ms)}ms` : 'N/A'}
            </Badge>
          </div>
        </CardHeader>
        <CardContent>
          {/* Score Display */}
          {score !== null && (
            <div className="mb-6">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-gray-700">Quality Score</span>
                <span className={`text-3xl font-bold ${getScoreColor(score)}`}>
                  {Math.round(score)}/100
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-4 overflow-hidden">
                <div 
                  className={`h-full ${getScoreBg(score)} transition-all duration-500`}
                  style={{ width: `${score}%` }}
                />
              </div>
              <p className="text-xs text-gray-600 mt-2">
                {score >= 90 && '✨ Excellent! Code quality is outstanding.'}
                {score >= 70 && score < 90 && '👍 Good! Minor improvements possible.'}
                {score >= 50 && score < 70 && '⚠️ Fair. Several areas need attention.'}
                {score < 50 && '🔴 Poor. Significant improvements needed.'}
              </p>
            </div>
          )}
          
          {/* Metrics */}
          {result.metrics && Object.keys(result.metrics).length > 0 && (
            <div>
              <h4 className="text-sm font-semibold text-gray-700 mb-3">Analysis Details</h4>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {Object.entries(result.metrics).map(([key, value]) => {
                  let displayValue = 'N/A';
                  if (typeof value === 'number') {
                    displayValue = value.toFixed(0);
                  } else if (typeof value === 'string') {
                    displayValue = value;
                  } else if (typeof value === 'boolean') {
                    displayValue = value ? 'Yes' : 'No';
                  } else if (Array.isArray(value)) {
                    displayValue = value.length.toString();
                  }
                  
                  return (
                    <div key={key} className="text-center p-3 bg-white rounded-lg border border-gray-100">
                      <p className="text-xl font-bold text-gray-900">
                        {displayValue}
                      </p>
                      <p className="text-xs text-gray-600 capitalize mt-1">
                        {key.replace(/_/g, ' ')}
                      </p>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
          
          {/* Severity Breakdown */}
          {result.issues && result.issues.length > 0 && (
            <div className="mt-6 pt-4 border-t border-gray-200">
              <p className="text-sm font-semibold text-gray-700 mb-3">Issue Breakdown by Severity:</p>
              <div className="flex gap-2 flex-wrap">{Object.entries(issuesBySeverity).map(([severity, count]) => {
                  const config = severityConfig[severity as keyof typeof severityConfig];
                  if (!config) return null;
                  return (
                    <Badge key={severity} variant="outline" className="text-xs">
                      {config.label}: {count}
                    </Badge>
                  );
                })}
              </div>
            </div>
          )}
        </CardContent>
      </Card>
      
      {/* Issues List */}
      {result.issues && result.issues.length > 0 ? (
        <div className="space-y-4">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold">Issues Found ({result.issues.length})</h3>
            <Badge variant="secondary">{result.issues.length} total</Badge>
          </div>
          {result.issues.map((issue, idx) => (
            <IssueCard key={idx} issue={issue} />
          ))}
        </div>
      ) : (
        <Card className="border-green-200 bg-green-50">
          <CardContent className="pt-6">
            <div className="flex items-start gap-4">
              <div className="flex-shrink-0">
                <div className="w-12 h-12 rounded-full bg-green-100 flex items-center justify-center">
                  <CheckCircle2 className="h-6 w-6 text-green-600" />
                </div>
              </div>
              <div className="flex-1">
                <h4 className="text-lg font-semibold text-green-900 mb-2">
                  ✨ No Issues Detected!
                </h4>
                <p className="text-sm text-green-800 mb-4">
                  Excellent work! This agent analyzed {filesAnalyzed} file{filesAnalyzed !== 1 ? 's' : ''} and found no {agentKey} issues.
                </p>
                
                {/* Positive Findings */}
                <div className="space-y-2 text-sm">
                  <p className="font-medium text-green-900">✓ What was checked:</p>
                  <ul className="list-disc list-inside text-green-800 space-y-1 ml-2">
                    {agentKey === 'security' && (
                      <>
                        <li>No hardcoded secrets or API keys found</li>
                        <li>No SQL injection vulnerabilities detected</li>
                        <li>No unsafe deserialization patterns</li>
                        <li>Proper cryptographic functions in use</li>
                      </>
                    )}
                    {agentKey === 'performance' && (
                      <>
                        <li>No excessive nested loops detected</li>
                        <li>Cyclomatic complexity within acceptable range</li>
                        <li>No N+1 query patterns found</li>
                        <li>Efficient algorithms in use</li>
                      </>
                    )}
                    {agentKey === 'architecture' && (
                      <>
                        <li>SOLID principles properly applied</li>
                        <li>Classes and functions well-sized</li>
                        <li>Low coupling between components</li>
                        <li>Good design patterns observed</li>
                      </>
                    )}
                    {agentKey === 'test' && (
                      <>
                        <li>All tests have proper assertions</li>
                        <li>Test functions are well-structured</li>
                        <li>No test smells detected</li>
                        <li>Good test coverage observed</li>
                      </>
                    )}
                    {agentKey === 'documentation' && (
                      <>
                        <li>Functions and classes well-documented</li>
                        <li>Complete docstrings with parameters</li>
                        <li>README sections present</li>
                        <li>API documentation complete</li>
                      </>
                    )}
                  </ul>
                </div>
                
                {score && score >= 90 && (
                  <div className="mt-4 p-3 bg-white rounded-lg border border-green-200">
                    <p className="text-sm font-medium text-green-900">
                      🏆 Recommendation: Your code quality is exceptional! Consider sharing your best practices with the team.
                    </p>
                  </div>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

export default function V3AnalysisDisplay({ results }: { results: V3AnalysisResults }) {
  // Safely convert agent_results dictionary to array
  const agentResultsArray = Object.entries(results.agent_results || {}).map(([key, value]) => {
    // Ensure issues is always an array
    const issues = Array.isArray(value.issues) ? value.issues : [];
    
    return {
      agent_type: key,
      issues: issues,
      metrics: value.metrics || {},
      summary: value.summary || 'No summary available',
      execution_time_ms: value.execution_time_ms || 0
    };
  });
  
  const [selectedAgent, setSelectedAgent] = useState<string>(
    agentResultsArray[0]?.agent_type || 'security'
  );
  
  // Calculate overall statistics
  const totalIssues = results.total_issues;
  const criticalIssues = agentResultsArray.reduce(
    (sum, r) => sum + (r.issues?.filter((i: AgentIssue) => i.severity === 'CRITICAL').length || 0),
    0
  );
  const highIssues = agentResultsArray.reduce(
    (sum, r) => sum + (r.issues?.filter((i: AgentIssue) => i.severity === 'HIGH').length || 0),
    0
  );
  const mediumIssues = agentResultsArray.reduce(
    (sum, r) => sum + (r.issues?.filter((i: AgentIssue) => i.severity === 'MEDIUM').length || 0),
    0
  );
  
  // Calculate overall health score
  const overallScore = Math.round(
    agentResultsArray.reduce((sum, r) => {
      const score = r.metrics?.security_score || 
                    r.metrics?.performance_score || 
                    r.metrics?.architecture_score ||
                    r.metrics?.test_score ||
                    r.metrics?.documentation_score ||
                    0;
      return sum + score;
    }, 0) / (agentResultsArray.length || 1)
  );
  
  // Calculate technical debt (hours to fix)
  const technicalDebt = Math.round(
    criticalIssues * 4 + highIssues * 2 + mediumIssues * 0.5
  );
  
  // Calculate risk score (0-100, higher = more risk)
  const riskScore = Math.min(100, 
    criticalIssues * 25 + highIssues * 10 + mediumIssues * 5
  );
  
  // Industry benchmark comparison
  const industryBenchmark: {
    score: number;
    issues: number;
    comparison: 'above' | 'average' | 'below';
  } = {
    score: 75,
    issues: 8,
    comparison: overallScore >= 75 ? 'above' : overallScore >= 65 ? 'average' : 'below'
  };
  
  const getHealthStatus = () => {
    if (criticalIssues > 0) return { text: 'Critical Issues', color: 'text-red-600', bg: 'bg-red-50', icon: XCircle };
    if (highIssues > 5) return { text: 'Needs Attention', color: 'text-orange-600', bg: 'bg-orange-50', icon: AlertTriangle };
    if (totalIssues > 10) return { text: 'Fair', color: 'text-yellow-600', bg: 'bg-yellow-50', icon: Info };
    if (totalIssues > 0) return { text: 'Good', color: 'text-blue-600', bg: 'bg-blue-50', icon: CheckCircle2 };
    return { text: 'Excellent', color: 'text-green-600', bg: 'bg-green-50', icon: CheckCircle2 };
  };
  
  const healthStatus = getHealthStatus();
  
  // Export functionality
  const exportToJSON = () => {
    const dataStr = JSON.stringify(results, null, 2);
    const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr);
    const exportFileDefaultName = `analysis-${results.repository.name.replace('/', '-')}-${Date.now()}.json`;
    const linkElement = document.createElement('a');
    linkElement.setAttribute('href', dataUri);
    linkElement.setAttribute('download', exportFileDefaultName);
    linkElement.click();
  };
  
  const exportToCSV = () => {
    const csvRows = [
      ['File', 'Line', 'Severity', 'Agent', 'Title', 'Description', 'Recommendation'].join(',')
    ];
    
    agentResultsArray.forEach(agent => {
      agent.issues.forEach((issue: AgentIssue) => {
        csvRows.push([
          `"${issue.file_path}"`,
          issue.line_number,
          issue.severity,
          agent.agent_type,
          `"${issue.title}"`,
          `"${issue.description}"`,
          `"${issue.recommendation}"`
        ].join(','));
      });
    });
    
    const csvString = csvRows.join('\n');
    const blob = new Blob([csvString], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `analysis-${results.repository.name.replace('/', '-')}-${Date.now()}.csv`;
    link.click();
  };
  
  return (
    <div className="space-y-6">
      {/* Executive Summary Card */}
      <Card className="border-2">
        <CardHeader>
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <div className="flex items-center gap-3 mb-2">
                <CardTitle className="text-3xl">Code Quality Report</CardTitle>
                <Badge className={`${healthStatus.bg} ${healthStatus.color} border-0 text-sm px-4 py-2`}>
                  {healthStatus.icon && <healthStatus.icon className="w-4 h-4 mr-1 inline" />}
                  {healthStatus.text}
                </Badge>
              </div>
              <CardDescription className="text-base">
                Repository: <span className="font-semibold">{results.repository.name}</span> • Branch: <span className="font-semibold">{results.repository.branch}</span>
              </CardDescription>
            </div>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={exportToJSON}>
                <Download className="w-4 h-4 mr-2" />
                JSON
              </Button>
              <Button variant="outline" size="sm" onClick={exportToCSV}>
                <Download className="w-4 h-4 mr-2" />
                CSV
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Key Metrics Row */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {/* Overall Score */}
            <Card className="border-2 border-blue-200 bg-blue-50">
              <CardContent className="pt-6">
                <div className="text-center">
                  <div className="text-5xl font-bold text-blue-600 mb-2">{overallScore}</div>
                  <p className="text-sm font-medium text-gray-700">Overall Quality Score</p>
                  <div className="mt-3 flex items-center justify-center gap-2">
                    {industryBenchmark.comparison === 'above' ? (
                      <><TrendingUp className="w-4 h-4 text-green-600" /><span className="text-xs text-green-600 font-semibold">Above Industry Avg</span></>
                    ) : industryBenchmark.comparison === 'average' ? (
                      <><Target className="w-4 h-4 text-yellow-600" /><span className="text-xs text-yellow-600 font-semibold">Industry Average</span></>
                    ) : (
                      <><TrendingDown className="w-4 h-4 text-red-600" /><span className="text-xs text-red-600 font-semibold">Below Industry Avg</span></>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
            
            {/* Risk Score */}
            <Card className="border-2 border-orange-200 bg-orange-50">
              <CardContent className="pt-6">
                <div className="text-center">
                  <div className="text-5xl font-bold text-orange-600 mb-2">{riskScore}</div>
                  <p className="text-sm font-medium text-gray-700">Risk Score</p>
                  <div className="mt-3">
                    <div className="w-full bg-orange-200 rounded-full h-2">
                      <div 
                        className="h-full bg-orange-600 rounded-full transition-all"
                        style={{ width: `${Math.min(100, riskScore)}%` }}
                      />
                    </div>
                    <p className="text-xs text-gray-600 mt-1 font-semibold">{riskScore < 30 ? '🟢 Low Risk' : riskScore < 60 ? '🟡 Moderate Risk' : '🔴 High Risk'}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
            
            {/* Technical Debt */}
            <Card className="border-2 border-purple-200 bg-purple-50">
              <CardContent className="pt-6">
                <div className="text-center">
                  <div className="flex items-center justify-center gap-2 mb-2">
                    <Clock className="w-6 h-6 text-purple-600" />
                    <div className="text-5xl font-bold text-purple-600">{technicalDebt}</div>
                  </div>
                  <p className="text-sm font-medium text-gray-700">Hours to Fix</p>
                  <p className="text-xs text-gray-600 mt-3">
                    Estimated technical debt
                  </p>
                </div>
              </CardContent>
            </Card>
            
            {/* Cost Impact */}
            <Card className="border-2 border-green-200 bg-green-50">
              <CardContent className="pt-6">
                <div className="text-center">
                  <div className="flex items-center justify-center gap-2 mb-2">
                    <DollarSign className="w-6 h-6 text-green-600" />
                    <div className="text-4xl font-bold text-green-600">${Math.round(technicalDebt * 75).toLocaleString()}</div>
                  </div>
                  <p className="text-sm font-medium text-gray-700">Cost Impact</p>
                  <p className="text-xs text-gray-600 mt-3">
                    @ $75/hour engineering cost
                  </p>
                </div>
              </CardContent>
            </Card>
          </div>
          
          {/* Severity Breakdown Grid */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <div className="text-center p-4 bg-gray-50 rounded-lg border border-gray-200">
              <p className="text-3xl font-bold text-gray-900">{totalIssues}</p>
              <p className="text-xs text-gray-600 mt-1">Total Issues</p>
            </div>
            <div className="text-center p-4 bg-red-50 rounded-lg border border-red-200">
              <p className="text-3xl font-bold text-red-600">{criticalIssues}</p>
              <p className="text-xs text-gray-600 mt-1">Critical</p>
            </div>
            <div className="text-center p-4 bg-orange-50 rounded-lg border border-orange-200">
              <p className="text-3xl font-bold text-orange-600">{highIssues}</p>
              <p className="text-xs text-gray-600 mt-1">High Priority</p>
            </div>
            <div className="text-center p-4 bg-yellow-50 rounded-lg border border-yellow-200">
              <p className="text-3xl font-bold text-yellow-600">{mediumIssues}</p>
              <p className="text-xs text-gray-600 mt-1">Medium</p>
            </div>
            <div className="text-center p-4 bg-blue-50 rounded-lg border border-blue-200">
              <p className="text-3xl font-bold text-blue-600">{results.agents_run?.length || agentResultsArray.length}</p>
              <p className="text-xs text-gray-600 mt-1">Agents Used</p>
            </div>
          </div>
          
          {/* Quick Insights */}
          {totalIssues === 0 && (
            <Alert className="border-green-200 bg-green-50">
              <CheckCircle2 className="h-4 w-4 text-green-600" />
              <AlertTitle className="text-green-900">🎉 Perfect Score!</AlertTitle>
              <AlertDescription className="text-green-800">
                All {agentResultsArray.length} agents completed their analysis and found zero issues. Your codebase follows best practices across security, performance, architecture, testing, and documentation.
              </AlertDescription>
            </Alert>
          )}
        </CardContent>
      </Card>
      
      {/* Enterprise Metrics & Business Impact */}
      <EnterpriseMetrics 
        overallScore={overallScore}
        totalIssues={totalIssues}
        criticalIssues={criticalIssues}
        highIssues={highIssues}
        mediumIssues={mediumIssues}
        technicalDebt={technicalDebt}
        riskScore={riskScore}
        industryBenchmark={industryBenchmark}
      />
      
      {/* Agent Results Tabs */}
      <Tabs value={selectedAgent} onValueChange={setSelectedAgent}>
        <TabsList className="grid grid-cols-2 md:grid-cols-5 w-full">
          {agentResultsArray.map((result) => {
            const agentKey = result.agent_type.toLowerCase();
            const config = agentConfig[agentKey as keyof typeof agentConfig];
            const Icon = config?.icon || FileText;
            
            return (
              <TabsTrigger key={agentKey} value={agentKey} className="flex items-center gap-2">
                <Icon className="w-4 h-4" />
                <span className="hidden md:inline">{config?.name.split(' ')[0] || agentKey}</span>
                <Badge variant="secondary" className="ml-auto">
                  {result.issues?.length || 0}
                </Badge>
              </TabsTrigger>
            );
          })}
        </TabsList>
        
        {agentResultsArray.map((result) => {
          const agentKey = result.agent_type.toLowerCase();
          return (
            <TabsContent key={agentKey} value={agentKey}>
              <AgentResultPanel result={result} />
            </TabsContent>
          );
        })}
      </Tabs>
    </div>
  );
}
