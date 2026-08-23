import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../api";
import { Badge, LoadingState, ErrorState, EmptyState } from "../components/ui";
import { relativeTime } from "../utils";
import { ListTree, ChevronLeft, ChevronRight } from "lucide-react";

function RunStatusBadge({ status }: { status: string }) {
  if (status === "paused") return <Badge variant="amber">PAUSED</Badge>;
  if (status === "running") return <Badge variant="green">RUNNING</Badge>;
  if (status === "pause_requested") return <Badge variant="amber">PAUSING</Badge>;
  if (status === "resume_requested") return <Badge variant="accent">RESUMING</Badge>;
  if (status === "completed") return <Badge variant="neutral">COMPLETED</Badge>;
  if (status === "failed") return <Badge variant="red">FAILED</Badge>;
  return <Badge>{status}</Badge>;
}

export function RunsList() {
  const [skip, setSkip] = useState(0);
  const limit = 50;

  const { data, isLoading, error } = useQuery({
    queryKey: ["runs", skip, limit],
    queryFn: () => api.getRuns(skip, limit),
    refetchOnWindowFocus: false
  });

  if (isLoading) return <LoadingState message="Loading runs..." />;
  if (error) return <ErrorState title="Failed to load runs" error={error} />;

  const runs = data?.data || [];
  const total = data?.total || 0;

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white tracking-wide">Agent Runs</h1>
        
        <div className="flex items-center gap-4">
          <div className="text-sm text-slate-400 font-mono">
            Showing {skip + 1}-{Math.min(skip + limit, total)} of {total}
          </div>
          <div className="flex gap-2">
            <button 
              disabled={skip === 0}
              onClick={() => setSkip(Math.max(0, skip - limit))}
              className="p-1 border border-border text-slate-400 hover:text-white disabled:opacity-30 transition-colors"
            >
              <ChevronLeft className="w-5 h-5" />
            </button>
            <button 
              disabled={skip + limit >= total}
              onClick={() => setSkip(skip + limit)}
              className="p-1 border border-border text-slate-400 hover:text-white disabled:opacity-30 transition-colors"
            >
              <ChevronRight className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>

      {runs.length === 0 ? (
        <EmptyState 
          title="No active runs" 
          description="No agents have been tracked by the control plane yet."
          icon={ListTree} 
        />
      ) : (
        <div className="border border-border bg-surface overflow-hidden">
          <table className="w-full text-left text-sm">
            <thead className="bg-background/50 border-b border-border text-slate-400">
              <tr>
                <th className="px-4 py-3 font-medium uppercase tracking-wider text-xs">Run ID</th>
                <th className="px-4 py-3 font-medium uppercase tracking-wider text-xs">Agent</th>
                <th className="px-4 py-3 font-medium uppercase tracking-wider text-xs">Framework</th>
                <th className="px-4 py-3 font-medium uppercase tracking-wider text-xs">Status</th>
                <th className="px-4 py-3 font-medium uppercase tracking-wider text-xs text-right">Started</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {runs.map(run => (
                <tr key={run.run_id} className="hover:bg-background/30 transition-colors">
                  <td className="px-4 py-3 font-mono">
                    <Link to={`/runs/${run.run_id}`} className="text-accent hover:underline">
                      {run.run_id.substring(0, 12)}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-slate-200">{run.agent_id}</td>
                  <td className="px-4 py-3 text-slate-400 capitalize">{run.framework}</td>
                  <td className="px-4 py-3">
                    <RunStatusBadge status={run.status} />
                  </td>
                  <td className="px-4 py-3 text-right text-slate-400 font-mono text-xs" title={run.start_time}>
                    {relativeTime(run.start_time)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
