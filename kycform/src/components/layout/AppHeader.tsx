import { Shield } from 'lucide-react';

export function AppHeader() {
  return (
    <header className="app-header">
      <div className="header-inner">
        <div className="header-brand">
          <Shield size={28} className="header-icon" />
          <div>
            <span className="header-title">VerifyID</span>
            <span className="header-subtitle">KYC Verification Portal</span>
          </div>
        </div>
        <div className="header-badge">
          <span className="badge-dot" />
          Secure Session
        </div>
      </div>
    </header>
  );
}
