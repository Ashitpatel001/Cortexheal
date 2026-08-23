import React from "react";
import { useParams, Link, Navigate } from "react-router-dom";
import { ArrowLeft, Clock, ShieldCheck, Cpu, Terminal, AlertTriangle, CheckCircle2 } from "lucide-react";
import { BLOG_POSTS } from "./BlogListPage";

export function BlogPostPage() {
  const { slug } = useParams<{ slug: string }>();
  const post = BLOG_POSTS.find((p) => p.slug === slug);

  if (!post) {
    return <Navigate to="/blog" replace />;
  }

  return (
    <article className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
      <Link
        to="/blog"
        className="inline-flex items-center gap-2 text-sm text-slate-500 hover:text-slate-900 transition-colors mb-8"
      >
        <ArrowLeft className="w-4 h-4" /> Back to all articles
      </Link>

      <header className="space-y-4 pb-8 border-b border-slate-200">
        <div className="flex items-center gap-3 text-xs font-mono text-slate-500">
          <span className="px-2.5 py-1 rounded bg-blue-50 text-blue-700 font-semibold uppercase">
            {post.category}
          </span>
          <span>•</span>
          <span className="flex items-center gap-1">
            <Clock className="w-3.5 h-3.5" /> {post.readTime}
          </span>
          <span>•</span>
          <span>{post.date}</span>
        </div>

        <h1 className="text-3xl sm:text-5xl font-extrabold text-slate-900 tracking-tight leading-tight">
          {post.title}
        </h1>

        <p className="text-lg text-slate-600 leading-relaxed font-normal">
          {post.excerpt}
        </p>

        <div className="pt-2 text-xs text-slate-500">
          Published by <strong className="text-slate-700">{post.author}</strong>
        </div>
      </header>

      {/* Full Article Content */}
      {slug === "deterministic-safety-imperative" ? (
        <div className="prose prose-slate max-w-none pt-8 space-y-6 text-slate-700 text-base leading-relaxed">
          <h2 className="text-2xl font-bold text-slate-900">
            1. The Flaw in "LLM-as-a-Judge" for Runtime Safety
          </h2>
          <p>
            As autonomous agent frameworks (such as LangGraph, AutoGen, and CrewAI) deploy into critical enterprise infrastructure, safety and circuit-breaking have become mandatory requirements. However, a dangerous architecture pattern has emerged across early prototypes: deploying a second "evaluator LLM" to watch the primary agent and determine if it is stuck in a loop or acting destructively.
          </p>
          <p>
            This approach fails three fundamental engineering tests:
          </p>

          <div className="p-6 bg-red-50/50 border border-red-200 rounded-xl space-y-3">
            <h3 className="text-base font-bold text-red-900 flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-red-600" />
              The Triad of Evaluator Failure Modes:
            </h3>
            <ul className="space-y-2 text-sm text-red-800 list-disc pl-5">
              <li><strong>Latency Compounding:</strong> Calling an LLM evaluator at every tool invocation adds 400ms–2,500ms of latency per step, rendering high-throughput agent workflows unusable.</li>
              <li><strong>Non-Deterministic Rulings:</strong> Two identical infinite loops can produce different evaluator verdicts depending on temperature, prompt truncation, or model drift.</li>
              <li><strong>Evaluation Hallucinations:</strong> The evaluator LLM can hallucinate that an agent is making progress when it is actually cycling through identical parameter hashes.</li>
            </ul>
          </div>

          <h2 className="text-2xl font-bold text-slate-900 pt-4">
            2. The Deterministic Imperative
          </h2>
          <p>
            A circuit breaker must be <em>deterministic</em>. In electrical engineering, a fuse does not "think" or "reason"—it breaks when the physical current crosses a fixed amperage limit. Similarly, in distributed systems, network circuit breakers trip when HTTP error thresholds exceed 50% over a 10-second sliding window.
          </p>
          <p>
            CortexHeal enforces this exact principle for AI agent fleets:
          </p>
          <pre className="bg-slate-900 text-emerald-400 p-4 rounded-xl font-mono text-xs overflow-x-auto">
            <code>{`# Deterministic Hash Comparison in CortexHeal Safety Path
curr_hash = sha256(canonical_json(tool_name, arguments, normalized_response))
if curr_hash == prev_hash:
    consecutive_repetitions += 1
    if consecutive_repetitions >= threshold:
        trip_circuit_breaker(run_id, reason="STUCK_LOOP")`}</code>
          </pre>

          <h2 className="text-2xl font-bold text-slate-900 pt-4">
            3. Separation of Safety Decision vs. Recovery Planning
          </h2>
          <p>
            CortexHeal strictly decouples the <strong>Safety Decision Path</strong> from the <strong>Recovery Planning Path</strong>:
          </p>
          <ul className="space-y-2 list-disc pl-5">
            <li><strong>Safety Gate (Zero LLMs):</strong> Pausing execution is 100% deterministic (0.15ms in-process handover, ~26.5ms p50 full database pipeline). Zero network hops to external LLMs.</li>
            <li><strong>Recovery Diagnosis (Optional AI Assist):</strong> Once safely paused, operators can optionally generate structured AI suggestions or rule-based fixes, with mandatory human sign-off before state resumption.</li>
          </ul>

          <div className="p-6 bg-blue-50 border border-blue-200 rounded-xl">
            <h4 className="font-bold text-blue-900 text-sm mb-1">Key Takeaway for Enterprise Architects:</h4>
            <p className="text-xs text-blue-800 leading-relaxed">
              Never delegate circuit-breaking to probabilistic models. Enforce hard deterministic boundaries at the application layer, and preserve AI for diagnostic suggestions outside the critical execution loop.
            </p>
          </div>
        </div>
      ) : (
        <div className="prose prose-slate max-w-none pt-8 space-y-6 text-slate-700 text-base leading-relaxed">
          <h2 className="text-2xl font-bold text-slate-900">
            1. Scaling to 50+ Concurrent Multi-Agent Workloads
          </h2>
          <p>
            Enterprise agent deployments do not run a single isolated agent—they run fleets of dozens or hundreds of concurrent agents communicating across asynchronous queues. Ensuring zero cross-contamination and sub-100ms p95 circuit breaking under load requires careful control plane architecture.
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
            <div className="p-4 border border-slate-200 rounded-xl bg-slate-50">
              <h4 className="font-bold text-slate-900 text-sm mb-1">In-Memory Ring Buffers</h4>
              <p className="text-xs text-slate-600">
                Agent events are buffered in bounded circular queues per run ID, enabling O(1) state hash lookups without continuous database roundtrips.
              </p>
            </div>
            <div className="p-4 border border-slate-200 rounded-xl bg-slate-50">
              <h4 className="font-bold text-slate-900 text-sm mb-1">Threaded Pool &amp; Write Throttling</h4>
              <p className="text-xs text-slate-600">
                PostgreSQL connections utilize a 100-client threaded pool with throttled timestamp updates, preventing hot-row contention under heavy parallel load.
              </p>
            </div>
          </div>

          <h2 className="text-2xl font-bold text-slate-900 pt-4">
            2. Verified Benchmark Evidence
          </h2>
          <p>
            During our Phase 2 concurrent-scale verification, CortexHeal was tested against 55 simultaneous external agent runs (30 stuck loops, 25 budget overruns) alongside 55 persistent SSE client connections:
          </p>
          <ul className="space-y-2 list-disc pl-5">
            <li><strong>Accuracy:</strong> 55/55 incidents accurately attributed with 0% false positives and 0 dropped events.</li>
            <li><strong>Latency:</strong> Full pipeline decision latency measured at <strong>p50 ~26.5ms</strong>, <strong>p95 ~94.0ms</strong>, and <strong>p99 ~240.0ms</strong>. In-process telemetry queue handover is <strong>0.15ms</strong>.</li>
            <li><strong>Attribution Isolation:</strong> Zero cross-contamination across concurrent agent runs.</li>
          </ul>

          <div className="p-6 bg-emerald-50 border border-emerald-200 rounded-xl">
            <h4 className="font-bold text-emerald-900 text-sm mb-1">Summary</h4>
            <p className="text-xs text-emerald-800 leading-relaxed">
              CortexHeal delivers the speed, predictability, and auditability required to operate agentic workflows in production environments without fear of runaway cost or infinite loops.
            </p>
          </div>
        </div>
      )}
    </article>
  );
}
