import { Search, Bell, Menu, Shield, LogOut } from 'lucide-react';
import { IconButton } from './IconButton';
import { useAuth } from '../context/AuthContext';

interface TopBarProps {
  onMenuToggle?: () => void;
  searchValue?: string;
  onSearchChange?: (val: string) => void;
  onSearchSubmit?: () => void;
}

function getInitials(name: string | null, email: string): string {
  if (name && name.trim()) {
    const parts = name.trim().split(/\s+/);
    if (parts.length >= 2) {
      return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
    }
    return parts[0].slice(0, 2).toUpperCase();
  }
  return email.slice(0, 2).toUpperCase();
}

function formatRole(role: string): string {
  switch (role.toLowerCase()) {
    case 'admin':
      return 'System Administrator';
    case 'fraud_analyst':
    case 'analyst':
      return 'Senior Fraud Analyst';
    case 'compliance_officer':
    case 'compliance':
      return 'Compliance Officer';
    case 'auditor':
      return 'Lead Auditor';
    default:
      return role.replace(/_/g, ' ').toUpperCase();
  }
}

export function TopBar({
  onMenuToggle,
  searchValue = '',
  onSearchChange,
  onSearchSubmit,
}: TopBarProps) {
  const { user, logout } = useAuth();

  const displayName = user?.name || user?.email || 'Argus Staff';
  const roleName = user?.role ? formatRole(user.role) : 'Security Staff';
  const initials = user ? getInitials(user.name, user.email) : 'AG';

  return (
    <header className="dash-topbar">
      <div className="dash-topbar-left">
        <button
          className="dash-menu-toggle"
          onClick={onMenuToggle}
          aria-label="Toggle navigation menu"
        >
          <Menu size={20} />
        </button>

        <form
          className="dash-search-bar"
          onSubmit={(e) => {
            e.preventDefault();
            if (onSearchSubmit) onSearchSubmit();
          }}
        >
          <Search size={15} />
          <input
            type="text"
            placeholder="Global search by applicant name, ID, national ID, or phone..."
            value={searchValue}
            onChange={(e) => onSearchChange?.(e.target.value)}
          />
        </form>
      </div>

      <div className="dash-topbar-right">
        <IconButton title="System Status" aria-label="Security Shield">
          <Shield size={16} />
        </IconButton>

        <div style={{ position: 'relative' }}>
          <IconButton title="Notifications" aria-label="Notifications">
            <Bell size={16} />
          </IconButton>
          <span
            style={{
              position: 'absolute',
              top: 4,
              right: 4,
              width: 7,
              height: 7,
              borderRadius: '50%',
              backgroundColor: 'var(--dash-accent)',
            }}
          />
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem', marginLeft: '0.5rem' }}>
          <div className="dash-avatar" title={roleName}>
            {initials}
          </div>
          <div className="dash-topbar-user">
            <span className="dash-topbar-username">{displayName}</span>
            <span className="dash-topbar-userrole">{roleName}</span>
          </div>
        </div>

        <IconButton title="Sign out" aria-label="Sign out" onClick={logout} style={{ marginLeft: '0.25rem' }}>
          <LogOut size={16} />
        </IconButton>
      </div>
    </header>
  );
}

