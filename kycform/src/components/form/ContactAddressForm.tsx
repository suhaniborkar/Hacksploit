import { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';
import { useKYC } from '../../context/KYCContext';
import { FormField } from '../shared/FormField';
import type { ContactInfo, AddressInfo } from '../../types/kyc';

const COUNTRIES = [
  { value: 'IN', label: 'India' },
  { value: 'US', label: 'United States' },
  { value: 'GB', label: 'United Kingdom' },
  { value: 'AU', label: 'Australia' },
  { value: 'CA', label: 'Canada' },
  { value: 'SG', label: 'Singapore' },
  { value: 'AE', label: 'United Arab Emirates' },
  { value: 'other', label: 'Other' },
];

interface FormValues extends ContactInfo {
  residential: AddressInfo;
  permanentSameAsResidential: boolean;
  permanent: AddressInfo;
}

function AddressFields({
  prefix,
  register,
  errors,
  required,
}: {
  prefix: 'residential' | 'permanent';
  register: ReturnType<typeof useForm<FormValues>>['register'];
  errors: Record<string, Record<string, { message?: string }>>;
  required: boolean;
}) {
  const e = errors[prefix] as Record<string, { message?: string }> | undefined;
  return (
    <div className="form-grid">
      <FormField
        label="Address Line 1"
        required={required}
        error={e?.line1?.message}
        htmlFor={`${prefix}-line1`}
      >
        <input
          id={`${prefix}-line1`}
          type="text"
          className={`form-input ${e?.line1 ? 'input-error' : ''}`}
          placeholder="House / flat number, street name"
          {...register(`${prefix}.line1` as keyof FormValues, {
            required: required ? 'Address line 1 is required.' : false,
          })}
        />
      </FormField>

      <FormField label="Address Line 2" htmlFor={`${prefix}-line2`}>
        <input
          id={`${prefix}-line2`}
          type="text"
          className="form-input"
          placeholder="Apartment, suite, landmark (optional)"
          {...register(`${prefix}.line2` as keyof FormValues)}
        />
      </FormField>

      <FormField
        label="Locality / Area"
        required={required}
        error={e?.locality?.message}
        htmlFor={`${prefix}-locality`}
      >
        <input
          id={`${prefix}-locality`}
          type="text"
          className={`form-input ${e?.locality ? 'input-error' : ''}`}
          placeholder="Locality or area name"
          {...register(`${prefix}.locality` as keyof FormValues, {
            required: required ? 'Locality is required.' : false,
          })}
        />
      </FormField>

      <FormField
        label="City"
        required={required}
        error={e?.city?.message}
        htmlFor={`${prefix}-city`}
      >
        <input
          id={`${prefix}-city`}
          type="text"
          className={`form-input ${e?.city ? 'input-error' : ''}`}
          placeholder="City"
          {...register(`${prefix}.city` as keyof FormValues, {
            required: required ? 'City is required.' : false,
          })}
        />
      </FormField>

      <FormField
        label="State / Region"
        required={required}
        error={e?.stateRegion?.message}
        htmlFor={`${prefix}-state`}
      >
        <input
          id={`${prefix}-state`}
          type="text"
          className={`form-input ${e?.stateRegion ? 'input-error' : ''}`}
          placeholder="State or region"
          {...register(`${prefix}.stateRegion` as keyof FormValues, {
            required: required ? 'State / Region is required.' : false,
          })}
        />
      </FormField>

      <FormField
        label="PIN / Postal Code"
        required={required}
        error={e?.postalCode?.message}
        htmlFor={`${prefix}-postal`}
      >
        <input
          id={`${prefix}-postal`}
          type="text"
          className={`form-input ${e?.postalCode ? 'input-error' : ''}`}
          placeholder="Postal code"
          {...register(`${prefix}.postalCode` as keyof FormValues, {
            required: required ? 'PIN / Postal code is required.' : false,
            pattern: { value: /^[A-Z0-9 -]{3,10}$/i, message: 'Invalid postal code format.' },
          })}
        />
      </FormField>

      <FormField
        label="Country"
        required={required}
        error={e?.country?.message}
        htmlFor={`${prefix}-country`}
      >
        <select
          id={`${prefix}-country`}
          className={`form-input ${e?.country ? 'input-error' : ''}`}
          {...register(`${prefix}.country` as keyof FormValues, {
            required: required ? 'Country is required.' : false,
          })}
        >
          <option value="">— Select country —</option>
          {COUNTRIES.map((c) => (
            <option key={c.value} value={c.value}>
              {c.label}
            </option>
          ))}
        </select>
      </FormField>
    </div>
  );
}

interface ContactAddressFormProps {
  onNext: () => void;
  onBack: () => void;
}

export function ContactAddressForm({ onNext, onBack }: ContactAddressFormProps) {
  const { application, updateContact, updateAddress } = useKYC();
  const [sameAddress, setSameAddress] = useState(
    application.address.permanentSameAsResidential
  );

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<FormValues>({
    defaultValues: {
      mobile: application.contact.mobile,
      email: application.contact.email,
      residential: application.address.residential,
      permanentSameAsResidential: application.address.permanentSameAsResidential,
      permanent: application.address.permanent ?? {
        line1: '',
        locality: '',
        city: '',
        stateRegion: '',
        postalCode: '',
        country: '',
      },
    },
  });

  useEffect(() => {
    reset({
      mobile: application.contact.mobile,
      email: application.contact.email,
      residential: application.address.residential,
      permanentSameAsResidential: application.address.permanentSameAsResidential,
      permanent: application.address.permanent ?? {
        line1: '',
        locality: '',
        city: '',
        stateRegion: '',
        postalCode: '',
        country: '',
      },
    });
  }, []);

  const onSubmit = (data: FormValues) => {
    updateContact({ mobile: data.mobile, email: data.email });
    updateAddress({
      residential: data.residential,
      permanentSameAsResidential: sameAddress,
      permanent: sameAddress ? undefined : data.permanent,
    });
    onNext();
  };

  const errs = errors as Record<string, Record<string, { message?: string }>>;

  return (
    <form className="step-form" onSubmit={handleSubmit(onSubmit)} noValidate>
      <div className="form-section-header">
        <h2>Contact Information &amp; Address</h2>
        <p>Provide your contact details and current residential address.</p>
      </div>

      <h3 className="subsection-title">Contact Details</h3>
      <div className="form-grid">
        <FormField
          label="Mobile Number"
          required
          error={errors.mobile?.message}
          htmlFor="mobile"
        >
          <input
            id="mobile"
            type="tel"
            className={`form-input ${errors.mobile ? 'input-error' : ''}`}
            placeholder="+91 98765 43210"
            {...register('mobile', {
              required: 'Mobile number is required.',
              pattern: {
                value: /^\+?[0-9\s\-()]{7,15}$/,
                message: 'Please enter a valid mobile number.',
              },
            })}
          />
        </FormField>

        <FormField
          label="Email Address"
          required
          error={errors.email?.message}
          htmlFor="email"
        >
          <input
            id="email"
            type="email"
            className={`form-input ${errors.email ? 'input-error' : ''}`}
            placeholder="you@example.com"
            {...register('email', {
              required: 'Email address is required.',
              pattern: {
                value: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
                message: 'Please enter a valid email address.',
              },
            })}
          />
        </FormField>
      </div>

      <h3 className="subsection-title">Residential Address</h3>
      <AddressFields prefix="residential" register={register} errors={errs} required />

      <div className="checkbox-field">
        <label className="checkbox-label">
          <input
            type="checkbox"
            checked={sameAddress}
            onChange={(e) => setSameAddress(e.target.checked)}
            className="checkbox-input"
          />
          <span>Permanent address is the same as residential address</span>
        </label>
      </div>

      {!sameAddress && (
        <>
          <h3 className="subsection-title">Permanent Address</h3>
          <AddressFields prefix="permanent" register={register} errors={errs} required={!sameAddress} />
        </>
      )}

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
