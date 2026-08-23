import type { PaginatedResponse, Incident, Run, TimelineEntry, RecoveryPlan } from "./types";

class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export function getApiKey(): string | null {
  return sessionStorage.getItem("cortexheal_api_key");
}

export function setApiKey(key: string) {
  sessionStorage.setItem("cortexheal_api_key", key);
}

export function clearApiKey() {
  sessionStorage.removeItem("cortexheal_api_key");
}

async function fetchWithAuth(endpoint: string, options: RequestInit = {}) {
  const key = getApiKey();
  const headers = new Headers(options.headers || {});
  
  // Do not attach for /health or /readiness
  if (key && !endpoint.startsWith('/health') && !endpoint.startsWith('/readiness')) {
    headers.set("X-API-Key", key);
  }

  const response = await fetch(endpoint, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new ApiError(response.status, errorData.detail || response.statusText);
  }

  return response.json();
}

export const api = {
  health: () => fetchWithAuth("/health"),
  
  getIncidents: (skip = 0, limit = 50): Promise<PaginatedResponse<Incident>> => 
    fetchWithAuth(`/api/incidents?skip=${skip}&limit=${limit}`),
    
  getIncident: (id: string): Promise<Incident> => 
    fetchWithAuth(`/api/incidents/${id}`),
    
  getPlan: (id: string): Promise<RecoveryPlan> => 
    fetchWithAuth(`/api/incidents/${id}/plan`),
    
  approvePlan: (id: string): Promise<{status: string, message: string}> => 
    fetchWithAuth(`/api/incidents/${id}/plan/approve`, { method: 'POST' }),
    
  rejectPlan: (id: string): Promise<{status: string, message: string}> => 
    fetchWithAuth(`/api/incidents/${id}/plan/reject`, { method: 'POST' }),
    
  getRuns: (skip = 0, limit = 50): Promise<PaginatedResponse<Run>> => 
    fetchWithAuth(`/api/runs?skip=${skip}&limit=${limit}`),
    
  getRun: (runId: string): Promise<Run> => 
    fetchWithAuth(`/api/runs/${runId}`),
    
  getRunTimeline: (runId: string): Promise<TimelineEntry[]> => 
    fetchWithAuth(`/api/runs/${runId}/timeline`),
    
  resumeRun: (runId: string): Promise<{status: string, message: string}> => 
    fetchWithAuth(`/api/runs/${runId}/resume`, { method: 'POST' }),

  downloadAuditExport: async (params: { format: 'json' | 'csv'; fromDate?: string; toDate?: string; agentId?: string; failureType?: string }) => {
    const key = getApiKey();
    const query = new URLSearchParams();
    query.set("format", params.format);
    if (params.fromDate) query.set("from_date", params.fromDate);
    if (params.toDate) query.set("to_date", params.toDate);
    if (params.agentId) query.set("agent_id", params.agentId);
    if (params.failureType) query.set("failure_type", params.failureType);

    const headers = new Headers();
    if (key) headers.set("X-API-Key", key);

    const response = await fetch(`/api/audit/export?${query.toString()}`, { headers });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new ApiError(response.status, err.detail || response.statusText);
    }

    if (params.format === "csv") {
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `cortexheal_audit_export_${new Date().toISOString().split('T')[0]}.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } else {
      const json = await response.json();
      const blob = new Blob([JSON.stringify(json, null, 2)], { type: "application/json" });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `cortexheal_audit_export_${new Date().toISOString().split('T')[0]}.json`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    }
  }
};
