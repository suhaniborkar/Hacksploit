import { KYCProvider, useKYC } from './context/KYCContext';
import { AppHeader } from './components/layout/AppHeader';
import { WelcomePage } from './pages/WelcomePage';
import { KYCApplicationPage } from './pages/KYCApplicationPage';
import { VerificationResultsPage } from './pages/VerificationResultsPage';
import { PageContainer } from './components/layout/PageContainer';

function AppContent() {
  const { currentStep } = useKYC();

  const renderPage = () => {
    if (currentStep === 'welcome') {
      return (
        <PageContainer>
          <WelcomePage />
        </PageContainer>
      );
    }
    if (currentStep === 'results') {
      return <VerificationResultsPage />;
    }
    return <KYCApplicationPage />;
  };

  return (
    <div className="app">
      <div className="app-global-bg" aria-hidden="true" />
      <div className="app-data-texture" aria-hidden="true">
        <div className="texture-halftone" />
        <div className="forensic-marker marker-bl">
          <div className="pixel-matrix">
            <span className="matrix-row">■ ■ □ ■</span>
            <span className="matrix-row">■ □ ■ ■</span>
            <span className="matrix-row">□ ■ ■ □</span>
          </div>
          <span className="marker-tag">ISO/IEC 19794-5 // BIO-DATA</span>
          <span className="marker-coords">48.912 : 72.854 // HASH_OK</span>
        </div>
        <div className="forensic-marker marker-br">
          <div className="pixel-matrix">
            <span className="matrix-row">□ ■ ■ ■</span>
            <span className="matrix-row">■ ■ □ ■</span>
            <span className="matrix-row">■ □ ■ □</span>
          </div>
          <span className="marker-tag">ID_VECTORS // CORRELATED</span>
          <span className="marker-coords">PKI_CHECKSUM: 9A4F // SECURE</span>
        </div>
        <div className="forensic-marker marker-tl">
          <span className="marker-tag">SYS_ID // 2026.03</span>
          <span className="marker-coords">AUTH_STREAM // 12ms</span>
        </div>
        <div className="forensic-marker marker-tr">
          <span className="marker-tag">GRID // 20.59° N, 78.96° E</span>
          <span className="marker-coords">NODE // IDENT_NET</span>
        </div>
      </div>
      <AppHeader />
      {renderPage()}
    </div>
  );
}

export default function App() {
  return (
    <KYCProvider>
      <AppContent />
    </KYCProvider>
  );
}
