import { useState } from "react";
import type { ReactNode } from "react";
import { getApiKey, setApiKey } from "../api";
import { useQueryClient } from "@tanstack/react-query";
import { KeyRound, PlayCircle } from "lucide-react";

export function AuthGate({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  
  // Check URL for auto-login token (e.g. embedded public demo)
  const urlParams = new URLSearchParams(window.location.search);
  const urlToken = urlParams.get('token');
  
  const [key, setKey] = useState<string | null>(urlToken || getApiKey());
  const [input, setInput] = useState("");

  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");

  // If URL token is provided, set it in session storage immediately
  if (urlToken && !getApiKey()) {
    setApiKey(urlToken);
    // Note: We bypass the /api/whoami check here for seamless iframe loading.
    // The backend will enforce role restrictions on subsequent API calls.
    sessionStorage.setItem("cortexheal_role", "VIEWER");
  }

  const handleDemoLogin = () => {
    const demoKey = "ctx_viewer_public_demo_key_12345";
    setInput(demoKey);
    // Auto-submit immediately
    executeLogin(demoKey);
  };

  const executeLogin = async (token: string) => {
    if (!token) return;
    
    setLoading(true);
    setErrorMsg("");
    
    try {
      const res = await fetch('/api/whoami', { headers: { 'X-API-Key': token } });
      if (!res.ok) throw new Error("Invalid API Key");
      
      const { role } = await res.json();
      sessionStorage.setItem("cortexheal_role", role);
      setApiKey(token);
      setKey(token);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setErrorMsg(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    executeLogin(input.trim());
  };

  const handleLogout = () => {
    sessionStorage.removeItem("cortexheal_api_key");
    sessionStorage.removeItem("cortexheal_role");
    setKey(null);
    queryClient.clear();
  };

  if (!key) {
    return (
      <div className="min-h-screen bg-background flex flex-col items-center justify-center p-4">
        <div className="max-w-md w-full bg-surface border border-border p-8 text-slate-200 shadow-xl mb-4">
          <div className="flex items-center gap-3 mb-6">
            <KeyRound className="w-8 h-8 text-accent" />
            <h1 className="text-2xl font-sans font-semibold text-white">CortexHeal Ops</h1>
          </div>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="apiKey" className="block text-sm font-medium mb-1">
                API Key
              </label>
              <input
                id="apiKey"
                type="password"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                className="w-full bg-background border border-border px-3 py-2 text-white font-mono focus:outline-none focus:border-accent"
                placeholder="dev-operator-key"
                autoFocus
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-accent text-white font-medium py-2 px-4 hover:bg-blue-600 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {loading ? 'Connecting...' : 'Connect'}
            </button>
            {errorMsg && (
              <div className="text-status-red text-sm font-mono mt-2 p-2 bg-status-red/10 border border-status-red/20">
                {errorMsg}
              </div>
            )}
          </form>
        </div>
        
        {/* Public Demo Entry Point */}
        <div className="max-w-md w-full text-center">
          <p className="text-sm text-slate-400 mb-2">Want to see CortexHeal in action?</p>
          <button 
            onClick={handleDemoLogin}
            disabled={loading}
            className="text-accent hover:text-white transition-colors text-sm font-medium flex items-center justify-center gap-2 mx-auto"
          >
            <PlayCircle className="w-4 h-4" />
            View Live Public Demo
          </button>
        </div>
      </div>
    );
  }

  // To allow child components to logout if 401 is hit
  return <AuthContext.Provider value={{ logout: handleLogout }}>{children}</AuthContext.Provider>;
}

import { createContext, useContext } from 'react';
export const AuthContext = createContext({ logout: () => {} });
export const useAuth = () => useContext(AuthContext);
