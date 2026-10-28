import { CheckCircle2, XCircle, Clock, HelpCircle, AlertCircle } from 'lucide-react';
import type { VerificationCheck, CheckStatus } from '../../types/kyc';

const CHECK_ICON: Record<CheckStatus, React.ReactNode> = {
  passed: <CheckCircle2 size={18} className="check-passed" />,
  failed: <XCircle size={18} className="check-failed" />,
  pending: <Clock size={18} className="check-pending" />,
  not_checked: <HelpCircle size={18} className="check-na" />,
  not_available: <HelpCircle size={18} className="check-na" />,
};

const CHECK_LABEL: Record<CheckStatus, string> = {
  passed: 'Passed',
  failed: 'Failed',
  pending: 'Pending',
  not_checked: 'Not Checked',
  not_available: 'Not Available',
};

interface VerificationCheckListProps {
  checks: VerificationCheck[];
}

export function VerificationCheckList({ checks }: VerificationCheckListProps) {
  if (!checks || checks.length === 0) {
    return (
      <div className="checks-empty">
        <Clock size={20} /> Verification checks are being processed…
      </div>
    );
  }

  return (
    <div className="check-list">
      {checks.map((check, i) => (
        <div key={i} className={`check-item check-item--${check.status}`}>
          <div className="check-header">
            <div className="check-name-row">
              {CHECK_ICON[check.status]}
              <span className="check-name">{check.name}</span>
            </div>
            <span className={`check-badge check-badge--${check.status}`}>
              {CHECK_LABEL[check.status]}
            </span>
          </div>
          <p className="check-explanation">{check.explanation}</p>
          {check.evidence && (
            <p className="check-evidence">
              <AlertCircle size={13} /> {check.evidence}
            </p>
          )}
        </div>
      ))}
    </div>
  );
}

