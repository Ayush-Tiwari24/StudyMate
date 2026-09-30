import React from 'react';

export default function HoverPreview({ source, index }) {
  if (!source) return null;
  const fileName = source.file || source.filename || 'Document';
  const page = source.page ? `· p.${source.page}` : '';
  const snippet = source.snippet || source.text || source.content || '';

  return (
    <div className="p-3 bg-[var(--surface)] text-[var(--ink)] border border-[var(--line)] rounded-[6px] shadow-sm text-xs font-sans text-left leading-relaxed">
      <span className="block font-mono text-[11px] font-semibold text-[var(--accent)] mb-1">
        Source {index}: {fileName} {page}
      </span>
      <p className="text-[var(--muted)] line-clamp-3">{snippet}</p>
    </div>
  );
}
