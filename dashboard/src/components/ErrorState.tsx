import type { ReactNode } from 'react';
import { AlertCircle, RotateCcw } from 'lucide-react';
import { SecondaryButton } from './SecondaryButton';

export interface ErrorStateProps {
  title?: string;
  message?: string;
  onRetry?: () => void;
  action?: ReactNode;
  className?: string;
}

export function ErrorState({
  title = 'Failed to load data',
  message = 'An unexpected error occurred while fetching information.',
  onRetry,
  action,
  className = '',
}: ErrorStateProps) {
  return (
    <div className={`dash-error-state ${className}`.trim()}>
      <AlertCircle size={38} />
      <h3>{title}</h3>
      <p>{message}</p>
      {onRetry && (
        <SecondaryButton onClick={onRetry} icon={<RotateCcw size={15} />} style={{ marginTop: '0.75rem' }}>
          Try Again
        </SecondaryButton>
      )}
      {action && <div style={{ marginTop: '0.75rem' }}>{action}</div>}
    </div>
  );
}

