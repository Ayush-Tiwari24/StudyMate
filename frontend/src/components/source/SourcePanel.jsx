import React, { useState, useEffect } from 'react';
import { X, ExternalLink, Maximize2, Minimize2 } from 'lucide-react';
import { getDocumentFileUrl } from '../../api/documents';
import PdfPageView from './PdfPageView';

export default function SourcePanel({
  isOpen = true,
  onClose,
  sources = [],
  activeCitationIndex = 1,
  onSelectCitation,
  query = '',
  className = '',
  isExpanded,
  onToggleExpand,
}) {
  const [currentIndex, setCurrentIndex] = useState(activeCitationIndex || 1);
  const [fullPage, setFullPage] = useState(false);
  const isFull = isExpanded !== undefined ? isExpanded : fullPage;
  const toggleFull = onToggleExpand || (() => setFullPage((prev) => !prev));

  useEffect(() => {
    if (activeCitationIndex && activeCitationIndex >= 1 && activeCitationIndex <= (sources.length || 1)) {
      setCurrentIndex(activeCitationIndex);
    } else if (sources.length > 0) {
      setCurrentIndex((prev) => (prev > sources.length || prev < 1 ? 1 : prev));
    }
  }, [activeCitationIndex, sources.length]);

  // Handle ESC key to close
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && onClose) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  if (!isOpen || sources.length === 0) {
    return (
      <aside
        className={`w-full bg-[var(--surface)] border-l border-[var(--line)] flex flex-col h-full overflow-hidden select-none transition-all duration-150 ease-out ${
          !className ? 'md:w-96' : ''
        } ${className}`}
        style={{ display: isOpen ? 'flex' : 'none' }}
      >
        <div className="p-3.5 border-b border-[var(--line)] flex items-center justify-between">
          <span className="font-mono text-xs font-semibold uppercase tracking-wider text-[var(--ink)]">
            Evidence Panel
          </span>
          {onClose && (
            <button
              onClick={onClose}
              className="p-1 rounded text-[var(--muted)] hover:text-[var(--ink)] hover:bg-[var(--surface-hover)]"
              title="Close evidence panel (Esc)"
            >
              <X size={15} />
            </button>
          )}
        </div>
        <div className="flex-1 flex items-center justify-center p-6 text-center text-xs text-[var(--muted)]">
          Select any footnote citation (such as ¹ or ²) in the answer to inspect its original page.
        </div>
      </aside>
    );
  }

  const selectedSource = sources[currentIndex - 1] || sources[0] || {};
  const fileName = selectedSource.file || selectedSource.filename || 'Source Document';
  const pageNum = selectedSource.page;
  const docId = selectedSource.document_id || selectedSource.documentId || selectedSource.doc_id;
  const isRemoved = selectedSource.is_removed || false;

  return (
    <aside
      className={`w-full bg-[var(--surface)] border-l border-[var(--line)] flex flex-col h-full overflow-hidden select-none transition-all duration-150 ease-out z-20 ${
        !className ? (isFull ? 'md:w-[680px]' : 'md:w-96') : ''
      } ${className}`}
      aria-label="Evidence and source page"
    >
      {/* Header: Mono file label + page */}
      <div className="p-3 border-b border-[var(--line)] flex items-center justify-between gap-2">
        <span
          className="font-mono text-xs font-medium text-[var(--ink)] truncate"
          title={`${fileName} · p.${pageNum || '?'}`}
        >
          {fileName} {pageNum ? `· p.${pageNum}` : ''}
        </span>

        <div className="flex items-center gap-1">
          <button
            onClick={toggleFull}
            className="p-1 rounded text-[var(--muted)] hover:text-[var(--ink)] hover:bg-[var(--surface-hover)]"
            title={isFull ? 'Standard width' : 'Expand full page'}
          >
            {isFull ? <Minimize2 size={13} /> : <Maximize2 size={13} />}
          </button>

          {onClose && (
            <button
              onClick={onClose}
              className="p-1 rounded text-[var(--muted)] hover:text-[var(--ink)] hover:bg-[var(--surface-hover)]"
              title="Close panel (Esc)"
              aria-label="Close source panel"
            >
              <X size={14} />
            </button>
          )}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-4">
        {/* Source citation switcher tabs if multiple citations exist */}
        {sources.length > 1 && (
          <div className="flex items-center gap-1.5 flex-wrap" role="tablist">
            {sources.map((src, idx) => {
              const num = idx + 1;
              const isActive = currentIndex === num;
              return (
                <button
                  key={idx}
                  role="tab"
                  aria-selected={isActive}
                  className={`font-mono text-xs px-2.5 py-1 rounded-[4px] border transition-colors ${
                    isActive
                      ? 'bg-[var(--mark)] text-[var(--mark-text)] border-[var(--accent)] font-semibold'
                      : 'bg-[var(--surface-muted)] text-[var(--muted)] border-[var(--line)] hover:bg-[var(--surface-hover)]'
                  }`}
                  onClick={() => {
                    setCurrentIndex(num);
                    onSelectCitation && onSelectCitation(src, num);
                  }}
                >
                  [{num}] {src.page ? `p.${src.page}` : ''}
                </button>
              );
            })}
          </div>
        )}

        {/* Real PDF Page View with Highlight Overlay */}
        <PdfPageView
          documentId={docId}
          pageNumber={pageNum}
          bboxes={selectedSource.bboxes || []}
          snippet={selectedSource.snippet || selectedSource.text || selectedSource.content || ''}
          query={query}
          isRemoved={isRemoved}
        />
      </div>

      {/* Footer: Open full PDF link */}
      {docId && !isRemoved && (
        <div className="p-3 border-t border-[var(--line)] flex items-center justify-between text-xs">
          <a
            href={getDocumentFileUrl(docId)}
            target="_blank"
            rel="noopener noreferrer"
            className="font-mono text-xs text-[var(--accent)] hover:underline inline-flex items-center gap-1"
          >
            <ExternalLink size={12} />
            <span>Open full page ({pageNum ? `p.${pageNum}` : 'PDF'})</span>
          </a>

          <span className="text-[11px] text-[var(--muted)] font-mono">
            Verified citation
          </span>
        </div>
      )}
    </aside>
  );
}
