import type { ButtonHTMLAttributes, ReactNode } from 'react';

export interface SecondaryButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  children: ReactNode;
  icon?: ReactNode;
}

export function SecondaryButton({
  children,
  icon,
  className = '',
  disabled,
  ...props
}: SecondaryButtonProps) {
  return (
    <button
      className={`dash-btn-secondary ${className}`.trim()}
      disabled={disabled}
      {...props}
    >
      {icon}
      {children}
    </button>
  );
}

