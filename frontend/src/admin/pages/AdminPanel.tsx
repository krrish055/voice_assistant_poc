import React, { useState } from 'react';
import { Settings, LayoutDashboard, MessageSquare, BarChart2, RefreshCw, ArrowLeft } from 'lucide-react';
import { useAdminData } from '../hooks/useAdminData';
import { AgentCard }    from '../components/AgentCard';
import { PromptEditor } from '../components/PromptEditor';
import { Sandbox }      from '../components/Sandbox';
import { Analytics }    from '../components/Analytics';
import { Toaster }      from '../components/Toaster';
import type { Agent }   from '../types';

type Tab = 'dashboard' | 'prompt' | 'sandbox' | 'analytics';

const TABS: { id: Tab; label: string; icon: React.ReactNode }[] = [
  { id: 'dashboard',  label: 'Dashboard',    icon: <LayoutDashboard size={15} /> },
  { id: 'prompt',     label: 'Prompt Editor',icon: <Settings        size={15} /> },
  { id: 'sandbox',    label: 'Sandbox',      icon: <MessageSquare   size={15} /> },
  { id: 'analytics',  label: 'Analytics',    icon: <BarChart2       size={15} /> },
];

interface Props { onBack?: () => void }

const AdminPanel: React.FC<Props> = ({ onBack }) => {
  const { agents, loading, error, refresh, updateAgent } = useAdminData();
  const [tab, setTab]               = useState<Tab>('dashboard');
  const [selectedAgent, setSelected] = useState<Agent | null>(null);

  const activeAgent = selectedAgent ?? agents[0] ?? null;

  return (
    <div style={{ minHeight: '100vh', background: '#0B132B', color: '#e2e8f0', fontFamily: 'Inter, sans-serif' }}>
      <Toaster />
      {/* Top bar */}
      <div style={{ borderBottom: '1px solid rgba(148,163,184,0.1)', padding: '0 24px', display: 'flex', alignItems: 'center', gap: 16, height: 56 }}>
        {onBack && (
          <button onClick={onBack} style={{ background: 'none', border: 'none', color: '#94A3B8', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6, fontSize: 13 }}>
            <ArrowLeft size={15} /> Back
          </button>
        )}
        <span style={{ fontWeight: 700, fontSize: 16, color: '#e2e8f0', letterSpacing: 0.5 }}>Admin Panel</span>
        <span style={{ fontSize: 12, color: '#94A3B8', background: 'rgba(148,163,184,0.1)', padding: '2px 10px', borderRadius: 20 }}>
          {agents.length} agents
        </span>
        <div style={{ flex: 1 }} />
        <button onClick={refresh} title="Refresh" style={{ background: 'none', border: 'none', color: '#94A3B8', cursor: 'pointer', display: 'flex' }}>
          <RefreshCw size={15} />
        </button>
      </div>

      <div style={{ display: 'flex', height: 'calc(100vh - 56px)' }}>
        {/* Sidebar */}
        <div style={{ width: 200, borderRight: '1px solid rgba(148,163,184,0.1)', padding: '16px 12px', display: 'flex', flexDirection: 'column', gap: 4, flexShrink: 0 }}>
          {TABS.map(t => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              style={{
                display: 'flex', alignItems: 'center', gap: 10,
                padding: '9px 12px', borderRadius: 8, border: 'none', cursor: 'pointer', fontSize: 13, textAlign: 'left',
                background: tab === t.id ? 'rgba(72,202,228,0.1)'  : 'transparent',
                color:      tab === t.id ? '#48CAE4'               : '#94A3B8',
                fontWeight: tab === t.id ? 600                     : 400,
              }}
            >
              {t.icon} {t.label}
            </button>
          ))}
        </div>

        {/* Main content */}
        <div style={{ flex: 1, overflow: 'auto', padding: 24 }}>
          {loading && <div style={{ color: '#94A3B8' }}>Loading agents…</div>}
          {error   && <div style={{ color: '#EF4444', fontSize: 13 }}>Error: {error}</div>}

          {!loading && !error && (
            <>
              {tab === 'dashboard' && (
                <div>
                  <h2 style={headingStyle}>Multi-Agent Control</h2>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 16 }}>
                    {agents.map(a => (
                      <AgentCard
                        key={a.id} agent={a}
                        onUpdate={updateAgent}
                        onSelect={agent => { setSelected(agent); setTab('prompt'); }}
                        selected={activeAgent?.id === a.id}
                      />
                    ))}
                  </div>
                </div>
              )}

              {tab === 'prompt' && (
                <div>
                  <h2 style={headingStyle}>Prompt Template Editor</h2>
                  <AgentSelector agents={agents} selected={activeAgent} onSelect={setSelected} />
                  {activeAgent
                    ? <div style={cardStyle}><PromptEditor agent={activeAgent} /></div>
                    : <Empty label="Select an agent to edit its prompt" />
                  }
                </div>
              )}

              {tab === 'sandbox' && (
                <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                  <h2 style={headingStyle}>Testing Sandbox</h2>
                  <AgentSelector agents={agents} selected={activeAgent} onSelect={setSelected} />
                  {activeAgent ? (
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, flex: 1 }}>
                      {/* Left: config summary */}
                      <div style={cardStyle}>
                        <p style={{ fontSize: 13, color: '#94A3B8', marginBottom: 14 }}>Current Configuration</p>
                        <ConfigRow label="Model"       value={activeAgent.config.model} />
                        <ConfigRow label="Temperature" value={activeAgent.config.temperature.toFixed(2)} />
                        <ConfigRow label="Max Tokens"  value={String(activeAgent.config.max_tokens)} />
                        <div style={{ marginTop: 16 }}>
                          <p style={{ fontSize: 12, color: '#94A3B8', marginBottom: 8 }}>System Prompt</p>
                          <div style={{ background: 'rgba(15,23,42,0.6)', borderRadius: 8, padding: 12, fontSize: 12, color: '#cbd5e1', lineHeight: 1.7, maxHeight: 200, overflowY: 'auto', whiteSpace: 'pre-wrap' }}>
                            {activeAgent.config.system_prompt || <span style={{ color: '#475569' }}>No system prompt set</span>}
                          </div>
                        </div>
                      </div>
                      {/* Right: chat */}
                      <div style={{ ...cardStyle, display: 'flex', flexDirection: 'column', minHeight: 500 }}>
                        <Sandbox agent={activeAgent} />
                      </div>
                    </div>
                  ) : <Empty label="Select an agent to start testing" />}
                </div>
              )}

              {tab === 'analytics' && (
                <div>
                  <h2 style={headingStyle}>System Analytics</h2>
                  <div style={cardStyle}><Analytics /></div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
};

const AgentSelector: React.FC<{ agents: Agent[]; selected: Agent | null; onSelect: (a: Agent) => void }> = ({ agents, selected, onSelect }) => (
  <div style={{ display: 'flex', gap: 8, marginBottom: 16, flexWrap: 'wrap' }}>
    {agents.map(a => (
      <button key={a.id} onClick={() => onSelect(a)} style={{
        padding: '5px 14px', borderRadius: 20, border: '1px solid',
        fontSize: 12, cursor: 'pointer',
        borderColor: selected?.id === a.id ? '#48CAE4' : 'rgba(148,163,184,0.2)',
        background:  selected?.id === a.id ? 'rgba(72,202,228,0.1)' : 'transparent',
        color:       selected?.id === a.id ? '#48CAE4' : '#94A3B8',
      }}>{a.name}</button>
    ))}
  </div>
);

const ConfigRow: React.FC<{ label: string; value: string }> = ({ label, value }) => (
  <div style={{ display: 'flex', justifyContent: 'space-between', padding: '7px 0', borderBottom: '1px solid rgba(148,163,184,0.07)' }}>
    <span style={{ fontSize: 13, color: '#94A3B8' }}>{label}</span>
    <span style={{ fontSize: 13, color: '#e2e8f0', fontWeight: 500 }}>{value}</span>
  </div>
);

const Empty: React.FC<{ label: string }> = ({ label }) => (
  <div style={{ textAlign: 'center', color: '#475569', fontSize: 13, marginTop: 60 }}>{label}</div>
);

const headingStyle: React.CSSProperties = { fontSize: 18, fontWeight: 600, color: '#e2e8f0', marginBottom: 20 };
const cardStyle: React.CSSProperties = { background: 'rgba(28,37,65,0.65)', border: '1px solid rgba(148,163,184,0.1)', borderRadius: 14, padding: 20 };

export default AdminPanel;
