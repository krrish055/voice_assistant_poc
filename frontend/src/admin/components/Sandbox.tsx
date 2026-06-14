import React, { useState, useEffect, useRef } from 'react';
import { Send, Trash2, Bot, User } from 'lucide-react';
import { adminApi } from '../api';
import { toast } from './Toaster';
import type { Agent, ChatMessage } from '../types';

interface Props { agent: Agent }

export const Sandbox: React.FC<Props> = ({ agent }) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput]       = useState('');
  const [sending, setSending]   = useState(false);
  const bottomRef               = useRef<HTMLDivElement>(null);

  useEffect(() => {
    adminApi.getChatHistory(agent.id)
      .then(d => setMessages(d.messages ?? []))
      .catch(() => {});
  }, [agent.id]);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);

  const send = async () => {
    if (!input.trim() || sending) return;
    const userMsg: ChatMessage = { id: Date.now().toString(), agent_id: agent.id, role: 'user', content: input.trim(), timestamp: new Date().toISOString() };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setSending(true);
    try {
      const res = await adminApi.sendMessage(agent.id, userMsg.content);
      const aiMsg: ChatMessage = { id: (Date.now() + 1).toString(), agent_id: agent.id, role: 'ai', content: res.response ?? '…', timestamp: new Date().toISOString() };
      setMessages(prev => [...prev, aiMsg]);
    } catch (e: any) {
      const errMsg: ChatMessage = { id: (Date.now() + 1).toString(), agent_id: agent.id, role: 'system', content: `Error: ${e.message}`, timestamp: new Date().toISOString() };
      setMessages(prev => [...prev, errMsg]);
    } finally {
      setSending(false);
    }
  };

  const clear = async () => {
    await adminApi.clearChat(agent.id);
    setMessages([]);
    toast.success('Chat history cleared');
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', gap: 0 }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <div>
          <span style={{ color: '#e2e8f0', fontWeight: 600 }}>Testing Sandbox</span>
          <span style={{ marginLeft: 10, color: '#94A3B8', fontSize: 12 }}>{agent.name}</span>
        </div>
        <button onClick={clear} style={{ display: 'flex', alignItems: 'center', gap: 5, background: 'rgba(239,68,68,0.1)', color: '#EF4444', border: '1px solid rgba(239,68,68,0.2)', borderRadius: 7, padding: '5px 12px', fontSize: 12, cursor: 'pointer' }}>
          <Trash2 size={12} /> Clear
        </button>
      </div>

      {/* Config summary strip */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 12, flexWrap: 'wrap' }}>
        {[
          { label: 'Model',       value: agent.config.model },
          { label: 'Temp',        value: agent.config.temperature.toFixed(2) },
          { label: 'Max Tokens',  value: agent.config.max_tokens },
        ].map(({ label, value }) => (
          <div key={label} style={{ background: 'rgba(72,202,228,0.08)', border: '1px solid rgba(72,202,228,0.15)', borderRadius: 8, padding: '4px 12px', fontSize: 12 }}>
            <span style={{ color: '#64748B' }}>{label}: </span>
            <span style={{ color: '#48CAE4', fontWeight: 600 }}>{value}</span>
          </div>
        ))}
      </div>

      {/* Messages */}
      <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 10, paddingRight: 4 }}>
        {messages.length === 0 && (
          <div style={{ textAlign: 'center', color: '#475569', fontSize: 13, marginTop: 40 }}>
            Send a message to test this agent's current configuration.
          </div>
        )}
        {messages.map(msg => <MessageBubble key={msg.id} msg={msg} />)}
        {sending && (
          <div style={{ display: 'flex', gap: 8, alignItems: 'center', color: '#94A3B8', fontSize: 13 }}>
            <div className="spinner" /> Thinking…
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && !e.shiftKey && send()}
          placeholder="Type a test message…"
          style={{ flex: 1, background: 'rgba(15,23,42,0.8)', color: '#e2e8f0', border: '1px solid rgba(148,163,184,0.2)', borderRadius: 9, padding: '10px 14px', fontSize: 13, outline: 'none' }}
        />
        <button
          onClick={send} disabled={sending || !input.trim()}
          style={{ background: '#0077B6', color: '#fff', border: 'none', borderRadius: 9, padding: '10px 16px', cursor: 'pointer', opacity: (sending || !input.trim()) ? 0.5 : 1, display: 'flex', alignItems: 'center' }}
        >
          <Send size={15} />
        </button>
      </div>
    </div>
  );
};

const MessageBubble: React.FC<{ msg: ChatMessage }> = ({ msg }) => {
  const isUser = msg.role === 'user';
  return (
    <div style={{ display: 'flex', gap: 8, justifyContent: isUser ? 'flex-end' : 'flex-start' }}>
      {!isUser && (
        <div style={{ width: 28, height: 28, borderRadius: '50%', background: 'rgba(0,119,182,0.2)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
          <Bot size={14} color="#0077B6" />
        </div>
      )}
      <div style={{
        maxWidth: '75%', background: isUser ? 'rgba(0,119,182,0.25)' : 'rgba(28,37,65,0.8)',
        border: `1px solid ${isUser ? 'rgba(0,119,182,0.3)' : 'rgba(148,163,184,0.1)'}`,
        borderRadius: isUser ? '12px 12px 4px 12px' : '12px 12px 12px 4px',
        padding: '9px 13px', fontSize: 13, color: '#e2e8f0', lineHeight: 1.6,
        whiteSpace: 'pre-wrap',
      }}>
        {msg.content}
      </div>
      {isUser && (
        <div style={{ width: 28, height: 28, borderRadius: '50%', background: 'rgba(72,202,228,0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
          <User size={14} color="#48CAE4" />
        </div>
      )}
    </div>
  );
};
