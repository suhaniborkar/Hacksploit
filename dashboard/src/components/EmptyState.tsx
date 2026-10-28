import type { ReactNode } from 'react';
import { Inbox } from 'lucide-react';

export interface EmptyStateProps {
  title?: string;
  description?: string;
  icon?: ReactNode;
  action?: ReactNode;
  className?: string;
}

export function EmptyState({
  title = 'No records found',
  description = 'There are no items matching your criteria.',
  icon,
  action,
  className = '',
}: EmptyStateProps) {
  return (
    <div className={`dash-empty-state ${className}`.trim()}>
      {icon || <Inbox size={38} />}
      <h3>{title}</h3>
      <p>{description}</p>
      {action && <div style={{ marginTop: '0.75rem' }}>{action}</div>}
    </div>
  );
}

