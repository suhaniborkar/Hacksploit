import { useState } from 'react';
import { ChevronDown, ChevronUp, Edit2, Send, AlertCircle } from 'lucide-react';
import { useKYC } from '../../context/KYCContext';
import type { KYCStep } from '../../types/kyc';
import { LoadingState } from '../shared/LoadingState';
import { ErrorMessage } from '../shared/ErrorMessage';

interface SectionProps {
  title: string;
  step: KYCStep;
  children: React.ReactNode;
}

function ReviewSection({ title, step, children }: SectionProps) {
  const [open, setOpen] = useState(true);
  const { goToStep } = useKYC();

  return (
    <div className="review-section">
      <div className="review-section-header" onClick={() => setOpen((o) => !o)}>
        <span className="review-section-title">{title}</span>
        <div className="review-section-actions">
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            onClick={(e) => {
              e.stopPropagation();
              goToStep(step);
            }}
            aria-label={`Edit ${title}`}
          >
            <Edit2 size={14} /> Edit
          </button>
          {open ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
        </div>
      </div>
      {open && <div className="review-section-body">{children}</div>}
    </div>
  );
}

function Row({ label, value }: { label: string; value?: string }) {
  return (
    <div className="review-row">
      <span className="review-label">{label}</span>
      <span className="review-value">{value || <em className="not-provided">Not provided</em>}</span>
    </div>
  );
}

function AddressBlock({ address }: { address: import('../../types/kyc').AddressInfo }) {
  return (
    <div className="address-block">
      <p>{address.line1}{address.line2 ? `, ${address.line2}` : ''}</p>
      <p>{address.locality}, {address.city}</p>
      <p>{address.stateRegion} – {address.postalCode}</p>
      <p>{address.country}</p>
    </div>
  );
}

const DOC_LABELS: Record<string, string> = {
  pan: 'PAN Card',
  aadhaar: 'Aadhaar Card',
  driving_licence: 'Driving Licence',
};

const OCC_LABELS: Record<string, string> = {
  salaried: 'Salaried Employee', self_employed: 'Self-Employed',
  business_owner: 'Business Owner', student: 'Student',
  unemployed: 'Unemployed', other: 'Other',
};

const PEP_LABELS: Record<string, string> = {
  no: 'Not a PEP', yes: 'PEP or associated',
  requires_clarification: 'Requires clarification',
};

interface ReviewFormProps {
  onBack: () => void;
}

export function ReviewForm({ onBack }: ReviewFormProps) {
  const { application, submitApplication } = useKYC();
  const { personal, contact, address, document, biometric, declarations, submissionStatus, submissionError } = application;

  const isSubmitting = submissionStatus === 'submitting';

  return (
    <div className="step-form">
      <div className="form-section-header">
        <h2>Review &amp; Submit</h2>
        <p>
          Please review all information before submitting. Use the Edit buttons to make
          corrections.
        </p>
      </div>

      {submissionStatus === 'error' && submissionError && (
        <ErrorMessage
          title="Submission Failed"
          message={submissionError}
          onRetry={submitApplication}
        />
      )}

      <ReviewSection title="Personal Information" step="personal">
        <Row label="Full Name" value={personal.fullName} />
        <Row label="Date of Birth" value={personal.dateOfBirth} />
        <Row label="Residency Status" value={personal.residencyStatus?.replace('_', ' ')} />
        {personal.fathersName && <Row label="Father's Name" value={personal.fathersName} />}
        {personal.mothersName && <Row label="Mother's Name" value={personal.mothersName} />}
        {personal.spouseName && <Row label="Spouse's Name" value={personal.spouseName} />}
        {personal.gender && <Row label="Gender" value={personal.gender?.replace('_', ' ')} />}
        {personal.maritalStatus && <Row label="Marital Status" value={personal.maritalStatus?.replace('_', ' ')} />}
      </ReviewSection>

      <ReviewSection title="Contact Information" step="contact">
        <Row label="Mobile Number" value={contact.mobile} />
        <Row label="Email Address" value={contact.email} />
      </ReviewSection>

      <ReviewSection title="Residential Address" step="contact">
        <AddressBlock address={address.residential} />
      </ReviewSection>

      {!address.permanentSameAsResidential && address.permanent && (
        <ReviewSection title="Permanent Address" step="contact">
          <AddressBlock address={address.permanent} />
        </ReviewSection>
      )}

      {address.permanentSameAsResidential && (
        <div className="review-note">Permanent address is the same as residential address.</div>
      )}

      <ReviewSection title="Identity Document" step="documents">
        <Row label="Document Type" value={DOC_LABELS[document.documentType] ?? document.documentType} />
        <Row label="Document Number" value={document.documentNumber} />
        {document.issuingAuthority && <Row label="Issuing Authority" value={document.issuingAuthority} />}
        {document.issueDate && <Row label="Issue Date" value={document.issueDate} />}
        {document.expiryDate && <Row label="Expiry Date" value={document.expiryDate} />}
      </ReviewSection>

      <ReviewSection title="Uploaded Documents" step="documents">
        <div className="review-images">
          {document.frontImagePreview ? (
            <div className="review-image-item">
              <img src={document.frontImagePreview} alt="Document front" className="review-thumb" />
              <span>Front</span>
            </div>
          ) : (
            <div className="review-missing">
              <AlertCircle size={16} /> Front image not uploaded
            </div>
          )}
          {document.backImagePreview && (
            <div className="review-image-item">
              <img src={document.backImagePreview} alt="Document back" className="review-thumb" />
              <span>Back</span>
            </div>
          )}
        </div>
      </ReviewSection>

      <ReviewSection title="Biometric Input" step="biometric">
        {biometric.selfiePreview ? (
          <div className="review-images">
            <div className="review-image-item">
              <img src={biometric.selfiePreview} alt="Selfie" className="review-thumb review-thumb--selfie" />
              <span>{biometric.livenessMode === 'live' ? 'Biometric Live Capture' : 'Selfie Photo'}</span>
            </div>
          </div>
        ) : (
          <div className="review-missing">
            <AlertCircle size={16} /> Selfie / Biometric photo not captured
          </div>
        )}
        <Row
          label="Verification Mode"
          value={
            biometric.livenessMode === 'live'
              ? 'Real Local Camera (Google MediaPipe + MiniFASNet)'
              : 'Simulated Demonstration'
          }
        />
        <Row
          label="Liveness Status"
          value={
            biometric.livenessStatus === 'passed' && biometric.visionResult?.livenessPassed
              ? biometric.visionResult.antiSpoofResult?.status === 'uncertain'
                ? 'Manual Review Required (Uncertain Anti-Spoof)'
                : 'Genuine Active Liveness Verified (Passed)'
              : biometric.livenessStatus === 'failed'
              ? 'Liveness Check Failed'
              : biometric.livenessStatus ?? 'Not completed'
          }
        />
        {biometric.visionResult?.activeChallengesCompleted && (
          <Row
            label="Challenges Completed"
            value={biometric.visionResult.activeChallengesCompleted.join(', ')}
          />
        )}
        {biometric.visionResult?.antiSpoofResult && (
          <Row
            label="Anti-Spoofing Inference"
            value={`${biometric.visionResult.antiSpoofResult.status.toUpperCase()} (${biometric.visionResult.antiSpoofResult.confidencePercent}% confidence)`}
          />
        )}
        {biometric.visionResult?.sessionId && (
          <Row label="Evidence Session" value={biometric.visionResult.sessionId} />
        )}
      </ReviewSection>

      <ReviewSection title="Additional Information" step="declarations">
        <Row label="Occupation" value={OCC_LABELS[declarations.occupation] ?? declarations.occupation} />
        {declarations.natureOfBusiness && (
          <Row label="Nature of Business" value={declarations.natureOfBusiness} />
        )}
        {declarations.sourceOfFunds && (
          <Row label="Source of Funds" value={declarations.sourceOfFunds?.replace('_', ' ')} />
        )}
        <Row label="PEP Declaration" value={PEP_LABELS[declarations.pepDeclaration] ?? declarations.pepDeclaration} />
        <Row label="Accuracy Consent" value={declarations.accuracyConsent ? 'Confirmed' : 'Not confirmed'} />
        <Row label="Privacy Consent" value={declarations.privacyConsent ? 'Confirmed' : 'Not confirmed'} />
        <Row label="Verification Consent" value={declarations.verificationConsent ? 'Confirmed' : 'Not confirmed'} />
      </ReviewSection>

      {isSubmitting && <LoadingState message="Submitting your application…" />}

      <div className="form-actions">
        <button
          type="button"
          className="btn btn-secondary"
          onClick={onBack}
          disabled={isSubmitting}
        >
          Back
        </button>
        <button
          type="button"
          className="btn btn-primary btn-lg"
          onClick={submitApplication}
          disabled={isSubmitting}
        >
          <Send size={18} />
          {isSubmitting ? 'Submitting…' : 'Submit Application'}
        </button>
      </div>
    </div>
  );
}
