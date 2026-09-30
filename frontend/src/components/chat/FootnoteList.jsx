import React from 'react';

const SUPERSCRIPTS = ['⁰', '¹', '²', '³', '⁴', '⁵', '⁶', '⁷', '⁸', '⁹'];

function toSuperscript(num) {
  if (num >= 0 && num <= 9) return SUPERSCRIPTS[num];
  return `[${num}]`;
}

export default function FootnoteList({ sources = [], onSelectCitation }) {
  if (!sources || sources.length === 0) return null;

  return (
    <div className="border-t border-[var(--line)] pt-3.5 mt-4 flex flex-col gap-1.5" aria-label="Footnotes">
      {sources.map((src, i) => {
        const index = i + 1;
        const fileName = src.file || src.filename || 'Notes';
        const page = src.page ? `· p.${src.page}` : '';

        return (
          <div key={i} className="flex items-baseline gap-2 text-xs font-mono text-[var(--muted)]">
            <span className="font-semibold text-[var(--accent)] w-4 text-right select-none">
              {toSuperscript(index)}
            </span>
            <button
              type="button"
              onClick={() => onSelectCitation && onSelectCitation(src, index)}
              className="text-[var(--ink)] hover:text-[var(--accent)] hover:underline text-left rounded-[4px] px-1 py-0.5 bg-[var(--surface-muted)] border border-[var(--line)] transition-colors inline-flex items-center gap-1"
              title={`Inspect ${fileName} page ${src.page || ''} in source panel`}
            >
              <span>{fileName}</span>
              {page && <span className="text-[var(--muted)]">{page}</span>}
            </button>
            {src.snippet && (
              <span className="text-[var(--subtle)] truncate max-w-sm hidden sm:inline font-sans">
                — {src.snippet.slice(0, 80)}…
              </span>
            )}
          </div>
        );
      })}
    </div>
  );
}
