import React, { useState, useEffect, useRef } from 'react';
import { getToken } from '../../api/client';
import { getDocumentFileUrl } from '../../api/documents';
import HighlightOverlay from './HighlightOverlay';

export default function PdfPageView({
  documentId,
  pageNumber = 1,
  bboxes = [],
  snippet = '',
  query = '',
  isRemoved = false,
}) {
  const [blobUrl, setBlobUrl] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const containerRef = useRef(null);

  useEffect(() => {
    if (isRemoved) {
      setLoadError('This source was removed.');
      setLoading(false);
      return;
    }

    if (!documentId) {
      setLoadError('Source document not available.');
      setLoading(false);
      return;
    }

    let isMounted = true;
    let objectUrl = null;
    setLoading(true);
    setLoadError(null);

    const fileUrl = getDocumentFileUrl(documentId);
    const token = getToken();

    // Fetch PDF as Blob using auth header
    fetch(fileUrl, {
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    })
      .then((res) => {
        if (!res.ok) {
          if (res.status === 404) throw new Error('This source was removed.');
          throw new Error('Unable to load source PDF.');
        }
        return res.blob();
      })
      .then((blob) => {
        if (isMounted) {
          objectUrl = URL.createObjectURL(blob);
          setBlobUrl(objectUrl);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (isMounted) {
          setLoadError(err.message || 'Unable to load page.');
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [documentId, isRemoved]);

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

  if (isRemoved || loadError === 'This source was removed.') {
    return (
      <div className="p-8 text-center text-sm text-[var(--muted)] font-sans">
        This source was removed.
      </div>
    );
  }

  return (
    <div ref={containerRef} className="flex flex-col gap-4 w-full">
      {/* Evidence passage excerpt card with yellow highlight */}
      <div className="p-4 bg-[var(--paper)] border border-[var(--line)] rounded-[6px]">
        <div className="font-mono text-[11px] font-semibold text-[var(--muted)] uppercase tracking-wider mb-2 flex items-center justify-between">
          <span>Cited passage</span>
          <span>Page {pageNumber}</span>
        </div>
        <div className="font-serif text-sm leading-relaxed text-[var(--ink)]">
          {snippet ? (
            renderHighlightedSnippet(snippet, query)
          ) : (
            <span className="text-[var(--subtle)]">Original page passage reference.</span>
          )}
        </div>
      </div>

      {/* PDF View or preview container */}
      <div className="relative border border-[var(--line)] rounded-[6px] overflow-hidden bg-white shadow-sm min-h-[360px] flex items-center justify-center">
        {loading ? (
          <div className="p-8 text-center text-xs text-[var(--muted)] font-mono">
            Reading page {pageNumber}…
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
          <div className="p-6 text-center text-xs text-[var(--muted)]">
            {loadError || 'Unable to render original page preview.'}
          </div>
        )}
      </div>
    </div>
  );
}
