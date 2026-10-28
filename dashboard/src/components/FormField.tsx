import type { ReactNode } from 'react';

export interface FormFieldProps {
  label: string;
  htmlFor?: string;
  required?: boolean;
  error?: string;
  hint?: string;
  children: ReactNode;
  className?: string;
}

export function FormField({
  label,
  htmlFor,
  required,
  error,
  hint,
  children,
  className = '',
}: FormFieldProps) {
  return (
    <div className={`dash-form-field ${className}`.trim()}>
      <label htmlFor={htmlFor} className="dash-form-label">
        {label}
        {required && <span style={{ color: 'var(--dash-text-muted)', marginLeft: 3 }}>*</span>}
      </label>

      {children}

      {hint && !error && (
        <span style={{ fontSize: '0.8rem', color: 'var(--dash-text-muted)' }}>
          {hint}
        </span>
      )}

      {error && (
        <span style={{ fontSize: '0.8rem', color: '#b91c1c', fontWeight: 600 }}>
          {error}
        </span>
      )}
    </div>
  );
}

