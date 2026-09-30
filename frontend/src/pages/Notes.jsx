import React, { useState } from 'react';
import { useNotes } from '../context/NotesContext';
import { Download, Trash2, Bookmark } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export default function Notes() {
  const { savedNotes, removeNote } = useNotes();
  const [selectedDocFilter, setSelectedDocFilter] = useState('all');
  const navigate = useNavigate();

  // Extract unique document names
  const docNames = Array.from(
    new Set(savedNotes.map((n) => n.document_name).filter(Boolean))
  );

  const filteredNotes =
    selectedDocFilter === 'all'
      ? savedNotes
      : savedNotes.filter((n) => n.document_name === selectedDocFilter);

  // Export to Markdown file
  const handleExportMarkdown = () => {
    if (savedNotes.length === 0) return;

    let content = `# StudyMate AI — Saved Notes & Answers\n\n`;
    content += `Exported on ${new Date().toLocaleDateString()}\n\n---\n\n`;

    filteredNotes.forEach((n, idx) => {
      content += `### ${idx + 1}. ${n.question}\n\n`;
      content += `${n.answer}\n\n`;
      if (n.sources && n.sources.length > 0) {
        content += `**Citations:**\n`;
        n.sources.forEach((s, sIdx) => {
          content += `- [${sIdx + 1}] ${s.file || s.filename} (Page ${s.page || '?'})\n`;
        });
        content += `\n`;
      }
      content += `---\n\n`;
    });

    const blob = new Blob([content], { type: 'text/markdown;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `StudyMate_Notes_${new Date().toISOString().slice(0, 10)}.md`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="flex-1 overflow-y-auto bg-[var(--paper)] p-6 md:p-10">
      <div className="max-w-4xl mx-auto flex flex-col gap-8">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[var(--line-subtle)]">
          <div>
            <h1 className="font-serif text-2xl md:text-3xl font-semibold text-[var(--ink)] tracking-tight">
              Saved Notes
            </h1>
            <p className="text-xs md:text-sm text-[var(--muted)] font-sans mt-1">
              Answers pinned from your reading desk with original page citations.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleExportMarkdown}
              disabled={filteredNotes.length === 0}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-[6px] border border-[var(--line)] bg-[var(--surface)] hover:bg-[var(--surface-hover)] disabled:opacity-40 disabled:cursor-not-allowed text-xs font-sans font-medium text-[var(--ink)] transition-colors shadow-xs"
              title="Download notes as Markdown file"
            >
              <Download size={13} />
              <span>Export to Markdown</span>
            </button>
          </div>
        </div>

        {/* Filter Bar */}
        {docNames.length > 0 && (
          <div className="flex items-center gap-2 text-xs">
            <span className="text-[var(--muted)]">Filter by document:</span>
            <select
              value={selectedDocFilter}
              onChange={(e) => setSelectedDocFilter(e.target.value)}
              className="text-xs px-2.5 py-1 bg-[var(--surface)] border border-[var(--line)] rounded-[6px] text-[var(--ink)] outline-none focus:border-[var(--accent)]"
            >
              <option value="all">All documents ({savedNotes.length})</option>
              {docNames.map((name) => (
                <option key={name} value={name}>
                  {name}
                </option>
              ))}
            </select>
          </div>
        )}

        {/* Notes List */}
        {filteredNotes.length === 0 ? (
          <div className="bg-[var(--surface)] border border-[var(--line)] rounded-[6px] p-12 text-center flex flex-col items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-[var(--surface-muted)] flex items-center justify-center text-[var(--muted)]">
              <Bookmark size={20} strokeWidth={1.5} />
            </div>
            <h2 className="font-serif text-lg font-medium text-[var(--ink)]">
              No saved notes yet
            </h2>
            <p className="text-xs text-[var(--muted)] max-w-sm">
              When you ask questions at the desk, click "Keep" below any answer to pin it here for review.
            </p>
            <button
              onClick={() => navigate('/chat')}
              className="mt-2 inline-flex items-center px-3.5 py-1.5 rounded-[6px] bg-[var(--accent)] text-white text-xs font-medium hover:bg-[var(--accent-hover)] transition-colors"
            >
              Open reading desk
            </button>
          </div>
        ) : (
          <div className="flex flex-col gap-4">
            {filteredNotes.map((note) => (
              <div
                key={note.id}
                className="bg-[var(--surface)] border border-[var(--line)] rounded-[6px] p-6 shadow-sm flex flex-col gap-4"
              >
                <div className="flex items-start justify-between gap-4">
                  <h3 className="font-sans text-base font-semibold text-[var(--ink)] leading-snug">
                    {note.question}
                  </h3>

                  <button
                    onClick={() => removeNote(note.id)}
                    className="p-1 rounded text-[var(--muted)] hover:text-[var(--status-failed)] hover:bg-[var(--surface-muted)] transition-colors flex-shrink-0"
                    title="Remove note"
                  >
                    <Trash2 size={13} />
                  </button>
                </div>

                <div className="prose-answer text-sm">
                  <p>{note.answer}</p>
                </div>

                {note.sources && note.sources.length > 0 && (
                  <div className="pt-3 border-t border-[var(--line-subtle)] flex flex-col gap-1.5">
                    <span className="font-mono text-[10px] uppercase tracking-wider text-[var(--muted)] font-semibold">
                      Citations
                    </span>
                    <div className="flex flex-wrap gap-2">
                      {note.sources.map((src, i) => (
                        <span
                          key={i}
                          className="font-mono text-[11px] text-[var(--muted)] bg-[var(--surface-muted)] px-2 py-0.5 rounded border border-[var(--line-subtle)]"
                        >
                          [{i + 1}] {src.file || src.filename} {src.page ? `· p.${src.page}` : ''}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                <div className="flex items-center justify-between text-[11px] text-[var(--subtle)] pt-2 border-t border-[var(--line-subtle)] font-mono">
                  <span>Saved on {new Date(note.savedAt).toLocaleDateString()}</span>
                  <span>{note.document_name}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
