/**
 * ADMIN DASHBOARD - Real-Time Multi-Agent Control Panel
 * 
 * Features:
 * - Live agent monitoring via WebSocket
 * - Hot-swap agent configs
 * - Runtime prompt variable injection
 * - Activity logs streaming
 */

import React, { useEffect, useState } from 'react';

interface AgentConfig {
  agent_id: string;
  name: string;
  model: string;
  temperature: number;
  max_tokens: number;
  system_prompt: string;
}

interface Agent {
  id: string;
  name: string;
  config: AgentConfig;
  status: 'idle' | 'running' | 'paused' | 'error';
  is_active: boolean;
  last_activity: string;
  memory_size: number;
}

interface AgentLog {
  id: string;
  agent_id: string;
  event_type: string;
  details: Record<string, any>;
  timestamp: string;
  user: string;
}

const API_BASE = 'http://localhost:8000/api/admin';
const WS_URL = 'ws://localhost:8000/api/admin/ws/monitor';

export const AdminDashboard: React.FC = () => {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);
  const [logs, setLogs] = useState<AgentLog[]>([]);
  const [ws, setWs] = useState<WebSocket | null>(null);
  const [editMode, setEditMode] = useState(false);
  const [configDraft, setConfigDraft] = useState<Partial<AgentConfig>>({});

  // WebSocket Connection for Real-Time Updates
  useEffect(() => {
    const socket = new WebSocket(WS_URL);

    socket.onopen = () => {
      console.log('🔴 Connected to orchestrator');
    };

    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);

      switch (data.type) {
        case 'initial_state':
          setAgents(data.agents);
          break;

        case 'config_changed':
          // Update specific agent in real-time
          setAgents(prev =>
            prev.map(a =>
              a.id === data.agent_id
                ? { ...a, config: { ...a.config, ...data.data } }
                : a
            )
          );
          // Show toast notification
          console.log(`✅ Agent ${data.agent_id} config updated live`);
          break;

        case 'agent_restarted':
          setAgents(prev =>
            prev.map(a =>
              a.id === data.agent_id
                ? { ...a, status: 'idle', memory_size: 0 }
                : a
            )
          );
          break;

        default:
          console.log('Unknown event:', data);
      }
    };

    socket.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    socket.onclose = () => {
      console.log('WebSocket disconnected. Reconnecting...');
      setTimeout(() => {
        // Reconnect logic
      }, 3000);
    };

    setWs(socket);

    return () => {
      socket.close();
    };
  }, []);

  // Fetch agents initially
  useEffect(() => {
    fetch(`${API_BASE}/agents`)
      .then(res => res.json())
      .then(data => setAgents(data.agents));
  }, []);

  // Fetch logs for selected agent
  useEffect(() => {
    if (selectedAgent) {
      fetch(`${API_BASE}/agents/${selectedAgent.id}/logs?limit=20`)
        .then(res => res.json())
        .then(data => setLogs(data.logs));
    }
  }, [selectedAgent]);

  // Hot-swap agent config (MANAGER'S POWER)
  const updateAgentConfig = async () => {
    if (!selectedAgent) return;

    const res = await fetch(`${API_BASE}/agents/${selectedAgent.id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(configDraft)
    });

    const result = await res.json();
    console.log('Config updated:', result);
    setEditMode(false);
    setConfigDraft({});
  };

  // Restart agent (clear memory)
  const restartAgent = async (agentId: string) => {
    const res = await fetch(`${API_BASE}/agents/${agentId}/restart`, {
      method: 'POST'
    });
    const result = await res.json();
    console.log('Agent restarted:', result);
  };

  // Pause agent
  const pauseAgent = async (agentId: string) => {
    await fetch(`${API_BASE}/agents/${agentId}/pause`, { method: 'POST' });
  };

  // Resume agent
  const resumeAgent = async (agentId: string) => {
    await fetch(`${API_BASE}/agents/${agentId}/resume`, { method: 'POST' });
  };

  return (
    <div style={{ padding: '20px', fontFamily: 'monospace' }}>
      <h1>🔥 Multi-Agent Orchestrator</h1>
      <p style={{ color: ws ? 'green' : 'red' }}>
        {ws ? '🔴 LIVE' : '⚫ Disconnected'}
      </p>

      <div style={{ display: 'flex', gap: '20px' }}>
        {/* Agent List */}
        <div style={{ flex: 1, border: '1px solid #ccc', padding: '10px' }}>
          <h2>Agents ({agents.length})</h2>
          {agents.map(agent => (
            <div
              key={agent.id}
              onClick={() => setSelectedAgent(agent)}
              style={{
                padding: '10px',
                margin: '5px 0',
                background: selectedAgent?.id === agent.id ? '#e0e0e0' : '#f9f9f9',
                cursor: 'pointer',
                border: '1px solid #ddd'
              }}
            >
              <strong>{agent.name}</strong> ({agent.status})
              <br />
              <small>Model: {agent.config.model}</small>
              <br />
              <small>Temp: {agent.config.temperature} | Tokens: {agent.config.max_tokens}</small>
              <br />
              <small style={{ color: agent.is_active ? 'green' : 'red' }}>
                {agent.is_active ? '✅ Active' : '⏸️ Paused'}
              </small>
            </div>
          ))}
        </div>

        {/* Agent Details & Config Editor */}
        {selectedAgent && (
          <div style={{ flex: 2, border: '1px solid #ccc', padding: '10px' }}>
            <h2>{selectedAgent.name}</h2>
            <p><strong>Status:</strong> {selectedAgent.status}</p>
            <p><strong>Memory Size:</strong> {selectedAgent.memory_size}</p>
            <p><strong>Last Activity:</strong> {new Date(selectedAgent.last_activity).toLocaleString()}</p>

            <hr />

            <h3>Configuration</h3>
            {editMode ? (
              <div>
                <label>
                  Temperature:
                  <input
                    type="number"
                    step="0.1"
                    value={configDraft.temperature ?? selectedAgent.config.temperature}
                    onChange={(e) => setConfigDraft({ ...configDraft, temperature: parseFloat(e.target.value) })}
                  />
                </label>
                <br />
                <label>
                  Max Tokens:
                  <input
                    type="number"
                    value={configDraft.max_tokens ?? selectedAgent.config.max_tokens}
                    onChange={(e) => setConfigDraft({ ...configDraft, max_tokens: parseInt(e.target.value) })}
                  />
                </label>
                <br />
                <label>
                  System Prompt:
                  <textarea
                    rows={5}
                    style={{ width: '100%' }}
                    value={configDraft.system_prompt ?? selectedAgent.config.system_prompt}
                    onChange={(e) => setConfigDraft({ ...configDraft, system_prompt: e.target.value })}
                  />
                </label>
                <br />
                <button onClick={updateAgentConfig}>💾 Save (Hot-Swap)</button>
                <button onClick={() => setEditMode(false)}>Cancel</button>
              </div>
            ) : (
              <div>
                <p><strong>Model:</strong> {selectedAgent.config.model}</p>
                <p><strong>Temperature:</strong> {selectedAgent.config.temperature}</p>
                <p><strong>Max Tokens:</strong> {selectedAgent.config.max_tokens}</p>
                <p><strong>System Prompt:</strong></p>
                <pre style={{ background: '#f0f0f0', padding: '10px' }}>
                  {selectedAgent.config.system_prompt || '(empty)'}
                </pre>
                <button onClick={() => { setEditMode(true); setConfigDraft({}); }}>
                  ✏️ Edit Config
                </button>
              </div>
            )}

            <hr />

            <h3>Actions</h3>
            <button onClick={() => restartAgent(selectedAgent.id)}>🔄 Restart</button>
            {selectedAgent.is_active ? (
              <button onClick={() => pauseAgent(selectedAgent.id)}>⏸️ Pause</button>
            ) : (
              <button onClick={() => resumeAgent(selectedAgent.id)}>▶️ Resume</button>
            )}

            <hr />

            <h3>Activity Logs</h3>
            <div style={{ maxHeight: '200px', overflow: 'auto', background: '#f9f9f9', padding: '10px' }}>
              {logs.map(log => (
                <div key={log.id} style={{ marginBottom: '10px', borderBottom: '1px solid #ddd' }}>
                  <strong>{log.event_type}</strong> - {new Date(log.timestamp).toLocaleString()}
                  <br />
                  <small>User: {log.user}</small>
                  <pre style={{ fontSize: '10px' }}>{JSON.stringify(log.details, null, 2)}</pre>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default AdminDashboard;
