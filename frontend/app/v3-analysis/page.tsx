'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Checkbox } from '@/components/ui/checkbox';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Loader2, AlertCircle } from 'lucide-react';
import { ModernV3Analysis } from '@/components/ModernV3Analysis';
import { apiClient } from '@/lib/api';

interface AgentOption {
  id: string;
  name: string;
  description: string;
  enabled: boolean;
}

export default function V3AnalysisPage() {
  const [repoUrl, setRepoUrl] = useState('');
  const [branch, setBranch] = useState('main');
  const [parallel, setParallel] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<any>(null);
  
  const [agents, setAgents] = useState<AgentOption[]>([
    {
      id: 'security',
      name: 'Security Agent',
      description: 'Detect vulnerabilities, hardcoded secrets, SQL injection',
      enabled: true,
    },
    {
      id: 'performance',
      name: 'Performance Agent',
      description: 'Find complexity issues, N+1 queries, optimization opportunities',
      enabled: true,
    },
    {
      id: 'architecture',
      name: 'Architecture Agent',
      description: 'Check SOLID principles, design patterns, code smells',
      enabled: true,
    },
    {
      id: 'test',
      name: 'Test Quality Agent',
      description: 'Analyze test coverage, test quality, missing tests',
      enabled: true,
    },
    {
      id: 'documentation',
      name: 'Documentation Agent',
      description: 'Check docstrings, API docs, README completeness',
      enabled: true,
    },
  ]);
  
  const toggleAgent = (agentId: string) => {
    setAgents(agents.map(a => 
      a.id === agentId ? { ...a, enabled: !a.enabled } : a
    ));
  };
  
  const runAnalysis = async () => {
    if (!repoUrl) {
      setError('Please enter a repository URL');
      return;
    }
    
    setLoading(true);
    setError(null);
    setResults(null);
    
    try {
      const selectedAgents = agents.filter(a => a.enabled).map(a => a.id);
      
      if (selectedAgents.length === 0) {
        setError('Please select at least one agent');
        setLoading(false);
        return;
      }
      
      const response = await apiClient.post('/analysis/v3/advanced', {
        repository_url: repoUrl,
        branch,
        agents: selectedAgents,
        parallel,
      });
      
      setResults(response.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Analysis failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };
  
  if (results) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-slate-50">
        <div className="max-w-7xl mx-auto px-6 py-8">
          <Button 
            variant="outline" 
            onClick={() => setResults(null)}
            className="mb-6"
          >
            ← New Analysis
          </Button>
        </div>
        <ModernV3Analysis results={results} />
      </div>
    );
  }
  
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-slate-50">
      <div className="max-w-4xl mx-auto px-6 py-12">
        <Card className="border-2 shadow-xl">
          <CardHeader className="bg-gradient-to-r from-slate-900 to-slate-800 text-white rounded-t-lg">
            <CardTitle className="text-3xl font-bold">Advanced Multi-Agent Analysis</CardTitle>
            <CardDescription className="text-slate-300 text-lg">
              Run comprehensive code analysis using specialized AI agents
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6 pt-6">
          {/* Repository Input */}
          <div className="space-y-2">
            <Label htmlFor="repo-url">Repository URL</Label>
            <Input
              id="repo-url"
              placeholder="https://github.com/owner/repo"
              value={repoUrl}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setRepoUrl(e.target.value)}
            />
          </div>
          
          {/* Branch Input */}
          <div className="space-y-2">
            <Label htmlFor="branch">Branch</Label>
            <Input
              id="branch"
              placeholder="main"
              value={branch}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setBranch(e.target.value)}
            />
          </div>
          
          {/* Agent Selection */}
          <div className="space-y-4">
            <Label>Select Agents</Label>
            <div className="space-y-3">
              {agents.map((agent) => (
                <div key={agent.id} className="flex items-start space-x-3 p-3 border rounded-lg">
                  <Checkbox
                    id={agent.id}
                    checked={agent.enabled}
                    onCheckedChange={() => toggleAgent(agent.id)}
                  />
                  <div className="flex-1">
                    <label
                      htmlFor={agent.id}
                      className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer"
                    >
                      {agent.name}
                    </label>
                    <p className="text-sm text-gray-500 mt-1">{agent.description}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
          
          {/* Parallel Execution */}
          <div className="flex items-center justify-between p-4 border rounded-lg">
            <div>
              <Label htmlFor="parallel">Parallel Execution</Label>
              <p className="text-sm text-gray-500">
                Run all agents simultaneously for faster analysis
              </p>
            </div>
            <Switch
              id="parallel"
              checked={parallel}
              onCheckedChange={setParallel}
            />
          </div>
          
          {/* Error Display */}
          {error && (
            <Alert className="border-red-200 bg-red-50">
              <AlertCircle className="h-4 w-4 text-red-600" />
              <AlertDescription className="text-red-800">{error}</AlertDescription>
            </Alert>
          )}
          
          {/* Submit Button */}
          <Button
            onClick={runAnalysis}
            disabled={loading}
            className="w-full"
            size="lg"
          >
            {loading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Running Analysis...
              </>
            ) : (
              'Run Advanced Analysis'
            )}
          </Button>
        </CardContent>
      </Card>
      </div>
    </div>
  );
}
