import { useState, useEffect, useCallback } from 'react';
import { subscribe, getSnapshot, updateAgentInStore, forceRefresh } from './adminStore';
import type { adminApi } from '../api';

export function useAdminData() {
  const [snap, setSnap] = useState(getSnapshot);

  useEffect(() => {
    const unsub = subscribe(() => setSnap({ ...getSnapshot() }));
    return () => { unsub(); };
  }, []);

  const updateAgent = useCallback(
    (id: string, patch: Parameters<typeof adminApi.updateAgent>[1]) =>
      updateAgentInStore(id, patch),
    []
  );

  return {
    agents:       snap.agents,
    loading:      snap.loading,
    error:        snap.error,
    refresh:      forceRefresh,
    updateAgent,
  };
}
