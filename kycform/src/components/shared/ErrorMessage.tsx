import { AlertCircle, RefreshCw } from 'lucide-react';

interface ErrorMessageProps {
  title?: string;
  message: string;
  onRetry?: () => void;
}

export function ErrorMessage({
  title = 'Something went wrong',
  message,
  onRetry,
}: ErrorMessageProps) {
  return (
    <div className="error-message" role="alert">
      <AlertCircle size={24} className="error-icon" />
      <div className="error-body">
        <strong className="error-title">{title}</strong>
        <p className="error-text">{message}</p>
        {onRetry && (
          <button className="btn btn-secondary btn-sm" onClick={onRetry}>
            <RefreshCw size={14} /> Retry
          </button>
        )}
      </div>
    </div>
  );
}
