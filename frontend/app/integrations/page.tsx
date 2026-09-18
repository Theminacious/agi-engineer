/**
 * GitHub Integration Page — Phase 17
 * 
 * Features:
 * - Connect GitHub App
 * - View connected repositories
 * - Enable/disable auto-analysis
 * - View PR analysis activity log
 */
"use client";




import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Loader2, CheckCircle2, XCircle, AlertCircle, Github, Activity } from "lucide-react";
import { apiUrl } from "@/lib/api";
import { ChangeRiskCard } from "@/components/github/ChangeRiskCard";
import {
  fetchPRAnalyses,
  fetchPRAnalysis,
  recommendationLabel,
  riskLevelClassName,
  riskLevelLabel,
  type PRAnalysisDetail,
  type PRAnalysisSummary,
} from "@/lib/prAnalyses";

interface Installation {
  id: number;
  installation_id: number;
  github_user: string;
  github_org?: string;
  is_active: boolean;
  created_at: string;
}

interface WebhookEvent {
  id: number;
  delivery_id: string;
  event_type: string;
  repository: string;
  pr_number?: number;
  created_at: string;
}

export default function IntegrationsPage() {
  const [loading, setLoading] = useState(true);
  const [installations, setInstallations] = useState<Installation[]>([]);
  const [prAnalyses, setPrAnalyses] = useState<PRAnalysisSummary[]>([]);
  const [repositories, setRepositories] = useState<string[]>([]);
  const [selectedRepository, setSelectedRepository] = useState<string>("");
  const [webhookEvents, setWebhookEvents] = useState<WebhookEvent[]>([]);
  const [activeTab, setActiveTab] = useState<"overview" | "risk" | "activity">("overview");
  const [analysesError, setAnalysesError] = useState<string | null>(null);
  const [analysesLoading, setAnalysesLoading] = useState(false);
  const [selectedAnalysisId, setSelectedAnalysisId] = useState<number | null>(null);
  const [detail, setDetail] = useState<PRAnalysisDetail | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    loadPRAnalyses();
  }, [selectedRepository]);

  useEffect(() => {
    if (selectedAnalysisId === null) {
      setDetail(null);
      return;
    }
    loadPRAnalysisDetail(selectedAnalysisId);
  }, [selectedAnalysisId]);

  const loadPRAnalyses = async () => {
    setAnalysesLoading(true);
    setAnalysesError(null);
    try {
      const data = await fetchPRAnalyses(selectedRepository || undefined);
      setPrAnalyses(data.analyses);
      setRepositories(data.repositories);
      setSelectedAnalysisId((current) => {
        if (current !== null && data.analyses.some((a) => a.id === current)) return current;
        return data.analyses.length > 0 ? data.analyses[0].id : null;
      });
    } catch (error) {
      setAnalysesError(
        error instanceof Error ? error.message : "Failed to load PR analyses",
      );
      setPrAnalyses([]);
    } finally {
      setAnalysesLoading(false);
    }
  };

  const loadPRAnalysisDetail = async (id: number) => {
    setDetailLoading(true);
    setDetailError(null);
    try {
      setDetail(await fetchPRAnalysis(id));
    } catch (error) {
      setDetailError(
        error instanceof Error ? error.message : "Failed to load change risk",
      );
      setDetail(null);
    } finally {
      setDetailLoading(false);
    }
  };

  const loadData = async () => {
    setLoading(true);
    try {
      // Load installations
      const installationsRes = await fetch(apiUrl("/api/installations"));
      if (installationsRes.ok) {
        const data = await installationsRes.json();
        setInstallations(data.installations || []);
      }

      // Load recent webhook events
      const webhooksRes = await fetch(apiUrl("/api/github/webhook-events?limit=20"));
      if (webhooksRes.ok) {
        const data = await webhooksRes.json();
        setWebhookEvents(data.events || []);
      }
    } catch (error) {
      console.error("Error loading data:", error);
    } finally {
      setLoading(false);
    }
  };

  const connectGitHub = () => {
    // Redirect to GitHub App installation
    window.location.href = "/oauth/authorize";
  };

  const getReliabilityBadge = (score?: string | null) => {
    if (!score) return null;
    
    const variants: Record<string, { color: string; icon: any }> = {
      excellent: { color: "bg-green-500", icon: CheckCircle2 },
      good: { color: "bg-blue-500", icon: CheckCircle2 },
      concerning: { color: "bg-yellow-500", icon: AlertCircle },
      critical: { color: "bg-red-500", icon: XCircle }
    };

    const variant = variants[score.toLowerCase()] || variants.concerning;
    const Icon = variant.icon;

    return (
      <Badge className={`${variant.color} text-white`}>
        <Icon className="w-3 h-3 mr-1" />
        {score.toUpperCase()}
      </Badge>
    );
  };

  const getStatusBadge = (status: string) => {
    const variants: Record<string, string> = {
      pending: "bg-gray-500",
      in_progress: "bg-blue-500",
      completed: "bg-green-500",
      failed: "bg-red-500"
    };

    return (
      <Badge className={`${variants[status] || "bg-gray-500"} text-white`}>
        {status.toUpperCase().replace("_", " ")}
      </Badge>
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="container mx-auto py-8 px-4">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">GitHub Integrations</h1>
        <p className="text-muted-foreground">
          Connect your GitHub repositories for automated reliability analysis on every PR
        </p>
      </div>

      {/* Tab Navigation */}
      <div className="flex space-x-1 mb-6 border-b">
        <button
          onClick={() => setActiveTab("overview")}
          className={`px-4 py-2 font-medium transition-colors ${
            activeTab === "overview"
              ? "border-b-2 border-primary text-primary"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          Overview
        </button>
        <button
          onClick={() => setActiveTab("risk")}
          className={`px-4 py-2 font-medium transition-colors ${
            activeTab === "risk"
              ? "border-b-2 border-primary text-primary"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          Change Risk
        </button>
        <button
          onClick={() => setActiveTab("activity")}
          className={`px-4 py-2 font-medium transition-colors ${
            activeTab === "activity"
              ? "border-b-2 border-primary text-primary"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          Activity Log
        </button>
      </div>

      {activeTab === "overview" && (
        <div className="space-y-6">
          {/* Connection Status */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center">
                <Github className="w-5 h-5 mr-2" />
                GitHub App Connection
              </CardTitle>
              <CardDescription>
                Connect AGI Engineer to your GitHub account to enable automated PR analysis
              </CardDescription>
            </CardHeader>
            <CardContent>
              {installations.length === 0 ? (
                <div className="text-center py-8">
                  <Github className="w-16 h-16 mx-auto mb-4 text-muted-foreground" />
                  <h3 className="text-lg font-semibold mb-2">No GitHub Connection</h3>
                  <p className="text-muted-foreground mb-4">
                    Connect your GitHub account to start analyzing PRs automatically
                  </p>
                  <Button onClick={connectGitHub}>
                    <Github className="w-4 h-4 mr-2" />
                    Connect GitHub
                  </Button>
                </div>
              ) : (
                <div className="space-y-4">
                  {installations.map((installation) => (
                    <div
                      key={installation.id}
                      className="flex items-center justify-between p-4 border rounded-lg"
                    >
                      <div className="flex items-center space-x-4">
                        <Github className="w-8 h-8 text-muted-foreground" />
                        <div>
                          <div className="font-semibold">
                            {installation.github_org || installation.github_user}
                          </div>
                          <div className="text-sm text-muted-foreground">
                            Connected {new Date(installation.created_at).toLocaleDateString()}
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center space-x-2">
                        {installation.is_active ? (
                          <Badge className="bg-green-500 text-white">
                            <CheckCircle2 className="w-3 h-3 mr-1" />
                            Active
                          </Badge>
                        ) : (
                          <Badge className="bg-gray-500 text-white">Inactive</Badge>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Auto-Analysis Settings */}
          {installations.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Auto-Analysis Settings</CardTitle>
                <CardDescription>
                  Configure which events trigger automatic reliability analysis
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex items-center justify-between p-4 border rounded-lg">
                    <div>
                      <div className="font-medium">Analyze Pull Requests</div>
                      <div className="text-sm text-muted-foreground">
                        Run analysis when PRs are opened or updated
                      </div>
                    </div>
                    <Switch defaultChecked />
                  </div>
                  <div className="flex items-center justify-between p-4 border rounded-lg">
                    <div>
                      <div className="font-medium">Post Comments</div>
                      <div className="text-sm text-muted-foreground">
                        Post reliability findings as PR comments
                      </div>
                    </div>
                    <Switch defaultChecked />
                  </div>
                  <div className="flex items-center justify-between p-4 border rounded-lg">
                    <div>
                      <div className="font-medium">Create Status Checks</div>
                      <div className="text-sm text-muted-foreground">
                        Add reliability status checks to PRs
                      </div>
                    </div>
                    <Switch defaultChecked />
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Recent PR Analyses */}
          {prAnalyses.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Recent PR Analyses</CardTitle>
                <CardDescription>Latest reliability analysis results</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {prAnalyses.map((analysis) => (
                    <div
                      key={analysis.id}
                      className="flex items-center justify-between p-4 border rounded-lg hover:bg-accent transition-colors"
                    >
                      <div className="flex-1">
                        <div className="font-medium">
                          {analysis.repository} #{analysis.pr_number}
                        </div>
                        <div className="text-sm text-muted-foreground">
                          {analysis.critical_risks_count} critical, {analysis.high_risks_count} high,{" "}
                          {analysis.medium_risks_count} medium | {analysis.fix_candidates_count} fixes
                        </div>
                      </div>
                      <div className="flex items-center space-x-2">
                        <Badge className={`border ${riskLevelClassName(analysis.change_risk_level)}`}>
                          {riskLevelLabel(analysis.change_risk_level)}
                        </Badge>
                        {getReliabilityBadge(analysis.reliability_score)}
                        {getStatusBadge(analysis.status || "pending")}
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {activeTab === "risk" && (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Analysed pull requests</CardTitle>
              <CardDescription>
                Select a PR to see what its change touches and why the risk level is what it is
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {repositories.length > 0 && (
                <div>
                  <label
                    htmlFor="repository-filter"
                    className="mb-1 block text-sm font-medium"
                  >
                    Repository
                  </label>
                  <select
                    id="repository-filter"
                    className="w-full rounded-md border bg-background px-3 py-2 text-sm sm:w-80"
                    value={selectedRepository}
                    onChange={(event) => setSelectedRepository(event.target.value)}
                  >
                    <option value="">All repositories</option>
                    {repositories.map((repository) => (
                      <option key={repository} value={repository}>
                        {repository}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              {analysesLoading && (
                <div role="status" className="flex items-center gap-2 py-6 text-sm text-muted-foreground">
                  <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                  Loading PR analyses…
                </div>
              )}

              {!analysesLoading && analysesError && (
                <div role="alert" className="rounded-lg border border-red-300 bg-red-50 p-4">
                  <p className="text-sm font-medium text-red-900">{analysesError}</p>
                  <Button className="mt-3" variant="outline" onClick={loadPRAnalyses}>
                    Retry
                  </Button>
                </div>
              )}

              {!analysesLoading && !analysesError && prAnalyses.length === 0 && (
                <div className="rounded-lg border border-dashed p-8 text-center text-sm text-muted-foreground">
                  <p className="font-medium text-foreground">No PR analyses yet</p>
                  <p className="mt-1">
                    Open or update a pull request on a connected repository and its change risk
                    will appear here.
                  </p>
                </div>
              )}

              {!analysesLoading && !analysesError && prAnalyses.length > 0 && (
                <ul className="space-y-2">
                  {prAnalyses.map((analysis) => (
                    <li key={analysis.id}>
                      <button
                        onClick={() => setSelectedAnalysisId(analysis.id)}
                        aria-current={selectedAnalysisId === analysis.id ? "true" : undefined}
                        className={`flex w-full flex-wrap items-center justify-between gap-2 rounded-lg border p-4 text-left transition-colors hover:bg-accent ${
                          selectedAnalysisId === analysis.id ? "border-primary bg-accent" : ""
                        }`}
                      >
                        <span>
                          <span className="block font-medium">
                            {analysis.repository} #{analysis.pr_number}
                          </span>
                          <span className="block text-sm text-muted-foreground">
                            {analysis.head_sha.slice(0, 7)} ·{" "}
                            {recommendationLabel(analysis.change_risk_recommendation)}
                          </span>
                        </span>
                        <Badge className={`border ${riskLevelClassName(analysis.change_risk_level)}`}>
                          {riskLevelLabel(analysis.change_risk_level)}
                        </Badge>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>

          {detailLoading && (
            <div role="status" className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
              Loading change risk…
            </div>
          )}

          {!detailLoading && detailError && selectedAnalysisId !== null && (
            <div role="alert" className="rounded-lg border border-red-300 bg-red-50 p-4">
              <p className="text-sm font-medium text-red-900">{detailError}</p>
              <Button
                className="mt-3"
                variant="outline"
                onClick={() => loadPRAnalysisDetail(selectedAnalysisId)}
              >
                Retry
              </Button>
            </div>
          )}

          {!detailLoading && !detailError && detail && (
            <ChangeRiskCard
              prNumber={detail.pr_number}
              repository={detail.repository}
              changeRisk={detail.change_risk}
            />
          )}
        </div>
      )}

      {activeTab === "activity" && (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center">
                <Activity className="w-5 h-5 mr-2" />
                Webhook Activity
              </CardTitle>
              <CardDescription>Recent GitHub webhook events</CardDescription>
            </CardHeader>
            <CardContent>
              {webhookEvents.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  No webhook events yet
                </div>
              ) : (
                <div className="space-y-2">
                  {webhookEvents.map((event) => (
                    <div
                      key={event.id}
                      className="flex items-center justify-between p-3 border rounded-lg text-sm"
                    >
                      <div className="flex-1">
                        <div className="font-medium">{event.event_type}</div>
                        <div className="text-muted-foreground">
                          {event.repository}
                          {event.pr_number && ` #${event.pr_number}`}
                        </div>
                      </div>
                      <div className="text-muted-foreground">
                        {new Date(event.created_at).toLocaleString()}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
