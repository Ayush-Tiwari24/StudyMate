import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useNotes } from '../context/NotesContext';
import { Download, Trash2, Bookmark, Copy, Check, FileText, Calendar } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export default function Notes() {
  const { savedNotes, removeNote } = useNotes();
  const [selectedDocFilter, setSelectedDocFilter] = useState('all');
  const [copiedId, setCopiedId] = useState(null);
  const navigate = useNavigate();

  // Extract unique document names
  const docNames = Array.from(
    new Set(savedNotes.map((n) => n.document_name).filter(Boolean))
  );

  const filteredNotes =
    selectedDocFilter === 'all'
      ? savedNotes
      : savedNotes.filter((n) => n.document_name === selectedDocFilter);

  // Copy note question and answer to clipboard
  const handleCopyNote = (note) => {
    const text = `${note.question}\n\n${note.answer}`;
    navigator.clipboard.writeText(text);
    setCopiedId(note.id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  // Pre-process note text to break crowded list items
  const formatNoteText = (text) => {
    if (!text) return '';
    let formatted = text;
    // Break numbered list items running together onto separate lines
    formatted = formatted.replace(/([^\n])\s+(\d+\.\s+\*\*)/g, '$1\n\n$2');
    // Break bullet points running together
    formatted = formatted.replace(/([^\n])\s+([•\-*]\s+\*\*)/g, '$1\n\n$2');
    return formatted;
  };

  // Export to Markdown file (plain questions and answers only)
  const handleExportMarkdown = () => {
    if (savedNotes.length === 0) return;

    let content = `# StudyMate AI — Saved Notes & Answers\n\n`;
    content += `Exported on ${new Date().toLocaleDateString()}\n\n---\n\n`;

    filteredNotes.forEach((n, idx) => {
      content += `### ${idx + 1}. ${n.question}\n\n`;
      content += `${n.answer}\n\n`;
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
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[var(--line-subtle)]">
          <div>
            <h1 className="font-serif text-2xl md:text-3xl font-semibold text-[var(--ink)] tracking-tight">
              Saved Notes
            </h1>
            <p className="text-xs md:text-sm text-[var(--muted)] font-sans mt-1">
              Answers saved from your reading desk.
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
          <div className="flex flex-col gap-6">
            {filteredNotes.map((note) => (
              <div
                key={note.id}
                className="bg-[var(--surface)] border border-[var(--line)] rounded-xl p-6 sm:p-8 shadow-sm flex flex-col gap-5 hover:border-[var(--line-subtle)] transition-all"
              >
                <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 pb-4 border-b border-[var(--line-subtle)]">
                  <div className="flex flex-col gap-1.5 flex-1">
                    <div className="flex items-center gap-2 flex-wrap text-xs text-[var(--muted)] font-mono">
                      {note.document_name && (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-[var(--surface-muted)] border border-[var(--line-subtle)] text-[var(--ink)] font-medium">
                          <FileText size={11} className="text-[var(--accent)]" />
                          {note.document_name}
                        </span>
                      )}
                      <span className="inline-flex items-center gap-1 text-[var(--subtle)]">
                        <Calendar size={11} />
                        {note.savedAt ? new Date(note.savedAt).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' }) : 'Saved note'}
                      </span>
                    </div>
                    <h3 className="font-sans text-lg sm:text-xl font-semibold text-[var(--ink)] tracking-tight leading-snug mt-1">
                      {note.question}
                    </h3>
                  </div>

                  <div className="flex items-center gap-1.5 flex-shrink-0 self-end sm:self-start">
                    <button
                      onClick={() => handleCopyNote(note)}
                      className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-[6px] border border-[var(--line)] bg-[var(--surface-muted)] hover:bg-[var(--surface-hover)] text-xs font-sans text-[var(--ink)] transition-colors"
                      title="Copy question and answer"
                    >
                      {copiedId === note.id ? (
                        <>
                          <Check size={12} className="text-emerald-500" />
                          <span className="text-emerald-500 font-medium">Copied</span>
                        </>
                      ) : (
                        <>
                          <Copy size={12} className="text-[var(--muted)]" />
                          <span>Copy</span>
                        </>
                      )}
                    </button>
                    <button
                      onClick={() => removeNote(note.id)}
                      className="p-1.5 rounded-[6px] border border-transparent hover:border-[var(--line)] hover:bg-[var(--surface-hover)] text-[var(--muted)] hover:text-rose-500 transition-colors"
                      title="Remove note"
                    >
                      <Trash2 size={13} />
                    </button>
                  </div>
                </div>

                <div className="prose-answer text-[15px] sm:text-base leading-relaxed text-[var(--ink)]">
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    components={{
                      a: ({ href, children }) => (
                        <a
                          href={href}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-[var(--accent)] underline hover:text-[var(--accent-hover)]"
                        >
                          {children}
                        </a>
                      ),
                    }}
                  >
                    {formatNoteText(note.answer)}
                  </ReactMarkdown>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
