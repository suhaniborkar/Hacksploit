interface ValidationMessageProps {
  message: string;
  type?: 'error' | 'info' | 'success' | 'warning';
}

export function ValidationMessage({ message, type = 'error' }: ValidationMessageProps) {
  return (
    <div className={`validation-msg validation-msg--${type}`} role="alert">
      {message}
    </div>
  );
}
