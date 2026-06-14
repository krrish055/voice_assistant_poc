import React, { useState, useEffect, useMemo } from 'react';
import { Save, Variable } from 'lucide-react';
import { adminApi } from '../api';
import { toast } from './Toaster';
import type { Agent } from '../types';

interface Props { agent: Agent }

// Extract {variable} or ${variable} patterns
const extractVars = (text: string): string[] => {
  const matches = [...text.matchAll(/\{(\w+)\}|\$\{(\w+)\}/g)];
  const vars = matches.map(m => m[1] || m[2]);
  return [...new Set(vars)];
};

export const PromptEditor: React.FC<Props> = ({ agent }) => {
  const [template, setTemplate]     = useState('');
  const [varValues, setVarValues]   = useState<Record<string, string>>({});
  const [preview, setPreview]       = useState(false);
  const [saving, setSaving]         = useState(false);
  const [saved, setSaved]           = useState(false);

  useEffect(() => {
    adminApi.getPrompt(agent.id).then(d => {
      if (d.template) {
        setTemplate(d.template.template ?? '');
        setVarValues(d.template.variables ?? {});
      } else {
        setTemplate(agent.config.system_prompt ?? '');
      }
    }).catch(() => setTemplate(agent.config.system_prompt ?? ''));
  }, [agent.id, agent.config.system_prompt]);

  const detectedVars = useMemo(() => extractVars(template), [template]);

  const renderedPreview = useMemo(() => {
    let out = template;
    detectedVars.forEach(v => { out = out.replaceAll(`{${v}}`, varValues[v] ?? `{${v}}`).replaceAll(`\${${v}}`, varValues[v] ?? `\${${v}}`); });
    return out;
  }, [template, varValues, detectedVars]);

  const save = async () => {
    setSaving(true);
    try {
      await adminApi.savePrompt(agent.id, template, varValues);
      setSaved(true);
      toast.success('Prompt template saved');
      setTimeout(() => setSaved(false), 2000);
    } catch (err: any) {
      toast.error(`Save failed: ${err.message}`);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ color: '#94A3B8', fontSize: 13 }}>System Prompt — <strong style={{ color: '#e2e8f0' }}>{agent.name}</strong></span>
        <div style={{ display: 'flex', gap: 8 }}>
          <ToggleBtn active={preview} onClick={() => setPreview(p => !p)} label={preview ? 'Edit' : 'Preview'} />
          <button onClick={save} disabled={saving} style={btnStyle('#0077B6')}>
            <Save size={13} />
            {saved ? 'Saved ✓' : saving ? 'Saving…' : 'Save Prompt'}
          </button>
        </div>
      </div>

      {/* Editor / Preview */}
      {preview ? (
        <div style={textareaBoxStyle}>
          <p style={{ whiteSpace: 'pre-wrap', lineHeight: 1.7, fontSize: 13, color: '#e2e8f0' }}>{renderedPreview}</p>
        </div>
      ) : (
        <textarea
          value={template}
          onChange={e => setTemplate(e.target.value)}
          placeholder='You are an expert in {topic}. Answer in {language}.'
          style={{ ...textareaBoxStyle, resize: 'vertical', outline: 'none', fontFamily: 'inherit', fontSize: 13, lineHeight: 1.7, color: '#e2e8f0' }}
          rows={8}
        />
      )}

      {/* Variable highlight hint */}
      {!preview && detectedVars.length > 0 && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
          <Variable size={13} color="#48CAE4" />
          <span style={{ fontSize: 12, color: '#94A3B8' }}>Detected variables:</span>
          {detectedVars.map(v => (
            <span key={v} style={{ background: 'rgba(72,202,228,0.15)', color: '#48CAE4', fontSize: 12, padding: '2px 8px', borderRadius: 12, border: '1px solid rgba(72,202,228,0.3)' }}>
              {`{${v}}`}
            </span>
          ))}
        </div>
      )}

      {/* Dynamic variable form */}
      {detectedVars.length > 0 && (
        <div style={{ background: 'rgba(15,23,42,0.6)', borderRadius: 10, padding: 16, border: '1px solid rgba(148,163,184,0.1)' }}>
          <p style={{ fontSize: 12, color: '#94A3B8', marginBottom: 12 }}>Variable Values (injected at runtime)</p>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 10 }}>
            {detectedVars.map(v => (
              <div key={v}>
                <label style={{ fontSize: 11, color: '#64748B', display: 'block', marginBottom: 4 }}>{`{${v}}`}</label>
                <input
                  value={varValues[v] ?? ''}
                  onChange={e => setVarValues(prev => ({ ...prev, [v]: e.target.value }))}
                  placeholder={`Enter ${v}…`}
                  style={inputStyle}
                />
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

const textareaBoxStyle: React.CSSProperties = {
  background: 'rgba(15,23,42,0.8)', border: '1px solid rgba(148,163,184,0.15)',
  borderRadius: 10, padding: 14, minHeight: 160,
};
const inputStyle: React.CSSProperties = {
  width: '100%', background: 'rgba(15,23,42,0.8)', color: '#e2e8f0',
  border: '1px solid rgba(148,163,184,0.2)', borderRadius: 7, padding: '7px 10px', fontSize: 13,
};
const btnStyle = (bg: string): React.CSSProperties => ({
  display: 'flex', alignItems: 'center', gap: 6,
  background: bg, color: '#fff', border: 'none', borderRadius: 7,
  padding: '7px 14px', fontSize: 12, cursor: 'pointer',
});
const ToggleBtn: React.FC<{ active: boolean; onClick: () => void; label: string }> = ({ active, onClick, label }) => (
  <button onClick={onClick} style={{ ...btnStyle(active ? 'rgba(72,202,228,0.15)' : 'rgba(148,163,184,0.1)'), border: '1px solid rgba(148,163,184,0.2)', color: active ? '#48CAE4' : '#94A3B8' }}>
    {label}
  </button>
);
