export interface LoadingStateProps {
  message?: string;
  className?: string;
}

export function LoadingState({ message = 'Loading...', className = '' }: LoadingStateProps) {
  return (
    <div className={`dash-loading-state ${className}`.trim()}>
      <div className="dash-spinner" role="status" aria-label="Loading indicator" />
      <p style={{ marginTop: '0.5rem', fontWeight: 600 }}>{message}</p>
    </div>
  );
}

