import React from 'react';
import { X } from 'lucide-react';

export default function Chip({
  label,
  onRemove,
  className = '',
  mono = true,
}) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-[6px] border border-[var(--line)] bg-[var(--surface-muted)] text-[var(--ink)] text-xs ${
        mono ? 'font-mono' : 'font-sans'
      } ${className}`}
    >
      <span className="truncate max-w-[200px]" title={label}>
        {label}
      </span>
      {onRemove && (
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onRemove();
          }}
          className="text-[var(--muted)] hover:text-[var(--accent)] transition-colors p-0.5 rounded"
          aria-label={`Remove ${label}`}
        >
          <X size={12} strokeWidth={2} />
        </button>
      )}
    </span>
  );
}
