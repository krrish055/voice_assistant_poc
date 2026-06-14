import React, { useState, useEffect } from 'react';
import { BarChart2, AlertTriangle } from 'lucide-react';
import { adminApi } from '../api';
import type { TokenStat } from '../types';

export const Analytics: React.FC = () => {
  const [stats, setStats]     = useState<TokenStat[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    adminApi.getTokenStats().then(s => { setStats(s); setLoading(false); });
  }, []);

  if (loading) return <div style={{ color: '#94A3B8', fontSize: 13 }}>Loading analytics…</div>;

  const maxTokens  = Math.max(...stats.map(s => s.tokens_used), 1);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      {/* Token Usage */}
      <div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
          <BarChart2 size={16} color="#48CAE4" />
          <span style={{ color: '#e2e8f0', fontWeight: 600 }}>Token Consumption per Agent</span>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {stats.map(s => (
            <div key={s.agent_id}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                <span style={{ fontSize: 13, color: '#cbd5e1' }}>{s.agent_name}</span>
                <span style={{ fontSize: 13, color: '#48CAE4', fontWeight: 600 }}>{s.tokens_used.toLocaleString()} tokens</span>
              </div>
              <div style={{ background: 'rgba(148,163,184,0.1)', borderRadius: 6, height: 10, overflow: 'hidden' }}>
                <div style={{
                  height: '100%', borderRadius: 6,
                  width: `${(s.tokens_used / maxTokens) * 100}%`,
                  background: 'linear-gradient(90deg, #0077B6, #48CAE4)',
                  transition: 'width 0.6s ease',
                }} />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Failure Rate */}
      <div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
          <AlertTriangle size={16} color="#F59E0B" />
          <span style={{ color: '#e2e8f0', fontWeight: 600 }}>Failure Rates</span>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: 12 }}>
          {stats.map(s => {
            const pct = (s.failure_rate * 100).toFixed(1);
            const color = s.failure_rate > 0.1 ? '#EF4444' : s.failure_rate > 0.05 ? '#F59E0B' : '#10B981';
            return (
              <div key={s.agent_id} style={{ background: 'rgba(28,37,65,0.65)', border: '1px solid rgba(148,163,184,0.1)', borderRadius: 10, padding: '14px 16px', textAlign: 'center' }}>
                <div style={{ fontSize: 26, fontWeight: 700, color, marginBottom: 4 }}>{pct}%</div>
                <div style={{ fontSize: 12, color: '#94A3B8' }}>{s.agent_name}</div>
                <div style={{ fontSize: 11, color, marginTop: 4 }}>{s.failure_rate > 0.1 ? '⚠ High' : s.failure_rate > 0.05 ? '~ Medium' : '✓ Normal'}</div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
