import React from "react";
import { Link } from "react-router-dom";
import { Activity, ShieldCheck, Lock, Terminal } from "lucide-react";

export function Footer() {
  return (
    <footer className="border-t border-slate-200 bg-slate-50 text-slate-600 text-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          <div className="space-y-4">
            <div className="flex items-center gap-2.5">
              <div className="p-1.5 bg-blue-600 rounded text-white">
                <Activity className="w-4 h-4" />
              </div>
              <span className="text-lg font-bold text-slate-900">
                Cortex<span className="text-blue-600">Heal</span>
              </span>
            </div>
            <p className="text-xs text-slate-500 leading-relaxed">
              Real-time, deterministic safety and circuit-breaker control plane for AI agent fleets. Zero LLMs in the safety path.
            </p>
            <div className="flex items-center gap-3 text-xs text-slate-400 font-mono">
              <span>v1.0.0</span>
              <span>•</span>
              <span className="flex items-center gap-1 text-emerald-600">
                <ShieldCheck className="w-3.5 h-3.5" /> SOC2 Compliant Audits
              </span>
            </div>
          </div>

          <div>
            <h4 className="font-semibold text-slate-900 mb-3 text-xs tracking-wider uppercase font-mono">
              Product
            </h4>
            <ul className="space-y-2 text-xs">
              <li><Link to="/docs" className="hover:text-blue-600 transition-colors">Documentation</Link></li>
              <li><Link to="/docs#architecture" className="hover:text-blue-600 transition-colors">Safety Gate Engine</Link></li>
              <li><Link to="/docs#adapters" className="hover:text-blue-600 transition-colors">LangGraph & AutoGen Adapters</Link></li>
              <li><Link to="/docs#compliance" className="hover:text-blue-600 transition-colors">Audit & Compliance Export</Link></li>
            </ul>
          </div>

          <div>
            <h4 className="font-semibold text-slate-900 mb-3 text-xs tracking-wider uppercase font-mono">
              Engineering
            </h4>
            <ul className="space-y-2 text-xs">
              <li><Link to="/blog/deterministic-safety-imperative" className="hover:text-blue-600 transition-colors">The Deterministic Imperative</Link></li>
              <li><Link to="/blog/sub-millisecond-circuit-breakers" className="hover:text-blue-600 transition-colors">Real-Time Circuit Breakers</Link></li>
              <li><a href="https://github.com/Ashitpatel001/CortexHeal" target="_blank" rel="noreferrer" className="hover:text-blue-600 transition-colors">GitHub Repository</a></li>
              <li><a href="http://127.0.0.1:8000/docs" target="_blank" rel="noreferrer" className="hover:text-blue-600 transition-colors">Swagger API Specs</a></li>
            </ul>
          </div>

          <div>
            <h4 className="font-semibold text-slate-900 mb-3 text-xs tracking-wider uppercase font-mono">
              Compliance & Security
            </h4>
            <div className="p-4 bg-white border border-slate-200 rounded-lg space-y-2">
              <div className="flex items-center gap-2 text-xs font-semibold text-slate-900">
                <Lock className="w-3.5 h-3.5 text-blue-600" />
                <span>Zero-LLM Decision Path</span>
              </div>
              <p className="text-[11px] text-slate-500 leading-normal">
                Safety decisions are calculated via deterministic hashing and bounded mathematical thresholds. No probabilistic agents evaluate agents.
              </p>
            </div>
          </div>
        </div>

        <div className="mt-12 pt-6 border-t border-slate-200 flex flex-col sm:flex-row items-center justify-between text-xs text-slate-400">
          <p>© {new Date().getFullYear()} CortexHeal Control Plane. All rights reserved.</p>
          <p className="flex items-center gap-1 mt-2 sm:mt-0 font-mono">
            <Terminal className="w-3.5 h-3.5" /> Deterministic AI Safety
          </p>
        </div>
      </div>
    </footer>
  );
}
