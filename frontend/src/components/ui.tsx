import type { ReactNode } from "react";
import { cn } from "../utils";
import { AlertCircle, Loader2 } from "lucide-react";

export function Badge({ children, variant = "neutral", className }: { children: ReactNode, variant?: "neutral" | "red" | "amber" | "green" | "accent", className?: string }) {
  const variants = {
    neutral: "bg-border text-slate-300",
    red: "bg-status-red/10 text-status-red border border-status-red/20",
    amber: "bg-status-amber/10 text-status-amber border border-status-amber/20",
    green: "bg-status-green/10 text-status-green border border-status-green/20",
    accent: "bg-accent/10 text-accent border border-accent/20"
  };
  return (
    <span className={cn("inline-flex items-center px-2 py-0.5 text-xs font-mono font-medium uppercase", variants[variant], className)}>
      {children}
    </span>
  );
}

export function LoadingState({ message = "Loading..." }: { message?: string }) {
  return (
    <div className="flex flex-col items-center justify-center p-12 text-slate-500">
      <Loader2 className="w-8 h-8 animate-spin mb-4 text-accent" />
      <p className="font-sans text-sm">{message}</p>
    </div>
  );
}

export function ErrorState({ title, error }: { title: string, error?: any }) {
  return (
    <div className="p-6 border border-status-red/30 bg-status-red/5 m-6">
      <div className="flex items-center gap-3 mb-2 text-status-red">
        <AlertCircle className="w-5 h-5" />
        <h3 className="font-semibold font-sans">{title}</h3>
      </div>
      {error && (
        <p className="text-sm font-mono text-status-red/80">
          {error.message || String(error)}
        </p>
      )}
    </div>
  );
}

export function EmptyState({ title, description, icon: Icon }: { title: string, description: string, icon?: any }) {
  return (
    <div className="flex flex-col items-center justify-center p-16 text-center border border-dashed border-border m-6 bg-surface/30">
      {Icon && <Icon className="w-12 h-12 text-slate-500 mb-4" />}
      <h3 className="text-lg font-semibold text-slate-300 mb-2">{title}</h3>
      <p className="text-sm text-slate-500 max-w-md">{description}</p>
    </div>
  );
}
