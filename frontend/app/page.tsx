'use client'

import { ArrowRight, Code2, GitBranch, Zap, TrendingUp, CheckCircle, Users, Rocket, Github } from 'lucide-react'
import { Button } from '@/components/ui'
import Link from 'next/link'

export default function HomePage() {
  return (
    <div className="min-h-screen bg-white">
      {/* Navigation */}
      <nav className="fixed w-full top-0 bg-white/80 backdrop-blur-md border-b border-gray-200 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
              <Code2 className="w-5 h-5 text-white" />
            </div>
            <span className="text-xl font-semibold text-gray-900">AGI Engineer</span>
          </div>
          <div className="flex items-center gap-6">
            <a href="#features" className="text-sm text-gray-600 hover:text-gray-900 transition">Features</a>
            <a href="#roadmap" className="text-sm text-gray-600 hover:text-gray-900 transition">Roadmap</a>
            <a href="#about" className="text-sm text-gray-600 hover:text-gray-900 transition">About</a>
            <Link href="/auth">
              <Button className="bg-blue-600 hover:bg-blue-700 text-white">Get Started</Button>
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="pt-32 pb-20 px-4">
        <div className="max-w-4xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 bg-blue-50 px-4 py-2 rounded-full mb-8 border border-blue-200">
            <Zap className="w-4 h-4 text-blue-600" />
            <span className="text-sm text-blue-700 font-medium">Intelligent Code Analysis</span>
          </div>
          <h1 className="text-6xl font-bold text-gray-900 mb-6 leading-tight">
            Ship Better Code, Faster
          </h1>
          <p className="text-xl text-gray-600 mb-8 max-w-2xl mx-auto leading-relaxed">
            AGI Engineer uses advanced AI to analyze your code automatically, catch quality issues early, and deliver actionable insights in real-time. Focus on building—let us handle the analysis.
          </p>
          <div className="flex items-center justify-center gap-4">
            <Link href="/auth">
              <Button className="bg-blue-600 hover:bg-blue-700 text-white text-base px-8 py-3 h-auto">
                Start Analyzing
                <ArrowRight className="w-4 h-4 ml-2" />
              </Button>
            </Link>
            <a href="https://github.com" className="text-gray-600 hover:text-gray-900 border border-gray-300 hover:border-gray-400 px-6 py-3 rounded-lg font-medium transition inline-flex items-center gap-2">
              <Github className="w-4 h-4" />
              View on GitHub
            </a>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="py-20 px-4 bg-gray-50 border-t border-gray-200">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold text-gray-900 mb-4">Powerful Features</h2>
            <p className="text-lg text-gray-600">Everything you need for comprehensive code analysis</p>
          </div>
          <div className="grid md:grid-cols-3 gap-8">
            {/* Feature 1 */}
            <div className="bg-white p-8 rounded-lg border border-gray-200 hover:border-blue-300 transition group">
              <div className="w-12 h-12 bg-blue-50 rounded-lg flex items-center justify-center mb-4 group-hover:bg-blue-100 transition">
                <Code2 className="w-6 h-6 text-blue-600" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-3">Code Quality Analysis</h3>
              <p className="text-gray-600">Detect code smells, high complexity, security vulnerabilities, and architectural anti-patterns automatically across your entire repository.</p>
            </div>

            {/* Feature 2 */}
            <div className="bg-white p-8 rounded-lg border border-gray-200 hover:border-blue-300 transition group">
              <div className="w-12 h-12 bg-blue-50 rounded-lg flex items-center justify-center mb-4 group-hover:bg-blue-100 transition">
                <TrendingUp className="w-6 h-6 text-blue-600" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-3">Real-Time Insights</h3>
              <p className="text-gray-600">Get instant feedback on every commit and pull request with detailed analysis, metrics, and trends across your team's work.</p>
            </div>

            {/* Feature 3 */}
            <div className="bg-white p-8 rounded-lg border border-gray-200 hover:border-blue-300 transition group">
              <div className="w-12 h-12 bg-blue-50 rounded-lg flex items-center justify-center mb-4 group-hover:bg-blue-100 transition">
                <Zap className="w-6 h-6 text-blue-600" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-3">AI-Powered Recommendations</h3>
              <p className="text-gray-600">Get actionable suggestions powered by AI, with clear explanations and best practices to improve your code quality.</p>
            </div>

            {/* Feature 4 */}
            <div className="bg-white p-8 rounded-lg border border-gray-200 hover:border-blue-300 transition group">
              <div className="w-12 h-12 bg-blue-50 rounded-lg flex items-center justify-center mb-4 group-hover:bg-blue-100 transition">
                <GitBranch className="w-6 h-6 text-blue-600" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-3">GitHub First</h3>
              <p className="text-gray-600">Native GitHub integration with automatic analysis on pull requests, commits, and repository webhooks—no setup required.</p>
            </div>

            {/* Feature 5 */}
            <div className="bg-white p-8 rounded-lg border border-gray-200 hover:border-blue-300 transition group">
              <div className="w-12 h-12 bg-blue-50 rounded-lg flex items-center justify-center mb-4 group-hover:bg-blue-100 transition">
                <Users className="w-6 h-6 text-blue-600" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-3">Team Collaboration</h3>
              <p className="text-gray-600">Share analysis results with your team, track improvements over sprints, and establish engineering standards together.</p>
            </div>

            {/* Feature 6 */}
            <div className="bg-white p-8 rounded-lg border border-gray-200 hover:border-blue-300 transition group">
              <div className="w-12 h-12 bg-blue-50 rounded-lg flex items-center justify-center mb-4 group-hover:bg-blue-100 transition">
                <CheckCircle className="w-6 h-6 text-blue-600" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-3">Enforce Standards</h3>
              <p className="text-gray-600">Define and enforce coding standards across your organization with configurable rules that scale with your team.</p>
            </div>
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section className="py-20 px-4 bg-white border-t border-gray-200">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-4xl font-bold text-gray-900 text-center mb-16">How It Works</h2>
          <div className="space-y-12">
            <div className="flex gap-8 items-start">
              <div className="flex-shrink-0">
                <div className="w-12 h-12 bg-blue-600 text-white rounded-lg flex items-center justify-center font-bold">1</div>
              </div>
              <div>
                <h3 className="text-xl font-semibold text-gray-900 mb-2">Connect Your Repository</h3>
                <p className="text-gray-600">Link your GitHub account and select the repositories you want to analyze. AGI Engineer needs read access to your code.</p>
              </div>
            </div>

            <div className="flex gap-8 items-start">
              <div className="flex-shrink-0">
                <div className="w-12 h-12 bg-blue-600 text-white rounded-lg flex items-center justify-center font-bold">2</div>
              </div>
              <div>
                <h3 className="text-xl font-semibold text-gray-900 mb-2">Automatic Analysis Runs</h3>
                <p className="text-gray-600">Our AI engine automatically analyzes your code on every push and pull request. Comprehensive reports are generated within seconds.</p>
              </div>
            </div>

            <div className="flex gap-8 items-start">
              <div className="flex-shrink-0">
                <div className="w-12 h-12 bg-blue-600 text-white rounded-lg flex items-center justify-center font-bold">3</div>
              </div>
              <div>
                <h3 className="text-xl font-semibold text-gray-900 mb-2">Review Insights</h3>
                <p className="text-gray-600">Access detailed analysis reports with actionable insights. Understand code issues, performance metrics, and improvement opportunities.</p>
              </div>
            </div>

            <div className="flex gap-8 items-start">
              <div className="flex-shrink-0">
                <div className="w-12 h-12 bg-blue-600 text-white rounded-lg flex items-center justify-center font-bold">4</div>
              </div>
              <div>
                <h3 className="text-xl font-semibold text-gray-900 mb-2">Improve Your Code</h3>
                <p className="text-gray-600">Implement recommendations to improve code quality, performance, and maintainability. Track progress over time.</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Roadmap Section */}
      <section id="roadmap" className="py-20 px-4 bg-gray-50 border-t border-gray-200">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-4xl font-bold text-gray-900 text-center mb-4">Product Roadmap</h2>
          <p className="text-center text-gray-600 mb-16">What we're building next</p>
          
          <div className="space-y-6">
            <div className="bg-white p-6 rounded-lg border border-green-200 bg-green-50">
              <div className="flex items-center gap-3 mb-2">
                <CheckCircle className="w-5 h-5 text-green-600" />
                <h3 className="font-semibold text-gray-900">Phase 1: Core Analysis Engine</h3>
              </div>
              <p className="text-gray-600 text-sm ml-8">Basic code quality analysis, GitHub integration, and dashboard. ✓ Complete</p>
            </div>

            <div className="bg-white p-6 rounded-lg border border-blue-200 bg-blue-50">
              <div className="flex items-center gap-3 mb-2">
                <Rocket className="w-5 h-5 text-blue-600" />
                <h3 className="font-semibold text-gray-900">Phase 2: Advanced Features (Q1 2026)</h3>
              </div>
              <p className="text-gray-600 text-sm ml-8">Custom rule engine, performance profiling, and team dashboards</p>
            </div>

            <div className="bg-white p-6 rounded-lg border border-gray-200">
              <div className="flex items-center gap-3 mb-2">
                <Rocket className="w-5 h-5 text-gray-400" />
                <h3 className="font-semibold text-gray-900">Phase 3: Enterprise Suite (Q2 2026)</h3>
              </div>
              <p className="text-gray-600 text-sm ml-8">Multi-repository analysis, team management, and reporting</p>
            </div>

            <div className="bg-white p-6 rounded-lg border border-gray-200">
              <div className="flex items-center gap-3 mb-2">
                <Rocket className="w-5 h-5 text-gray-400" />
                <h3 className="font-semibold text-gray-900">Phase 4: AI Code Generation (Q3 2026)</h3>
              </div>
              <p className="text-gray-600 text-sm ml-8">Automatic code fixes, refactoring suggestions, and documentation generation</p>
            </div>
          </div>
        </div>
      </section>

      {/* About Section */}
      <section id="about" className="py-20 px-4 bg-white border-t border-gray-200">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-4xl font-bold text-gray-900 text-center mb-8">About AGI Engineer</h2>
          <div className="space-y-6 text-gray-600 text-lg">
            <p>
              AGI Engineer was built with the vision of making professional-grade code analysis accessible to every developer and team. We believe that understanding your code is the first step toward writing better software.
            </p>
            <p>
              Our platform combines cutting-edge AI technology with software engineering best practices to deliver actionable insights that help teams write cleaner, faster, and more maintainable code.
            </p>
            <p>
              Whether you're a solo developer working on open-source projects or part of a large enterprise team, AGI Engineer provides the tools you need to continuously improve your codebase.
            </p>
            <div>
              <h3 className="text-2xl font-semibold text-gray-900 mb-3">Our Mission</h3>
              <p>
                To empower developers with intelligent insights that make code review faster, more thorough, and more effective. We're committed to building tools that enhance human expertise, not replace it.
              </p>
            </div>
            <div>
              <h3 className="text-2xl font-semibold text-gray-900 mb-3">Technical Foundation</h3>
              <p>
                AGI Engineer is built on a foundation of modern technologies including FastAPI for the backend, Next.js for the frontend, and advanced machine learning models for code analysis. We prioritize security, privacy, and performance in everything we build.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 px-4 bg-blue-600 text-white border-t border-blue-700">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-4xl font-bold mb-6">Ready to Improve Your Code?</h2>
          <p className="text-xl text-blue-100 mb-8">Start analyzing your repositories today with AGI Engineer</p>
          <Link href="/auth">
            <Button className="bg-white hover:bg-gray-100 text-blue-600 font-semibold px-8 py-3 h-auto">
              Get Started Now
              <ArrowRight className="w-4 h-4 ml-2" />
            </Button>
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-gray-900 text-gray-400 py-12 px-4 border-t border-gray-800">
        <div className="max-w-6xl mx-auto">
          <div className="grid md:grid-cols-4 gap-8 mb-12">
            <div>
              <div className="flex items-center gap-2 mb-4">
                <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
                  <Code2 className="w-5 h-5 text-white" />
                </div>
                <span className="font-semibold text-white">AGI Engineer</span>
              </div>
              <p className="text-sm">Intelligent code analysis for modern development teams.</p>
            </div>
            <div>
              <h4 className="font-semibold text-white mb-4">Product</h4>
              <ul className="space-y-2 text-sm">
                <li><a href="#features" className="hover:text-white transition">Features</a></li>
                <li><a href="#roadmap" className="hover:text-white transition">Roadmap</a></li>
                <li><a href="#about" className="hover:text-white transition">About</a></li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold text-white mb-4">Developers</h4>
              <ul className="space-y-2 text-sm">
                <li><a href="https://github.com" className="hover:text-white transition">GitHub</a></li>
                <li><a href="https://github.com" className="hover:text-white transition">Documentation</a></li>
                <li><a href="https://github.com" className="hover:text-white transition">API Reference</a></li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold text-white mb-4">Legal</h4>
              <ul className="space-y-2 text-sm">
                <li><a href="#" className="hover:text-white transition">Privacy</a></li>
                <li><a href="#" className="hover:text-white transition">Terms</a></li>
                <li><a href="#" className="hover:text-white transition">Contact</a></li>
              </ul>
            </div>
          </div>
          <div className="border-t border-gray-800 pt-8 text-center text-sm">
            <p>© 2026 AGI Engineer. All rights reserved.</p>
          </div>
        </div>
      </footer>
    </div>
  )
}
