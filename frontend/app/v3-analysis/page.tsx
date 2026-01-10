'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Checkbox } from '@/components/ui/checkbox';
import { Loader2, AlertCircle } from 'lucide-react';
import { PiecesStyleAnalysis } from '@/components/PiecesStyleAnalysis';
import { apiClient } from '@/lib/api';
import { Header } from '@/components/layout';

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
  
  return (
    <>
      <Header />
      <main className="min-h-screen bg-background">
        {/* Render Results or Form */}
        {results ? (
          <PiecesStyleAnalysis results={results} onBack={() => setResults(null)} />
        ) : (
          <div className="px-6 py-6">
            <div className="max-w-3xl mx-auto">
              {/* Header */}
              <div className="mb-4">
                <h1 className="text-lg font-medium text-foreground mb-1">Advanced Multi-Agent Analysis</h1>
                <p className="text-xs text-muted-foreground">Run comprehensive code analysis using specialized AI agents</p>
              </div>

              {/* Form */}
              <div className="bg-card border border-border rounded p-4 space-y-4">
                {/* Repository Input */}
                <div className="space-y-1">
                  <Label htmlFor="repo-url" className="text-xs text-muted-foreground">Repository URL</Label>
                  <Input
                    id="repo-url"
                    placeholder="https://github.com/owner/repo"
                    value={repoUrl}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setRepoUrl(e.target.value)}
                    className="bg-muted border-border text-foreground"
                  />
                </div>
                
                {/* Branch Input */}
                <div className="space-y-1">
                  <Label htmlFor="branch" className="text-xs text-muted-foreground">Branch</Label>
                  <Input
                    id="branch"
                    placeholder="main"
                    value={branch}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setBranch(e.target.value)}
                    className="bg-muted border-border text-foreground"
                  />
                </div>
          
                {/* Agent Selection */}
                <div className="space-y-2">
                  <Label className="text-xs text-muted-foreground">Select Agents</Label>
                  <div className="space-y-1">
                    {agents.map((agent) => (
                      <div key={agent.id} className="flex items-start space-x-3 p-2 border border-border rounded hover:bg-muted/20 transition-colors">
                        <Checkbox
                          id={agent.id}
                          checked={agent.enabled}
                          onCheckedChange={() => toggleAgent(agent.id)}
                        />
                        <div className="flex-1">
                          <label
                            htmlFor={agent.id}
                            className="text-xs font-medium text-foreground cursor-pointer"
                          >
                            {agent.name}
                          </label>
                          <p className="text-[11px] text-muted-foreground mt-0.5">{agent.description}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
          
                {/* Parallel Execution */}
                <div className="flex items-center justify-between p-3 border border-border rounded">
                  <div>
                    <Label htmlFor="parallel" className="text-xs font-medium text-foreground">Parallel Execution</Label>
                    <p className="text-[11px] text-muted-foreground">
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
                  <div className="bg-card border border-destructive rounded p-3 flex items-start gap-2">
                    <AlertCircle className="w-4 h-4 text-destructive flex-shrink-0 mt-0.5" />
                    <p className="text-xs text-destructive">{error}</p>
                  </div>
                )}
                
                {/* Submit Button */}
                <Button
                  onClick={runAnalysis}
                  disabled={loading}
                  className="w-full bg-primary hover:bg-primary/90 text-primary-foreground"
                >
                  {loading ? (
                    <>
                      <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" />
                      Running Analysis...
                    </>
                  ) : (
                    'Run Advanced Analysis'
                  )}
                </Button>
              </div>
            </div>
          </div>
        )}
      </main>
    </>
  );
}
