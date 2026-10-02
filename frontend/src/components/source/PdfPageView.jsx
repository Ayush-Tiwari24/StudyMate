import React, { useState, useEffect, useRef, useCallback } from 'react';
import { fetchDocumentBlob } from '../../api/documents';
import HighlightOverlay from './HighlightOverlay';

// In-memory cache for downloaded PDF blobs (documentId -> objectUrl)
const blobUrlCache = new Map();

export default function PdfPageView({
  documentId,
  pageNumber = 1,
  bboxes = [],
  snippet = '',
  query = '',
  isRemoved = false,
}) {
  const [blobUrl, setBlobUrl] = useState(() => (documentId ? blobUrlCache.get(documentId) || null : null));
  const [loading, setLoading] = useState(() => !blobUrlCache.has(documentId));
  const [loadError, setLoadError] = useState(null);
  const containerRef = useRef(null);

  const loadPdf = useCallback(async (force = false) => {
    if (isRemoved) {
      setLoadError('This source document was removed.');
      setLoading(false);
      return;
    }

    if (!documentId) {
      setLoadError('Source document not available.');
      setLoading(false);
      return;
    }

    if (!force && blobUrlCache.has(documentId)) {
      setBlobUrl(blobUrlCache.get(documentId));
      setLoading(false);
      setLoadError(null);
      return;
    }

    setLoading(true);
    setLoadError(null);

    try {
      const res = await fetchDocumentBlob(documentId);
      const url = URL.createObjectURL(res.data);
      blobUrlCache.set(documentId, url);
      setBlobUrl(url);
      setLoadError(null);
    } catch (err) {
      console.error('Failed to load PDF blob:', err);
      const status = err.response?.status;
      if (status === 404) {
        setLoadError('This source document is not found on the server.');
      } else if (status === 401) {
        setLoadError('Authentication required to view document.');
      } else {
        setLoadError(err.message || 'Unable to load source PDF preview.');
      }
    } finally {
      setLoading(false);
    }
  }, [documentId, isRemoved]);

  useEffect(() => {
    loadPdf();
  }, [loadPdf]);

  // Function to highlight query terms in snippet text
  const renderHighlightedSnippet = (text, searchQuery) => {
    if (!searchQuery || !searchQuery.trim()) {
      return <mark className="source-mark">{text}</mark>;
    }

    const terms = searchQuery
      .split(/\s+/)
      .filter((w) => w.length > 3)
      .map((w) => w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));

    if (terms.length === 0) {
      return <mark className="source-mark">{text}</mark>;
    }

    try {
      const regex = new RegExp(`(${terms.join('|')})`, 'gi');
      const parts = text.split(regex);
      return parts.map((part, i) =>
        regex.test(part) ? (
          <mark key={i} className="source-mark">
            {part}
          </mark>
        ) : (
          part
        )
      );
    } catch {
      return <mark className="source-mark">{text}</mark>;
    }
  };

  return (
    <div ref={containerRef} className="flex flex-col gap-4 w-full">
      <div className="p-4 bg-[var(--paper)] border border-[var(--line)] rounded-[6px]">
        <div className="font-mono text-[11px] font-semibold text-[var(--muted)] uppercase tracking-wider mb-2 flex items-center justify-between">
          <span>Cited passage</span>
          <span>Page {pageNumber || '?'}</span>
        </div>
        <div className="font-serif text-sm leading-relaxed text-[var(--ink)]">
          {snippet ? (
            renderHighlightedSnippet(snippet, query)
          ) : (
            <span className="text-[var(--subtle)]">Original page passage reference.</span>
          )}
        </div>
      </div>

      <div className="relative border border-[var(--line)] rounded-[6px] overflow-hidden bg-white shadow-sm min-h-[360px] flex items-center justify-center">
        {loading ? (
          <div className="p-8 text-center text-xs text-[var(--muted)] font-mono flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-[var(--accent)] animate-pulse" />
            <span>Reading page {pageNumber}…</span>
          </div>
        ) : blobUrl ? (
          <div className="relative w-full h-[480px]">
            <iframe
              src={`${blobUrl}#page=${pageNumber}&toolbar=0&navpanes=0`}
              title={`Source Page ${pageNumber}`}
              className="w-full h-full border-none"
            />
            {bboxes && bboxes.length > 0 && (
              <HighlightOverlay
                bboxes={bboxes}
                pageWidth={containerRef.current?.offsetWidth || 340}
                pageHeight={480}
              />
            )}
          </div>
        ) : (
          <div className="p-6 text-center text-xs text-[var(--muted)] flex flex-col items-center gap-2">
            <span>{isRemoved ? 'This source document was removed.' : (loadError || 'Unable to render original page preview.')}</span>
            {!isRemoved && (
              <button
                type="button"
                onClick={() => loadPdf(true)}
                className="mt-2 px-3 py-1 rounded bg-[var(--surface-muted)] hover:bg-[var(--surface-hover)] border border-[var(--line)] text-[var(--ink)] font-mono text-[11px] transition-colors"
              >
                Retry loading PDF
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
