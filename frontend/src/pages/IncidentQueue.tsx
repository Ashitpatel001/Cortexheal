import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api";
import { IncidentRow } from "../components/IncidentRow";
import { LoadingState, ErrorState, EmptyState } from "../components/ui";
import { ExportAuditModal } from "../components/ExportAuditModal";
import { ShieldCheck, ChevronLeft, ChevronRight, Download } from "lucide-react";

export function IncidentQueue() {
  const [skip, setSkip] = useState(0);
  const [isExportOpen, setIsExportOpen] = useState(false);
  const limit = 50;

  const { data, isLoading, error } = useQuery({
    queryKey: ["incidents", skip, limit],
    queryFn: () => api.getIncidents(skip, limit),
    refetchOnWindowFocus: false
  });

  if (isLoading) return <LoadingState message="Loading incidents..." />;
  if (error) return <ErrorState title="Failed to load incidents" error={error} />;

  const incidents = data?.data || [];
  const total = data?.total || 0;
  
  // Open items first, then by newest
  const sorted = [...incidents].sort((a, b) => {
    if (a.status === "OPEN" && b.status !== "OPEN") return -1;
    if (a.status !== "OPEN" && b.status === "OPEN") return 1;
    return new Date(b.triggered_at).getTime() - new Date(a.triggered_at).getTime();
  });

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white tracking-wide">Incident Queue</h1>
        <div className="flex items-center gap-4">
          <button
            onClick={() => setIsExportOpen(true)}
            className="flex items-center gap-2 px-3 py-1.5 border border-border bg-surface hover:bg-border/60 text-slate-300 hover:text-white text-xs font-medium transition-colors"
          >
            <Download className="w-4 h-4 text-accent" />
            Export Compliance Log
          </button>
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

      {sorted.length === 0 ? (
        <EmptyState 
          title="No active incidents" 
          description="All systems are nominal. Agents are running within safety bounds."
          icon={ShieldCheck} 
        />
      ) : (
        <div className="flex flex-col gap-2">
          {sorted.map(incident => (
            <IncidentRow key={incident.incident_id} incident={incident} />
          ))}
        </div>
      )}

      <ExportAuditModal
        isOpen={isExportOpen}
        onClose={() => setIsExportOpen(false)}
      />
    </div>
  );
}
