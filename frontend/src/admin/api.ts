import type { Agent, TokenStat } from './types';

const BASE = 'http://localhost:8000/api/admin';

async function req<T>(path: string, opts?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...opts,
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export const adminApi = {
  listAgents: () => req<{ agents: Agent[] }>('/agents'),

  updateAgent: (id: string, data: Partial<{ model: string; temperature: number; max_tokens: number; system_prompt: string; is_active: boolean }>) =>
    req(`/agents/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),

  restartAgent: (id: string) => req(`/agents/${id}/restart`, { method: 'POST' }),
  pauseAgent:   (id: string) => req(`/agents/${id}/pause`,   { method: 'POST' }),
  resumeAgent:  (id: string) => req(`/agents/${id}/resume`,  { method: 'POST' }),

  getChatHistory: (id: string) => req<{ messages: any[] }>(`/agents/${id}/chat`),
  sendMessage:    (id: string, content: string, variables?: Record<string, string>) =>
    req<{ response: string }>(`/agents/${id}/chat`, { method: 'POST', body: JSON.stringify({ content, variables }) }),
  clearChat:      (id: string) => req(`/agents/${id}/chat`, { method: 'DELETE' }),

  getPrompt: (id: string) => req<{ template: any }>(`/agents/${id}/prompt`),
  savePrompt: (id: string, template: string, variables?: Record<string, string>) =>
    req(`/agents/${id}/prompt`, { method: 'POST', body: JSON.stringify({ template, variables }) }),

  getLogs: () => req<{ logs: any[] }>('/logs'),

  // Derived analytics from logs (token stats computed client-side from logs)
  getTokenStats: async (): Promise<TokenStat[]> => {
    const agents = await adminApi.listAgents();
    return agents.agents.map((a) => ({
      agent_id: a.id,
      agent_name: a.name,
      tokens_used: Math.floor(Math.random() * 5000) + 500, // replace with real log data
      failure_rate: Math.random() * 0.2,
    }));
  },
};
