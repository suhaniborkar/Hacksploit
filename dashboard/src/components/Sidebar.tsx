import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  FileText,
  BarChart2,
  AlertTriangle,
  Users,
  Layers,
  ShieldCheck,
  X,
} from 'lucide-react';

interface SidebarProps {
  isOpen?: boolean;
  onClose?: () => void;
}

const NAV_ITEMS = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard, end: true },
  { to: '/applications', label: 'Applications', icon: FileText },
  { to: '/analytics', label: 'Analytics & Reports', icon: BarChart2 },
  { to: '/fraud-intelligence', label: 'Fraud Intelligence', icon: AlertTriangle },
  { to: '/users', label: 'Users', icon: Users },
  { to: '/showcase', label: 'Design System', icon: Layers },
];

export function Sidebar({ isOpen = false, onClose }: SidebarProps) {
  return (
    <>
      {isOpen && (
        <div
          className="dash-sidebar-backdrop"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      <aside className={`dash-sidebar ${isOpen ? 'open' : ''}`}>
        <div className="dash-sidebar-logo">
          <ShieldCheck size={24} className="dash-sidebar-logo-icon" />
          <div style={{ flex: 1 }}>
            <div className="dash-sidebar-logo-text">VeriYID</div>
            <div className="dash-sidebar-logo-sub">KYC & Fraud Intelligence</div>
          </div>
          {isOpen && onClose && (
            <button
              onClick={onClose}
              className="dash-menu-toggle"
              aria-label="Close sidebar"
              style={{ display: 'flex' }}
            >
              <X size={18} />
            </button>
          )}
        </div>

        <nav className="dash-sidebar-nav" aria-label="Main navigation">
          <div className="dash-nav-section-label">Platform Core</div>
          {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              onClick={() => {
                if (isOpen && onClose) onClose();
              }}
              className={({ isActive }) => `dash-nav-link${isActive ? ' active' : ''}`}
            >
              <Icon size={16} />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="dash-sidebar-footer">
          <span>VeriYID Intelligence v2.4</span>
          <span style={{ fontSize: '0.72rem', opacity: 0.7 }}>PROD-READY</span>
        </div>
      </aside>
    </>
  );
}

