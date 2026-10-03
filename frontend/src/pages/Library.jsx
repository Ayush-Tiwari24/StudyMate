import React, { useState } from 'react';
import { useDocuments } from '../hooks/useDocuments';
import UploadDropzone from '../components/library/UploadDropzone';
import DocumentTable from '../components/library/DocumentTable';
import { Search, RotateCw } from 'lucide-react';

export default function Library() {
  const { documents, loading, storage, refresh, upload, remove, retry } = useDocuments();
  const [searchTerm, setSearchTerm] = useState('');

  const filteredDocs = documents.filter((doc) =>
    (doc.filename || '').toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="flex-1 overflow-y-auto bg-[var(--paper)] p-6 md:p-10">
      <div className="max-w-5xl mx-auto flex flex-col gap-8">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[var(--line-subtle)]">
          <div>
            <h1 className="font-serif text-2xl md:text-3xl font-semibold text-[var(--ink)] tracking-tight">
              The Shelf
            </h1>
            <p className="text-xs md:text-sm text-[var(--muted)] font-sans mt-1">
              Upload course materials, lecture notes, and textbooks. Chunks and embeddings are created automatically.
            </p>
          </div>

          <button
            onClick={refresh}
            type="button"
            className="self-start sm:self-auto inline-flex items-center gap-1.5 px-3 py-1.5 rounded-[6px] border border-[var(--line)] bg-[var(--surface)] hover:bg-[var(--surface-hover)] text-xs font-sans font-medium text-[var(--ink)] transition-colors shadow-xs"
            title="Refresh shelf status"
          >
            <RotateCw size={13} />
            <span>Refresh</span>
          </button>
        </div>

        <UploadDropzone onUploadSuccess={upload} storage={storage} />

        <div className="flex flex-col gap-3">
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-2 bg-[var(--surface)] border border-[var(--line)] rounded-[6px] px-3 py-1.5 w-full max-w-xs shadow-xs focus-within:border-[var(--accent)] transition-colors">
              <Search size={14} className="text-[var(--muted)]" />
              <input
                type="text"
                placeholder="Search documents by name…"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="text-xs bg-transparent border-none outline-none w-full text-[var(--ink)] placeholder-[var(--subtle)]"
              />
            </div>

            <span className="text-xs font-mono text-[var(--muted)] flex-shrink-0">
              {filteredDocs.length} of {documents.length} files
            </span>
          </div>

          <DocumentTable
            documents={filteredDocs}
            loading={loading}
            onDelete={remove}
            onRefresh={refresh}
          />
        </div>
      </div>
    </div>
  );
}
