import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ChevronDown, ChevronRight, CheckCircle2, XCircle, AlertTriangle, PlayCircle } from "lucide-react";
import type { Incident } from "../types";
import { api } from "../api";
import { Badge, LoadingState, ErrorState } from "./ui";
import { relativeTime, cn } from "../utils";
import { useRole } from "../hooks/useRole";

function SeverityBadge({ severity }: { severity: string }) {
  if (severity === "CRITICAL" || severity === "HIGH") return <Badge variant="red">{severity}</Badge>;
  if (severity === "MEDIUM") return <Badge variant="amber">{severity}</Badge>;
  if (severity === "LOW") return <Badge variant="neutral">{severity}</Badge>;
  return <Badge>{severity}</Badge>;
}

function StatusBadge({ status }: { status: string }) {
  if (status === "OPEN") return <Badge variant="amber">{status}</Badge>;
  if (status === "RESOLVED") return <Badge variant="green">{status}</Badge>;
  return <Badge>{status}</Badge>;
}

function RunStatusBadge({ status }: { status: string }) {
  if (status === "paused") return <Badge variant="amber">PAUSED</Badge>;
  if (status === "running") return <Badge variant="green">RUNNING</Badge>;
  if (status === "pause_requested") return <Badge variant="amber">PAUSING</Badge>;
  if (status === "resume_requested") return <Badge variant="accent">RESUMING</Badge>;
  if (status === "completed") return <Badge variant="neutral">COMPLETED</Badge>;
  if (status === "failed") return <Badge variant="red">FAILED</Badge>;
  return <Badge>{status}</Badge>;
}

export function IncidentRow({ incident }: { incident: Incident }) {
  const [expanded, setExpanded] = useState(false);
  const { role, handleApiError } = useRole();
  const queryClient = useQueryClient();

  const { data: plan, isLoading: planLoading, error: planError } = useQuery({
    queryKey: ["plan", incident.incident_id],
    queryFn: () => api.getPlan(incident.incident_id),
    enabled: expanded,
    retry: false
  });

  const approveMutation = useMutation({
    mutationFn: () => api.approvePlan(incident.incident_id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["incidents"] });
      queryClient.invalidateQueries({ queryKey: ["plan", incident.incident_id] });
    },
    onError: handleApiError
  });

  const rejectMutation = useMutation({
    mutationFn: () => api.rejectPlan(incident.incident_id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["incidents"] });
      queryClient.invalidateQueries({ queryKey: ["plan", incident.incident_id] });
    },
    onError: handleApiError
  });

  const resumeMutation = useMutation({
    mutationFn: () => api.resumeRun(incident.run_id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["incidents"] });
    },
    onError: handleApiError
  });

  const isViewer = role === 'VIEWER';
  const disableActions = isViewer || approveMutation.isPending || rejectMutation.isPending || resumeMutation.isPending;

  return (
    <div className="border border-border bg-surface hover:border-slate-600 transition-colors">
      <div 
        className="flex items-center p-4 cursor-pointer gap-4"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="text-slate-400">
          {expanded ? <ChevronDown className="w-5 h-5" /> : <ChevronRight className="w-5 h-5" />}
        </div>
        
        <div className="flex-1 grid grid-cols-12 gap-4 items-center">
          <div className="col-span-3 flex flex-col gap-1">
            <span className="text-sm font-semibold text-slate-200">{incident.failure_type}</span>
            <div className="flex gap-2">
              <SeverityBadge severity={incident.severity} />
              <StatusBadge status={incident.status} />
            </div>
          </div>
          
          <div className="col-span-5 flex flex-col gap-1">
            <span className="text-sm text-slate-300 truncate" title={incident.description}>
              {incident.description}
            </span>
            <div className="flex items-center gap-2 text-xs font-mono text-slate-500">
              <Link 
                to={`/runs/${incident.run_id}`}
                className="hover:text-accent hover:underline"
                onClick={e => e.stopPropagation()}
                title={incident.run_id}
              >
                run:{incident.run_id.substring(0,8)}
              </Link>
              <span>&bull;</span>
              <span title={incident.triggered_at}>{relativeTime(incident.triggered_at)}</span>
            </div>
          </div>
          
          <div className="col-span-2 flex items-center">
            <RunStatusBadge status={incident.run_status} />
          </div>

          <div className="col-span-2 flex justify-end">
            <Link 
              to={`/incidents/${incident.incident_id}`}
              className="text-sm text-accent hover:underline"
              onClick={e => e.stopPropagation()}
            >
              Details &rarr;
            </Link>
          </div>
        </div>
      </div>

      {expanded && (
        <div className="border-t border-border p-6 bg-background/50 grid grid-cols-2 gap-8">
          <div>
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-3 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4" /> Evidence
            </h4>
            <div className="bg-surface border border-border p-3 space-y-2">
              {Object.entries(incident.evidence || {}).map(([key, value]) => (
                <div key={key} className="flex flex-col border-b border-border/50 pb-2 last:border-0 last:pb-0">
                  <span className="text-xs text-slate-500">{key}</span>
                  <span className="text-sm font-mono text-slate-300 break-all">{String(value)}</span>
                </div>
              ))}
            </div>
            {(incident.observed_value !== undefined || incident.threshold !== undefined) && (
              <div className="mt-3 flex gap-4 text-sm font-mono">
                {incident.observed_value !== undefined && <div>Observed: <span className="text-slate-200">{incident.observed_value}</span></div>}
                {incident.threshold !== undefined && <div>Threshold: <span className="text-slate-200">{incident.threshold}</span></div>}
              </div>
            )}
          </div>

          <div>
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-3 flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4" /> Recovery Plan
            </h4>
            
            {planLoading ? (
              <LoadingState message="Generating plan..." />
            ) : planError ? (
              <ErrorState title="Failed to load plan" error={planError} />
            ) : plan ? (
              <div className="space-y-4">
                <div className="bg-surface border border-border p-3">
                  <div className="text-sm text-slate-300 mb-2">{plan.diagnosis}</div>
                  <div className="flex gap-2">
                    <Badge variant={plan.risk_level === "HIGH" ? "red" : plan.risk_level === "MEDIUM" ? "amber" : "neutral"}>
                      Risk: {plan.risk_level}
                    </Badge>
                    <Badge variant={plan.status === "PROPOSED" ? "amber" : plan.status === "REJECTED" ? "red" : "green"}>
                      {plan.status}
                    </Badge>
                  </div>
                </div>

                {plan.status === "PROPOSED" && incident.status === "OPEN" && (
                  <div className="flex gap-3 pt-2" title={isViewer ? "Requires OPERATOR or ADMIN role" : ""}>
                    <button
                      disabled={disableActions}
                      onClick={() => approveMutation.mutate()}
                      className={cn(
                        "flex items-center gap-2 px-4 py-2 font-medium transition-colors",
                        "bg-accent text-white hover:bg-blue-600",
                        disableActions && "opacity-50 cursor-not-allowed"
                      )}
                    >
                      {approveMutation.isPending && <PlayCircle className="w-4 h-4 animate-spin" />}
                      Approve Plan
                    </button>
                    <button
                      disabled={disableActions}
                      onClick={() => rejectMutation.mutate()}
                      className={cn(
                        "flex items-center gap-2 px-4 py-2 font-medium transition-colors",
                        "border border-border text-slate-300 hover:bg-border/50",
                        disableActions && "opacity-50 cursor-not-allowed"
                      )}
                    >
                      {rejectMutation.isPending && <XCircle className="w-4 h-4 animate-spin" />}
                      Reject
                    </button>
                  </div>
                )}
                
                {incident.run_status === "paused" && (incident.status === "RESOLVED" || plan.status === "COMPLETED" || plan.status === "APPROVED") && (
                  <div className="flex gap-3 pt-2" title={isViewer ? "Requires OPERATOR or ADMIN role" : ""}>
                    <button
                      disabled={disableActions}
                      onClick={() => resumeMutation.mutate()}
                      className={cn(
                        "flex items-center gap-2 px-4 py-2 font-medium transition-colors",
                        "bg-accent text-white hover:bg-blue-600",
                        disableActions && "opacity-50 cursor-not-allowed"
                      )}
                    >
                      {resumeMutation.isPending && <PlayCircle className="w-4 h-4 animate-spin" />}
                      Resume Run
                    </button>
                  </div>
                )}

                {!!(approveMutation.error || rejectMutation.error || resumeMutation.error) && (
                  <div className="text-sm font-mono text-status-red mt-2">
                    Action failed. See console for details.
                  </div>
                )}
              </div>
            ) : null}
          </div>
        </div>
      )}
    </div>
  );
}
