import type { ReactNode } from 'react';

interface FormFieldProps {
  label: string;
  required?: boolean;
  error?: string;
  hint?: string;
  children: ReactNode;
  htmlFor?: string;
}

export function FormField({
  label,
  required,
  error,
  hint,
  children,
  htmlFor,
}: FormFieldProps) {
  return (
    <div className={`form-field ${error ? 'form-field--error' : ''}`}>
      <label className="field-label" htmlFor={htmlFor}>
        {label}
        {required && <span className="required-mark" aria-hidden="true"> *</span>}
        {!required && <span className="optional-mark"> (optional)</span>}
      </label>
      {children}
      {hint && !error && <p className="field-hint">{hint}</p>}
      {error && (
        <p className="field-error" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
