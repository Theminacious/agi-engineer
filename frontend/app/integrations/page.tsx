/**
 * GitHub Integration Page — Phase 17
 * 
 * Features:
 * - Connect GitHub App
 * - View connected repositories
 * - Enable/disable auto-analysis
 * - View PR analysis activity log
 */

export const dynamic = 'force-dynamic';

"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Loader2, CheckCircle2, XCircle, AlertCircle, Github, Activity } from "lucide-react";

interface Installation {
  id: number;
  installation_id: number;
  github_user: string;
  github_org?: string;
  is_active: boolean;
  created_at: string;
}

interface PRAnalysis {
  id: number;
  repository: string;
  pr_number: number;
  head_sha: string;
  status: string;
  reliability_score?: string;
  critical_risks_count: number;
  high_risks_count: number;
  medium_risks_count: number;
  fix_candidates_count: number;
  comment_posted: boolean;
  status_check_posted: boolean;
  completed_at?: string;
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
  const [prAnalyses, setPrAnalyses] = useState<PRAnalysis[]>([]);
  const [webhookEvents, setWebhookEvents] = useState<WebhookEvent[]>([]);
  const [activeTab, setActiveTab] = useState<"overview" | "activity">("overview");

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      // Load installations
      const installationsRes = await fetch("/api/installations");
      if (installationsRes.ok) {
        const data = await installationsRes.json();
        setInstallations(data.installations || []);
      }

      // Load recent webhook events
      const webhooksRes = await fetch("/api/github/webhook-events?limit=20");
      if (webhooksRes.ok) {
        const data = await webhooksRes.json();
        setWebhookEvents(data.events || []);
      }

      // Load recent PR analyses (would need backend endpoint)
      // For now, mock data
      setPrAnalyses([]);
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

  const getReliabilityBadge = (score?: string) => {
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
                        {getReliabilityBadge(analysis.reliability_score)}
                        {getStatusBadge(analysis.status)}
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
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
