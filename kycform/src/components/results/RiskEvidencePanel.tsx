import { AlertTriangle, ArrowRight } from 'lucide-react';

interface RiskEvidencePanelProps {
  riskScore?: number;
  riskIndicators: string[];
  mismatches: string[];
  recommendedAction?: string;
}

export function RiskEvidencePanel({
  riskScore,
  riskIndicators,
  mismatches,
  recommendedAction,
}: RiskEvidencePanelProps) {
  const riskLevel =
    riskScore === undefined
      ? null
      : riskScore <= 30
      ? 'low'
      : riskScore <= 60
      ? 'medium'
      : 'high';

  return (
    <div className="risk-panel">
      {riskScore !== undefined && (
        <div className={`risk-score risk-score--${riskLevel}`}>
          <div className="risk-score-label">Overall Risk Score</div>
          <div className="risk-score-bar">
            <div
              className="risk-score-fill"
              style={{ width: `${riskScore}%` }}
              aria-valuenow={riskScore}
              aria-valuemin={0}
              aria-valuemax={100}
              role="progressbar"
            />
          </div>
          <div className="risk-score-value">
            {riskScore} / 100 —{' '}
            <strong>
              {riskLevel === 'low' ? 'Low Risk' : riskLevel === 'medium' ? 'Medium Risk' : 'High Risk'}
            </strong>
          </div>
        </div>
      )}

      {riskIndicators.length > 0 && (
        <div className="risk-section">
          <h4 className="risk-section-title">
            <AlertTriangle size={16} /> Risk Indicators
          </h4>
          <ul className="risk-list">
            {riskIndicators.map((indicator, i) => (
              <li key={i} className="risk-list-item risk-list-item--warning">
                {indicator}
              </li>
            ))}
          </ul>
        </div>
      )}

      {mismatches.length > 0 && (
        <div className="risk-section">
          <h4 className="risk-section-title">
            <AlertTriangle size={16} /> Identified Mismatches
          </h4>
          <ul className="risk-list">
            {mismatches.map((mismatch, i) => (
              <li key={i} className="risk-list-item risk-list-item--error">
                {mismatch}
              </li>
            ))}
          </ul>
        </div>
      )}

      {riskIndicators.length === 0 && mismatches.length === 0 && (
        <p className="risk-none">No significant risk indicators or mismatches identified.</p>
      )}

      {recommendedAction && (
        <div className="recommended-action">
          <h4 className="risk-section-title">
            <ArrowRight size={16} /> Recommended Action
          </h4>
          <p>{recommendedAction}</p>
        </div>
      )}
    </div>
  );
}

