import type { ReactNode } from 'react';
import { CheckCircle2, Clock, AlertTriangle, AlertCircle } from 'lucide-react';
import type { ApplicationStatus } from '../types/dashboard';

export interface StatusBadgeProps {
  status: ApplicationStatus | string;
  label?: string;
  showIcon?: boolean;
  className?: string;
}

export function StatusBadge({ status, label, showIcon = true, className = '' }: StatusBadgeProps) {
  const norm = status.toLowerCase().replace(/\s+/g, '_');

  let defaultLabel = 'Unknown';
  let badgeClass = 'status-badge--review_required';
  let icon: ReactNode = <AlertCircle size={13} />;

  switch (norm) {
    case 'verified':
      defaultLabel = 'Verified';
      badgeClass = 'status-badge--verified';
      icon = <CheckCircle2 size={13} />;
      break;
    case 'pending':
      defaultLabel = 'Pending';
      badgeClass = 'status-badge--pending';
      icon = <Clock size={13} />;
      break;
    case 'flagged':
      defaultLabel = 'Flagged';
      badgeClass = 'status-badge--flagged';
      icon = <AlertTriangle size={13} />;
      break;
    case 'review_required':
    case 'review':
      defaultLabel = 'Review Required';
      badgeClass = 'status-badge--review_required';
      icon = <AlertCircle size={13} />;
      break;
    default:
      defaultLabel = status;
      badgeClass = 'status-badge--review_required';
      icon = <AlertCircle size={13} />;
      break;
  }

  return (
    <span className={`status-badge ${badgeClass} ${className}`.trim()}>
      {showIcon && icon}
      <span>{label || defaultLabel}</span>
    </span>
  );
}

