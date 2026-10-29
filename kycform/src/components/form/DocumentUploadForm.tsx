import { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { AlertTriangle, CheckCircle2, Loader2 } from 'lucide-react';
import { useKYC } from '../../context/KYCContext';
import { FormField } from '../shared/FormField';
import { FileUpload } from '../shared/FileUpload';
import type { DocumentUpload, DocumentType } from '../../types/kyc';

const DOCUMENT_TYPES: { value: DocumentType; label: string; hasBack: boolean; hasExpiry: boolean }[] = [
  { value: 'pan', label: 'PAN Card', hasBack: false, hasExpiry: false },
  { value: 'aadhaar', label: 'Aadhaar Card', hasBack: true, hasExpiry: false },
  { value: 'driving_licence', label: 'Driving Licence', hasBack: true, hasExpiry: true },
];

interface DocumentFormProps {
  onNext: () => void;
  onBack: () => void;
}

interface AnalysisFeedback {
  status: 'analyzing' | 'valid' | 'warning' | 'error';
  title: string;
  message: string;
  detectedType?: string;
  checksumValid?: boolean;
  checksumDetails?: string;
  isAiGenerated?: boolean;
  aiReasons?: string[];
  extractedNumber?: string;
  extractedName?: string;
  extractedFacePreview?: string;
}

export function DocumentUploadForm({ onNext, onBack }: DocumentFormProps) {
  const { application, updateDocument } = useKYC();
  const [frontError, setFrontError] = useState('');
  const [backError, setBackError] = useState('');
  const [analysis, setAnalysis] = useState<AnalysisFeedback | null>(null);
  const [analyzing, setAnalyzing] = useState(false);

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    getValues,
    formState: { errors },
    reset,
  } = useForm<DocumentUpload>({
    defaultValues: application.document,
  });

  useEffect(() => {
    reset(application.document);
  }, []);

  const selectedType = watch('documentType') as DocumentType | '';
  const docConfig = DOCUMENT_TYPES.find((d) => d.value === selectedType);

  const runDocumentAnalysis = async (dataUrl: string, type: string, num?: string) => {
    setAnalyzing(true);
    try {
      const res = await fetch('/api/kyc/document/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          documentType: type,
          documentNumber: num || getValues('documentNumber') || '',
          imagePreview: dataUrl,
        }),
      });

      if (res.ok) {
        const data = await res.json();
        if (data.isAiGenerated || data.kycStatus === 'REJECT') {
          const reasonText = (data.aiReasons && data.aiReasons.length > 0)
            ? data.aiReasons.join('; ')
            : data.kycSummary || 'Synthetic AI generation, C2PA anomaly, or statutory invalidity detected.';
          setAnalysis({
            status: 'error',
            title: data.isAiGenerated ? 'Synthetic AI Document Detected (Rejected)' : 'Document Integrity Rejected',
            message: reasonText,
            detectedType: data.detectedType,
            checksumValid: data.checksumValid,
            checksumDetails: data.checksumDetails,
            isAiGenerated: data.isAiGenerated,
            aiReasons: data.aiReasons,
            extractedFacePreview: data.extractedFacePreview,
          });
          setFrontError(`Verification rejected: ${reasonText}`);
        } else if (data.kycStatus === 'REVIEW' || !data.checksumValid) {
          setAnalysis({
            status: 'warning',
            title: 'Verification Flag / Review Required',
            message: data.kycSummary || data.checksumDetails || 'Format anomaly detected; manual forensic review will be required.',
            detectedType: data.detectedType,
            checksumValid: data.checksumValid,
            checksumDetails: data.checksumDetails,
            extractedFacePreview: data.extractedFacePreview,
          });
          setFrontError('');
        } else {
          setAnalysis({
            status: 'valid',
            title: 'Statutory Credential Confirmed',
            message: `${data.detectedType?.replace('_', ' ')} format & integrity verified.`,
            detectedType: data.detectedType,
            checksumValid: data.checksumValid,
            checksumDetails: data.checksumDetails,
            extractedNumber: data.extractedNumber,
            extractedName: data.extractedName,
            extractedFacePreview: data.extractedFacePreview,
          });
          setFrontError('');
          if (data.extractedNumber && !getValues('documentNumber')) {
            setValue('documentNumber', data.extractedNumber);
          }
        }
      }
    } catch {
      // Backend offline or unreachable
    } finally {
      setAnalyzing(false);
    }
  };

  const validate = (_data: DocumentUpload): boolean => {
    let valid = true;
    if (!application.document.frontImagePreview) {
      setFrontError('Please upload the front image of your identity document.');
      valid = false;
    } else {
      setFrontError('');
    }
    if (docConfig?.hasBack && !application.document.backImagePreview) {
      setBackError('Back side image is required for this identity credential.');
      valid = false;
    } else {
      setBackError('');
    }
    if (analysis?.status === 'error') {
      setFrontError(analysis.message || 'Cannot proceed with forged or AI-generated identity document.');
      valid = false;
    }
    return valid;
  };

  const onSubmit = (data: DocumentUpload) => {
    if (!validate(data)) return;
    updateDocument(data);
    onNext();
  };

  return (
    <form className="step-form" onSubmit={handleSubmit(onSubmit)} noValidate>
      <div className="form-section-header">
        <h2>Identity Document Verification</h2>
        <p>
          Please upload your official government-issued identity credential. Project Argus
          performs real-time multi-plane forensic checks, optical character recognition (OCR),
          and tamper verification.
        </p>
      </div>

      <div className="form-grid">
        <FormField
          label="Document Type"
          required
          error={errors.documentType?.message}
          htmlFor="documentType"
        >
          <select
            id="documentType"
            className={`form-input ${errors.documentType ? 'input-error' : ''}`}
            {...register('documentType', { required: 'Please select a document type.' })}
            onChange={(e) => {
              const val = e.target.value as DocumentType;
              updateDocument({
                documentType: val,
                frontImageRef: undefined,
                backImageRef: undefined,
                frontImagePreview: undefined,
                backImagePreview: undefined,
              });
              setAnalysis(null);
            }}
          >
            <option value="">— Select document type —</option>
            {DOCUMENT_TYPES.map((d) => (
              <option key={d.value} value={d.value}>
                {d.label}
              </option>
            ))}
          </select>
        </FormField>

        <FormField
          label="Document Number"
          required
          error={errors.documentNumber?.message}
          htmlFor="documentNumber"
        >
          <input
            id="documentNumber"
            type="text"
            className={`form-input ${errors.documentNumber ? 'input-error' : ''}`}
            placeholder="e.g. 4597 1693 9274 or ABCDE1234F"
            {...register('documentNumber', {
              required: 'Document number is required.',
            })}
          />
        </FormField>

        <FormField label="Issuing Authority / Country" htmlFor="issuingAuthority">
          <input
            id="issuingAuthority"
            type="text"
            className="form-input"
            placeholder="e.g. Government of India / UIDAI"
            {...register('issuingAuthority')}
          />
        </FormField>

        <FormField label="Issue Date" htmlFor="issueDate">
          <input
            id="issueDate"
            type="date"
            className="form-input"
            {...register('issueDate')}
          />
        </FormField>

        {docConfig?.hasExpiry && (
          <FormField label="Expiry Date" htmlFor="expiryDate">
            <input
              id="expiryDate"
              type="date"
              className="form-input"
              {...register('expiryDate')}
            />
          </FormField>
        )}
      </div>

      {selectedType && (
        <div className="upload-section">
          <h3 className="subsection-title">Official Document Image</h3>

          <div className="upload-grid">
            <FileUpload
              label="Front of Document"
              side="front"
              preview={application.document.frontImagePreview}
              required
              error={frontError}
              onFileSelected={(file, dataUrl) => {
                setFrontError('');
                updateDocument({
                  frontImageRef: file.name,
                  frontImagePreview: dataUrl,
                });
                runDocumentAnalysis(dataUrl, selectedType, getValues('documentNumber'));
              }}
              onRemove={() => {
                updateDocument({ frontImageRef: undefined, frontImagePreview: undefined });
                setAnalysis(null);
              }}
            />

            {docConfig?.hasBack && (
              <FileUpload
                label="Back of Document"
                side="back"
                preview={application.document.backImagePreview}
                required
                error={backError}
                onFileSelected={(file, dataUrl) => {
                  setBackError('');
                  updateDocument({
                    backImageRef: file.name,
                    backImagePreview: dataUrl,
                  });
                }}
                onRemove={() =>
                  updateDocument({ backImageRef: undefined, backImagePreview: undefined })
                }
              />
            )}
          </div>

          {/* Real-Time Forensic Feedback Panel */}
          {analyzing && (
            <div style={{ marginTop: '1rem', padding: '0.85rem 1.1rem', borderRadius: '8px', background: 'rgba(56, 189, 248, 0.08)', border: '1px solid rgba(56, 189, 248, 0.3)', display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
              <Loader2 size={18} className="animate-spin" style={{ color: '#0284c7' }} />
              <span style={{ fontSize: '0.88rem', fontWeight: 600, color: '#0369a1' }}>
                Executing multi-plane forensic checks, C2PA provenance scan, and statutory checksum validation...
              </span>
            </div>
          )}

          {!analyzing && analysis && (
            <div
              style={{
                marginTop: '1rem',
                padding: '1rem 1.25rem',
                borderRadius: '8px',
                background:
                  analysis.status === 'valid'
                    ? 'rgba(34, 197, 94, 0.08)'
                    : analysis.status === 'error'
                    ? 'rgba(239, 68, 68, 0.08)'
                    : 'rgba(245, 158, 11, 0.08)',
                border: `1px solid ${
                  analysis.status === 'valid'
                    ? 'rgba(34, 197, 94, 0.4)'
                    : analysis.status === 'error'
                    ? 'rgba(239, 68, 68, 0.4)'
                    : 'rgba(245, 158, 11, 0.4)'
                }`,
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 700, fontSize: '0.95rem', color: analysis.status === 'valid' ? '#15803d' : analysis.status === 'error' ? '#b91c1c' : '#b45309' }}>
                {analysis.status === 'valid' ? (
                  <CheckCircle2 size={18} />
                ) : (
                  <AlertTriangle size={18} />
                )}
                <span>{analysis.title}</span>
              </div>
              <p style={{ margin: '0.4rem 0 0.2rem', fontSize: '0.86rem', color: '#334155' }}>
                {analysis.message}
              </p>
              {analysis.checksumDetails && (
                <div style={{ marginTop: '0.35rem', fontSize: '0.8rem', color: '#64748b' }}>
                  <strong>Integrity:</strong> {analysis.checksumDetails}
                </div>
              )}
              {analysis.extractedFacePreview && (
                <div style={{ marginTop: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.75rem', background: 'rgba(255,255,255,0.7)', padding: '0.5rem 0.75rem', borderRadius: '6px', border: '1px solid rgba(0,0,0,0.08)' }}>
                  <img
                    src={analysis.extractedFacePreview}
                    alt="Extracted Document Photo"
                    style={{ width: '48px', height: '48px', borderRadius: '4px', objectFit: 'cover', border: '1px solid #cbd5e1' }}
                  />
                  <div>
                    <div style={{ fontSize: '0.75rem', fontWeight: 600, color: '#334155' }}>Biometric Photograph Localized</div>
                    <div style={{ fontSize: '0.7rem', color: '#64748b' }}>Extracted from credential for comparison against live webcam selfie.</div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      <div className="form-actions">
        <button type="button" className="btn btn-secondary" onClick={onBack}>
          Back
        </button>
        <button
          type="submit"
          className="btn btn-primary"
          disabled={analyzing || analysis?.status === 'error'}
          style={analysis?.status === 'error' ? { opacity: 0.5, cursor: 'not-allowed' } : {}}
        >
          Continue
        </button>
      </div>
    </form>
  );
}
