import { useState, type ReactNode } from 'react';
import { Sidebar } from './Sidebar';
import { TopBar } from './TopBar';

export interface AppShellProps {
  children: ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="dash-root">
      {/* Fixed continuous visual background */}
      <div className="dash-bg" aria-hidden="true" />
      <div className="dash-bg-overlay" aria-hidden="true" />

      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <TopBar onMenuToggle={() => setSidebarOpen(!sidebarOpen)} />

      <main className="dash-main">
        {children}
      </main>
    </div>
  );
}

