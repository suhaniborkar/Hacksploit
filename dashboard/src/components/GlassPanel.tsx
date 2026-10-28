import type { ReactNode, CSSProperties } from 'react';

export interface GlassPanelProps {
  children: ReactNode;
  className?: string;
  style?: CSSProperties;
  interactive?: boolean;
  onClick?: () => void;
}

export function GlassPanel({
  children,
  className = '',
  style,
  interactive = false,
  onClick,
}: GlassPanelProps) {
  return (
    <div
      className={`glass-panel ${interactive ? 'glass-panel--interactive' : ''} ${className}`.trim()}
      style={style}
      onClick={onClick}
    >
      {children}
    </div>
  );
}
