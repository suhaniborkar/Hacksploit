import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { useKYC } from '../../context/KYCContext';
import { FormField } from '../shared/FormField';
import type { DeclarationInfo, Occupation, SourceOfFunds, PEPDeclaration } from '../../types/kyc';

const OCCUPATIONS: { value: Occupation; label: string }[] = [
  { value: 'salaried', label: 'Salaried Employee' },
  { value: 'self_employed', label: 'Self-Employed' },
  { value: 'business_owner', label: 'Business Owner' },
  { value: 'student', label: 'Student' },
  { value: 'unemployed', label: 'Unemployed' },
  { value: 'other', label: 'Other' },
];

const SOURCES_OF_FUNDS: { value: SourceOfFunds; label: string }[] = [
  { value: 'salary', label: 'Salary / Employment Income' },
  { value: 'business_income', label: 'Business Income' },
  { value: 'savings', label: 'Savings' },
  { value: 'investments', label: 'Investments' },
  { value: 'other', label: 'Other' },
];

const PEP_OPTIONS: { value: PEPDeclaration; label: string }[] = [
  { value: 'no', label: 'No — I am not a PEP or associated with one' },
  { value: 'yes', label: 'Yes — I am a PEP or closely associated with one' },
  { value: 'requires_clarification', label: 'Requires clarification — I am unsure' },
];

interface DueDiligenceFormProps {
  onNext: () => void;
  onBack: () => void;
}

export function DueDiligenceForm({ onNext, onBack }: DueDiligenceFormProps) {
  const { application, updateDeclarations } = useKYC();

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
    watch,
  } = useForm<DeclarationInfo>({
    defaultValues: application.declarations,
  });

  useEffect(() => {
    reset(application.declarations);
  }, []);

  const occupation = watch('occupation');

  const onSubmit = (data: DeclarationInfo) => {
    updateDeclarations(data);
    onNext();
  };

  return (
    <form className="step-form" onSubmit={handleSubmit(onSubmit)} noValidate>
      <div className="form-section-header">
        <h2>Additional Information &amp; Declarations</h2>
        <p>
          Please provide the following information to complete your KYC application.
        </p>
      </div>

      <h3 className="subsection-title">Financial &amp; Professional Information</h3>
      <div className="form-grid">
        <FormField
          label="Occupation"
          required
          error={errors.occupation?.message}
          htmlFor="occupation"
        >
          <select
            id="occupation"
            className={`form-input ${errors.occupation ? 'input-error' : ''}`}
            {...register('occupation', { required: 'Please select your occupation.' })}
          >
            <option value="">— Select occupation —</option>
            {OCCUPATIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </FormField>

        {(occupation === 'business_owner' || occupation === 'self_employed') && (
          <FormField label="Nature of Business" htmlFor="natureOfBusiness">
            <input
              id="natureOfBusiness"
              type="text"
              className="form-input"
              placeholder="Describe the nature of your business"
              {...register('natureOfBusiness')}
            />
          </FormField>
        )}

        <FormField label="Source of Funds" htmlFor="sourceOfFunds">
          <select
            id="sourceOfFunds"
            className="form-input"
            {...register('sourceOfFunds')}
          >
            <option value="">— Select source of funds —</option>
            {SOURCES_OF_FUNDS.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
              </option>
            ))}
          </select>
        </FormField>

        <FormField
          label="Politically Exposed Person (PEP) Declaration"
          required
          error={errors.pepDeclaration?.message}
          htmlFor="pepDeclaration"
          hint="A PEP is someone who holds or has held a prominent public function, or is closely associated with such a person."
        >
          <select
            id="pepDeclaration"
            className={`form-input ${errors.pepDeclaration ? 'input-error' : ''}`}
            {...register('pepDeclaration', {
              required: 'Please complete the PEP declaration.',
            })}
          >
            <option value="">— Select —</option>
            {PEP_OPTIONS.map((p) => (
              <option key={p.value} value={p.value}>
                {p.label}
              </option>
            ))}
          </select>
        </FormField>
      </div>

      <div className="form-section-divider">
        <span>Consent &amp; Declarations</span>
      </div>

      <div className="declarations-section">
        <div className="declaration-card">
          <h4>Accuracy of Information</h4>
          <p>
            I confirm that all information provided in this application is accurate and
            complete to the best of my knowledge. I understand that providing false
            information may result in rejection of my application or legal consequences.
          </p>
          <label className="checkbox-label">
            <input
              type="checkbox"
              className="checkbox-input"
              {...register('accuracyConsent', {
                required: 'You must confirm the accuracy of your information.',
              })}
            />
            <span>I confirm that all information provided is accurate and complete.</span>
          </label>
          {errors.accuracyConsent && (
            <p className="field-error" role="alert">
              {errors.accuracyConsent.message}
            </p>
          )}
        </div>

        <div className="declaration-card">
          <h4>Privacy Notice</h4>
          <p>
            I have read and understood how my personal data will be processed for identity
            verification purposes. I consent to the collection and processing of my personal
            information, identity documents, and biometric data as described in the{' '}
            <a href="#" className="text-link" onClick={(e) => e.preventDefault()}>
              Privacy Notice
            </a>
            .
          </p>
          <label className="checkbox-label">
            <input
              type="checkbox"
              className="checkbox-input"
              {...register('privacyConsent', {
                required: 'You must accept the privacy notice to proceed.',
              })}
            />
            <span>I consent to the processing of my personal data for identity verification.</span>
          </label>
          {errors.privacyConsent && (
            <p className="field-error" role="alert">
              {errors.privacyConsent.message}
            </p>
          )}
        </div>

        <div className="declaration-card">
          <h4>Verification Activities</h4>
          <p>
            I authorise the verification service to conduct checks against relevant databases
            and records for the purpose of verifying my identity as part of this KYC process.
          </p>
          <label className="checkbox-label">
            <input
              type="checkbox"
              className="checkbox-input"
              {...register('verificationConsent', {
                required: 'You must authorise the verification activities.',
              })}
            />
            <span>I authorise the verification service to conduct identity checks.</span>
          </label>
          {errors.verificationConsent && (
            <p className="field-error" role="alert">
              {errors.verificationConsent.message}
            </p>
          )}
        </div>
      </div>

      <div className="form-actions">
        <button type="button" className="btn btn-secondary" onClick={onBack}>
          Back
        </button>
        <button type="submit" className="btn btn-primary">
          Continue to Review
        </button>
      </div>
    </form>
  );
}
