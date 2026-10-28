import { RefreshCw } from 'lucide-react';
import { useKYC } from '../context/KYCContext';
import { LoadingState } from '../components/shared/LoadingState';
import { VerificationStatus } from '../components/results/VerificationStatus';
import { VerificationCheckList } from '../components/results/VerificationCheckList';
import { RiskEvidencePanel } from '../components/results/RiskEvidencePanel';
import { ApplicationSummary } from '../components/results/ApplicationSummary';
import { PageContainer } from '../components/layout/PageContainer';

export function VerificationResultsPage() {
  const { application, resetApplication } = useKYC();
  const { result } = application;

  if (!result) {
    return (
      <PageContainer>
        <LoadingState message="Preparing your results…" />
      </PageContainer>
    );
  }

  const isProcessing = result.outcome === 'processing';

  return (
    <PageContainer className="results-page">
      <div className="results-header">
        <h1>Verification Results</h1>
        <p className="results-subtitle">
          Official verification verdict and automated forensic analysis generated for this identity application.
        </p>
      </div>

      <ApplicationSummary
        applicationRef={result.applicationRef}
        submittedAt={result.submittedAt}
      />

      <VerificationStatus outcome={result.outcome} />

      {isProcessing ? (
        <LoadingState message="Verification is in progress. This page will update automatically…" />
      ) : (
        <>
          <section className="results-section">
            <h2 className="results-section-title">Verification Checks</h2>
            <VerificationCheckList checks={result.checks} />
          </section>

          <section className="results-section">
            <h2 className="results-section-title">Risk Analysis</h2>
            <div className="results-disclaimer">
              The evidence below is returned by the verification service. A mismatch or shared
              identifier should not be automatically interpreted as proof of fraud.
            </div>
            <RiskEvidencePanel
              riskScore={result.overallRiskScore}
              riskIndicators={result.riskIndicators}
              mismatches={result.mismatches}
              recommendedAction={result.recommendedAction}
            />
          </section>
        </>
      )}

      <div className="results-footer">
        <p className="results-footnote">
          Automated identity verification and multi-plane forensic checks evaluated by Project Argus.
          Final regulatory determination subject to statutory compliance policy.
        </p>
        <button className="btn btn-secondary" onClick={resetApplication}>
          <RefreshCw size={16} /> Start New Application
        </button>
      </div>
    </PageContainer>
  );
}

