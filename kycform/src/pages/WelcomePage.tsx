import { Shield, Clock, FileText, Camera, CheckSquare, ArrowRight } from 'lucide-react';
import { useKYC } from '../context/KYCContext';

export function WelcomePage() {
  const { nextStep } = useKYC();

  return (
    <div className="welcome-page">
      <div className="welcome-hero">
        <div className="welcome-icon-ring">
          <Shield size={52} />
        </div>
        <h1 className="welcome-title">Identity Verification</h1>
        <p className="welcome-subtitle">
          Complete your Know Your Customer (KYC) verification to access our services.
        </p>
      </div>

      <div className="welcome-card">
        <div className="welcome-time">
          <Clock size={16} />
          <span>Estimated completion time: <strong>10–15 minutes</strong></span>
        </div>

        <h2 className="welcome-section-title">What you'll need</h2>
        <ul className="welcome-requirements">
          <li>
            <FileText size={20} className="req-icon" />
            <div>
              <strong>Identity Document</strong>
              <p>PAN card, Passport, Driving Licence, Voter ID, or Aadhaar card</p>
            </div>
          </li>
          <li>
            <Camera size={20} className="req-icon" />
            <div>
              <strong>Selfie Photograph</strong>
              <p>A clear, well-lit photo of your face</p>
            </div>
          </li>
          <li>
            <CheckSquare size={20} className="req-icon" />
            <div>
              <strong>Personal Details</strong>
              <p>Contact information, address, and basic personal information</p>
            </div>
          </li>
        </ul>

        <div className="welcome-notice">
          <h3>Privacy & Security Notice</h3>
          <p>
            The information and identity documents you provide will be processed using
            cryptographic zero-knowledge proofing and biometric liveness verification in
            accordance with statutory digital identity standards.
          </p>
        </div>

        <div className="welcome-steps-preview">
          <h3>Verification Steps</h3>
          <ol className="steps-list">
            <li>Personal Information</li>
            <li>Contact Details &amp; Address</li>
            <li>Identity Document Upload</li>
            <li>Biometric Verification</li>
            <li>Declarations &amp; Consents</li>
            <li>Review &amp; Submit</li>
          </ol>
        </div>

        <button className="btn btn-primary btn-lg welcome-cta" onClick={nextStep}>
          Start Verification <ArrowRight size={20} />
        </button>
      </div>
    </div>
  );
}

