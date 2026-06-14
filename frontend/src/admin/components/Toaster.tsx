import React, { useState, useEffect } from 'react';
import { CheckCircle, XCircle, AlertTriangle, X } from 'lucide-react';

// ── Types ──────────────────────────────────────────────────────────────────
type ToastType = 'success' | 'error' | 'warning';

interface Toast {
  id: number;
  type: ToastType;
  message: string;
}

// ── Module-level store (no context needed) ─────────────────────────────────
let _toasts: Toast[]              = [];
let _nextId                       = 0;
const _listeners                  = new Set<(t: Toast[]) => void>();

function notify() { _listeners.forEach(fn => fn([..._toasts])); }

export const toast = {
  success: (message: string, duration = 3000) => add('success', message, duration),
  error:   (message: string, duration = 4000) => add('error',   message, duration),
  warning: (message: string, duration = 3500) => add('warning', message, duration),
};

function add(type: ToastType, message: string, duration: number) {
  const id = ++_nextId;
  _toasts = [..._toasts, { id, type, message }];
  notify();
  setTimeout(() => {
    _toasts = _toasts.filter(t => t.id !== id);
    notify();
  }, duration);
}

function dismiss(id: number) {
  _toasts = _toasts.filter(t => t.id !== id);
  notify();
}

// ── Component ──────────────────────────────────────────────────────────────
const ICONS: Record<ToastType, React.ReactNode> = {
  success: <CheckCircle  size={16} color="#10B981" />,
  error:   <XCircle      size={16} color="#EF4444" />,
  warning: <AlertTriangle size={16} color="#F59E0B" />,
};

const BORDER: Record<ToastType, string> = {
  success: 'rgba(16,185,129,0.35)',
  error:   'rgba(239,68,68,0.35)',
  warning: 'rgba(245,158,11,0.35)',
};

const ToastItem: React.FC<{ toast: Toast }> = ({ toast: t }) => {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    // Tiny delay so CSS transition plays
    const id = setTimeout(() => setVisible(true), 10);
    return () => clearTimeout(id);
  }, []);

  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 10,
      background: 'rgba(15,23,42,0.95)',
      border: `1px solid ${BORDER[t.type]}`,
      borderRadius: 10, padding: '11px 14px',
      minWidth: 260, maxWidth: 380,
      boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
      transform: visible ? 'translateX(0)' : 'translateX(120%)',
      opacity: visible ? 1 : 0,
      transition: 'transform 0.3s cubic-bezier(0.16,1,0.3,1), opacity 0.3s ease',
    }}>
      {ICONS[t.type]}
      <span style={{ flex: 1, fontSize: 13, color: '#e2e8f0', lineHeight: 1.4 }}>{t.message}</span>
      <button
        onClick={() => dismiss(t.id)}
        style={{ background: 'none', border: 'none', color: '#475569', cursor: 'pointer', padding: 2, display: 'flex' }}
      >
        <X size={13} />
      </button>
    </div>
  );
};

export const Toaster: React.FC = () => {
  const [toasts, setToasts] = useState<Toast[]>([]);

  useEffect(() => {
    const unsub = (() => {
      _listeners.add(setToasts);
      return () => { _listeners.delete(setToasts); };
    })();
    return unsub;
  }, []);

  if (toasts.length === 0) return null;

  return (
    <div style={{
      position: 'fixed', bottom: 24, right: 24,
      display: 'flex', flexDirection: 'column', gap: 10,
      zIndex: 9999, pointerEvents: 'none',
    }}>
      {toasts.map(t => (
        <div key={t.id} style={{ pointerEvents: 'auto' }}>
          <ToastItem toast={t} />
        </div>
      ))}
    </div>
  );
};
