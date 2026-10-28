import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { useKYC } from '../../context/KYCContext';
import { FormField } from '../shared/FormField';
import type { PersonalInfo, Nationality, ResidencyStatus, Gender, MaritalStatus } from '../../types/kyc';

const NATIONALITIES: { value: Nationality; label: string }[] = [
  { value: 'IN', label: 'Indian' },
  { value: 'US', label: 'American' },
  { value: 'GB', label: 'British' },
  { value: 'AU', label: 'Australian' },
  { value: 'CA', label: 'Canadian' },
  { value: 'SG', label: 'Singaporean' },
  { value: 'AE', label: 'Emirati' },
  { value: 'other', label: 'Other' },
];

const RESIDENCY_STATUSES: { value: ResidencyStatus; label: string }[] = [
  { value: 'citizen', label: 'Citizen' },
  { value: 'permanent_resident', label: 'Permanent Resident' },
  { value: 'temporary_resident', label: 'Temporary Resident' },
  { value: 'non_resident', label: 'Non-Resident' },
  { value: 'other', label: 'Other' },
];

const GENDERS: { value: Gender; label: string }[] = [
  { value: 'male', label: 'Male' },
  { value: 'female', label: 'Female' },
  { value: 'non_binary', label: 'Non-binary' },
  { value: 'prefer_not_to_say', label: 'Prefer not to say' },
];

const MARITAL_STATUSES: { value: MaritalStatus; label: string }[] = [
  { value: 'single', label: 'Single' },
  { value: 'married', label: 'Married' },
  { value: 'divorced', label: 'Divorced' },
  { value: 'widowed', label: 'Widowed' },
  { value: 'other', label: 'Other' },
];

// Minimum age: 18, Maximum age: 120
function getMaxDOB(): string {
  const d = new Date();
  d.setFullYear(d.getFullYear() - 18);
  return d.toISOString().split('T')[0];
}

function getMinDOB(): string {
  const d = new Date();
  d.setFullYear(d.getFullYear() - 120);
  return d.toISOString().split('T')[0];
}

interface PersonalFormProps {
  onNext: () => void;
  onBack: () => void;
}

export function PersonalInformationForm({ onNext, onBack }: PersonalFormProps) {
  const { application, updatePersonal } = useKYC();

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<PersonalInfo>({
    defaultValues: application.personal,
  });

  useEffect(() => {
    reset(application.personal);
  }, []);

  const onSubmit = (data: PersonalInfo) => {
    updatePersonal(data);
    onNext();
  };

  return (
    <form className="step-form" onSubmit={handleSubmit(onSubmit)} noValidate>
      <div className="form-section-header">
        <h2>Personal Information</h2>
        <p>Please provide your legal details exactly as they appear on your identity documents.</p>
      </div>

      <div className="form-grid">
        <FormField label="Full Legal Name" required error={errors.fullName?.message} htmlFor="fullName">
          <input
            id="fullName"
            type="text"
            className={`form-input ${errors.fullName ? 'input-error' : ''}`}
            placeholder="e.g. Priya Sharma"
            {...register('fullName', {
              required: 'Full legal name is required.',
              validate: (v) =>
                v.trim().length > 0 || 'Full legal name cannot be blank or whitespace.',
            })}
          />
        </FormField>

        <FormField
          label="Date of Birth"
          required
          error={errors.dateOfBirth?.message}
          htmlFor="dateOfBirth"
        >
          <input
            id="dateOfBirth"
            type="date"
            className={`form-input ${errors.dateOfBirth ? 'input-error' : ''}`}
            max={getMaxDOB()}
            min={getMinDOB()}
            {...register('dateOfBirth', {
              required: 'Date of birth is required.',
              validate: (v) => {
                if (!v) return 'Date of birth is required.';
                const d = new Date(v);
                if (isNaN(d.getTime())) return 'Please enter a valid date.';
                if (d > new Date(getMaxDOB())) return 'You must be at least 18 years old.';
                if (d < new Date(getMinDOB())) return 'Please enter a valid date of birth.';
                return true;
              },
            })}
          />
        </FormField>

        <FormField
          label="Nationality"
          required
          error={errors.nationality?.message}
          htmlFor="nationality"
        >
          <select
            id="nationality"
            className={`form-input ${errors.nationality ? 'input-error' : ''}`}
            {...register('nationality', { required: 'Please select your nationality.' })}
          >
            <option value="">— Select nationality —</option>
            {NATIONALITIES.map((n) => (
              <option key={n.value} value={n.value}>
                {n.label}
              </option>
            ))}
          </select>
        </FormField>

        <FormField
          label="Residency Status"
          required
          error={errors.residencyStatus?.message}
          htmlFor="residencyStatus"
        >
          <select
            id="residencyStatus"
            className={`form-input ${errors.residencyStatus ? 'input-error' : ''}`}
            {...register('residencyStatus', { required: 'Please select your residency status.' })}
          >
            <option value="">— Select residency status —</option>
            {RESIDENCY_STATUSES.map((r) => (
              <option key={r.value} value={r.value}>
                {r.label}
              </option>
            ))}
          </select>
        </FormField>
      </div>

      <div className="form-section-divider">
        <span>Optional Details</span>
      </div>

      <div className="form-grid">
        <FormField label="Father's Name" htmlFor="fathersName">
          <input
            id="fathersName"
            type="text"
            className="form-input"
            placeholder="Father's full name"
            {...register('fathersName')}
          />
        </FormField>

        <FormField label="Mother's Name" htmlFor="mothersName">
          <input
            id="mothersName"
            type="text"
            className="form-input"
            placeholder="Mother's full name"
            {...register('mothersName')}
          />
        </FormField>

        <FormField label="Spouse's Name" htmlFor="spouseName">
          <input
            id="spouseName"
            type="text"
            className="form-input"
            placeholder="Spouse's full name"
            {...register('spouseName')}
          />
        </FormField>

        <FormField label="Gender" htmlFor="gender">
          <select id="gender" className="form-input" {...register('gender')}>
            <option value="">— Select gender —</option>
            {GENDERS.map((g) => (
              <option key={g.value} value={g.value}>
                {g.label}
              </option>
            ))}
          </select>
        </FormField>

        <FormField label="Marital Status" htmlFor="maritalStatus">
          <select id="maritalStatus" className="form-input" {...register('maritalStatus')}>
            <option value="">— Select marital status —</option>
            {MARITAL_STATUSES.map((m) => (
              <option key={m.value} value={m.value}>
                {m.label}
              </option>
            ))}
          </select>
        </FormField>
      </div>

      <div className="form-actions">
        <button type="button" className="btn btn-secondary" onClick={onBack}>
          Back
        </button>
        <button type="submit" className="btn btn-primary">
          Continue
        </button>
      </div>
    </form>
  );
}
