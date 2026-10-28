import type { ReactNode } from 'react';
import { GlassPanel } from './GlassPanel';

export interface MetricCardProps {
  label: string;
  value: number | string;
  delta?: number | string;
  deltaLabel?: string;
  icon?: ReactNode;
  onClick?: () => void;
  className?: string;
}

export function MetricCard({
  label,
  value,
  delta,
  deltaLabel,
  icon,
  onClick,
  className = '',
}: MetricCardProps) {
  return (
    <GlassPanel
      className={`dash-metric-card ${onClick ? 'glass-panel--interactive' : ''} ${className}`.trim()}
      onClick={onClick}
      style={{ cursor: onClick ? 'pointer' : 'default' }}
    >
      <div className="dash-metric-card-top">
        <span className="dash-metric-label">{label}</span>
        {icon && <span className="dash-metric-icon">{icon}</span>}
      </div>

      <div className="dash-metric-value">{value}</div>

      {(delta !== undefined || deltaLabel) && (
        <div className="dash-metric-delta">
          {delta !== undefined && <span>{delta}</span>}
          {deltaLabel && <span style={{ color: 'var(--dash-text-muted)' }}>{deltaLabel}</span>}
        </div>
      )}
    </GlassPanel>
  );
}

