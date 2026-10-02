import React from 'react';
import { AlertCircle, HardDrive } from 'lucide-react';

export default function StorageBar({
  usedMb = 0,
  quotaMb = 50,
  percentUsed = 0,
  compact = false,
  className = '',
}) {
  const isWarning = percentUsed >= 80 && percentUsed < 100;
  const isFull = percentUsed >= 100;

  // Format usedMb nicely: "12 MB" if integer, "12.4 MB" if fractional
  const formattedUsed =
    Number(usedMb) % 1 === 0 ? Number(usedMb).toFixed(0) : Number(usedMb).toFixed(1);

  return (
    <div className={`flex flex-col gap-2 ${className}`}>
      {/* Label and text breakdown */}
      <div className="flex items-center justify-between gap-2 text-xs font-sans">
        <span className="text-[var(--muted)] flex items-center gap-1.5 font-medium">
          <HardDrive size={13} className="text-[var(--muted)]" />
          <span>Storage</span>
        </span>
        <span
          className={`font-mono text-xs font-semibold ${
            isFull
              ? 'text-[var(--status-failed)]'
              : isWarning
              ? 'text-[var(--status-amber, #d97706)]'
              : 'text-[var(--ink)]'
          }`}
        >
          {formattedUsed} MB of {quotaMb} MB used
        </span>
      </div>

      {/* Accessible Progress Bar */}
      <div
        role="progressbar"
        aria-valuenow={Math.min(100, Math.round(percentUsed))}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`Storage quota: ${formattedUsed} MB of ${quotaMb} MB used`}
        className="w-full h-2 rounded-full bg-[var(--surface-muted, #e5e5e5)] overflow-hidden"
      >
        <div
          className={`h-full transition-all duration-300 rounded-full ${
            isFull
              ? 'bg-[var(--status-failed, #dc2626)]'
              : isWarning
              ? 'bg-[var(--status-amber, #d97706)]'
              : 'bg-[var(--accent, #4f46e5)]'
          }`}
          style={{ width: `${Math.min(100, Math.max(0, percentUsed))}%` }}
        />
      </div>

      {/* Warning / Error Messages */}
      {isFull ? (
        <div className="flex items-center gap-1.5 text-xs text-[var(--status-failed, #dc2626)] font-sans mt-0.5">
          <AlertCircle size={13} className="flex-shrink-0" />
          <span>You've used all your storage. Delete a document to add more.</span>
        </div>
      ) : isWarning ? (
        <div className="flex items-center gap-1.5 text-xs text-[var(--status-amber, #d97706)] font-sans mt-0.5">
          <AlertCircle size={13} className="flex-shrink-0" />
          <span>Storage almost full ({Math.round(percentUsed)}% used)</span>
        </div>
      ) : null}
    </div>
  );
}
