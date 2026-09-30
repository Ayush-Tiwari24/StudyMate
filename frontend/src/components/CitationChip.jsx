import { useState } from 'react';

const SUPERSCRIPTS = ['⁰', '¹', '²', '³', '⁴', '⁵', '⁶', '⁷', '⁸', '⁹'];

function toSuperscript(num) {
  if (num >= 0 && num <= 9) return SUPERSCRIPTS[num];
  return `[${num}]`;
}

export default function CitationChip({ index, source, onClick }) {
  const [showTooltip, setShowTooltip] = useState(false);

  const label = toSuperscript(index);
  const fileName = source?.filename || source?.file || 'Document';
  const page = source?.page ? `p.${source.page}` : '';
  const excerpt = source?.text || source?.content || '';

  return (
    <span
      style={{ position: 'relative', display: 'inline-block' }}
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
    >
      <button
        type="button"
        className="footnote-cite"
        onClick={() => onClick && onClick(source, index)}
        aria-label={`Source ${index}: ${fileName}, page ${source?.page || ''}`}
        title={`${fileName} · ${page}`}
      >
        {label}
      </button>

      {/* Hover preview tooltip (Section 5, idea 3) */}
      {showTooltip && (
        <span
          style={{
            position: 'absolute',
            bottom: '100%',
            left: '50%',
            transform: 'translateX(-50%)',
            marginBottom: '6px',
            width: '260px',
            backgroundColor: 'var(--bg-surface)',
            border: '1px solid var(--border-hairline)',
            borderRadius: 'var(--radius)',
            padding: '0.6rem 0.75rem',
            boxShadow: '0 4px 12px rgba(0, 0, 0, 0.08)',
            zIndex: 50,
            pointerEvents: 'none',
            fontFamily: 'var(--font-sans)',
            fontSize: 'var(--text-xs)',
            lineHeight: 1.45,
            color: 'var(--text-main)',
            textAlign: 'left',
          }}
        >
          <span
            style={{
              display: 'block',
              fontFamily: 'var(--font-mono)',
              fontWeight: 600,
              fontSize: '0.7rem',
              color: 'var(--accent)',
              marginBottom: '0.25rem',
            }}
          >
            Source {index}: {fileName} {page && `· ${page}`}
          </span>
          {excerpt ? (
            <span style={{ display: 'block', color: 'var(--text-muted)' }}>
              {excerpt.slice(0, 140)}...
            </span>
          ) : (
            <span style={{ color: 'var(--text-subtle)' }}>Click to view source page.</span>
          )}
        </span>
      )}
    </span>
  );
}
