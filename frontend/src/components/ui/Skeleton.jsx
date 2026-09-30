import React from 'react';

export default function Skeleton({ className = '', lines = 1 }) {
  if (lines > 1) {
    return (
      <div className="space-y-2 w-full">
        {Array.from({ length: lines }).map((_, i) => (
          <div
            key={i}
            className={`h-4 bg-[var(--surface-muted)] rounded-[4px] animate-pulse ${
              i === lines - 1 ? 'w-3/4' : 'w-full'
            } ${className}`}
          />
        ))}
      </div>
    );
  }

  return (
    <div
      className={`h-4 bg-[var(--surface-muted)] rounded-[4px] animate-pulse ${className}`}
    />
  );
}
