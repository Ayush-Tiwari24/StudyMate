import React from 'react';

const STATUS_CONFIG = {
  uploaded: {
    color: 'bg-[var(--status-uploaded)]',
    label: 'Uploaded',
    pulse: false,
  },
  processing: {
    color: 'bg-[var(--status-reading)]',
    label: 'Reading',
    pulse: true,
  },
  reading: {
    color: 'bg-[var(--status-reading)]',
    label: 'Reading',
    pulse: true,
  },
  ready: {
    color: 'bg-[var(--status-ready)]',
    label: 'Ready',
    pulse: false,
  },
  failed: {
    color: 'bg-[var(--status-failed)]',
    label: 'Failed',
    pulse: false,
  },
};

export default function StatusDot({
  status = 'uploaded',
  labelOverride,
  className = '',
}) {
  const normalized = (status || '').toLowerCase();
  const config = STATUS_CONFIG[normalized] || STATUS_CONFIG.uploaded;
  const labelText = labelOverride !== undefined ? labelOverride : config.label;

  return (
    <span className={`inline-flex items-center gap-1.5 text-xs font-sans text-[var(--muted)] select-none ${className}`}>
      <span
        data-testid="status-dot"
        className={`w-2 h-2 rounded-full flex-shrink-0 ${config.color} ${
          config.pulse ? 'animate-pulse' : ''
        }`}
        aria-hidden="true"
      />
      {labelText && <span>{labelText}</span>}
    </span>
  );
}
