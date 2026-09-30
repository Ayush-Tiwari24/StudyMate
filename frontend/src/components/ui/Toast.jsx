import React from 'react';

export default function Toast({ message }) {
  if (!message) return null;
  return (
    <div className="bg-[var(--surface)] text-[var(--ink)] border border-[var(--line)] rounded-[6px] px-3.5 py-2 text-xs font-sans shadow-sm">
      {message}
    </div>
  );
}
