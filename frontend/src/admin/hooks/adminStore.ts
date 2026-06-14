import type { Agent } from '../types';
import { adminApi } from '../api';

// ── Module-level singleton: survives component unmounts / tab switches ──
// Timer stored on window so hot-reload doesn't spawn multiple intervals
const W = window as any;

let _agents: Agent[]         = W.__adminAgents  ?? [];
let _loading                 = W.__adminLoading ?? true;
let _error: string | null    = W.__adminError   ?? null;
let _lastFetch               = W.__adminLastFetch ?? 0;
let _fetchInFlight           = false;
const _listeners             = new Set<() => void>();

function notify() { _listeners.forEach(fn => fn()); }

async function fetchAgents(force = false) {
  if (_fetchInFlight) return;
  if (!force && Date.now() - _lastFetch < 5000) return;
  _fetchInFlight = true;
  try {
    const data  = await adminApi.listAgents();
    _agents     = data.agents ?? [];
    _error      = null;
    _lastFetch  = Date.now();
    W.__adminAgents    = _agents;
    W.__adminError     = _error;
    W.__adminLastFetch = _lastFetch;
    W.__adminLoading   = false;
  } catch (e: any) {
    _error = e.message;
    W.__adminError = _error;
  } finally {
    _loading       = false;
    W.__adminLoading = false;
    _fetchInFlight = false;
    notify();
  }
}

function startPolling() {
  if (W.__adminPollTimer) return;   // survive hot-reload: only one timer ever
  fetchAgents(true);
  W.__adminPollTimer = setInterval(() => fetchAgents(), 10000);
}

export async function updateAgentInStore(id: string, patch: Parameters<typeof adminApi.updateAgent>[1]) {
  _agents = _agents.map(a =>
    a.id === id ? { ...a, config: { ...a.config, ...patch } } : a
  );
  W.__adminAgents = _agents;
  notify();
  await adminApi.updateAgent(id, patch);
}

export function getSnapshot() {
  return { agents: _agents, loading: _loading, error: _error };
}

export function subscribe(fn: () => void) {
  _listeners.add(fn);
  startPolling();                               // ensure polling is running
  return () => _listeners.delete(fn);
}

export function forceRefresh() { fetchAgents(true); }
