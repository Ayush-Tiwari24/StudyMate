import React from 'react';

export default function Input({
  type = 'text',
  className = '',
  error = false,
  ...props
}) {
  return (
    <input
      type={type}
      className={`w-full rounded-[6px] border border-[var(--line)] bg-[var(--surface)] px-3 py-2 text-sm text-[var(--ink)] placeholder-[var(--subtle)] transition-colors focus:border-[var(--accent)] focus:outline-none disabled:opacity-50 ${
        error ? 'border-[var(--status-failed)] focus:border-[var(--status-failed)]' : ''
      } ${className}`}
      {...props}
    />
  );
}
