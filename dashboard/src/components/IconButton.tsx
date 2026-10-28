import type { ButtonHTMLAttributes, ReactNode } from 'react';

export interface IconButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  children: ReactNode;
}

export function IconButton({ children, className = '', ...props }: IconButtonProps) {
  return (
    <button className={`dash-btn-icon ${className}`.trim()} {...props}>
      {children}
    </button>
  );
}

