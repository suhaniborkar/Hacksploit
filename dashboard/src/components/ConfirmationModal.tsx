import type { ReactNode } from 'react';
import { PrimaryButton } from './PrimaryButton';
import { SecondaryButton } from './SecondaryButton';

export interface ConfirmationModalProps {
  title: string;
  description?: string;
  children?: ReactNode;
  confirmLabel?: string;
  cancelLabel?: string;
  isDanger?: boolean;
  loading?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmationModal({
  title,
  description,
  children,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  isDanger = false,
  loading = false,
  onConfirm,
  onCancel,
}: ConfirmationModalProps) {
  return (
    <div
      className="dash-modal-overlay"
      onClick={(e) => {
        if (e.target === e.currentTarget) onCancel();
      }}
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
    >
      <div className="dash-modal">
        <h2 id="modal-title" className="dash-modal-title">
          {title}
        </h2>

        {description && <p className="dash-modal-body">{description}</p>}
        {children && <div style={{ marginBottom: '1.5rem' }}>{children}</div>}

        <div className="dash-modal-actions">
          <SecondaryButton onClick={onCancel} disabled={loading}>
            {cancelLabel}
          </SecondaryButton>

          {isDanger ? (
            <button
              className="dash-btn-danger"
              onClick={onConfirm}
              disabled={loading}
            >
              {loading ? 'Processing...' : confirmLabel}
            </button>
          ) : (
            <PrimaryButton onClick={onConfirm} loading={loading}>
              {confirmLabel}
            </PrimaryButton>
          )}
        </div>
      </div>
    </div>
  );
}

