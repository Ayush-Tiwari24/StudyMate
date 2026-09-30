import React, { useState } from 'react';

const SUPERSCRIPTS = ['⁰', '¹', '²', '³', '⁴', '⁵', '⁶', '⁷', '⁸', '⁹'];

function toSuperscript(num) {
  if (num >= 0 && num <= 9) return SUPERSCRIPTS[num];
  return `[${num}]`;
}

export default function FootnoteMarker({
  index = 1,
  source,
  onClick,
}) {
  const [hovered, setHovered] = useState(false);
  const [timer, setTimer] = useState(null);

  const fileName = source?.file || source?.filename || 'Document';
  const page = source?.page ? `p.${source.page}` : '';
  const snippet = source?.snippet || source?.text || source?.content || '';

  const handleMouseEnter = () => {
    // 200ms delay as specified in Section 1 ("Hover previews appear after 200 ms")
    const t = setTimeout(() => setHovered(true), 200);
    setTimer(t);
  };

  const handleMouseLeave = () => {
    if (timer) clearTimeout(timer);
    setHovered(false);
  };

  return (
    <span
      className="relative inline-block"
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      <button
        type="button"
        onClick={() => onClick && onClick(source, index)}
        className="footnote-cite inline-flex items-center justify-center font-semibold text-[var(--accent)] hover:underline px-0.5 cursor-pointer align-super text-xs leading-none transition-colors"
        aria-label={`Source ${index}: ${fileName}, page ${source?.page || ''}`}
        title={`${fileName} · ${page}`}
      >
        {toSuperscript(index)}
      </button>

      {/* Hover preview tooltip appearing after 200ms */}
      {hovered && (
        <span
          className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-64 p-3 bg-[var(--surface)] text-[var(--ink)] border border-[var(--line)] rounded-[6px] shadow-sm text-xs font-sans pointer-events-none z-50 text-left leading-relaxed animate-fadeIn"
          role="tooltip"
        >
          <span className="block font-mono text-[11px] font-semibold text-[var(--accent)] mb-1">
            Source {index}: {fileName} {page && `· ${page}`}
          </span>
          {snippet ? (
            <span className="block text-[var(--muted)] line-clamp-3">
              {snippet}
            </span>
          ) : (
            <span className="text-[var(--subtle)]">Click to open source page.</span>
          )}
        </span>
      )}
    </span>
  );
}
