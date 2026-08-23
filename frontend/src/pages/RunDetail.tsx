import { useQuery } from "@tanstack/react-query";
import { useParams, Link } from "react-router-dom";
import { api } from "../api";
import { LoadingState, ErrorState, Badge } from "../components/ui";
import { relativeTime, cn } from "../utils";
import { Activity, ShieldAlert, FileText } from "lucide-react";

export function RunDetail() {
  const { id } = useParams<{ id: string }>();

  const { data: run, isLoading: runLoading, error: runError } = useQuery({
    queryKey: ["run", id],
    queryFn: () => api.getRun(id!),
    enabled: !!id
  });

  const { data: timeline, isLoading: timelineLoading, error: timelineError } = useQuery({
    queryKey: ["timeline", id],
    queryFn: () => api.getRunTimeline(id!),
    enabled: !!id
  });

  if (runLoading || timelineLoading) return <LoadingState message="Loading run details..." />;
  if (runError) return <ErrorState title="Failed to load run" error={runError} />;
  if (timelineError) return <ErrorState title="Failed to load timeline" error={timelineError} />;

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6">
      <div className="flex items-center gap-2 text-sm text-slate-500 font-mono mb-4">
        <Link to="/runs" className="hover:text-slate-300">runs</Link>
        <span>/</span>
        <span className="text-slate-300">{id}</span>
      </div>

      <div className="bg-surface border border-border p-6 flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white mb-2">{run?.agent_id}</h1>
          <div className="text-sm font-mono text-slate-400 mb-4">{run?.run_id}</div>
          <div className="flex gap-4">
            <div className="flex flex-col">
              <span className="text-xs text-slate-500 uppercase">Framework</span>
              <span className="text-slate-300 capitalize">{run?.framework}</span>
            </div>
            <div className="flex flex-col">
              <span className="text-xs text-slate-500 uppercase">Protection</span>
              <span className="text-slate-300">{run?.protection_mode}</span>
            </div>
            <div className="flex flex-col">
              <span className="text-xs text-slate-500 uppercase">Started</span>
              <span className="text-slate-300" title={run?.start_time}>{run?.start_time ? relativeTime(run?.start_time) : '-'}</span>
            </div>
          </div>
        </div>
        <div className="text-right flex flex-col items-end gap-2">
          <Badge variant={
            run?.status === 'running' ? 'green' : 
            run?.status === 'failed' ? 'red' : 
            run?.status === 'completed' ? 'neutral' : 'amber'
          }>
            {run?.status?.toUpperCase()}
          </Badge>
        </div>
      </div>

      <div>
        <h3 className="text-lg font-bold text-white mb-4">Execution Timeline</h3>
        <div className="border-l-2 border-border ml-4 space-y-8 py-4">
          {timeline?.map((entry, idx) => {
            const isEvent = entry.type === 'event';
            const isIncident = entry.type === 'incident';
            const isAudit = entry.type === 'audit';

            return (
              <div key={idx} className="relative pl-8">
                {/* Timeline dot/icon */}
                <div className={cn(
                  "absolute -left-3.5 p-1 rounded-full border-2 border-background",
                  isEvent ? "bg-slate-700 text-slate-300" :
                  isIncident ? "bg-status-red text-white" :
                  "bg-accent text-white"
                )}>
                  {isEvent && <Activity className="w-4 h-4" />}
                  {isIncident && <ShieldAlert className="w-4 h-4" />}
                  {isAudit && <FileText className="w-4 h-4" />}
                </div>

                <div className="flex items-center gap-2 mb-1">
                  <span className="text-sm font-semibold text-slate-200 uppercase tracking-wider">
                    {isEvent && String(entry.data.event_type)}
                    {isIncident && "SAFETY INCIDENT DETECTED"}
                    {isAudit && String(entry.data.action)}
                  </span>
                  <span className="text-xs font-mono text-slate-500" title={entry.timestamp}>
                    {relativeTime(entry.timestamp)}
                  </span>
                </div>

                <div className="bg-surface border border-border p-3 text-sm">
                  {isEvent && (
                    <div className="font-mono text-slate-400">
                      Seq: {String(entry.data.sequence_number)} | Tool: {String(entry.data.tool) || 'N/A'}
                    </div>
                  )}
                  {isIncident && (
                    <div className="space-y-2">
                      <div className="flex items-center gap-2">
                        <Badge variant="red">{String(entry.data.failure_type)}</Badge>
                        <span className="font-mono text-xs text-slate-500">{String(entry.data.incident_id)}</span>
                      </div>
                      <Link 
                        to={`/incidents/${String(entry.data.incident_id)}`}
                        className="text-accent hover:underline inline-block mt-1"
                      >
                        View Incident Details &rarr;
                      </Link>
                    </div>
                  )}
                  {isAudit && (
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <Badge variant={String(entry.data.result) === 'SUCCESS' ? 'green' : String(entry.data.result) === 'FAILED' ? 'red' : 'neutral'}>
                          {String(entry.data.result)}
                        </Badge>
                        <span className="text-slate-400">by {String(entry.data.actor_id) || String(entry.data.actor_type)}</span>
                      </div>
                      {String(entry.data.reason) && <p className="text-slate-300 mt-1">{String(entry.data.reason)}</p>}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
          {timeline?.length === 0 && (
            <div className="pl-8 text-slate-500 italic text-sm">No timeline entries found.</div>
          )}
        </div>
      </div>
    </div>
  );
}
