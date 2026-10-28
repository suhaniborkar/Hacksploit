import type { ReactNode } from 'react';
import { Filter, RotateCcw } from 'lucide-react';
import { SecondaryButton } from './SecondaryButton';

export interface FilterBarProps {
  children: ReactNode;
  onReset?: () => void;
  showReset?: boolean;
  className?: string;
}

export function FilterBar({ children, onReset, showReset = false, className = '' }: FilterBarProps) {
  return (
    <div className={`dash-filter-bar ${className}`.trim()}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: 'var(--dash-text-muted)', fontSize: '0.85rem', fontWeight: 700 }}>
        <Filter size={15} />
        <span>Filters:</span>
      </div>

      {children}

      {showReset && onReset && (
        <SecondaryButton
          onClick={onReset}
          style={{ minHeight: 38, padding: '0.35rem 0.85rem', fontSize: '0.85rem' }}
          icon={<RotateCcw size={13} />}
        >
          Reset
        </SecondaryButton>
      )}
    </div>
  );
}

