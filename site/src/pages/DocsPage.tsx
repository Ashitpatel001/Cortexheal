import React from "react";
import { Terminal, Shield, Cpu, Zap, Download, Lock, CheckCircle2, Server, Bell, FileText } from "lucide-react";

export function DocsPage() {
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-12">
        {/* Sticky Docs Navigation Sidebar */}
        <aside className="hidden lg:block lg:col-span-1">
          <div className="sticky top-24 space-y-6 text-sm">
            <div>
              <h4 className="font-mono font-bold text-xs uppercase text-slate-900 tracking-wider mb-3">
                Getting Started
              </h4>
              <ul className="space-y-2 text-slate-600 border-l border-slate-200 pl-3">
                <li><a href="#quickstart" className="hover:text-blue-600">Quickstart</a></li>
                <li><a href="#core-concepts" className="hover:text-blue-600">Core Concepts</a></li>
                <li><a href="#architecture" className="hover:text-blue-600">Architecture</a></li>
              </ul>
            </div>

            <div>
              <h4 className="font-mono font-bold text-xs uppercase text-slate-900 tracking-wider mb-3">
                Framework Adapters
              </h4>
              <ul className="space-y-2 text-slate-600 border-l border-slate-200 pl-3">
                <li><a href="#adapter-langgraph" className="hover:text-blue-600">LangGraph</a></li>
                <li><a href="#adapter-autogen" className="hover:text-blue-600">AutoGen</a></li>
                <li><a href="#adapter-crewai" className="hover:text-blue-600">CrewAI & Custom</a></li>
              </ul>
            </div>

            <div>
              <h4 className="font-mono font-bold text-xs uppercase text-slate-900 tracking-wider mb-3">
                Control Plane & API
              </h4>
              <ul className="space-y-2 text-slate-600 border-l border-slate-200 pl-3">
                <li><a href="#api-auth" className="hover:text-blue-600">Multi-Tenant Auth</a></li>
                <li><a href="#api-alerting" className="hover:text-blue-600">Alerts & Webhooks</a></li>
                <li><a href="#api-export" className="hover:text-blue-600">Compliance Export</a></li>
                <li><a href="#api-sse" className="hover:text-blue-600">Server-Sent Events (SSE)</a></li>
              </ul>
            </div>
          </div>
        </aside>

        {/* Main Documentation Body */}
        <main className="lg:col-span-3 space-y-16">
          {/* Section: Quickstart */}
          <section id="quickstart" className="space-y-4">
            <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-blue-50 text-blue-700 text-xs font-mono font-semibold">
              <Terminal className="w-3.5 h-3.5" /> 5-Minute Setup
            </div>
            <h1 className="text-3xl sm:text-4xl font-extrabold text-slate-900 tracking-tight">
              Quickstart Guide
            </h1>
            <p className="text-base text-slate-600 leading-relaxed">
              Install the CortexHeal Python client and connect your agent execution graph in 3 steps.
            </p>

            <div className="space-y-3 pt-2">
              <h3 className="text-base font-bold text-slate-900">1. Install Package</h3>
              <pre className="bg-slate-900 text-slate-200 p-4 rounded-xl font-mono text-xs overflow-x-auto">
                <code>pip install cortexheal</code>
              </pre>
            </div>

            <div className="space-y-3 pt-4">
              <h3 className="text-base font-bold text-slate-900">2. Configure Environment</h3>
              <p className="text-sm text-slate-600">
                Set the CortexHeal backend URL and your organization API key:
              </p>
              <pre className="bg-slate-900 text-slate-200 p-4 rounded-xl font-mono text-xs overflow-x-auto">
                <code>export CORTEXHEAL_API_URL="http://127.0.0.1:8000"
export CORTEXHEAL_API_KEY="ctx_admin_prod_corp_001"</code>
              </pre>
            </div>

            <div className="space-y-3 pt-4">
              <h3 className="text-base font-bold text-slate-900">3. Attach SafetyGate in LangGraph</h3>
              <pre className="bg-slate-900 text-slate-200 p-4 rounded-xl font-mono text-xs overflow-x-auto">
                <code>{`from cortexheal import CortexHeal
from cortexheal.adapters.langgraph import LangGraphAdapter
from langgraph.graph import StateGraph

# Initialize adapter with unique agent ID
adapter = LangGraphAdapter(agent_id="customer_service_agent")
cortex = CortexHeal(adapter=adapter)

# Insert SafetyGate as entry point or tool guard
builder = StateGraph(MyAgentState)
builder.add_node("safety_gate", cortex.safety_gate)
builder.add_node("agent_worker", agent_worker_node)

builder.set_entry_point("safety_gate")
builder.add_edge("safety_gate", "agent_worker")`}</code>
              </pre>
            </div>
          </section>

          {/* Section: Architecture & Core Concepts */}
          <section id="core-concepts" className="space-y-6 pt-8 border-t border-slate-200">
            <h2 className="text-2xl font-bold text-slate-900 tracking-tight">
              Core Concepts & Architecture
            </h2>
            <p className="text-sm text-slate-600 leading-relaxed">
              CortexHeal enforces application-layer safety constraints without evaluating prompts with secondary language models. All circuit breakers operate on deterministic mathematics.
            </p>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="p-5 border border-slate-200 rounded-xl bg-slate-50 space-y-2">
                <div className="flex items-center gap-2 font-bold text-slate-900 text-sm">
                  <Cpu className="w-4 h-4 text-blue-600" />
                  Deterministic Hash Engine
                </div>
                <p className="text-xs text-slate-600 leading-relaxed">
                  Every tool call signature (tool name, JSON argument hash, response hash) is normalized and recorded in an in-memory ring buffer. Consecutive identical execution hashes immediately increment repetition counters.
                </p>
              </div>

              <div className="p-5 border border-slate-200 rounded-xl bg-slate-50 space-y-2">
                <div className="flex items-center gap-2 font-bold text-slate-900 text-sm">
                  <Shield className="w-4 h-4 text-blue-600" />
                  SafetyGate & Circuit Breaker
                </div>
                <p className="text-xs text-slate-600 leading-relaxed">
                  SafetyGate intercepts state transitions before tool execution. If repetitions reach the threshold (e.g. 4 iterations) or cumulative run cost exceeds budget (e.g. $1.00), SafetyGate halts the thread instantly with a non-recoverable pause.
                </p>
              </div>
            </div>
          </section>

          {/* Section: Adapters */}
          <section id="adapters" className="space-y-6 pt-8 border-t border-slate-200">
            <h2 className="text-2xl font-bold text-slate-900 tracking-tight">
              Framework Adapters
            </h2>

            <div className="space-y-4">
              <h3 id="adapter-langgraph" className="text-lg font-bold text-slate-900">
                LangGraph Adapter
              </h3>
              <p className="text-sm text-slate-600">
                Wraps LangGraph StateGraph nodes. Implements checkpointer compatibility and state injection for approved recovery plans.
              </p>

              <h3 id="adapter-autogen" className="text-lg font-bold text-slate-900 pt-4">
                AutoGen Adapter
              </h3>
              <p className="text-sm text-slate-600">
                Hooks into AutoGen conversational message dispatch and agent tool invocation callbacks to track consecutive repeated tool execution.
              </p>
            </div>
          </section>

          {/* Section: API Reference */}
          <section id="api-reference" className="space-y-6 pt-8 border-t border-slate-200">
            <h2 className="text-2xl font-bold text-slate-900 tracking-tight">
              REST Control Plane Reference
            </h2>

            <div className="space-y-4">
              <div className="p-4 bg-slate-900 text-slate-200 rounded-xl font-mono text-xs space-y-3">
                <div className="text-emerald-400 font-bold">// 1. Retrieve Current Caller Identity</div>
                <div>GET /api/whoami</div>
                <div className="text-slate-400">Response: &#123; "role": "OPERATOR", "org_id": "default_org" &#125;</div>

                <div className="text-emerald-400 font-bold pt-2">// 2. Export Compliance Audit Log</div>
                <div>GET /api/audit/export?format=csv&amp;failure_type=STUCK_LOOP</div>
                <div className="text-slate-400">Response: Content-Type: text/csv (Downloadable attachment)</div>

                <div className="text-emerald-400 font-bold pt-2">// 3. Register Outbound Alert Webhook (Slack / PagerDuty)</div>
                <div>POST /api/webhooks</div>
                <div className="text-slate-400">Body: &#123; "url": "https://hooks.slack.com/...", "target_type": "slack", "min_severity": "HIGH" &#125;</div>

                <div className="text-emerald-400 font-bold pt-2">// 4. Connect to Real-Time SSE Stream</div>
                <div>GET /api/stream</div>
                <div className="text-slate-400">Events: run_status_changed, incident_created, action_executed, heartbeat</div>
              </div>
            </div>
          </section>
        </main>
      </div>
    </div>
  );
}
