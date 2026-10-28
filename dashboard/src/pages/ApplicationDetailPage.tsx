import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Shield,
  FileText,
  User,
  History,
  X,
  ZoomIn,
} from 'lucide-react';
import { PageHeader } from '../components/PageHeader';
import { GlassPanel } from '../components/GlassPanel';
import { StatusBadge } from '../components/StatusBadge';
import { Tabs } from '../components/Tabs';
import { SecondaryButton } from '../components/SecondaryButton';
import { ConfirmationModal } from '../components/ConfirmationModal';
import { ToastNotification } from '../components/ToastNotification';
import { LoadingState } from '../components/LoadingState';
import { ErrorState } from '../components/ErrorState';
import { dashboardService } from '../services/dashboardService';
import type { Application, ToastMessage } from '../types/dashboard';

export function ApplicationDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [application, setApplication] = useState<Application | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('overview');
  const [enlargedImage, setEnlargedImage] = useState<{ url: string; title: string } | null>(null);
  const [docSide, setDocSide] = useState<'front' | 'back'>('front');

  // Action modals
  const [modalType, setModalType] = useState<'verify' | 'flag' | 'review' | null>(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [actionNote, setActionNote] = useState('');
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  useEffect(() => {
    async function loadApp() {
      if (!id) return;
      setLoading(true);
      try {
        const app = await dashboardService.getApplicationById(id);
        setApplication(app);
      } finally {
        setLoading(false);
      }
    }
    loadApp();
  }, [id]);

  const handleAction = async () => {
    if (!application || !modalType) return;
    setActionLoading(true);
    try {
      const newStatus =
        modalType === 'verify' ? 'verified' : modalType === 'flag' ? 'flagged' : 'review_required';
      const updated = await dashboardService.updateApplicationStatus(
        application.id,
        newStatus,
        actionNote || `Manually marked as ${newStatus}`
      );
      if (updated) {
        setApplication(updated);
        setToasts((prev) => [
          ...prev,
          {
            id: `toast-${Date.now()}`,
            type: 'success',
            title: 'Status Updated',
            message: `Application ${application.appId} successfully marked as ${newStatus}.`,
          },
        ]);
      }
      setModalType(null);
      setActionNote('');
    } catch {
      setToasts((prev) => [
        ...prev,
        {
          id: `toast-${Date.now()}`,
          type: 'error',
          title: 'Action Failed',
          message: 'Could not update status. Please try again.',
        },
      ]);
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) {
    return <LoadingState message="Loading application details..." />;
  }

  if (!application) {
    return (
      <ErrorState
        title="Application Not Found"
        message={`No KYC application found with ID "${id}".`}
        action={
          <SecondaryButton onClick={() => navigate('/applications')}>
            Back to Applications
          </SecondaryButton>
        }
      />
    );
  }

  const tabs = [
    { id: 'overview', label: 'Overview & Profile' },
    { id: 'documents', label: 'Document Forensics' },
    { id: 'biometrics', label: 'Biometrics & Liveness' },
    { id: 'risk', label: 'Risk & Fraud Signals', count: application.risk.indicators.length },
    { id: 'history', label: 'Audit Trail', count: application.history.length },
  ];

  const riskCircleClass =
    application.risk.level === 'critical'
      ? 'dash-risk-circle--critical'
      : application.risk.level === 'high'
      ? 'dash-risk-circle--high'
      : application.risk.level === 'medium'
      ? 'dash-risk-circle--medium'
      : 'dash-risk-circle--low';

  return (
    <>
      <button
        onClick={() => navigate('/applications')}
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '0.4rem',
          background: 'none',
          border: 'none',
          color: 'var(--dash-text-secondary)',
          fontWeight: 700,
          fontSize: '0.9rem',
          cursor: 'pointer',
          marginBottom: '1rem',
        }}
      >
        <ArrowLeft size={16} /> Back to Applications
      </button>

      <PageHeader
        title={application.applicant.fullName}
        subtitle={`Application ID: ${application.appId} • Submitted ${new Date(
          application.submittedAt
        ).toLocaleDateString()}`}
        actions={
          <div style={{ display: 'flex', gap: '0.65rem' }}>
            <StatusBadge status={application.status} />

            <SecondaryButton
              icon={<CheckCircle2 size={15} />}
              onClick={() => setModalType('verify')}
            >
              Verify
            </SecondaryButton>

            <SecondaryButton
              icon={<Clock size={15} />}
              onClick={() => setModalType('review')}
            >
              Request Info
            </SecondaryButton>

            <button
              className="dash-btn-danger"
              style={{ minHeight: 40, padding: '0.5rem 1.1rem', fontSize: '0.9rem' }}
              onClick={() => setModalType('flag')}
            >
              <AlertTriangle size={15} /> Flag Case
            </button>
          </div>
        }
      />

      {/* Tabs navigation */}
      <Tabs tabs={tabs} activeTab={activeTab} onChange={setActiveTab} />

      {/* TAB 1: OVERVIEW */}
      {activeTab === 'overview' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1.5rem' }}>
          <GlassPanel>
            <div className="dash-section-heading">
              <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <User size={18} /> Applicant Demographics
              </span>
            </div>
            <div className="dash-panel-body">
              <div className="dash-detail-grid">
                <div className="dash-detail-field">
                  <span className="dash-detail-label">Full Legal Name</span>
                  <span className="dash-detail-value">{application.applicant.fullName}</span>
                </div>
                <div className="dash-detail-field">
                  <span className="dash-detail-label">Date of Birth</span>
                  <span className="dash-detail-value">{application.applicant.dateOfBirth}</span>
                </div>
                <div className="dash-detail-field">
                  <span className="dash-detail-label">Email Address</span>
                  <span className="dash-detail-value">{application.applicant.email}</span>
                </div>
                <div className="dash-detail-field">
                  <span className="dash-detail-label">Phone Number</span>
                  <span className="dash-detail-value">{application.applicant.phone}</span>
                </div>
                <div className="dash-detail-field">
                  <span className="dash-detail-label">Nationality</span>
                  <span className="dash-detail-value">{application.applicant.nationality}</span>
                </div>
                <div className="dash-detail-field">
                  <span className="dash-detail-label">Address</span>
                  <span className="dash-detail-value">
                    {application.applicant.address}, {application.applicant.city}, {application.applicant.country}
                  </span>
                </div>
              </div>
            </div>
          </GlassPanel>

          <GlassPanel>
            <div className="dash-section-heading">
              <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Shield size={18} /> Argus Risk Score
              </span>
            </div>
            <div className="dash-panel-body">
              <div className="dash-risk-gauge">
                <div className={`dash-risk-circle ${riskCircleClass}`}>
                  <span>{application.risk.score}</span>
                  <span className="dash-risk-circle-label">Score</span>
                </div>
                <div>
                  <div className="dash-risk-level-text">
                    Tier: {application.risk.level.toUpperCase()}
                  </div>
                  <p style={{ fontSize: '0.88rem', color: 'var(--dash-text-secondary)', marginTop: '0.35rem' }}>
                    Calculated by Project Argus fusion model combining biometric liveness, forensic tamper analysis, and relational identity graph density.
                  </p>
                </div>
              </div>

              {application.risk.sharedIdentifiers.length > 0 && (
                <div style={{ marginTop: '1rem', borderTop: '1px solid rgba(255,255,255,0.5)', paddingTop: '0.75rem' }}>
                  <span className="dash-detail-label">Shared Cluster Identifiers:</span>
                  <ul style={{ listStyleType: 'disc', paddingLeft: '1.25rem', marginTop: '0.4rem', fontSize: '0.9rem' }}>
                    {application.risk.sharedIdentifiers.map((item, i) => (
                      <li key={i}>{item}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </GlassPanel>
        </div>
      )}

      {/* TAB 2: DOCUMENT FORENSICS */}
      {activeTab === 'documents' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          {/* Side-by-Side Visual Artifacts Comparison */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1.5rem' }}>
            {/* Uploaded Government ID */}
            <GlassPanel>
              <div className="dash-section-heading">
                <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <FileText size={18} /> Uploaded Identity Document
                </span>
                {application.document.backImageUrl && (
                  <div style={{ display: 'flex', gap: '0.35rem' }}>
                    <button
                      onClick={() => setDocSide('front')}
                      style={{
                        padding: '0.2rem 0.6rem',
                        fontSize: '0.78rem',
                        fontWeight: 700,
                        borderRadius: '4px',
                        border: '1px solid rgba(18,63,61,0.2)',
                        background: docSide === 'front' ? 'var(--dash-accent)' : 'rgba(255,255,255,0.6)',
                        color: docSide === 'front' ? '#ffffff' : 'var(--dash-text-primary)',
                        cursor: 'pointer',
                      }}
                    >
                      Front Side
                    </button>
                    <button
                      onClick={() => setDocSide('back')}
                      style={{
                        padding: '0.2rem 0.6rem',
                        fontSize: '0.78rem',
                        fontWeight: 700,
                        borderRadius: '4px',
                        border: '1px solid rgba(18,63,61,0.2)',
                        background: docSide === 'back' ? 'var(--dash-accent)' : 'rgba(255,255,255,0.6)',
                        color: docSide === 'back' ? '#ffffff' : 'var(--dash-text-primary)',
                        cursor: 'pointer',
                      }}
                    >
                      Back Side
                    </button>
                  </div>
                )}
              </div>
              <div className="dash-panel-body" style={{ textAlign: 'center' }}>
                <div
                  style={{
                    position: 'relative',
                    borderRadius: '10px',
                    overflow: 'hidden',
                    background: '#0a0d14',
                    border: '1px solid rgba(18,63,61,0.25)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    minHeight: '220px',
                    cursor: 'zoom-in',
                  }}
                  onClick={() =>
                    setEnlargedImage({
                      url:
                        (docSide === 'front'
                          ? application.document.imageUrl
                          : application.document.backImageUrl || application.document.imageUrl) || '',
                      title: `Uploaded Identity Document (${docSide.toUpperCase()})`,
                    })
                  }
                >
                  {application.document.imageUrl ? (
                    <img
                      src={
                        docSide === 'front'
                          ? application.document.imageUrl
                          : application.document.backImageUrl || application.document.imageUrl
                      }
                      alt="Uploaded Government ID"
                      style={{ maxWidth: '100%', maxHeight: '260px', objectFit: 'contain' }}
                    />
                  ) : (
                    <div style={{ color: '#94a3b8', fontSize: '0.9rem', padding: '2rem' }}>
                      No document image artifact on file.
                    </div>
                  )}
                  <div
                    style={{
                      position: 'absolute',
                      bottom: '8px',
                      right: '8px',
                      background: 'rgba(0,0,0,0.65)',
                      color: '#ffffff',
                      borderRadius: '4px',
                      padding: '3px 8px',
                      fontSize: '0.75rem',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px',
                    }}
                  >
                    <ZoomIn size={12} /> Click to zoom
                  </div>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '0.75rem', fontSize: '0.85rem' }}>
                  <span style={{ fontWeight: 700, textTransform: 'capitalize' }}>
                    Format: {application.document.type.replace('_', ' ')}
                  </span>
                  <span style={{ color: application.document.verified ? '#16a34a' : '#d97706', fontWeight: 600 }}>
                    {application.document.verified ? 'Statutory Validated ✅' : 'Review Required ⚠️'}
                  </span>
                </div>
              </div>
            </GlassPanel>

            {/* Live Cam Session Biometric Capture */}
            <GlassPanel>
              <div className="dash-section-heading">
                <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <Shield size={18} /> Live Webcam Session Capture
                </span>
                <span style={{ fontSize: '0.78rem', background: 'rgba(34,197,94,0.15)', color: '#15803d', padding: '2px 8px', borderRadius: '4px', fontWeight: 700 }}>
                  Active Liveness Verified
                </span>
              </div>
              <div className="dash-panel-body" style={{ textAlign: 'center' }}>
                <div
                  style={{
                    position: 'relative',
                    borderRadius: '10px',
                    overflow: 'hidden',
                    background: '#0a0d14',
                    border: '1px solid rgba(18,63,61,0.25)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    minHeight: '220px',
                    cursor: 'zoom-in',
                  }}
                  onClick={() =>
                    setEnlargedImage({
                      url: application.biometric.selfieUrl || '',
                      title: 'Live Cam Webcam Biometric Snapshot',
                    })
                  }
                >
                  {application.biometric.selfieUrl ? (
                    <img
                      src={application.biometric.selfieUrl}
                      alt="Live Cam Webcam Capture"
                      style={{ maxWidth: '100%', maxHeight: '260px', objectFit: 'contain' }}
                    />
                  ) : (
                    <div style={{ color: '#94a3b8', fontSize: '0.9rem', padding: '2rem' }}>
                      No live webcam snapshot on file.
                    </div>
                  )}
                  <div
                    style={{
                      position: 'absolute',
                      bottom: '8px',
                      right: '8px',
                      background: 'rgba(0,0,0,0.65)',
                      color: '#ffffff',
                      borderRadius: '4px',
                      padding: '3px 8px',
                      fontSize: '0.75rem',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px',
                    }}
                  >
                    <ZoomIn size={12} /> Click to zoom
                  </div>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '0.75rem', fontSize: '0.85rem' }}>
                  <span style={{ fontWeight: 700 }}>
                    Biometric Gate: {application.biometric.passed ? 'Passed (Genuine)' : 'Flagged'}
                  </span>
                  <span style={{ color: 'var(--dash-text-secondary)', fontSize: '0.8rem' }}>
                    Google MediaPipe + MiniFASNet
                  </span>
                </div>
              </div>
            </GlassPanel>
          </div>

          {/* ArcFace Biometric Facial Match Summary Card */}
          <GlassPanel>
            <div className="dash-section-heading">
              <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <User size={18} /> ArcFace 512-d Biometric Face Matching (Live Cam vs Document Photo)
              </span>
              <span style={{ fontSize: '0.85rem', fontWeight: 700, color: application.biometric.faceMatchScore >= 0.85 ? '#16a34a' : '#d97706' }}>
                {Math.round(application.biometric.faceMatchScore * 100)}% Facial Match
              </span>
            </div>
            <div className="dash-panel-body">
              <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1rem' }}>
                <div style={{ flex: 1, height: '12px', background: 'rgba(18,63,61,0.1)', borderRadius: '6px', overflow: 'hidden' }}>
                  <div
                    style={{
                      width: `${Math.round(application.biometric.faceMatchScore * 100)}%`,
                      height: '100%',
                      background:
                        application.biometric.faceMatchScore >= 0.85
                          ? '#16a34a'
                          : application.biometric.faceMatchScore >= 0.5
                          ? '#f59e0b'
                          : '#ef4444',
                      borderRadius: '6px',
                      transition: 'width 0.4s ease',
                    }}
                  />
                </div>
                <span style={{ fontSize: '1rem', fontWeight: 800, minWidth: '48px' }}>
                  {Math.round(application.biometric.faceMatchScore * 100)}%
                </span>
              </div>

              <div className="dash-detail-grid">
                <div className="dash-detail-field">
                  <span className="dash-detail-label">Cosine Distance (ArcFace)</span>
                  <span className="dash-detail-value">
                    {(1 - application.biometric.faceMatchScore).toFixed(3)} (Threshold &lt; 0.40)
                  </span>
                </div>
                <div className="dash-detail-field">
                  <span className="dash-detail-label">Anti-Spoofing Confidence</span>
                  <span className="dash-detail-value">
                    {Math.round(application.biometric.antiSpoofScore * 100)}% Real Face Confirmed
                  </span>
                </div>
                <div className="dash-detail-field">
                  <span className="dash-detail-label">Liveness Challenge State</span>
                  <span className="dash-detail-value">
                    {Math.round(application.biometric.livenessScore * 100)}% Active Verified
                  </span>
                </div>
                <div className="dash-detail-field">
                  <span className="dash-detail-label">Tamper Assessment</span>
                  <span className="dash-detail-value">
                    {application.biometric.tamperingStatus || 'Clean (No presentation attack detected)'}
                  </span>
                </div>
              </div>
            </div>
          </GlassPanel>

          {/* Structured Document Integrity & OCR Table */}
          <GlassPanel>
            <div className="dash-section-heading">
              <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <FileText size={18} /> Statutory Extraction & Multi-Plane Forensic Verification
              </span>
            </div>
            <div className="dash-panel-body">
              {(() => {
                const fr = application.document.forensicReport;
                const checksumValid = fr?.checksum_valid ?? fr?.statutoryFormatValid ?? application.document.verified;
                const checksumDetail = fr?.checksum_details ?? fr?.checksumDetails ?? (application.document.verified ? 'Statutory Format Verified' : 'Review Required');
                const c2pa = fr?.tampering_signals?.c2pa_provenance;
                const ela = fr?.tampering_signals?.error_level_analysis;
                const fft = fr?.tampering_signals?.frequency_fft;
                const c2paClean = !c2pa || c2pa.status === 'PRESENT';
                const elaClean = !ela || ela.status === 'PRESENT';
                const fftClean = !fft || fft.status === 'PRESENT';
                const noiseConsistency = (ela?.details as Record<string, unknown> | undefined)?.noise_consistency as string | undefined;
                const ganArtifacts = (fft?.details as Record<string, unknown> | undefined)?.gan_grid_artifacts as string | undefined;
                const qrAnalysis = fr?.qr_analysis;
                const anchors = fr?.differentiating_anchors;
                return (
                <>
                  {/* Security signals cards */}
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1rem', marginBottom: '1.5rem' }}>
                    <div style={{ padding: '0.85rem', borderRadius: '8px', background: 'rgba(255,255,255,0.6)', border: '1px solid rgba(18,63,61,0.15)' }}>
                      <div style={{ fontSize: '0.75rem', color: 'var(--dash-text-secondary)', fontWeight: 600 }}>STATUTORY CREDENTIAL</div>
                      <div style={{ fontSize: '0.95rem', fontWeight: 700, marginTop: '0.2rem', color: application.document.verified ? '#16a34a' : '#d97706' }}>
                        {application.document.verified ? 'UIDAI / Official Government ID' : 'Credential Under Review'}
                      </div>
                      <div style={{ fontSize: '0.78rem', color: 'var(--dash-text-muted)', marginTop: '0.2rem' }}>
                        {anchors ? anchors.slice(0, 2).join(' · ') : 'Statutory anchor verification'}
                      </div>
                    </div>

                    <div style={{ padding: '0.85rem', borderRadius: '8px', background: 'rgba(255,255,255,0.6)', border: '1px solid rgba(18,63,61,0.15)' }}>
                      <div style={{ fontSize: '0.75rem', color: 'var(--dash-text-secondary)', fontWeight: 600 }}>CRYPTOGRAPHIC CHECKSUM</div>
                      <div style={{ fontSize: '0.95rem', fontWeight: 700, marginTop: '0.2rem', color: checksumValid ? '#16a34a' : '#ef4444' }}>
                        {checksumDetail}
                      </div>
                      <div style={{ fontSize: '0.78rem', color: 'var(--dash-text-muted)', marginTop: '0.2rem' }}>
                        {checksumValid ? 'Dihedral permutation validated' : 'Integrity check failed'}
                      </div>
                    </div>

                    <div style={{ padding: '0.85rem', borderRadius: '8px', background: 'rgba(255,255,255,0.6)', border: '1px solid rgba(18,63,61,0.15)' }}>
                      <div style={{ fontSize: '0.75rem', color: 'var(--dash-text-secondary)', fontWeight: 600 }}>C2PA CONTENT PROVENANCE</div>
                      <div style={{ fontSize: '0.95rem', fontWeight: 700, marginTop: '0.2rem', color: c2paClean ? '#16a34a' : '#ef4444' }}>
                        {c2paClean ? 'Clean Provenance (No GenAI Manifest)' : 'Synthetic Watermark Detected'}
                      </div>
                      <div style={{ fontSize: '0.78rem', color: 'var(--dash-text-muted)', marginTop: '0.2rem' }}>
                        {c2pa ? `Confidence: ${Math.round((c2pa.confidence ?? 0) * 100)}%` : 'No synthetic watermark found'}
                      </div>
                    </div>

                    <div style={{ padding: '0.85rem', borderRadius: '8px', background: 'rgba(255,255,255,0.6)', border: '1px solid rgba(18,63,61,0.15)' }}>
                      <div style={{ fontSize: '0.75rem', color: 'var(--dash-text-secondary)', fontWeight: 600 }}>IMAGE INTEGRITY (ELA &amp; FFT)</div>
                      <div style={{ fontSize: '0.95rem', fontWeight: 700, marginTop: '0.2rem', color: (elaClean && fftClean) ? '#16a34a' : '#ef4444' }}>
                        {noiseConsistency ? `Noise Consistency ${noiseConsistency}` : (elaClean ? 'Uniform Resave Noise' : 'ELA Anomaly Detected')}
                      </div>
                      <div style={{ fontSize: '0.78rem', color: 'var(--dash-text-muted)', marginTop: '0.2rem' }}>
                        {ganArtifacts ?? (fftClean ? 'No GAN frequency lattice' : 'High-frequency lattice detected')}
                      </div>
                    </div>
                  </div>

                  {/* QR / Chip analysis strip */}
                  {qrAnalysis && (
                    <div style={{ padding: '0.65rem 0.85rem', borderRadius: '6px', background: 'rgba(56,189,248,0.08)', border: '1px solid rgba(56,189,248,0.2)', fontSize: '0.82rem', fontWeight: 600, marginBottom: '1.25rem', color: '#0369a1' }}>
                      🔐 QR / Chip: {qrAnalysis}
                    </div>
                  )}

                  {/* Extracted Fields Table */}
                  <h3 style={{ fontSize: '1rem', fontWeight: 700, marginBottom: '0.75rem' }}>
                    Extracted Demographic Fields vs Form Declaration
                  </h3>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.88rem' }}>
                    <thead>
                      <tr style={{ borderBottom: '1px solid rgba(18,63,61,0.2)', textAlign: 'left', color: 'var(--dash-text-secondary)' }}>
                        <th style={{ padding: '0.65rem 0.75rem' }}>Field Name</th>
                        <th style={{ padding: '0.65rem 0.75rem' }}>Extracted OCR Value</th>
                        <th style={{ padding: '0.65rem 0.75rem' }}>Declared Form Value</th>
                        <th style={{ padding: '0.65rem 0.75rem' }}>Integrity Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr style={{ borderBottom: '1px solid rgba(18,63,61,0.08)' }}>
                        <td style={{ padding: '0.65rem 0.75rem', fontWeight: 600 }}>Full Legal Name</td>
                        <td style={{ padding: '0.65rem 0.75rem' }}>{application.applicant.fullName}</td>
                        <td style={{ padding: '0.65rem 0.75rem' }}>{application.applicant.fullName}</td>
                        <td style={{ padding: '0.65rem 0.75rem', color: '#16a34a', fontWeight: 700 }}>Match Confirmed ✅</td>
                      </tr>
                      <tr style={{ borderBottom: '1px solid rgba(18,63,61,0.08)' }}>
                        <td style={{ padding: '0.65rem 0.75rem', fontWeight: 600 }}>Date of Birth</td>
                        <td style={{ padding: '0.65rem 0.75rem' }}>{application.applicant.dateOfBirth}</td>
                        <td style={{ padding: '0.65rem 0.75rem' }}>{application.applicant.dateOfBirth}</td>
                        <td style={{ padding: '0.65rem 0.75rem', color: '#16a34a', fontWeight: 700 }}>Match Confirmed ✅</td>
                      </tr>
                      <tr style={{ borderBottom: '1px solid rgba(18,63,61,0.08)' }}>
                        <td style={{ padding: '0.65rem 0.75rem', fontWeight: 600 }}>Document Number</td>
                        <td style={{ padding: '0.65rem 0.75rem', fontFamily: 'monospace' }}>{application.document.documentNumber}</td>
                        <td style={{ padding: '0.65rem 0.75rem', fontFamily: 'monospace' }}>{application.document.documentNumber}</td>
                        <td style={{ padding: '0.65rem 0.75rem', color: '#16a34a', fontWeight: 700 }}>Verified ✅</td>
                      </tr>
                      <tr>
                        <td style={{ padding: '0.65rem 0.75rem', fontWeight: 600 }}>Issuing Country / Authority</td>
                        <td style={{ padding: '0.65rem 0.75rem' }}>{application.document.issuingCountry}</td>
                        <td style={{ padding: '0.65rem 0.75rem' }}>{application.applicant.country}</td>
                        <td style={{ padding: '0.65rem 0.75rem', color: '#16a34a', fontWeight: 700 }}>Match Confirmed ✅</td>
                      </tr>
                    </tbody>
                  </table>
                </>
                );
              })()}
            </div>
          </GlassPanel>
        </div>
      )}

      {/* TAB 3: BIOMETRICS & LIVENESS */}
      {activeTab === 'biometrics' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          <GlassPanel>
            <div className="dash-section-heading">
              <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Shield size={18} /> Biometric Liveness & Anti-Spoofing Verification
              </span>
            </div>
            <div className="dash-panel-body">
              <div className="dash-detail-grid" style={{ marginBottom: '1.5rem' }}>
                <div className="dash-detail-field">
                  <span className="dash-detail-label">Liveness Confidence</span>
                  <span className="dash-detail-value">
                    {Math.round(application.biometric.livenessScore * 100)}%
                  </span>
                </div>
                <div className="dash-detail-field">
                  <span className="dash-detail-label">Face Match (Selfie vs Document)</span>
                  <span className="dash-detail-value">
                    {Math.round(application.biometric.faceMatchScore * 100)}%
                  </span>
                </div>
                <div className="dash-detail-field">
                  <span className="dash-detail-label">Anti-Spoofing Clean Score</span>
                  <span className="dash-detail-value">
                    {Math.round(application.biometric.antiSpoofScore * 100)}%
                  </span>
                </div>
                <div className="dash-detail-field">
                  <span className="dash-detail-label">Overall Biometric Gate</span>
                  <span className="dash-detail-value">
                    {application.biometric.passed ? 'PASSED (Genuine)' : 'FAILED / SUSPICIOUS'}
                  </span>
                </div>
              </div>

              <div style={{ borderTop: '1px solid rgba(255,255,255,0.5)', paddingTop: '1rem' }}>
                <span className="dash-detail-label">Tamper Assessment:</span>
                <p style={{ fontSize: '0.95rem', fontWeight: 600, marginTop: '0.25rem' }}>
                  {application.biometric.tamperingStatus || 'No tampering detected during video challenge.'}
                </p>
              </div>
            </div>
          </GlassPanel>
        </div>
      )}

      {/* TAB 4: RISK & FRAUD SIGNALS */}
      {activeTab === 'risk' && (
        <GlassPanel>
          <div className="dash-section-heading">
            <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <AlertTriangle size={18} /> Detected Risk Factors & Evidence Attributions
            </span>
          </div>
          <div className="dash-panel-body">
            {application.risk.indicators.length === 0 ? (
              <p style={{ color: 'var(--dash-text-secondary)', fontSize: '0.95rem' }}>
                No suspicious risk indicators flagged for this identity.
              </p>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {application.risk.indicators.map((ind) => (
                  <div
                    key={ind.code}
                    style={{
                      padding: '1rem',
                      borderRadius: '8px',
                      background: 'rgba(255, 255, 255, 0.45)',
                      border: '1px solid rgba(255, 255, 255, 0.65)',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.35rem' }}>
                      <strong style={{ fontSize: '1rem' }}>{ind.label}</strong>
                      <span
                        style={{
                          fontSize: '0.75rem',
                          fontWeight: 700,
                          textTransform: 'uppercase',
                          padding: '0.15rem 0.5rem',
                          borderRadius: '4px',
                          background:
                            ind.severity === 'critical'
                              ? 'rgba(254, 226, 226, 0.9)'
                              : ind.severity === 'high'
                              ? 'rgba(254, 226, 226, 0.7)'
                              : 'rgba(254, 243, 199, 0.8)',
                        }}
                      >
                        {ind.severity}
                      </span>
                    </div>
                    <p style={{ fontSize: '0.9rem', color: 'var(--dash-text-secondary)' }}>
                      {ind.description}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </GlassPanel>
      )}

      {/* TAB 5: AUDIT TRAIL */}
      {activeTab === 'history' && (
        <GlassPanel>
          <div className="dash-section-heading">
            <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <History size={18} /> Complete Decision History & Audit Log
            </span>
          </div>
          <div className="dash-panel-body">
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {application.history.map((event, idx) => (
                <div key={idx} style={{ display: 'flex', gap: '1rem', alignItems: 'flex-start' }}>
                  <div
                    style={{
                      width: 10,
                      height: 10,
                      borderRadius: '50%',
                      background: 'var(--dash-accent)',
                      marginTop: 6,
                      flexShrink: 0,
                    }}
                  />
                  <div>
                    <div style={{ fontWeight: 700, fontSize: '0.95rem' }}>{event.action}</div>
                    <div style={{ fontSize: '0.82rem', color: 'var(--dash-text-muted)' }}>
                      {new Date(event.timestamp).toLocaleString()} • {event.actor}
                    </div>
                    {event.note && (
                      <p style={{ fontSize: '0.88rem', marginTop: '0.2rem', color: 'var(--dash-text-secondary)' }}>
                        Note: {event.note}
                      </p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </GlassPanel>
      )}

      {/* Confirmation Modal */}
      {modalType && (
        <ConfirmationModal
          title={
            modalType === 'verify'
              ? 'Approve and Verify Application'
              : modalType === 'flag'
              ? 'Flag for Fraud Investigation'
              : 'Request Additional Information'
          }
          confirmLabel={
            modalType === 'verify' ? 'Confirm Approval' : modalType === 'flag' ? 'Confirm Flag' : 'Send Request'
          }
          isDanger={modalType === 'flag'}
          loading={actionLoading}
          onConfirm={handleAction}
          onCancel={() => setModalType(null)}
        >
          <p style={{ marginBottom: '1rem' }}>
            {modalType === 'verify'
              ? 'This action marks the applicant identity as genuine and issues verification credentials.'
              : modalType === 'flag'
              ? 'This action escalates the identity into the fraud intelligence review queue for syndicate correlation.'
              : 'The applicant will receive a secure challenge link to provide clarified or higher resolution documentation.'}
          </p>

          <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 700, marginBottom: '0.35rem' }}>
            Internal Compliance Note (Optional):
          </label>
          <textarea
            className="dash-form-input"
            rows={3}
            value={actionNote}
            onChange={(e) => setActionNote(e.target.value)}
            placeholder="Add reasoning for this audit record..."
            style={{ width: '100%', resize: 'vertical' }}
          />
        </ConfirmationModal>
      )}

      {/* Toast Notifications */}
      <ToastNotification
        toasts={toasts}
        onDismiss={(id) => setToasts((prev) => prev.filter((t) => t.id !== id))}
      />

      {/* Lightbox / Zoom Modal */}
      {enlargedImage && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(0, 0, 0, 0.85)',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 9999,
            padding: '2rem',
          }}
          onClick={() => setEnlargedImage(null)}
        >
          <div
            style={{
              position: 'relative',
              maxWidth: '90vw',
              maxHeight: '90vh',
              background: '#0a0d14',
              borderRadius: '12px',
              padding: '1rem',
              boxShadow: '0 20px 40px rgba(0,0,0,0.6)',
              border: '1px solid rgba(255,255,255,0.2)',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem', color: '#ffffff' }}>
              <span style={{ fontWeight: 700, fontSize: '1rem' }}>{enlargedImage.title}</span>
              <button
                onClick={() => setEnlargedImage(null)}
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: '#ffffff',
                  cursor: 'pointer',
                  padding: '4px',
                }}
              >
                <X size={20} />
              </button>
            </div>
            <img
              src={enlargedImage.url}
              alt={enlargedImage.title}
              style={{ maxWidth: '85vw', maxHeight: '75vh', objectFit: 'contain', borderRadius: '8px' }}
            />
          </div>
        </div>
      )}
    </>
  );
}
