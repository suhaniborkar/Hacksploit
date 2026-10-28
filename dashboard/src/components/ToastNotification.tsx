import { useEffect } from 'react';
import { CheckCircle2, AlertCircle, Info, X } from 'lucide-react';
import type { ToastMessage } from '../types/dashboard';

export interface ToastNotificationProps {
  toasts: ToastMessage[];
  onDismiss: (id: string) => void;
  autoDismissMs?: number;
}

export function ToastNotification({
  toasts,
  onDismiss,
  autoDismissMs = 4500,
}: ToastNotificationProps) {
  useEffect(() => {
    if (toasts.length === 0) return;

    const timers = toasts.map((t) =>
      setTimeout(() => {
        onDismiss(t.id);
      }, autoDismissMs)
    );

    return () => {
      timers.forEach(clearTimeout);
    };
  }, [toasts, onDismiss, autoDismissMs]);

  if (toasts.length === 0) return null;

  return (
    <div className="dash-toast-container" role="status" aria-live="polite">
      {toasts.map((toast) => {
        const type = toast.type || 'info';
        return (
          <div key={toast.id} className={`dash-toast dash-toast--${type}`}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
              {type === 'success' && <CheckCircle2 size={18} />}
              {type === 'error' && <AlertCircle size={18} />}
              {type === 'info' && <Info size={18} />}
              <div>
                {toast.title && <div style={{ fontWeight: 700 }}>{toast.title}</div>}
                <div style={{ fontSize: '0.88rem' }}>{toast.message}</div>
              </div>
            </div>
            <button
              onClick={() => onDismiss(toast.id)}
              style={{
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                color: 'var(--dash-text-muted)',
                padding: '2px',
                display: 'flex',
              }}
              aria-label="Dismiss toast"
            >
              <X size={15} />
            </button>
          </div>
        );
      })}
    </div>
  );
}

