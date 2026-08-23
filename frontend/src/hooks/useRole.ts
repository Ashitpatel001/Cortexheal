import { useState, useCallback } from "react";
import { useAuth } from "../components/AuthGate";

export function useRole() {
  const [role, setRole] = useState<'UNKNOWN' | 'VIEWER'>(
    (sessionStorage.getItem('cortexheal_role') as 'VIEWER') || 'UNKNOWN'
  );
  const { logout } = useAuth();

  const handleApiError = useCallback((error: unknown) => {
    const err = error as { status?: number; [key: string]: unknown };
    if (err?.status === 401) {
      logout();
    } else if (err?.status === 403) {
      sessionStorage.setItem('cortexheal_role', 'VIEWER');
      setRole('VIEWER');
    }
  }, [logout]);

  return { role, handleApiError };
}
