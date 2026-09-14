import { useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { Activity, ShieldAlert, LogOut, Download, Server, KeyRound } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { useSSE } from "../sse";
import { useAuth } from "./AuthGate";
import { ExportAuditModal } from "./ExportAuditModal";
import { cn } from "../utils";

export function Layout() {
  useSSE();
  const { logout } = useAuth();
  const [isExportOpen, setIsExportOpen] = useState(false);
  const { data: sseStatus = "disconnected" } = useQuery<string>({ queryKey: ["sse_status"], queryFn: () => "disconnected", staleTime: Infinity, refetchOnMount: false, refetchOnWindowFocus: false, refetchOnReconnect: false });

  return (
    <div className="flex h-screen bg-background text-slate-300 font-sans">
      <aside className="w-64 border-r border-border bg-surface flex flex-col">
        <div className="p-4 border-b border-border flex items-center gap-3">
          <Activity className="w-6 h-6 text-accent" />
          <span className="text-lg font-bold text-white tracking-wide">CortexHeal</span>
        </div>
        
        <nav className="flex-1 p-4 space-y-2">
          <NavLink
            to="/"
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 px-3 py-2 transition-colors",
                isActive ? "bg-border text-white" : "text-slate-400 hover:text-slate-200 hover:bg-border/50"
              )
            }
          >
            <ShieldAlert className="w-5 h-5" />
            Incidents
          </NavLink>
          <NavLink
            to="/runs"
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 px-3 py-2 rounded-md transition-colors",
                isActive ? "bg-accent/10 text-accent font-medium" : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/50"
              )
            }
          >
            <Activity className="w-5 h-5" />
            Executions
          </NavLink>
          <NavLink
            to="/fleet"
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 px-3 py-2 rounded-md transition-colors",
                isActive ? "bg-accent/10 text-accent font-medium" : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/50"
              )
            }
          >
            <Server className="w-5 h-5" />
            Fleet Status
          </NavLink>
          {sessionStorage.getItem("cortexheal_role") === "ADMIN" && (
            <NavLink
              to="/keys"
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 px-3 py-2 rounded-md transition-colors",
                  isActive ? "bg-accent/10 text-accent font-medium" : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/50"
                )
              }
            >
              <KeyRound className="w-5 h-5" />
              API Keys
            </NavLink>
          )}

          <button
            onClick={() => setIsExportOpen(true)}
            className="flex items-center gap-3 px-3 py-2 w-full text-slate-400 hover:text-slate-200 hover:bg-border/50 transition-colors text-left"
          >
            <Download className="w-5 h-5 text-accent" />
            Export Audit Log
          </button>
        </nav>

        <div className="p-4 border-t border-border space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-sm text-slate-400">Stream</span>
            <div className="flex items-center gap-2">
              <span className="text-xs uppercase tracking-wider font-mono text-slate-500">
                {sseStatus}
              </span>
              <div
                className={cn(
                  "w-2.5 h-2.5 rounded-full",
                  sseStatus === "connected" && "bg-accent shadow-[0_0_8px_rgba(59,130,246,0.6)]",
                  sseStatus === "reconnecting" && "bg-status-amber animate-pulse",
                  sseStatus === "disconnected" && "bg-status-red"
                )}
              />
            </div>
          </div>
          <button 
            onClick={logout}
            className="flex items-center gap-2 text-sm text-slate-500 hover:text-slate-300 transition-colors w-full"
          >
            <LogOut className="w-4 h-4" />
            Disconnect
          </button>
        </div>
      </aside>

      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>

      <ExportAuditModal
        isOpen={isExportOpen}
        onClose={() => setIsExportOpen(false)}
      />
    </div>
  );
}
