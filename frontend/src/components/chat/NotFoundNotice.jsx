import React from 'react';

export default function NotFoundNotice({ onSelectMore }) {
  return (
    <div
      className="p-4 bg-[var(--surface-muted)] border border-[var(--line)] rounded-[6px] text-sm text-[var(--muted)] leading-relaxed my-2"
      role="status"
    >
      <p>
        Nothing in your selected notes covers this. Try selecting more documents on your shelf.
      </p>
      {onSelectMore && (
        <button
          type="button"
          onClick={onSelectMore}
          className="text-xs text-[var(--accent)] hover:underline mt-2 inline-block font-medium"
        >
          Select all ready documents →
        </button>
      )}
    </div>
  );
}
