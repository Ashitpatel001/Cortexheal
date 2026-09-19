
with open("frontend/src/pages/IncidentDetail.tsx", "r", encoding="utf-8") as f:
    content = f.read()

import re

old_block = """                <div className="space-y-3 flex-1">
                  <div className="text-xs text-slate-500 uppercase tracking-wider">Proposed Actions</div>"""

new_block = """                {/* Pattern Trust Summary */}
                {plan.pattern_trust ? (
                  <div className="mb-6 p-4 border border-blue-900/50 bg-blue-950/20 rounded-md">
                    <div className="text-xs text-blue-400 uppercase tracking-wider mb-2 font-bold flex items-center gap-2">
                      <Zap className="w-3.5 h-3.5" /> Historical Trust
                    </div>
                    {plan.pattern_trust.actions.length > 0 ? (
                      <div className="space-y-2">
                        {plan.pattern_trust.actions.map((act: any) => (
                          <div key={act.action} className="text-sm text-slate-300">
                            Action <span className="font-mono text-accent">{act.action}</span> has{" "}
                            <span className="font-bold text-emerald-400">{(act.success_rate * 100).toFixed(0)}% success</span> over {act.attempted} attempts.
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="text-sm text-slate-400 italic">Insufficient data yet.</div>
                    )}
                  </div>
                ) : (
                  <div className="mb-6 p-4 border border-slate-800 bg-slate-900/50 rounded-md">
                    <div className="text-xs text-slate-500 uppercase tracking-wider mb-2 font-bold">Historical Trust</div>
                    <div className="text-sm text-slate-400 italic">Insufficient data yet.</div>
                  </div>
                )}

                <div className="space-y-3 flex-1">
                  <div className="text-xs text-slate-500 uppercase tracking-wider">Proposed Actions</div>"""

content = content.replace(old_block, new_block)

with open("frontend/src/pages/IncidentDetail.tsx", "w", encoding="utf-8") as f:
    f.write(content)

