import { useState, useEffect, useCallback } from 'react';
import { getDashboardSummary } from '../services/api';

// Workspace-scoped dashboard summary (KPIs, top files, debt categories).
export function useMetrics() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const refresh = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      setData(await getDashboardSummary());
    } catch (err) {
      setError(err.message || 'Failed to load metrics');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  return { data, loading, error, refresh };
}
