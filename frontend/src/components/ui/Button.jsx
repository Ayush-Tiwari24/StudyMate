import React from 'react';

export default function Button({
  children,
  variant = 'primary', // 'primary' | 'secondary' | 'ghost' | 'link'
  size = 'md', // 'sm' | 'md' | 'lg'
  className = '',
  disabled = false,
  type = 'button',
  onClick,
  ...props
}) {
  const baseStyles = 'inline-flex items-center justify-center font-sans font-medium transition-colors select-none rounded-[6px] border';

  const variantStyles = {
    primary:
      'bg-[var(--accent)] text-white border-transparent hover:bg-[var(--accent-hover)] active:bg-[var(--accent-hover)] disabled:opacity-50 disabled:cursor-not-allowed',
    secondary:
      'bg-[var(--surface)] text-[var(--ink)] border-[var(--line)] hover:bg-[var(--surface-hover)] hover:border-[var(--muted)] disabled:opacity-50 disabled:cursor-not-allowed',
    ghost:
      'bg-transparent text-[var(--muted)] border-transparent hover:bg-[var(--surface-hover)] hover:text-[var(--ink)] disabled:opacity-40 disabled:cursor-not-allowed',
    link:
      'bg-transparent text-[var(--accent)] border-transparent hover:underline p-0 h-auto disabled:opacity-50 disabled:cursor-not-allowed',
  };

  const sizeStyles = {
    sm: 'text-xs px-2.5 py-1 gap-1.5 h-7',
    md: 'text-sm px-3.5 py-1.5 gap-2 h-9',
    lg: 'text-base px-5 py-2.5 gap-2.5 h-11',
  };

  return (
    <button
      type={type}
      disabled={disabled}
      onClick={onClick}
      className={`${baseStyles} ${variantStyles[variant] || variantStyles.primary} ${
        variant !== 'link' ? sizeStyles[size] || sizeStyles.md : ''
      } ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}
