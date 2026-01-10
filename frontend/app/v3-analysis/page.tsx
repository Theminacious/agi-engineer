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
      name: 'Security',
      description: 'Vulnerabilities, secrets, injection risks',
      enabled: true,
    },
    {
      id: 'performance',
      name: 'Performance',
      description: 'Complexity, hot paths, optimization signals',
      enabled: true,
    },
    {
      id: 'architecture',
      name: 'Architecture',
      description: 'Design quality, coupling, code smells',
      enabled: true,
    },
    {
      id: 'test',
      name: 'Test Quality',
      description: 'Coverage gaps, weak or missing tests',
      enabled: true,
    },
    {
      id: 'documentation',
      name: 'Documentation',
      description: 'Docs, comments, API clarity',
      enabled: true,
    },
  ]);

  const toggleAgent = (id: string) => {
    setAgents(prev =>
      prev.map(a => (a.id === id ? { ...a, enabled: !a.enabled } : a))
    );
  };

  const runAnalysis = async () => {
    if (!repoUrl) {
      setError('Repository URL is required');
      return;
    }

    const selectedAgents = agents.filter(a => a.enabled).map(a => a.id);
    if (selectedAgents.length === 0) {
      setError('Select at least one agent');
      return;
    }

    setLoading(true);
    setError(null);
    setResults(null);

    try {
      const res = await apiClient.post('/analysis/v3/advanced', {
        repository_url: repoUrl,
        branch,
        agents: selectedAgents,
        parallel,
      });

      setResults(res.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Analysis failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <Header />
      <main className="min-h-screen bg-background">
        {results ? (
          <PiecesStyleAnalysis results={results} onBack={() => setResults(null)} />
        ) : (
          <div className="px-6 py-6">
            <div className="mx-auto max-w-4xl space-y-6">

              {/* Page Header */}
              <div>
                <h1 className="text-xl font-semibold text-foreground">
                  New V3 Analysis
                </h1>
                <p className="text-sm text-muted-foreground">
                  Configure and run multi-agent analysis on a repository
                </p>
              </div>

              {/* Repository Config */}
              <div className="grid md:grid-cols-2 gap-4">
                <div className="space-y-1">
                  <Label className="text-xs text-muted-foreground">
                    Repository URL
                  </Label>
                  <Input
                    placeholder="https://github.com/org/repo"
                    value={repoUrl}
                    onChange={e => setRepoUrl(e.target.value)}
                    className="bg-muted border-border"
                  />
                </div>

                <div className="space-y-1">
                  <Label className="text-xs text-muted-foreground">
                    Branch
                  </Label>
                  <Input
                    placeholder="main"
                    value={branch}
                    onChange={e => setBranch(e.target.value)}
                    className="bg-muted border-border"
                  />
                </div>
              </div>

              {/* Agents */}
              <div className="bg-card border border-border rounded">
                <div className="px-4 py-3 border-b border-border">
                  <h2 className="text-sm font-semibold">Analysis Agents</h2>
                  <p className="text-xs text-muted-foreground">
                    Enable or disable specialized agents
                  </p>
                </div>

                <div className="divide-y divide-border">
                  {agents.map(agent => (
                    <div
                      key={agent.id}
                      className="flex items-start gap-3 px-4 py-3 hover:bg-muted/30 transition"
                    >
                      <Checkbox
                        checked={agent.enabled}
                        onCheckedChange={() => toggleAgent(agent.id)}
                      />
                      <div className="flex-1">
                        <p className="text-sm font-medium text-foreground">
                          {agent.name}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {agent.description}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Parallel Toggle */}
              <div className="flex items-center justify-between border border-border rounded px-4 py-3 bg-card">
                <div>
                  <p className="text-sm font-medium">Parallel Execution</p>
                  <p className="text-xs text-muted-foreground">
                    Run all enabled agents simultaneously
                  </p>
                </div>
                <Switch checked={parallel} onCheckedChange={setParallel} />
              </div>

              {/* Error */}
              {error && (
                <div className="flex items-start gap-2 border border-destructive rounded px-3 py-2 bg-card">
                  <AlertCircle className="w-4 h-4 text-destructive mt-0.5" />
                  <p className="text-xs text-destructive">{error}</p>
                </div>
              )}

              {/* Action */}
              <div className="flex justify-end">
                <Button
                  onClick={runAnalysis}
                  disabled={loading}
                  className="bg-primary"
                >
                  {loading ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Running…
                    </>
                  ) : (
                    'Run Analysis'
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
