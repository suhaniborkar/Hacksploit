import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { ShieldCheck, LogIn, AlertCircle, Eye, EyeOff } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

const DEMO_ROLES = [
  { label: 'Admin', email: 'admin@argus.internal', password: 'ArgusAdmin2026!', badge: 'admin' },
  { label: 'Analyst', email: 'analyst@argus.internal', password: 'ArgusAnalyst2026!', badge: 'analyst' },
  { label: 'Compliance', email: 'compliance@argus.internal', password: 'ArgusCompliance2026!', badge: 'compliance' },
  { label: 'Auditor', email: 'auditor@argus.internal', password: 'ArgusAuditor2026!', badge: 'auditor' },
];

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPw, setShowPw] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login(email, password);
      navigate('/', { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed');
    } finally {
      setLoading(false);
    }
  }

  function fillDemo(demoEmail: string, demoPassword: string) {
    setEmail(demoEmail);
    setPassword(demoPassword);
    setError(null);
  }

  return (
    <div className="login-root">
      {/* Same background as dashboard */}
      <div className="dash-bg" aria-hidden="true" />
      <div className="dash-bg-overlay" aria-hidden="true" />

      <div className="login-card glass-panel">
        {/* Brand header */}
        <div className="login-brand">
          <div className="login-brand-icon">
            <ShieldCheck size={32} />
          </div>
          <div>
            <h1 className="login-brand-name">VeriYID</h1>
            <p className="login-brand-sub">KYC &amp; Fraud Intelligence Platform</p>
          </div>
        </div>

        <div className="login-divider" />

        <h2 className="login-title">Sign in to your account</h2>
        <p className="login-subtitle">Authorised personnel only. All access is logged and audited.</p>

        {error && (
          <div className="login-error" role="alert">
            <AlertCircle size={15} style={{ flexShrink: 0 }} />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="login-form" noValidate>
          <div className="login-field">
            <label htmlFor="login-email" className="login-label">Email address</label>
            <input
              id="login-email"
              type="email"
              className="login-input"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="analyst@argus.internal"
              autoComplete="username"
              required
              disabled={loading}
            />
          </div>

          <div className="login-field">
            <label htmlFor="login-password" className="login-label">Password</label>
            <div className="login-input-wrapper">
              <input
                id="login-password"
                type={showPw ? 'text' : 'password'}
                className="login-input login-input--pw"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••••"
                autoComplete="current-password"
                required
                disabled={loading}
              />
              <button
                type="button"
                className="login-pw-toggle"
                onClick={() => setShowPw((v) => !v)}
                aria-label={showPw ? 'Hide password' : 'Show password'}
                tabIndex={-1}
              >
                {showPw ? <EyeOff size={15} /> : <Eye size={15} />}
              </button>
            </div>
          </div>

          <button
            id="login-submit"
            type="submit"
            className="login-btn"
            disabled={loading || !email || !password}
          >
            {loading ? (
              <span className="login-spinner" />
            ) : (
              <LogIn size={16} />
            )}
            {loading ? 'Signing in…' : 'Sign in'}
          </button>
        </form>

        <div className="login-demo-section">
          <p className="login-demo-label">Quick demo access</p>
          <div className="login-demo-grid">
            {DEMO_ROLES.map((r) => (
              <button
                key={r.email}
                type="button"
                className={`login-demo-chip login-demo-chip--${r.badge}`}
                onClick={() => fillDemo(r.email, r.password)}
                disabled={loading}
              >
                {r.label}
              </button>
            ))}
          </div>
        </div>

        <p className="login-footer">
          VeriYID Intelligence v2.4 &nbsp;·&nbsp; SOC 2 Type II &nbsp;·&nbsp; ISO 27001
        </p>
      </div>
    </div>
  );
}
