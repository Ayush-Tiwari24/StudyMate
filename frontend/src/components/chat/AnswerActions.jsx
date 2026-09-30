import React, { useState } from 'react';
import { Bookmark, Copy, Check, RotateCw, ThumbsUp, ThumbsDown } from 'lucide-react';
import { useNotes } from '../../context/NotesContext';
import { submitFeedback } from '../../api/chat';

export default function AnswerActions({
  messageId,
  question,
  answer,
  sources = [],
  onRetry,
}) {
  const [copied, setCopied] = useState(false);
  const [feedback, setFeedback] = useState(null); // 1 or -1
  const { saveNote, isNoteSaved } = useNotes();

  const isSaved = isNoteSaved(question, answer);

  const handleCopy = () => {
    navigator.clipboard.writeText(`${question ? `${question}\n\n` : ''}${answer}`);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleKeep = () => {
    saveNote({
      question,
      answer,
      sources,
      document_name: sources[0]?.file || sources[0]?.filename || 'Study Notes',
    });
  };

  const handleFeedback = async (val) => {
    if (feedback === val) return;
    setFeedback(val);
    if (messageId) {
      try {
        await submitFeedback(messageId, val);
      } catch (err) {
        console.error('Feedback failed:', err);
      }
    }
  };

  return (
    <div className="flex items-center justify-between pt-3 border-t border-[var(--line-subtle)] text-xs text-[var(--muted)]">
      <div className="flex items-center gap-3">
        {/* Keep / Save to notes */}
        <button
          type="button"
          onClick={handleKeep}
          className={`inline-flex items-center gap-1.5 py-1 px-1.5 rounded transition-colors hover:text-[var(--ink)] hover:bg-[var(--surface-hover)] ${
            isSaved ? 'text-[var(--accent)] font-medium' : ''
          }`}
          title="Save this answer to your notes"
        >
          <Bookmark size={13} fill={isSaved ? 'currentColor' : 'none'} />
          <span>{isSaved ? 'Saved to notes' : 'Keep'}</span>
        </button>

        {/* Copy */}
        <button
          type="button"
          onClick={handleCopy}
          className="inline-flex items-center gap-1.5 py-1 px-1.5 rounded transition-colors hover:text-[var(--ink)] hover:bg-[var(--surface-hover)]"
          title="Copy answer text"
        >
          {copied ? <Check size={13} /> : <Copy size={13} />}
          <span>{copied ? 'Copied' : 'Copy'}</span>
        </button>

        {/* Retry / Regenerate */}
        {onRetry && (
          <button
            type="button"
            onClick={() => onRetry(question)}
            className="inline-flex items-center gap-1.5 py-1 px-1.5 rounded transition-colors hover:text-[var(--ink)] hover:bg-[var(--surface-hover)]"
            title="Find answer again"
          >
            <RotateCw size={13} />
            <span>Regenerate</span>
          </button>
        )}
      </div>

      {/* Thumbs up / down feedback */}
      <div className="flex items-center gap-1">
        <button
          type="button"
          onClick={() => handleFeedback(1)}
          className={`p-1 rounded transition-colors hover:bg-[var(--surface-hover)] ${
            feedback === 1 ? 'text-[var(--accent)]' : 'hover:text-[var(--ink)]'
          }`}
          title="Accurate citation"
          aria-label="Thumbs up"
        >
          <ThumbsUp size={13} strokeWidth={1.75} />
        </button>

        <button
          type="button"
          onClick={() => handleFeedback(-1)}
          className={`p-1 rounded transition-colors hover:bg-[var(--surface-hover)] ${
            feedback === -1 ? 'text-[var(--status-failed)]' : 'hover:text-[var(--ink)]'
          }`}
          title="Incorrect citation or answer"
          aria-label="Thumbs down"
        >
          <ThumbsDown size={13} strokeWidth={1.75} />
        </button>
      </div>
    </div>
  );
}
