import { CheckCircle, Clock, AlertTriangle, XCircle, Loader } from 'lucide-react';
import type { VerificationOutcome } from '../../types/kyc';

const STATUS_CONFIG: Record<
  VerificationOutcome,
  { label: string; icon: React.ReactNode; className: string; description: string }
> = {
  verified: {
    label: 'Verified',
    icon: <CheckCircle size={32} />,
    className: 'outcome-verified',
    description: 'The required checks have passed. Your identity has been verified.',
  },
  review_required: {
    label: 'Review Required',
    icon: <Clock size={32} />,
    className: 'outcome-review',
    description:
      'Additional verification or human review is needed. A compliance officer will contact you.',
  },
  high_risk: {
    label: 'High Risk',
    icon: <AlertTriangle size={32} />,
    className: 'outcome-high-risk',
    description:
      'The system has identified significant risk indicators. This application requires escalation.',
  },
  processing: {
    label: 'Processing',
    icon: <Loader size={32} className="spin" />,
    className: 'outcome-processing',
    description: 'Verification is still in progress. Results will appear shortly.',
  },
  unable_to_complete: {
    label: 'Unable to Complete',
    icon: <XCircle size={32} />,
    className: 'outcome-failed',
    description:
      'A technical or verification failure prevents a final result. Please contact support.',
  },
};

interface VerificationStatusProps {
  outcome: VerificationOutcome;
}

export function VerificationStatus({ outcome }: VerificationStatusProps) {
  const config = STATUS_CONFIG[outcome];
  return (
    <div className={`verification-status ${config.className}`}>
      <div className="status-icon">{config.icon}</div>
      <div className="status-body">
        <h3 className="status-label">{config.label}</h3>
        <p className="status-description">{config.description}</p>
      </div>
    </div>
  );
}

