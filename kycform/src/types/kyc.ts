// KYC Application Types

export type KYCStep =
  | 'welcome'
  | 'personal'
  | 'contact'
  | 'documents'
  | 'biometric'
  | 'declarations'
  | 'review'
  | 'results';

export const STEPS: KYCStep[] = [
  'welcome',
  'personal',
  'contact',
  'documents',
  'biometric',
  'declarations',
  'review',
  'results',
];

export const STEP_LABELS: Record<KYCStep, string> = {
  welcome: 'Welcome',
  personal: 'Personal Info',
  contact: 'Contact & Address',
  documents: 'Documents',
  biometric: 'Biometrics',
  declarations: 'Declarations',
  review: 'Review',
  results: 'Results',
};

export type Nationality =
  | 'IN' | 'US' | 'GB' | 'AU' | 'CA' | 'SG' | 'AE' | 'other';

export type ResidencyStatus =
  | 'citizen' | 'permanent_resident' | 'temporary_resident' | 'non_resident' | 'other';

export type Gender = 'male' | 'female' | 'non_binary' | 'prefer_not_to_say';

export type MaritalStatus = 'single' | 'married' | 'divorced' | 'widowed' | 'other';

export interface PersonalInfo {
  fullName: string;
  dateOfBirth: string; // ISO date YYYY-MM-DD
  nationality?: Nationality | '';
  residencyStatus: ResidencyStatus | '';
  fathersName?: string;
  mothersName?: string;
  spouseName?: string;
  gender?: Gender | '';
  maritalStatus?: MaritalStatus | '';
}

export interface ContactInfo {
  mobile: string;
  email: string;
}

export interface AddressInfo {
  line1: string;
  line2?: string;
  locality: string;
  city: string;
  stateRegion: string;
  postalCode: string;
  country: string;
}

export interface AddressSection {
  residential: AddressInfo;
  permanentSameAsResidential: boolean;
  permanent?: AddressInfo;
}

export type DocumentType = 'pan' | 'aadhaar' | 'driving_licence';

export interface DocumentUpload {
  documentType: DocumentType | '';
  documentNumber: string;
  issuingAuthority?: string;
  issuingCountry?: string;
  issueDate?: string;
  expiryDate?: string;
  frontImageRef?: string;  // file name or upload ID
  backImageRef?: string;
  frontImagePreview?: string; // data URL for preview
  backImagePreview?: string;
}

export interface BiometricVisionResult {
  sessionId?: string;
  livenessPassed: boolean;
  prediction?: string; // e.g. "0.9980"
  scorePercent?: number; // e.g. 99.8
  eyeClosed?: boolean;
  faceCenter?: boolean;
  faceDirection?: string;
  failureReason?: string | null;
  facePhoto?: string;
  verifiedAt?: string;
  mode: 'live' | 'simulated';
  // Real Local Pipeline telemetry:
  verifiedBy?: 'mediapipe_local' | 'biometric_vision' | 'simulated';
  activeChallengesCompleted?: string[];
  antiSpoofResult?: {
    isReal: boolean;
    status: 'real' | 'spoof' | 'uncertain' | 'unavailable';
    confidencePercent: number;
    logitDiff: number;
  };
  videoEvidenceUrl?: string;
  videoEvidenceFileName?: string;
}

export interface BiometricInfo {
  selfieRef?: string;
  selfiePreview?: string;
  livenessMode: 'live';
  livenessStatus?: 'pending' | 'passed' | 'failed';
  livenessProvider?: 'mediapipe_local' | 'biometric_vision';
  visionResult?: BiometricVisionResult;
  consentGiven?: boolean;
}

export type Occupation =
  | 'salaried' | 'self_employed' | 'business_owner' | 'student' | 'unemployed' | 'other';

export type SourceOfFunds =
  | 'salary' | 'business_income' | 'savings' | 'investments' | 'other';

export type PEPDeclaration = 'no' | 'yes' | 'requires_clarification';

export interface DeclarationInfo {
  occupation: Occupation | '';
  natureOfBusiness?: string;
  sourceOfFunds?: SourceOfFunds | '';
  pepDeclaration: PEPDeclaration | '';
  accuracyConsent: boolean;
  privacyConsent: boolean;
  verificationConsent: boolean;
}

export type SubmissionStatus =
  | 'idle'
  | 'submitting'
  | 'submitted'
  | 'error';

export type VerificationOutcome =
  | 'verified'
  | 'review_required'
  | 'high_risk'
  | 'processing'
  | 'unable_to_complete';

export type CheckStatus =
  | 'passed'
  | 'failed'
  | 'pending'
  | 'not_checked'
  | 'not_available';

export interface VerificationCheck {
  name: string;
  status: CheckStatus;
  explanation: string;
  evidence?: string;
}

export interface VerificationResult {
  applicationRef: string;
  submittedAt: string;
  outcome: VerificationOutcome;
  overallRiskScore?: number; // 0–100
  checks: VerificationCheck[];
  riskIndicators: string[];
  mismatches: string[];
  recommendedAction?: string;
}

export interface KYCApplication {
  personal: PersonalInfo;
  contact: ContactInfo;
  address: AddressSection;
  document: DocumentUpload;
  biometric: BiometricInfo;
  declarations: DeclarationInfo;
  submissionStatus: SubmissionStatus;
  submissionError?: string;
  result?: VerificationResult;
}

export const emptyPersonal: PersonalInfo = {
  fullName: '',
  dateOfBirth: '',
  nationality: '',
  residencyStatus: '',
};

export const emptyContact: ContactInfo = {
  mobile: '',
  email: '',
};

export const emptyAddress: AddressInfo = {
  line1: '',
  line2: '',
  locality: '',
  city: '',
  stateRegion: '',
  postalCode: '',
  country: '',
};

export const emptyAddressSection: AddressSection = {
  residential: { ...emptyAddress },
  permanentSameAsResidential: true,
};

export const emptyDocument: DocumentUpload = {
  documentType: '',
  documentNumber: '',
};

export const emptyBiometric: BiometricInfo = {
  livenessMode: 'live',
};

export const emptyDeclarations: DeclarationInfo = {
  occupation: '',
  pepDeclaration: '',
  accuracyConsent: false,
  privacyConsent: false,
  verificationConsent: false,
};

export const initialApplication: KYCApplication = {
  personal: { ...emptyPersonal },
  contact: { ...emptyContact },
  address: { ...emptyAddressSection },
  document: { ...emptyDocument },
  biometric: { ...emptyBiometric },
  declarations: { ...emptyDeclarations },
  submissionStatus: 'idle',
};
