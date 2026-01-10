import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Progress } from '@/components/ui/progress';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { 
  Shield, 
  Zap, 
  Building, 
  FileCheck, 
  FileText,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Info
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
  agent_results: AgentResult[];
  total_issues: number;
  execution_time_ms: number;
  agents_used: string[];
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
  const issuesBySeverity = result.issues.reduce((acc, issue) => {
    acc[issue.severity] = (acc[issue.severity] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);
  
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
              {result.execution_time_ms.toFixed(0)}ms
            </Badge>
          </div>
        </CardHeader>
        <CardContent>
          {/* Metrics */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {Object.entries(result.metrics).map(([key, value]) => (
              <div key={key} className="text-center">
                <p className="text-2xl font-bold text-gray-900">
                  {typeof value === 'number' ? value.toFixed(0) : value}
                </p>
                <p className="text-xs text-gray-600 capitalize">
                  {key.replace(/_/g, ' ')}
                </p>
              </div>
            ))}
          </div>
          
          {/* Severity Breakdown */}
          {result.issues.length > 0 && (
            <div className="mt-4">
              <p className="text-sm font-medium mb-2">Issue Breakdown:</p>
              <div className="flex gap-2 flex-wrap">
                {Object.entries(issuesBySeverity).map(([severity, count]) => (
                  <Badge key={severity} variant="outline">
                    {severityConfig[severity as keyof typeof severityConfig].label}: {count}
                  </Badge>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>
      
      {/* Issues List */}
      {result.issues.length > 0 ? (
        <div className="space-y-4">
          <h3 className="text-lg font-semibold">Issues Found ({result.issues.length})</h3>
          {result.issues.map((issue, idx) => (
            <IssueCard key={idx} issue={issue} />
          ))}
        </div>
      ) : (
        <Alert>
          <CheckCircle2 className="h-4 w-4" />
          <AlertTitle>No Issues Found</AlertTitle>
          <AlertDescription>
            This agent found no issues in the analyzed code.
          </AlertDescription>
        </Alert>
      )}
    </div>
  );
}

export default function V3AnalysisDisplay({ results }: { results: V3AnalysisResults }) {
  const [selectedAgent, setSelectedAgent] = useState<string>(
    results.agent_results[0]?.agent_type?.toLowerCase() || 'security'
  );
  
  // Calculate overall statistics
  const totalIssues = results.total_issues;
  const criticalIssues = results.agent_results.reduce(
    (sum, r) => sum + r.issues.filter(i => i.severity === 'CRITICAL').length,
    0
  );
  const highIssues = results.agent_results.reduce(
    (sum, r) => sum + r.issues.filter(i => i.severity === 'HIGH').length,
    0
  );
  
  return (
    <div className="space-y-6">
      {/* Repository Header */}
      <Card>
        <CardHeader>
          <CardTitle className="text-2xl">Advanced Multi-Agent Analysis</CardTitle>
          <CardDescription>
            <div className="flex items-center gap-2 mt-2">
              <span className="font-medium">{results.repository.name}</span>
              <Badge variant="outline">{results.repository.branch}</Badge>
            </div>
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center">
              <p className="text-3xl font-bold text-gray-900">{totalIssues}</p>
              <p className="text-sm text-gray-600">Total Issues</p>
            </div>
            <div className="text-center">
              <p className="text-3xl font-bold text-red-600">{criticalIssues}</p>
              <p className="text-sm text-gray-600">Critical</p>
            </div>
            <div className="text-center">
              <p className="text-3xl font-bold text-orange-600">{highIssues}</p>
              <p className="text-sm text-gray-600">High Priority</p>
            </div>
            <div className="text-center">
              <p className="text-3xl font-bold text-blue-600">{results.agents_used.length}</p>
              <p className="text-sm text-gray-600">Agents Used</p>
            </div>
          </div>
        </CardContent>
      </Card>
      
      {/* Agent Results Tabs */}
      <Tabs value={selectedAgent} onValueChange={setSelectedAgent}>
        <TabsList className="grid grid-cols-2 md:grid-cols-5 w-full">
          {results.agent_results.map((result) => {
            const agentKey = result.agent_type.toLowerCase();
            const config = agentConfig[agentKey as keyof typeof agentConfig];
            const Icon = config?.icon || FileText;
            
            return (
              <TabsTrigger key={agentKey} value={agentKey} className="flex items-center gap-2">
                <Icon className="w-4 h-4" />
                <span className="hidden md:inline">{config?.name.split(' ')[0] || agentKey}</span>
                <Badge variant="secondary" className="ml-auto">
                  {result.issues.length}
                </Badge>
              </TabsTrigger>
            );
          })}
        </TabsList>
        
        {results.agent_results.map((result) => {
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
