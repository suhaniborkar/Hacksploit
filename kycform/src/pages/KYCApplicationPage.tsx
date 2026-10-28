import { useKYC } from '../context/KYCContext';
import { StepIndicator } from '../components/layout/StepIndicator';
import { PageContainer } from '../components/layout/PageContainer';
import { PersonalInformationForm } from '../components/form/PersonalInformationForm';
import { ContactAddressForm } from '../components/form/ContactAddressForm';
import { DocumentUploadForm } from '../components/form/DocumentUploadForm';
import { BiometricVerificationForm } from '../components/form/BiometricVerificationForm';
import { DueDiligenceForm } from '../components/form/DueDiligenceForm';
import { ReviewForm } from '../components/form/ReviewForm';

export function KYCApplicationPage() {
  const { currentStep, nextStep, prevStep } = useKYC();

  const renderStep = () => {
    switch (currentStep) {
      case 'personal':
        return <PersonalInformationForm onNext={nextStep} onBack={prevStep} />;
      case 'contact':
        return <ContactAddressForm onNext={nextStep} onBack={prevStep} />;
      case 'documents':
        return <DocumentUploadForm onNext={nextStep} onBack={prevStep} />;
      case 'biometric':
        return <BiometricVerificationForm onNext={nextStep} onBack={prevStep} />;
      case 'declarations':
        return <DueDiligenceForm onNext={nextStep} onBack={prevStep} />;
      case 'review':
        return <ReviewForm onBack={prevStep} />;
      default:
        return null;
    }
  };

  return (
    <PageContainer>
      <StepIndicator />
      {renderStep()}
    </PageContainer>
  );
}

