import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../api";
import { Key, Plus, Trash2, CheckCircle2, Copy } from "lucide-react";

import { Badge, LoadingState, ErrorState } from "../components/ui";

export function ApiKeysView() {
  const queryClient = useQueryClient();
  const role = sessionStorage.getItem("cortexheal_role") as any;
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState("");
  const [newRole, setNewRole] = useState("VIEWER");
  const [newlyCreatedKey, setNewlyCreatedKey] = useState<string | null>(null);

  const { data: keys, isLoading, error } = useQuery({
    queryKey: ["apiKeys"],
    queryFn: () => api.getKeys(),
    enabled: role === "ADMIN",
  });

  const createMutation = useMutation({
    mutationFn: (data: { name: string; role: string }) => api.createKey(data.name, data.role),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["apiKeys"] });
      setNewlyCreatedKey(data.raw_key);
      setShowCreate(false);
      setNewName("");
      setNewRole("VIEWER");
    }
  });

  const revokeMutation = useMutation({
    mutationFn: (keyId: string) => api.revokeKey(keyId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["apiKeys"] });
    }
  });

  const handleCopy = () => {
    if (newlyCreatedKey) {
      navigator.clipboard.writeText(newlyCreatedKey);
      alert("API Key copied to clipboard");
    }
  };

  if (role !== "ADMIN") {
    return (
      <div className="p-8 max-w-5xl mx-auto flex flex-col items-center justify-center text-center space-y-4">
        <Key className="w-12 h-12 text-slate-500" />
        <h2 className="text-xl font-bold text-slate-300">Access Denied</h2>
        <p className="text-slate-500">Only ADMIN users can manage API keys.</p>
      </div>
    );
  }

  if (isLoading) return <LoadingState message="Loading API keys..." />;
  if (error) return <ErrorState title="Failed to load API keys" error={error} />;

  return (
    <div className="p-8 max-w-5xl mx-auto space-y-6">
      <div className="flex items-center justify-between border-b border-border pb-4">
        <div className="flex items-center gap-3">
          <Key className="w-6 h-6 text-accent" />
          <h1 className="text-2xl font-bold text-white tracking-wide">API Keys</h1>
        </div>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="flex items-center gap-2 bg-accent text-white px-4 py-2 text-sm font-medium hover:bg-blue-600 transition-colors"
        >
          <Plus className="w-4 h-4" />
          Create New Key
        </button>
      </div>

      {newlyCreatedKey && (
        <div className="bg-status-green/10 border border-status-green/30 p-6 shadow-lg mb-6">
          <div className="flex items-start gap-3">
            <CheckCircle2 className="w-6 h-6 text-status-green shrink-0 mt-0.5" />
            <div className="space-y-3 flex-1">
              <h3 className="font-bold text-status-green text-lg">Key Created Successfully</h3>
              <p className="text-sm text-slate-300">
                Please copy this key now. You will not be able to see it again.
              </p>
              <div className="flex items-center gap-2 mt-4">
                <code className="flex-1 bg-black/40 border border-status-green/20 p-3 font-mono text-sm text-green-100 break-all">
                  {newlyCreatedKey}
                </code>
                <button
                  onClick={handleCopy}
                  className="bg-surface hover:bg-border border border-border p-3 text-slate-300 transition-colors"
                  title="Copy to clipboard"
                >
                  <Copy className="w-5 h-5" />
                </button>
              </div>
              <button
                onClick={() => setNewlyCreatedKey(null)}
                className="text-sm text-slate-400 hover:text-white mt-2 block"
              >
                I have copied this key
              </button>
            </div>
          </div>
        </div>
      )}

      {showCreate && !newlyCreatedKey && (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (newName.trim()) {
              createMutation.mutate({ name: newName.trim(), role: newRole });
            }
          }}
          className="bg-surface border border-border p-6 shadow-lg"
        >
          <h2 className="text-lg font-semibold text-white mb-4">Create New API Key</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            <div>
              <label className="block text-sm text-slate-400 mb-2">Key Name</label>
              <input
                type="text"
                required
                placeholder="e.g., ci-runner, developer-macbook"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                className="w-full bg-background border border-border px-3 py-2 text-white focus:outline-none focus:border-accent"
              />
            </div>
            <div>
              <label className="block text-sm text-slate-400 mb-2">Role</label>
              <select
                value={newRole}
                onChange={(e) => setNewRole(e.target.value)}
                className="w-full bg-background border border-border px-3 py-2 text-white focus:outline-none focus:border-accent"
              >
                <option value="VIEWER">VIEWER (Read-only)</option>
                <option value="OPERATOR">OPERATOR (Can approve/reject plans)</option>
                <option value="ADMIN">ADMIN (Full access)</option>
              </select>
            </div>
          </div>
          <div className="flex justify-end gap-3">
            <button
              type="button"
              onClick={() => setShowCreate(false)}
              className="px-4 py-2 text-sm text-slate-400 hover:text-white transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={createMutation.isPending || !newName.trim()}
              className="bg-accent text-white px-4 py-2 text-sm font-medium hover:bg-blue-600 transition-colors disabled:opacity-50"
            >
              {createMutation.isPending ? "Generating..." : "Generate Key"}
            </button>
          </div>
        </form>
      )}

      <div className="bg-surface border border-border">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-border bg-black/20">
              <th className="p-4 text-xs font-bold uppercase tracking-wider text-slate-500">Name</th>
              <th className="p-4 text-xs font-bold uppercase tracking-wider text-slate-500">Prefix</th>
              <th className="p-4 text-xs font-bold uppercase tracking-wider text-slate-500">Role</th>
              <th className="p-4 text-xs font-bold uppercase tracking-wider text-slate-500">Created</th>
              <th className="p-4 text-xs font-bold uppercase tracking-wider text-slate-500">Status</th>
              <th className="p-4 text-xs font-bold uppercase tracking-wider text-slate-500 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {keys?.map((k) => (
              <tr key={k.key_id} className="hover:bg-black/10 transition-colors">
                <td className="p-4">
                  <div className="font-medium text-slate-200">{k.name}</div>
                  <div className="text-xs text-slate-500 font-mono mt-1">ID: {k.key_id.split("-")[0]}</div>
                </td>
                <td className="p-4 font-mono text-sm text-slate-400">{k.key_prefix}</td>
                <td className="p-4">
                  <Badge variant={
                    k.role === 'ADMIN' ? 'red' : 
                    k.role === 'OPERATOR' ? 'amber' : 'neutral'
                  }>{k.role}</Badge>
                </td>
                <td className="p-4 text-sm text-slate-400">
                  {new Date(k.created_at).toLocaleDateString()}
                </td>
                <td className="p-4">
                  {k.revoked_at ? (
                    <Badge variant="red">REVOKED</Badge>
                  ) : (
                    <Badge variant="green">ACTIVE</Badge>
                  )}
                </td>
                <td className="p-4 text-right">
                  {!k.revoked_at && (
                    <button
                      onClick={() => {
                        if (confirm(`Are you sure you want to revoke key "${k.name}"? This action cannot be undone.`)) {
                          revokeMutation.mutate(k.key_id);
                        }
                      }}
                      disabled={revokeMutation.isPending}
                      className="text-status-red hover:text-red-400 transition-colors p-2 disabled:opacity-50"
                      title="Revoke Key"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  )}
                </td>
              </tr>
            ))}
            {(!keys || keys.length === 0) && (
              <tr>
                <td colSpan={6} className="p-8 text-center text-slate-500">
                  No API keys found.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
