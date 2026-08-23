import React, { useState, useEffect } from "react";
import { Play, ShieldAlert, Cpu, CheckCircle2, PauseCircle, RefreshCw, Zap } from "lucide-react";

export function SafetyDiagram() {
  const [activeStep, setActiveStep] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setActiveStep((prev) => (prev + 1) % 4);
    }, 2400);
    return () => clearInterval(timer);
  }, []);

  const steps = [
    {
      title: "1. Agent Telemetry Ingestion",
      desc: "LangGraph, AutoGen, or Custom Agent emits structured tool call and token events.",
      badge: "STREAMING",
      icon: Play,
      detail: "POST /events -> sequence_num: 4, tool: 'query_db'",
    },
    {
      title: "2. Deterministic Hash Comparison",
      desc: "SHA-256 normalized hash calculates state repetitions and cost accumulation.",
      badge: "SUB-MS MATH",
      icon: Cpu,
      detail: "hash(args) == hash(prev_args) [Count: 4/4]",
    },
    {
      title: "3. Circuit Breaker Auto-Pause",
      desc: "Threshold breached (repetition >= 4). Deterministic policy halts the run immediately.",
      badge: "ZERO LLMs",
      icon: ShieldAlert,
      detail: "STATUS: PAUSED | Severity: CRITICAL | SLA: <10ms",
    },
    {
      title: "4. Human / Policy Recovery",
      desc: "Recovery plan injected into graph context. Agent resumes safely on verified index.",
      badge: "VERIFIED",
      icon: CheckCircle2,
      detail: "PLAN: MODIFY_CONTEXT -> RESUMED -> COMPLETED",
    },
  ];

  return (
    <div className="w-full bg-white border border-slate-200 rounded-2xl shadow-xl p-6 sm:p-8">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8 pb-6 border-b border-slate-100">
        <div>
          <div className="flex items-center gap-2 text-xs font-mono font-semibold text-blue-600 uppercase tracking-wider mb-1">
            <Zap className="w-3.5 h-3.5" /> Execution Loop Architecture
          </div>
          <h3 className="text-xl font-bold text-slate-900">
            How Deterministic Safety Operates in Real Time
          </h3>
        </div>
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 mr-1.5 animate-pulse" />
            Safety Path Active
          </span>
        </div>
      </div>

      {/* Interactive Step Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {steps.map((step, idx) => {
          const Icon = step.icon;
          const isActive = activeStep === idx;
          return (
            <div
              key={idx}
              onClick={() => setActiveStep(idx)}
              className={`cursor-pointer rounded-xl p-5 border transition-all duration-300 ${
                isActive
                  ? "border-blue-600 bg-blue-50/40 shadow-md ring-1 ring-blue-600"
                  : "border-slate-200 bg-slate-50/50 hover:bg-slate-50 hover:border-slate-300"
              }`}
            >
              <div className="flex items-center justify-between mb-3">
                <div
                  className={`p-2 rounded-lg ${
                    isActive
                      ? "bg-blue-600 text-white"
                      : "bg-slate-200 text-slate-700"
                  }`}
                >
                  <Icon className="w-4 h-4" />
                </div>
                <span className="text-[10px] font-mono font-bold tracking-wider px-2 py-0.5 rounded bg-white border border-slate-200 text-slate-600 uppercase">
                  {step.badge}
                </span>
              </div>
              <h4 className="text-sm font-bold text-slate-900 mb-1">
                {step.title}
              </h4>
              <p className="text-xs text-slate-500 leading-relaxed">
                {step.desc}
              </p>
            </div>
          );
        })}
      </div>

      {/* Live State Wire Box */}
      <div className="mt-6 p-4 bg-slate-900 rounded-xl text-slate-200 font-mono text-xs overflow-x-auto border border-slate-800 shadow-inner">
        <div className="flex items-center justify-between text-slate-400 border-b border-slate-800 pb-2 mb-2">
          <span className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-blue-500" />
            LIVE TELEMETRY LOG [STEP {activeStep + 1}/4]
          </span>
          <span className="text-[11px] text-slate-500">Handover: 0.15ms | DB Pipeline: ~26.5ms p50</span>
        </div>
        <p className="text-emerald-400 leading-relaxed font-semibold">
          &gt; {steps[activeStep].detail}
        </p>
      </div>
    </div>
  );
}
