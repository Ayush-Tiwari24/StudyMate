import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { BookOpen, Trash2, ExternalLink, RotateCw, MessageSquare } from 'lucide-react';
import { getDocumentFileUrl } from '../../api/documents';
import StatusDot from './StatusDot';

export default function DocumentTable({
  documents = [],
  loading = false,
  onDelete,
  onRefresh,
  onRetry,
}) {
  const [deletingId, setDeletingId] = useState(null);
  const [retryingId, setRetryingId] = useState(null);
  const navigate = useNavigate();

  const handleDelete = async (id, name) => {
    if (window.confirm(`Remove "${name}" from your shelf? This deletes its indexed passages.`)) {
      setDeletingId(id);
      try {
        await onDelete(id);
      } finally {
        setDeletingId(null);
      }
    }
  };

  const handleRetry = async (id) => {
    setRetryingId(id);
    try {
      await onRetry(id);
    } finally {
      setRetryingId(null);
    }
  };

  if (loading && documents.length === 0) {
    return (
      <div className="p-12 text-center text-xs text-[var(--muted)] font-mono">
        Loading your shelf…
      </div>
    );
  }

  return (
    <div className="bg-[var(--surface)] border border-[var(--line)] rounded-[6px] overflow-hidden shadow-sm">
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs border-collapse">
          <thead>
            <tr className="border-b border-[var(--line)] bg-[var(--surface-muted)] text-[var(--muted)] font-mono uppercase tracking-wider text-[11px]">
              <th className="py-2.5 px-4 font-semibold">File name</th>
              <th className="py-2.5 px-4 font-semibold">Pages</th>
              <th className="py-2.5 px-4 font-semibold">Added</th>
              <th className="py-2.5 px-4 font-semibold">Status</th>
              <th className="py-2.5 px-4 font-semibold text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--line-subtle)] font-sans">
            {documents.length === 0 ? (
              <tr>
                <td colSpan={5} className="text-center text-[var(--muted)] py-10">
                  Your shelf is empty. Drop your notes above to begin.
                </td>
              </tr>
            ) : (
              documents.map((doc) => {
                const isDeleting = deletingId === doc.id;
                const isReady = doc.status === 'ready';
                const isFailed = doc.status === 'failed';
                const dateStr = doc.uploaded_at
                  ? new Date(doc.uploaded_at).toLocaleDateString(undefined, {
                      month: 'short',
                      day: 'numeric',
                    })
                  : '—';

                return (
                  <tr
                    key={doc.id}
                    className="hover:bg-[var(--surface-hover)] transition-colors"
                    style={{ opacity: isDeleting ? 0.4 : 1 }}
                  >
                    <td className="py-3 px-4 font-medium text-[var(--ink)]">
                      <div className="flex items-center gap-2 max-w-sm">
                        <BookOpen size={15} className="text-[var(--accent)] flex-shrink-0" />
                        <span className="truncate" title={doc.filename}>
                          {doc.filename}
                        </span>
                      </div>
                    </td>

                    <td className="py-3 px-4 text-[var(--muted)] font-mono">
                      {doc.pages || '—'}
                    </td>

                    <td className="py-3 px-4 text-[var(--muted)] font-mono">
                      {dateStr}
                    </td>

                    <td className="py-3 px-4">
                      <div className="flex items-center gap-2">
                        <StatusDot
                          status={doc.status}
                          labelOverride={
                            isReady && doc.chunk_count
                              ? `Ready (${doc.chunk_count} sections)`
                              : undefined
                          }
                        />

                        {isFailed && onRetry && (
                          <button
                            type="button"
                            onClick={() => handleRetry(doc.id)}
                            disabled={retryingId === doc.id}
                            className="text-[var(--accent)] hover:underline inline-flex items-center gap-1 font-mono text-[11px]"
                          >
                            <RotateCw
                              size={11}
                              className={retryingId === doc.id ? 'animate-spin' : ''}
                            />
                            Retry
                          </button>
                        )}
                      </div>
                    </td>

                    <td className="py-3 px-4 text-right">
                      <div className="inline-flex items-center gap-2">
                        {isReady && (
                          <button
                            type="button"
                            onClick={() => navigate('/chat')}
                            className="inline-flex items-center gap-1 px-2 py-1 rounded text-xs font-medium text-[var(--accent)] hover:bg-[var(--accent-subtle)] transition-colors"
                            title="Ask notes"
                          >
                            <MessageSquare size={13} />
                            <span>Ask notes</span>
                          </button>
                        )}

                        <a
                          href={getDocumentFileUrl(doc.id)}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="p-1 rounded text-[var(--muted)] hover:text-[var(--ink)] hover:bg-[var(--surface-muted)] transition-colors"
                          title="Open original PDF in new tab"
                        >
                          <ExternalLink size={13} />
                        </a>

                        <button
                          type="button"
                          onClick={() => handleDelete(doc.id, doc.filename)}
                          disabled={isDeleting}
                          className="p-1 rounded text-[var(--muted)] hover:text-[var(--status-failed)] hover:bg-[var(--surface-muted)] transition-colors"
                          title="Remove from shelf"
                          aria-label={`Remove ${doc.filename}`}
                        >
                          <Trash2 size={13} />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
