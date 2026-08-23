import React, { useState } from "react";
import { Download, X, FileSpreadsheet, FileCode, AlertCircle } from "lucide-react";
import { api } from "../api";

interface ExportAuditModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function ExportAuditModal({ isOpen, onClose }: ExportAuditModalProps) {
  const [format, setFormat] = useState<"csv" | "json">("csv");
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");
  const [agentId, setAgentId] = useState("");
  const [failureType, setFailureType] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleExport = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);
    try {
      await api.downloadAuditExport({
        format,
        fromDate: fromDate || undefined,
        toDate: toDate || undefined,
        agentId: agentId.trim() || undefined,
        failureType: failureType || undefined,
      });
      onClose();
    } catch (err: any) {
      setError(err.message || "Failed to download compliance export");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 animate-in fade-in duration-150">
      <div className="bg-surface border border-border w-full max-w-lg shadow-2xl p-6 relative">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-slate-400 hover:text-white transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-3 mb-5">
          <div className="p-2.5 bg-blue-500/10 border border-blue-500/20 text-accent">
            <Download className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-white tracking-wide">
              Export Compliance & Audit Log
            </h2>
            <p className="text-xs text-slate-400">
              Download deterministic safety telemetry and incident verification history.
            </p>
          </div>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-500/10 border border-red-500/30 text-status-red text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleExport} className="space-y-4">
          <div>
            <label className="block text-xs font-mono uppercase text-slate-400 mb-2">
              Export Format
            </label>
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => setFormat("csv")}
                className={`flex items-center justify-center gap-2 p-3 border text-sm font-medium transition-colors ${
                  format === "csv"
                    ? "border-accent bg-accent/10 text-white shadow-sm"
                    : "border-border bg-background text-slate-400 hover:text-slate-200"
                }`}
              >
                <FileSpreadsheet className="w-4 h-4" />
                CSV Spreadsheet
              </button>
              <button
                type="button"
                onClick={() => setFormat("json")}
                className={`flex items-center justify-center gap-2 p-3 border text-sm font-medium transition-colors ${
                  format === "json"
                    ? "border-accent bg-accent/10 text-white shadow-sm"
                    : "border-border bg-background text-slate-400 hover:text-slate-200"
                }`}
              >
                <FileCode className="w-4 h-4" />
                Raw JSON Schema
              </button>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-mono uppercase text-slate-400 mb-1">
                From Date (Optional)
              </label>
              <input
                type="datetime-local"
                value={fromDate}
                onChange={(e) => setFromDate(e.target.value)}
                className="w-full bg-background border border-border px-3 py-2 text-xs text-white focus:outline-none focus:border-accent"
              />
            </div>
            <div>
              <label className="block text-xs font-mono uppercase text-slate-400 mb-1">
                To Date (Optional)
              </label>
              <input
                type="datetime-local"
                value={toDate}
                onChange={(e) => setToDate(e.target.value)}
                className="w-full bg-background border border-border px-3 py-2 text-xs text-white focus:outline-none focus:border-accent"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-mono uppercase text-slate-400 mb-1">
                Failure Type
              </label>
              <select
                value={failureType}
                onChange={(e) => setFailureType(e.target.value)}
                className="w-full bg-background border border-border px-3 py-2 text-xs text-white focus:outline-none focus:border-accent"
              >
                <option value="">All Failure Types</option>
                <option value="STUCK_LOOP">STUCK_LOOP</option>
                <option value="BUDGET_EXCEEDED">BUDGET_EXCEEDED</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-mono uppercase text-slate-400 mb-1">
                Agent ID Filter
              </label>
              <input
                type="text"
                placeholder="e.g. support_agent_1"
                value={agentId}
                onChange={(e) => setAgentId(e.target.value)}
                className="w-full bg-background border border-border px-3 py-2 text-xs text-white focus:outline-none focus:border-accent"
              />
            </div>
          </div>

          <div className="pt-2 flex items-center justify-end gap-3 border-t border-border mt-4">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border border-border text-xs text-slate-400 hover:text-white transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading}
              className="px-4 py-2 bg-accent text-white text-xs font-semibold hover:bg-blue-600 transition-colors flex items-center gap-2 disabled:opacity-50"
            >
              <Download className="w-3.5 h-3.5" />
              {isLoading ? "Generating Export..." : `Download ${format.toUpperCase()}`}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
