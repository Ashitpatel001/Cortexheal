import React, { useState } from "react";
import { Link } from "react-router-dom";
import {
  ShieldCheck,
  Zap,
  Activity,
  CheckCircle2,
  Lock,
  ArrowRight,
  Terminal,
  Copy,
  Check,
  FileSpreadsheet,
  AlertTriangle,
  RotateCcw,
  Cpu
} from "lucide-react";
import { SafetyDiagram } from "../components/SafetyDiagram";

export function LandingPage() {
  const [copied, setCopied] = useState(false);

  const codeSnippet = `from cortexheal import CortexHeal
from cortexheal.adapters.langgraph import LangGraphAdapter

# 1. Attach deterministic safety adapter
adapter = LangGraphAdapter(agent_id="support_router")
cortex = CortexHeal(adapter=adapter)

# 2. Add SafetyGate node to your LangGraph StateGraph
builder.add_node("safety_gate", cortex.safety_gate)
builder.set_entry_point("safety_gate")`;

  const copyCode = () => {
    navigator.clipboard.writeText(codeSnippet);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="relative overflow-hidden">
      {/* Background Grids */}
      <div className="absolute inset-0 grid-bg pointer-events-none opacity-60" />
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full max-w-7xl h-96 gradient-hero pointer-events-none" />

      {/* Hero Section */}
      <section className="relative pt-20 pb-16 sm:pt-28 sm:pb-24 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
        <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full border border-blue-200 bg-blue-50/80 text-blue-700 text-xs font-semibold uppercase tracking-wider mb-8 shadow-xs">
          <span className="w-2 h-2 rounded-full bg-blue-600 animate-pulse" />
          Enterprise Control Plane v1.0 Launch
        </div>

        <h1 className="text-4xl sm:text-6xl lg:text-7xl font-extrabold text-slate-900 tracking-tight max-w-5xl mx-auto leading-[1.1]">
          Real-time, <span className="text-blue-600">deterministic</span> safety & circuit-breaker control plane for AI agents.
        </h1>

        <p className="mt-6 text-lg sm:text-xl text-slate-600 max-w-3xl mx-auto font-normal leading-relaxed">
          CortexHeal watches agent execution as it happens and pauses an agent that is provably stuck in a loop or burning budget, before it causes further damage. <strong>Zero LLMs in the safety-decision path.</strong>
        </p>

        <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4">
          <a
            href="http://localhost:5173"
            target="_blank"
            rel="noreferrer"
            className="w-full sm:w-auto inline-flex items-center justify-center gap-2.5 px-6 py-3.5 text-base font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-xl shadow-lg shadow-blue-600/20 transition-all hover:scale-[1.02]"
          >
            <span>Launch Live Ops Dashboard</span>
            <ArrowRight className="w-4 h-4" />
          </a>

          <Link
            to="/docs"
            className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-6 py-3.5 text-base font-semibold text-slate-700 bg-white hover:bg-slate-50 border border-slate-200 rounded-xl shadow-xs transition-all"
          >
            <Terminal className="w-4 h-4 text-slate-500" />
            <span>Read Quickstart Guide</span>
          </Link>
        </div>

        {/* Feature Pills */}
        <div className="mt-12 pt-8 border-t border-slate-200/80 grid grid-cols-2 md:grid-cols-4 gap-4 max-w-4xl mx-auto text-left">
          <div className="p-3 bg-white/80 border border-slate-100 rounded-lg shadow-xs">
            <span className="block text-xs font-mono font-bold text-slate-400">DECISION LATENCY</span>
            <span className="text-sm font-bold text-slate-900">~26.5ms p50 (Pipeline)</span>
          </div>
          <div className="p-3 bg-white/80 border border-slate-100 rounded-lg shadow-xs">
            <span className="block text-xs font-mono font-bold text-slate-400">SAFETY DECISION PATH</span>
            <span className="text-sm font-bold text-slate-900">0 LLMs (Deterministic)</span>
          </div>
          <div className="p-3 bg-white/80 border border-slate-100 rounded-lg shadow-xs">
            <span className="block text-xs font-mono font-bold text-slate-400">CONCURRENT SCALE</span>
            <span className="text-sm font-bold text-slate-900">50+ Parallel Agents</span>
          </div>
          <div className="p-3 bg-white/80 border border-slate-100 rounded-lg shadow-xs">
            <span className="block text-xs font-mono font-bold text-slate-400">COMPLIANCE</span>
            <span className="text-sm font-bold text-slate-900">SOC2 / JSON Audit Trail</span>
          </div>
        </div>
      </section>

      {/* Interactive Safety Gate Diagram */}
      <section className="py-12 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <SafetyDiagram />
      </section>

      {/* Value Pillars */}
      <section className="py-20 bg-slate-50 border-y border-slate-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto mb-16">
            <h2 className="text-xs font-mono font-bold text-blue-600 uppercase tracking-wider mb-2">
              Why Determinism Matters
            </h2>
            <p className="text-3xl font-extrabold text-slate-900 tracking-tight sm:text-4xl">
              Engineered for Enterprise Reliability, Not Probabilistic Guesses.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {/* Card 1 */}
            <div className="bg-white p-8 rounded-2xl border border-slate-200 shadow-sm space-y-4 hover:border-blue-300 transition-colors">
              <div className="w-12 h-12 rounded-xl bg-blue-50 border border-blue-200 text-blue-600 flex items-center justify-center">
                <Lock className="w-6 h-6" />
              </div>
              <h3 className="text-xl font-bold text-slate-900">
                Zero LLMs in Decision Path
              </h3>
              <p className="text-sm text-slate-600 leading-relaxed">
                An LLM evaluator in the safety loop adds latency, cost, and introduces hallucinated safety judgments. CortexHeal uses SHA-256 state hashing and exact mathematical threshold math for 100% reproducible circuit breaks.
              </p>
              <ul className="space-y-2 pt-2 text-xs text-slate-600 font-medium">
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                  Exact hash argument & response matching
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                  Deterministic token budget ceilings
                </li>
              </ul>
            </div>

            {/* Card 2 */}
            <div className="bg-white p-8 rounded-2xl border border-slate-200 shadow-sm space-y-4 hover:border-blue-300 transition-colors">
              <div className="w-12 h-12 rounded-xl bg-blue-50 border border-blue-200 text-blue-600 flex items-center justify-center">
                <RotateCcw className="w-6 h-6" />
              </div>
              <h3 className="text-xl font-bold text-slate-900">
                Human-in-the-Loop Recovery
              </h3>
              <p className="text-sm text-slate-600 leading-relaxed">
                When an agent trips a circuit breaker, CortexHeal generates structured recovery proposals. Operators can review the diagnosis, modify state parameters, and safely resume without restarting from scratch.
              </p>
              <ul className="space-y-2 pt-2 text-xs text-slate-600 font-medium">
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                  Context injection & prompt redirection
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                  Verified recovery validation engine
                </li>
              </ul>
            </div>

            {/* Card 3 */}
            <div className="bg-white p-8 rounded-2xl border border-slate-200 shadow-sm space-y-4 hover:border-blue-300 transition-colors">
              <div className="w-12 h-12 rounded-xl bg-blue-50 border border-blue-200 text-blue-600 flex items-center justify-center">
                <FileSpreadsheet className="w-6 h-6" />
              </div>
              <h3 className="text-xl font-bold text-slate-900">
                Compliance & Audit Export
              </h3>
              <p className="text-sm text-slate-600 leading-relaxed">
                Enterprise compliance teams demand verifiable records. Download complete immutable audit logs in CSV and JSON formats containing raw trigger events, hashes, actor IDs, and policy versions.
              </p>
              <ul className="space-y-2 pt-2 text-xs text-slate-600 font-medium">
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                  REST Export API with date & agent filters
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                  Strict tenant isolation per organization
                </li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* Code Integration Section */}
      <section className="py-20 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
          <div>
            <div className="inline-flex items-center gap-2 text-xs font-mono font-bold text-blue-600 uppercase tracking-wider mb-3">
              <Terminal className="w-4 h-4" /> 3-Line Integration
            </div>
            <h2 className="text-3xl font-extrabold text-slate-900 tracking-tight sm:text-4xl mb-4">
              Integrate in seconds. Works with LangGraph, AutoGen, and CrewAI.
            </h2>
            <p className="text-base text-slate-600 leading-relaxed mb-6">
              Drop the CortexHeal SafetyGate node directly into your agent execution graph. Zero complex proxies, zero network hops in the critical decision path.
            </p>
            <div className="space-y-3 text-sm text-slate-700">
              <div className="flex items-center gap-3">
                <span className="w-6 h-6 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center font-mono font-bold text-xs">1</span>
                <span>Install via pip: <code className="bg-slate-100 px-2 py-0.5 rounded text-slate-900 font-mono text-xs">pip install cortexheal</code></span>
              </div>
              <div className="flex items-center gap-3">
                <span className="w-6 h-6 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center font-mono font-bold text-xs">2</span>
                <span>Wrap your execution framework with the adapter.</span>
              </div>
              <div className="flex items-center gap-3">
                <span className="w-6 h-6 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center font-mono font-bold text-xs">3</span>
                <span>SafetyGate automatically intercepts runaway loops & overruns.</span>
              </div>
            </div>
          </div>

          <div className="relative bg-slate-900 rounded-2xl p-6 shadow-2xl border border-slate-800 text-slate-200">
            <div className="flex items-center justify-between pb-4 mb-4 border-b border-slate-800 text-xs font-mono text-slate-400">
              <span className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-full bg-red-500/80" />
                <span className="w-3 h-3 rounded-full bg-yellow-500/80" />
                <span className="w-3 h-3 rounded-full bg-green-500/80" />
                <span className="ml-2 text-slate-400">agent_pipeline.py</span>
              </span>
              <button
                onClick={copyCode}
                className="flex items-center gap-1.5 text-slate-400 hover:text-white transition-colors"
                title="Copy code"
              >
                {copied ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
                <span>{copied ? "Copied" : "Copy"}</span>
              </button>
            </div>
            <pre className="font-mono text-xs leading-relaxed overflow-x-auto text-blue-300">
              <code>{codeSnippet}</code>
            </pre>
          </div>
        </div>
      </section>

      {/* CTA Banner */}
      <section className="py-16 bg-blue-600 text-white text-center">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 space-y-6">
          <h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight">
            Ready to secure your enterprise agent fleet?
          </h2>
          <p className="text-blue-100 text-base sm:text-lg max-w-2xl mx-auto">
            Stop runaway loops and budget leaks before they happen. Start with deterministic safety in minutes.
          </p>
          <div className="pt-2 flex flex-col sm:flex-row items-center justify-center gap-4">
            <a
              href="http://localhost:5173"
              target="_blank"
              rel="noreferrer"
              className="w-full sm:w-auto px-8 py-3.5 bg-white text-blue-700 font-bold rounded-xl shadow-md hover:bg-blue-50 transition-all"
            >
              Open Live Dashboard
            </a>
            <Link
              to="/blog/deterministic-safety-imperative"
              className="w-full sm:w-auto px-8 py-3.5 bg-blue-700 hover:bg-blue-800 text-white font-semibold rounded-xl border border-blue-500 transition-all"
            >
              Read the Whitepaper
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
