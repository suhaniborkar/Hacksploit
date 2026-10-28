import type { ReactNode } from 'react';

interface PageContainerProps {
  children: ReactNode;
  className?: string;
}

export function PageContainer({ children, className = '' }: PageContainerProps) {
  return (
    <main className={`page-container ${className}`}>
      <div className="page-inner">{children}</div>
    </main>
  );
}
