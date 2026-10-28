import type { ButtonHTMLAttributes, ReactNode } from 'react';

export interface PrimaryButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  children: ReactNode;
  icon?: ReactNode;
  loading?: boolean;
}

export function PrimaryButton({
  children,
  icon,
  loading = false,
  disabled,
  className = '',
  ...props
}: PrimaryButtonProps) {
  return (
    <button
      className={`dash-btn-primary ${className}`.trim()}
      disabled={disabled || loading}
      {...props}
    >
      {loading ? (
        <span
          className="dash-spinner"
          style={{ width: 16, height: 16, borderWidth: 2, borderTopColor: '#ffffff' }}
        />
      ) : (
        icon
      )}
      {children}
    </button>
  );
}

