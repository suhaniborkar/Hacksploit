import type { ReactNode } from 'react';

export interface PageHeaderProps {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
  children?: ReactNode;
}

export function PageHeader({ title, subtitle, actions, children }: PageHeaderProps) {
  return (
    <div className="dash-page-header">
      <div className="dash-page-title-group">
        <h1 className="dash-page-title">{title}</h1>
        {subtitle && <p className="dash-page-subtitle">{subtitle}</p>}
        {children}
      </div>
      {actions && <div className="dash-page-actions">{actions}</div>}
    </div>
  );
}

