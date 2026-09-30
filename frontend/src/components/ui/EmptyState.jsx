import React from 'react';
import Button from './Button';

export default function EmptyState({
  title,
  description,
  actionLabel,
  onAction,
  className = '',
}) {
  return (
    <div className={`flex flex-col items-center justify-center text-center p-8 max-w-md mx-auto ${className}`}>
      {title && (
        <h3 className="font-serif text-lg font-medium text-[var(--ink)] mb-1">
          {title}
        </h3>
      )}
      {description && (
        <p className="text-sm text-[var(--muted)] mb-5 leading-relaxed">
          {description}
        </p>
      )}
      {actionLabel && onAction && (
        <Button variant="primary" onClick={onAction}>
          {actionLabel}
        </Button>
      )}
    </div>
  );
}
