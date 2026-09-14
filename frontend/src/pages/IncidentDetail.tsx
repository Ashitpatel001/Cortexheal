import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useParams, Link, useNavigate } from "react-router-dom";
import { api } from "../api";
import { Badge, LoadingState, ErrorState } from "../components/ui";
import { relativeTime, cn } from "../utils";
import { AlertTriangle, PlayCircle, XCircle, ArrowLeft } from "lucide-react";
import { useRole } from "../hooks/useRole";

export function IncidentDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { role, handleApiError } = useRole();

  const { data: incident, isLoading: incLoading, error: incError } = useQuery({
    queryKey: ["incident", id],
    queryFn: () => api.getIncident(id!),
    enabled: !!id
  });

  const { data: plan, isLoading: planLoading, error: planError } = useQuery({
    queryKey: ["plan", id],
    queryFn: () => api.getPlan(id!),
    enabled: !!id
  });

  const approveMutation = useMutation({
    mutationFn: () => api.approvePlan(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["incident", id] });
      queryClient.invalidateQueries({ queryKey: ["plan", id] });
    },
    onError: handleApiError
  });

  const rejectMutation = useMutation({
    mutationFn: () => api.rejectPlan(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["incident", id] });
      queryClient.invalidateQueries({ queryKey: ["plan", id] });
    },
    onError: handleApiError
  });
  
  const resumeMutation = useMutation({
    mutationFn: () => api.resumeRun(incident?.run_id || ''),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["incident", id] });
    },
    onError: handleApiError
  });

  if (incLoading) return <LoadingState message="Loading incident..." />;
  if (incError) return <ErrorState title="Failed to load incident" error={incError} />;
  if (!incident) return <ErrorState title="Incident not found" />;

  const isViewer = role === 'VIEWER';
  const disableActions = isViewer || approveMutation.isPending || rejectMutation.isPending || resumeMutation.isPending;

  const handleCopyContext = () => {
    if (!incident) return;
    const ctx = `CortexHeal Incident Context
ID: ${incident.incident_id}
Run ID: ${incident.run_id}
Agent ID: ${incident.agent_id}
Failure Type: ${incident.failure_type}
Severity: ${incident.severity}
Status: ${incident.status}

Description:
${incident.description}

Evidence:
${JSON.stringify(incident.evidence, null, 2)}

Observed Value: ${incident.observed_value ?? 'N/A'}
Threshold Limit: ${incident.threshold ?? 'N/A'}`;
    
    navigator.clipboard.writeText(ctx).then(() => {
      alert("Incident context copied to clipboard for AI assistant.");
    });
  };

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      <button 
        onClick={() => navigate(-1)}
        className="flex items-center gap-2 text-sm text-slate-400 hover:text-white transition-colors mb-2"
      >
        <ArrowLeft className="w-4 h-4" /> Back
      </button>

      <div className="bg-surface border border-border p-6 shadow-lg">
        <div className="flex items-start justify-between mb-6">
          <div>
            <div className="flex items-center gap-4 mb-2">
              <h1 className="text-3xl font-bold text-white">{incident.failure_type}</h1>
              <button 
                onClick={handleCopyContext}
                className="bg-accent/10 text-accent hover:bg-accent/20 border border-accent/30 px-3 py-1 rounded text-xs font-mono uppercase transition-colors flex items-center gap-2"
              >
                Copy as AI context
              </button>
            </div>
            <div className="text-slate-300 mb-4 max-w-2xl">{incident.description}</div>
            
            <div className="flex items-center gap-3">
              <Badge variant={
                incident.severity === "CRITICAL" || incident.severity === "HIGH" ? "red" : 
                incident.severity === "MEDIUM" ? "amber" : "neutral"
              }>{incident.severity}</Badge>
              <Badge variant={incident.status === "OPEN" ? "amber" : "green"}>{incident.status}</Badge>
              <span className="text-slate-500 font-mono text-sm" title={incident.triggered_at}>
                {relativeTime(incident.triggered_at)}
              </span>
            </div>
          </div>
          
          <div className="text-right flex flex-col items-end gap-1 font-mono text-sm">
            <span className="text-slate-500">INCIDENT ID</span>
            <span className="text-slate-300">{incident.incident_id}</span>
            <span className="text-slate-500 mt-2">RUN ID</span>
            <Link to={`/runs/${incident.run_id}`} className="text-accent hover:underline">
              {incident.run_id}
            </Link>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-8 border-t border-border pt-6">
          {/* Left Column: Context & Evidence */}
          <div className="space-y-6">
            <section>
              <h3 className="text-sm font-bold uppercase tracking-wider text-slate-400 mb-3 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4" /> Detection Evidence
              </h3>
              <div className="bg-background border border-border p-4 rounded-sm">
                <div className="grid gap-3">
                  {Object.entries(incident.evidence || {}).map(([k, v]) => (
                    <div key={k} className="border-b border-border/50 pb-2 last:border-0 last:pb-0">
                      <div className="text-xs text-slate-500 mb-1">{k}</div>
                      <div className="font-mono text-sm text-slate-200 break-all">{String(v)}</div>
                    </div>
                  ))}
                  {(incident.observed_value !== undefined || incident.threshold !== undefined) && (
                    <div className="flex gap-6 mt-2 pt-2 border-t border-border/50">
                      {incident.observed_value !== undefined && (
                        <div>
                          <div className="text-xs text-slate-500">Observed Value</div>
                          <div className="font-mono text-status-red text-lg">{incident.observed_value}</div>
                        </div>
                      )}
                      {incident.threshold !== undefined && (
                        <div>
                          <div className="text-xs text-slate-500">Threshold Limit</div>
                          <div className="font-mono text-slate-300 text-lg">{incident.threshold}</div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </section>
            
            <section>
              <h3 className="text-sm font-bold uppercase tracking-wider text-slate-400 mb-3">System Context</h3>
              <div className="bg-background border border-border p-4 grid grid-cols-2 gap-4">
                <div>
                  <div className="text-xs text-slate-500">Detector</div>
                  <div className="font-mono text-sm text-slate-300">{incident.detector} v{incident.detector_version}</div>
                </div>
                <div>
                  <div className="text-xs text-slate-500">Current Run Status</div>
                  <div className="mt-1">
                    <Badge variant={
                      incident.run_status === 'paused' ? 'amber' : 
                      incident.run_status === 'running' ? 'green' : 
                      incident.run_status === 'failed' ? 'red' : 'neutral'
                    }>
                      {incident.run_status?.toUpperCase()}
                    </Badge>
                  </div>
                </div>
              </div>
            </section>
          </div>

          {/* Right Column: Recovery Plan */}
          <div>
            <h3 className="text-sm font-bold uppercase tracking-wider text-slate-400 mb-3">Recovery Plan</h3>
            {planLoading ? (
              <LoadingState message="Fetching recovery plan..." />
            ) : planError ? (
              <ErrorState title="Failed to load plan" error={planError} />
            ) : plan ? (
              <div className="bg-background border border-border p-5 h-full flex flex-col">
                <div className="flex justify-between items-start mb-4">
                  <Badge variant={plan.status === "PROPOSED" ? "amber" : plan.status === "REJECTED" ? "red" : "green"}>
                    PLAN {plan.status}
                  </Badge>
                  <Badge variant={plan.risk_level === "HIGH" ? "red" : plan.risk_level === "MEDIUM" ? "amber" : "neutral"}>
                    {plan.risk_level} RISK
                  </Badge>
                </div>
                
                <p className="text-slate-200 mb-6 font-medium">{plan.diagnosis}</p>
                
                <div className="space-y-3 flex-1">
                  <div className="text-xs text-slate-500 uppercase tracking-wider">Proposed Actions</div>
                  {plan.proposed_actions.map(action => (
                    <div key={action.action_id} className="border border-border/50 bg-surface p-3">
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-mono text-accent text-sm font-bold">{action.action_type}</span>
                        <Badge>{action.status}</Badge>
                      </div>
                      <p className="text-sm text-slate-400">{action.reason}</p>
                    </div>
                  ))}
                </div>

                {/* Actions */}
                <div className="mt-8 pt-4 border-t border-border flex gap-3">
                  {plan.status === "PROPOSED" && incident.status === "OPEN" && (
                    <>
                      <button
                        title={isViewer ? "Requires OPERATOR or ADMIN role" : ""}
                        disabled={disableActions}
                        onClick={() => approveMutation.mutate()}
                        className={cn(
                          "flex-1 flex justify-center items-center gap-2 py-2.5 font-medium transition-colors",
                          "bg-accent text-white hover:bg-blue-600",
                          disableActions && "opacity-50 cursor-not-allowed"
                        )}
                      >
                        {approveMutation.isPending && <PlayCircle className="w-5 h-5 animate-spin" />}
                        Approve & Execute
                      </button>
                      <button
                        title={isViewer ? "Requires OPERATOR or ADMIN role" : ""}
                        disabled={disableActions}
                        onClick={() => rejectMutation.mutate()}
                        className={cn(
                          "px-6 flex justify-center items-center gap-2 py-2.5 font-medium transition-colors",
                          "border border-border text-slate-300 hover:bg-border/50",
                          disableActions && "opacity-50 cursor-not-allowed"
                        )}
                      >
                        {rejectMutation.isPending && <XCircle className="w-5 h-5 animate-spin" />}
                        Reject
                      </button>
                    </>
                  )}
                  {incident.run_status === "paused" && (incident.status === "RESOLVED" || plan.status === "COMPLETED" || plan.status === "APPROVED") && (
                     <button
                        title={isViewer ? "Requires OPERATOR or ADMIN role" : ""}
                        disabled={disableActions}
                        onClick={() => resumeMutation.mutate()}
                        className={cn(
                          "flex-1 flex justify-center items-center gap-2 py-2.5 font-medium transition-colors",
                          "bg-accent text-white hover:bg-blue-600",
                          disableActions && "opacity-50 cursor-not-allowed"
                        )}
                      >
                        {resumeMutation.isPending && <PlayCircle className="w-5 h-5 animate-spin" />}
                        Resume Run
                      </button>
                  )}
                </div>
                {!!(approveMutation.error || rejectMutation.error || resumeMutation.error) && (
                  <div className="text-sm font-mono text-status-red mt-3 bg-status-red/10 p-2 border border-status-red/20">
                    Action failed: See console for details.
                  </div>
                )}
              </div>
            ) : null}
          </div>
        </div>
      </div>
    </div>
  );
}
