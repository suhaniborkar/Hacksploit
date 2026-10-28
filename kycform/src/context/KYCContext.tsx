import React, { createContext, useContext, useState, useCallback } from 'react';
import type {
  KYCApplication,
  KYCStep,
  PersonalInfo,
  ContactInfo,
  AddressSection,
  DocumentUpload,
  BiometricInfo,
  DeclarationInfo,
  VerificationResult,
} from '../types/kyc';
import { initialApplication, STEPS } from '../types/kyc';
import { submitKYCApplication, fetchVerificationResult } from '../services/kycApi';

interface KYCContextValue {
  application: KYCApplication;
  currentStep: KYCStep;
  currentStepIndex: number;

  updatePersonal: (data: Partial<PersonalInfo>) => void;
  updateContact: (data: Partial<ContactInfo>) => void;
  updateAddress: (data: Partial<AddressSection>) => void;
  updateDocument: (data: Partial<DocumentUpload>) => void;
  updateBiometric: (data: Partial<BiometricInfo>) => void;
  updateDeclarations: (data: Partial<DeclarationInfo>) => void;

  goToStep: (step: KYCStep) => void;
  nextStep: () => void;
  prevStep: () => void;

  submitApplication: () => Promise<void>;
  resetApplication: () => void;
}

const KYCContext = createContext<KYCContextValue | null>(null);

export function KYCProvider({ children }: { children: React.ReactNode }) {
  const [application, setApplication] = useState<KYCApplication>(initialApplication);
  const [currentStep, setCurrentStep] = useState<KYCStep>('welcome');

  const currentStepIndex = STEPS.indexOf(currentStep);

  const updatePersonal = useCallback((data: Partial<PersonalInfo>) => {
    setApplication((prev) => ({
      ...prev,
      personal: { ...prev.personal, ...data },
    }));
  }, []);

  const updateContact = useCallback((data: Partial<ContactInfo>) => {
    setApplication((prev) => ({
      ...prev,
      contact: { ...prev.contact, ...data },
    }));
  }, []);

  const updateAddress = useCallback((data: Partial<AddressSection>) => {
    setApplication((prev) => ({
      ...prev,
      address: { ...prev.address, ...data },
    }));
  }, []);

  const updateDocument = useCallback((data: Partial<DocumentUpload>) => {
    setApplication((prev) => ({
      ...prev,
      document: { ...prev.document, ...data },
    }));
  }, []);

  const updateBiometric = useCallback((data: Partial<BiometricInfo>) => {
    setApplication((prev) => ({
      ...prev,
      biometric: { ...prev.biometric, ...data },
    }));
  }, []);

  const updateDeclarations = useCallback((data: Partial<DeclarationInfo>) => {
    setApplication((prev) => ({
      ...prev,
      declarations: { ...prev.declarations, ...data },
    }));
  }, []);

  const goToStep = useCallback((step: KYCStep) => {
    setCurrentStep(step);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, []);

  const nextStep = useCallback(() => {
    const idx = STEPS.indexOf(currentStep);
    if (idx < STEPS.length - 1) {
      setCurrentStep(STEPS[idx + 1]);
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  }, [currentStep]);

  const prevStep = useCallback(() => {
    const idx = STEPS.indexOf(currentStep);
    if (idx > 0) {
      setCurrentStep(STEPS[idx - 1]);
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  }, [currentStep]);

  const submitApplication = useCallback(async () => {
    setApplication((prev) => ({ ...prev, submissionStatus: 'submitting' }));
    try {
      const { applicationRef, submittedAt } = await submitKYCApplication(application);
      setApplication((prev) => ({
        ...prev,
        submissionStatus: 'submitted',
        result: {
          applicationRef,
          submittedAt,
          outcome: 'processing',
          checks: [],
          riskIndicators: [],
          mismatches: [],
        } as VerificationResult,
      }));
      setCurrentStep('results');
      window.scrollTo({ top: 0, behavior: 'smooth' });

      // Fetch verification result (incorporating Biometric Vision result if present)
      const result = await fetchVerificationResult(applicationRef, application.biometric);
      setApplication((prev) => ({ ...prev, result }));
    } catch (err) {
      setApplication((prev) => ({
        ...prev,
        submissionStatus: 'error',
        submissionError:
          err instanceof Error ? err.message : 'An unexpected error occurred. Please try again.',
      }));
    }
  }, [application]);

  const resetApplication = useCallback(() => {
    setApplication(initialApplication);
    setCurrentStep('welcome');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, []);

  return (
    <KYCContext.Provider
      value={{
        application,
        currentStep,
        currentStepIndex,
        updatePersonal,
        updateContact,
        updateAddress,
        updateDocument,
        updateBiometric,
        updateDeclarations,
        goToStep,
        nextStep,
        prevStep,
        submitApplication,
        resetApplication,
      }}
    >
      {children}
    </KYCContext.Provider>
  );
}

export function useKYC(): KYCContextValue {
  const ctx = useContext(KYCContext);
  if (!ctx) throw new Error('useKYC must be used inside KYCProvider');
  return ctx;
}
