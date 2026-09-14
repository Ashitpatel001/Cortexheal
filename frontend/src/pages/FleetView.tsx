import { useQuery } from "@tanstack/react-query";
import { api } from "../api";
import { Link } from "react-router-dom";
import { Activity, Play, Pause, CheckCircle, AlertTriangle, Loader2 } from "lucide-react";
import { cn } from "../utils";

export function FleetView() {
  const { data: fleet, isLoading, error } = useQuery({
    queryKey: ["fleet"],
    queryFn: () => api.getFleet(),
  });

  if (isLoading) {
    return (
      <div className="p-8 flex justify-center text-slate-500">
        <Loader2 className="w-8 h-8 animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8 text-status-red flex flex-col gap-2">
        <AlertTriangle className="w-8 h-8" />
        <p>Failed to load fleet data</p>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      <div className="flex items-center gap-3 border-b border-border pb-4">
        <Activity className="w-6 h-6 text-accent" />
        <h1 className="text-2xl font-bold text-white tracking-wide">Fleet Observability</h1>
        <span className="ml-auto bg-surface border border-border px-3 py-1 rounded-full text-xs text-slate-400 font-mono flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-accent shadow-[0_0_8px_rgba(59,130,246,0.6)] animate-pulse" />
          LIVE
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {fleet?.map((agent) => (
          <Link
            key={agent.agent_id}
            to={`/runs/${agent.run_id}`}
            className="block group bg-surface border border-border p-4 hover:border-slate-500 transition-colors"
          >
            <div className="flex justify-between items-start mb-3">
              <h3 className="font-mono text-sm text-slate-200 group-hover:text-white transition-colors truncate pr-4">
                {agent.agent_id}
              </h3>
              <StatusBadge status={agent.status} />
            </div>
            
            <div className="space-y-3">
              <div className="flex items-center justify-between text-xs text-slate-400">
                <span>Run ID</span>
                <span className="font-mono">{agent.run_id.split("-")[0]}...</span>
              </div>
              
              <div className="flex items-center justify-between text-xs text-slate-400">
                <span>Events</span>
                <span className="font-mono bg-border px-2 py-0.5 rounded-sm">
                  {agent.event_count || 0}
                </span>
              </div>

              <div className="flex items-center justify-between text-xs text-slate-400">
                <span>Last Active</span>
                <span>{new Date(agent.end_time || agent.start_time).toLocaleTimeString()}</span>
              </div>
            </div>
            
            {/* Visual indicator of activity - simulated via event_count presence */}
            <div className="mt-4 pt-3 border-t border-border flex items-end gap-1 h-6">
              {[...Array(12)].map((_, i) => {
                const isActive = ['running', 'resuming', 'pause_requested'].includes(agent.status);
                const height = agent.event_count > 0 
                  ? Math.max(10, Math.min(100, Math.random() * 100))
                  : 10;
                const opacity = isActive ? 1 : 0.2;
                return (
                  <div 
                    key={i} 
                    className="flex-1 bg-accent transition-all duration-500 rounded-sm"
                    style={{ height: `${height}%`, opacity }}
                  />
                );
              })}
            </div>
          </Link>
        ))}
        {(!fleet || fleet.length === 0) && (
          <div className="col-span-full py-12 text-center text-slate-500 border border-dashed border-border">
            No active or recent agents found in the fleet.
          </div>
        )}
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  let colorClass = "text-slate-400 bg-slate-900 border-slate-700";
  let Icon = Activity;

  switch (status.toLowerCase()) {
    case "running":
    case "resuming":
      colorClass = "text-status-green bg-status-green/10 border-status-green/20";
      Icon = Play;
      break;
    case "paused":
    case "pause_requested":
      colorClass = "text-status-amber bg-status-amber/10 border-status-amber/20";
      Icon = Pause;
      break;
    case "completed":
      colorClass = "text-accent bg-accent/10 border-accent/20";
      Icon = CheckCircle;
      break;
    case "failed":
      colorClass = "text-status-red bg-status-red/10 border-status-red/20";
      Icon = AlertTriangle;
      break;
  }

  return (
    <span className={cn("inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider border", colorClass)}>
      <Icon className="w-3 h-3" />
      {status}
    </span>
  );
}
