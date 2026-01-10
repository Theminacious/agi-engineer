import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { 
  TrendingUp, 
  TrendingDown, 
  Target, 
  Clock, 
  DollarSign, 
  Users,
  AlertTriangle,
  CheckCircle2,
  Shield,
  Zap,
  FileCode,
  BarChart3
} from 'lucide-react';

interface EnterpriseMetricsProps {
  overallScore: number;
  totalIssues: number;
  criticalIssues: number;
  highIssues: number;
  mediumIssues: number;
  technicalDebt: number;
  riskScore: number;
  industryBenchmark: {
    score: number;
    issues: number;
    comparison: 'above' | 'average' | 'below';
  };
}

export function EnterpriseMetrics({
  overallScore,
  totalIssues,
  criticalIssues,
  highIssues,
  mediumIssues,
  technicalDebt,
  riskScore,
  industryBenchmark
}: EnterpriseMetricsProps) {
  // Calculate priority recommendations
  const getPriorityActions = () => {
    const actions = [];
    
    if (criticalIssues > 0) {
      actions.push({
        priority: 'URGENT',
        title: `Fix ${criticalIssues} Critical Security Issues`,
        description: 'These issues pose immediate security risks and should be addressed within 24 hours',
        impact: 'High',
        effort: `${criticalIssues * 4}h`,
        color: 'red',
        icon: Shield
      });
    }
    
    if (highIssues > 5) {
      actions.push({
        priority: 'HIGH',
        title: `Address ${highIssues} High-Priority Performance Issues`,
        description: 'Performance bottlenecks affecting user experience and scalability',
        impact: 'High',
        effort: `${highIssues * 2}h`,
        color: 'orange',
        icon: Zap
      });
    }
    
    if (overallScore < 70) {
      actions.push({
        priority: 'MEDIUM',
        title: 'Improve Code Quality Score',
        description: `Current score (${overallScore}/100) is below industry standard (75/100)`,
        impact: 'Medium',
        effort: `${technicalDebt}h`,
        color: 'yellow',
        icon: BarChart3
      });
    }
    
    if (mediumIssues > 10) {
      actions.push({
        priority: 'MEDIUM',
        title: `Refactor ${mediumIssues} Architecture Violations`,
        description: 'Code structure improvements for better maintainability',
        impact: 'Medium',
        effort: `${mediumIssues * 0.5}h`,
        color: 'blue',
        icon: FileCode
      });
    }
    
    return actions;
  };

  const priorityActions = getPriorityActions();
  
  // Calculate ROI metrics
  const estimatedCostOfDebt = technicalDebt * 75; // $75/hour
  const preventedDowntimeCost = criticalIssues * 5000; // $5k per critical issue
  const improvedVelocity = Math.round((100 - overallScore) * 0.5); // % improvement in velocity
  
  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'URGENT': return 'bg-red-100 text-red-800 border-red-300';
      case 'HIGH': return 'bg-orange-100 text-orange-800 border-orange-300';
      case 'MEDIUM': return 'bg-yellow-100 text-yellow-800 border-yellow-300';
      default: return 'bg-gray-100 text-gray-800 border-gray-300';
    }
  };
  
  return (
    <div className="space-y-6">
      {/* ROI & Business Impact Card */}
      <Card className="border-2 border-indigo-200 bg-gradient-to-br from-indigo-50 to-purple-50">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-indigo-900">
            <DollarSign className="w-6 h-6" />
            Business Impact & ROI Analysis
          </CardTitle>
          <CardDescription>Financial impact of addressing code quality issues</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-4 bg-white rounded-lg border-2 border-indigo-200">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-gray-700">Investment Required</span>
                <Clock className="w-4 h-4 text-indigo-600" />
              </div>
              <div className="text-3xl font-bold text-indigo-600">${estimatedCostOfDebt.toLocaleString()}</div>
              <p className="text-xs text-gray-600 mt-1">{technicalDebt} hours @ $75/hour</p>
            </div>
            
            <div className="p-4 bg-white rounded-lg border-2 border-green-200">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-gray-700">Prevented Losses</span>
                <Shield className="w-4 h-4 text-green-600" />
              </div>
              <div className="text-3xl font-bold text-green-600">${preventedDowntimeCost.toLocaleString()}</div>
              <p className="text-xs text-gray-600 mt-1">Avoided security incidents</p>
            </div>
            
            <div className="p-4 bg-white rounded-lg border-2 border-blue-200">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-gray-700">Velocity Improvement</span>
                <TrendingUp className="w-4 h-4 text-blue-600" />
              </div>
              <div className="text-3xl font-bold text-blue-600">+{improvedVelocity}%</div>
              <p className="text-xs text-gray-600 mt-1">Expected dev speed increase</p>
            </div>
          </div>
          
          {preventedDowntimeCost > estimatedCostOfDebt && (
            <div className="p-4 bg-green-50 border-2 border-green-200 rounded-lg">
              <div className="flex items-center gap-2 mb-2">
                <CheckCircle2 className="w-5 h-5 text-green-600" />
                <span className="font-semibold text-green-900">Positive ROI: ${(preventedDowntimeCost - estimatedCostOfDebt).toLocaleString()} net benefit</span>
              </div>
              <p className="text-sm text-green-800">
                Investing ${estimatedCostOfDebt.toLocaleString()} to prevent ${preventedDowntimeCost.toLocaleString()} in losses = {Math.round((preventedDowntimeCost / estimatedCostOfDebt) * 100)}% return on investment
              </p>
            </div>
          )}
        </CardContent>
      </Card>
      
      {/* Priority Action Items */}
      {priorityActions.length > 0 && (
        <Card className="border-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Target className="w-6 h-6 text-orange-600" />
              Priority Action Items
            </CardTitle>
            <CardDescription>Recommended fixes ranked by business impact</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {priorityActions.map((action, index) => {
              const IconComponent = action.icon;
              return (
                <div key={index} className={`p-4 rounded-lg border-2 ${getPriorityColor(action.priority)}`}>
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center gap-3">
                      <IconComponent className="w-5 h-5" />
                      <div>
                        <div className="flex items-center gap-2 mb-1">
                          <Badge variant="outline" className="font-bold">
                            {action.priority}
                          </Badge>
                          <h4 className="font-semibold text-lg">{action.title}</h4>
                        </div>
                        <p className="text-sm opacity-90">{action.description}</p>
                      </div>
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-6 mt-3 pt-3 border-t border-current/20">
                    <div className="flex items-center gap-2">
                      <Target className="w-4 h-4" />
                      <span className="text-sm font-medium">Impact: {action.impact}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Clock className="w-4 h-4" />
                      <span className="text-sm font-medium">Effort: {action.effort}</span>
                    </div>
                  </div>
                </div>
              );
            })}
          </CardContent>
        </Card>
      )}
      
      {/* Industry Benchmark Comparison */}
      <Card className="border-2">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <BarChart3 className="w-6 h-6 text-purple-600" />
            Industry Benchmark Comparison
          </CardTitle>
          <CardDescription>How your codebase compares to industry standards</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <div className="flex items-center justify-between mb-3">
                <span className="text-sm font-medium text-gray-700">Your Score</span>
                <span className="text-2xl font-bold text-blue-600">{overallScore}/100</span>
              </div>
              <Progress value={overallScore} className="h-3" />
              
              <div className="flex items-center justify-between mt-4 mb-3">
                <span className="text-sm font-medium text-gray-700">Industry Average</span>
                <span className="text-2xl font-bold text-gray-600">{industryBenchmark.score}/100</span>
              </div>
              <Progress value={industryBenchmark.score} className="h-3" />
            </div>
            
            <div>
              <div className="flex items-center justify-between mb-3">
                <span className="text-sm font-medium text-gray-700">Your Issues</span>
                <span className="text-2xl font-bold text-orange-600">{totalIssues}</span>
              </div>
              <Progress value={Math.min(100, (totalIssues / 20) * 100)} className="h-3" />
              
              <div className="flex items-center justify-between mt-4 mb-3">
                <span className="text-sm font-medium text-gray-700">Industry Average</span>
                <span className="text-2xl font-bold text-gray-600">{industryBenchmark.issues}</span>
              </div>
              <Progress value={Math.min(100, (industryBenchmark.issues / 20) * 100)} className="h-3" />
            </div>
          </div>
          
          <div className={`p-4 rounded-lg border-2 ${
            industryBenchmark.comparison === 'above' ? 'bg-green-50 border-green-200' :
            industryBenchmark.comparison === 'average' ? 'bg-yellow-50 border-yellow-200' :
            'bg-red-50 border-red-200'
          }`}>
            <div className="flex items-center gap-3">
              {industryBenchmark.comparison === 'above' ? (
                <>
                  <TrendingUp className="w-6 h-6 text-green-600" />
                  <div>
                    <h4 className="font-semibold text-green-900">Above Industry Standard</h4>
                    <p className="text-sm text-green-800">
                      Your codebase quality exceeds industry averages. Keep up the excellent work!
                    </p>
                  </div>
                </>
              ) : industryBenchmark.comparison === 'average' ? (
                <>
                  <Target className="w-6 h-6 text-yellow-600" />
                  <div>
                    <h4 className="font-semibold text-yellow-900">Meeting Industry Standard</h4>
                    <p className="text-sm text-yellow-800">
                      Your codebase is on par with industry norms. Consider addressing priority issues to excel.
                    </p>
                  </div>
                </>
              ) : (
                <>
                  <TrendingDown className="w-6 h-6 text-red-600" />
                  <div>
                    <h4 className="font-semibold text-red-900">Below Industry Standard</h4>
                    <p className="text-sm text-red-800">
                      Focus on the priority action items above to bring your codebase up to industry standards.
                    </p>
                  </div>
                </>
              )}
            </div>
          </div>
        </CardContent>
      </Card>
      
      {/* Team Productivity Insights */}
      <Card className="border-2">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Users className="w-6 h-6 text-cyan-600" />
            Team Productivity Insights
          </CardTitle>
          <CardDescription>Impact on development velocity and team efficiency</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="p-4 bg-gradient-to-br from-blue-50 to-cyan-50 rounded-lg border-2 border-blue-200">
              <h4 className="font-semibold text-blue-900 mb-2">Time Savings After Fixes</h4>
              <div className="text-3xl font-bold text-blue-600 mb-2">
                {Math.round(technicalDebt * 0.3)}h/week
              </div>
              <p className="text-sm text-blue-800">
                Developers will save ~{Math.round(technicalDebt * 0.3)} hours per week after resolving these issues, improving sprint velocity by {improvedVelocity}%.
              </p>
            </div>
            
            <div className="p-4 bg-gradient-to-br from-purple-50 to-pink-50 rounded-lg border-2 border-purple-200">
              <h4 className="font-semibold text-purple-900 mb-2">Code Review Efficiency</h4>
              <div className="text-3xl font-bold text-purple-600 mb-2">
                -{Math.round((totalIssues / 10) * 100)}min
              </div>
              <p className="text-sm text-purple-800">
                Cleaner code reduces code review time by approximately {Math.round((totalIssues / 10) * 100)} minutes per PR, accelerating deployment cycles.
              </p>
            </div>
          </div>
          
          {criticalIssues > 0 && (
            <div className="p-4 bg-red-50 border-2 border-red-200 rounded-lg">
              <div className="flex items-center gap-2 mb-2">
                <AlertTriangle className="w-5 h-5 text-red-600" />
                <h4 className="font-semibold text-red-900">Deployment Risk</h4>
              </div>
              <p className="text-sm text-red-800">
                {criticalIssues} critical issue{criticalIssues !== 1 ? 's' : ''} detected. Deploying with these issues could result in:
              </p>
              <ul className="list-disc list-inside text-sm text-red-800 mt-2 space-y-1">
                <li>Security vulnerabilities exposed to attackers</li>
                <li>Production outages costing ${Math.round(criticalIssues * 5000).toLocaleString()} per incident</li>
                <li>Emergency hotfixes disrupting planned work</li>
                <li>Damaged customer trust and reputation</li>
              </ul>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
