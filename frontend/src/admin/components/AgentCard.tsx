import React, { useState, useEffect } from 'react';
import { Activity, Pause, Play, RotateCcw, ChevronDown } from 'lucide-react';
import type { Agent } from '../types';
import { AVAILABLE_MODELS } from '../types';
import { adminApi } from '../api';
import { toast } from './Toaster';

const STATUS_COLOR: Record<string, string> = {
  idle:    '#94A3B8',
  running: '#10B981',
  paused:  '#F59E0B',
  error:   '#EF4444',
};

interface Props {
  agent: Agent;
  onUpdate: (id: string, patch: any) => Promise<void>;
  onSelect: (agent: Agent) => void;
  selected: boolean;
}

export const AgentCard: React.FC<Props> = ({ agent, onUpdate, onSelect, selected }) => {
  const [saving, setSaving]         = useState(false);
  const [saved, setSaved]           = useState(false);
  const [localTemp, setLocalTemp]   = useState(agent.config.temperature);
  const [localModel, setLocalModel] = useState(agent.config.model);

  // Sync local state if store pushes an update from elsewhere
  useEffect(() => {
    setLocalTemp(agent.config.temperature);
    setLocalModel(agent.config.model);
  }, [agent.config.temperature, agent.config.model]);

  const isDirty = localTemp !== agent.config.temperature || localModel !== agent.config.model;

  const save = async (e: React.MouseEvent) => {
    e.stopPropagation();
    setSaving(true);
    try {
      await onUpdate(agent.id, { temperature: localTemp, model: localModel });
      setSaved(true);
      toast.success(`${agent.name} config saved`);
      setTimeout(() => setSaved(false), 1500);
    } catch (err: any) {
      toast.error(`Save failed: ${err.message}`);
    } finally {
      setSaving(false);
    }
  };

  const handleAction = async (e: React.MouseEvent, action: 'pause' | 'resume' | 'restart') => {
    e.stopPropagation();
    try {
      if (action === 'pause')   await adminApi.pauseAgent(agent.id);
      if (action === 'resume')  await adminApi.resumeAgent(agent.id);
      if (action === 'restart') await adminApi.restartAgent(agent.id);
      toast.success(`${agent.name} ${action}d`);
    } catch (err: any) {
      toast.error(`Action failed: ${err.message}`);
    }
  };

  return (
    <div
      onClick={() => onSelect(agent)}
      style={{
        background: selected ? 'rgba(72,202,228,0.08)' : 'rgba(28,37,65,0.65)',
        border: `1px solid ${selected ? '#48CAE4' : 'rgba(148,163,184,0.15)'}`,
        borderRadius: 12,
        padding: '18px 20px',
        cursor: 'pointer',
        transition: 'all 0.2s ease',
      }}
    >
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{
            width: 8, height: 8, borderRadius: '50%',
            background: STATUS_COLOR[agent.status ?? ''] ?? '#94A3B8',
            boxShadow: `0 0 8px ${STATUS_COLOR[agent.status ?? ''] ?? '#94A3B8'}`,
          }} />
          <span style={{ fontWeight: 600, color: '#e2e8f0', fontSize: 15 }}>{agent.name}</span>
          <span style={{ fontSize: 11, color: '#94A3B8', background: 'rgba(148,163,184,0.1)', padding: '2px 8px', borderRadius: 20 }}>
            {agent.status?.toUpperCase() ?? 'UNKNOWN'}
          </span>
        </div>
        <div style={{ display: 'flex', gap: 6 }} onClick={e => e.stopPropagation()}>
          {agent.status !== 'paused' && agent.status !== undefined
            ? <IconBtn title="Pause"   onClick={e => handleAction(e, 'pause')}   icon={<Pause size={13} />} />
            : <IconBtn title="Resume"  onClick={e => handleAction(e, 'resume')}  icon={<Play  size={13} />} />
          }
          <IconBtn title="Restart" onClick={e => handleAction(e, 'restart')} icon={<RotateCcw size={13} />} />
        </div>
      </div>

      {/* Temperature Slider */}
      <div style={{ marginBottom: 12 }} onClick={e => e.stopPropagation()}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
          <span style={{ fontSize: 12, color: '#94A3B8' }}>Temperature</span>
          <span style={{ fontSize: 12, color: '#48CAE4', fontWeight: 600 }}>{localTemp.toFixed(2)}</span>
        </div>
        <input
          type="range" min={0} max={1.2} step={0.01}
          value={localTemp}
          onChange={e => setLocalTemp(parseFloat(e.target.value))}
          style={{ width: '100%', accentColor: '#48CAE4', cursor: 'pointer' }}
        />
        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 2 }}>
          <span style={{ fontSize: 10, color: '#475569' }}>Precise</span>
          <span style={{ fontSize: 10, color: '#475569' }}>Creative</span>
        </div>
      </div>

      {/* Model Selector */}
      <div style={{ marginBottom: 14 }} onClick={e => e.stopPropagation()}>
        <span style={{ fontSize: 12, color: '#94A3B8', display: 'block', marginBottom: 6 }}>Model</span>
        <div style={{ position: 'relative' }}>
          <select
            value={localModel}
            onChange={e => setLocalModel(e.target.value)}
            style={{
              width: '100%', background: 'rgba(15,23,42,0.8)', color: '#e2e8f0',
              border: '1px solid rgba(148,163,184,0.2)', borderRadius: 8,
              padding: '8px 32px 8px 12px', fontSize: 13, cursor: 'pointer',
              appearance: 'none',
            }}
          >
            {AVAILABLE_MODELS.map(m => <option key={m} value={m}>{m}</option>)}
          </select>
          <ChevronDown size={14} style={{ position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)', color: '#94A3B8', pointerEvents: 'none' }} />
        </div>
      </div>

      {/* Footer */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: '#94A3B8', fontSize: 12 }}>
          <Activity size={12} />
          <span>{agent.metadata?.uptime ?? '—'}</span>
          <span style={{ marginLeft: 8, color: '#475569' }}>
            {agent.metadata?.type ?? ''}
          </span>
        </div>
        {(isDirty || saved) && (
          <button
            onClick={save}
            disabled={saving}
            style={{
              background: saved ? '#10B981' : '#0077B6', color: '#fff', border: 'none',
              borderRadius: 6, padding: '5px 14px', fontSize: 12,
              cursor: saving ? 'not-allowed' : 'pointer', opacity: saving ? 0.6 : 1,
              transition: 'background 0.3s',
            }}
          >
            {saved ? 'Saved ✓' : saving ? 'Saving…' : 'Save'}
          </button>
        )}
      </div>
    </div>
  );
};

const IconBtn: React.FC<{ icon: React.ReactNode; onClick: (e: React.MouseEvent) => void; title: string }> = ({ icon, onClick, title }) => (
  <button
    title={title}
    onClick={onClick}
    style={{
      background: 'rgba(148,163,184,0.1)', border: '1px solid rgba(148,163,184,0.15)',
      borderRadius: 6, padding: '5px 7px', color: '#94A3B8', cursor: 'pointer',
      display: 'flex', alignItems: 'center',
    }}
  >
    {icon}
  </button>
);
