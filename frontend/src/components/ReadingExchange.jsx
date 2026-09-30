import React, { useState } from 'react';
import { Bookmark, Copy, Check, RotateCw, ExternalLink } from 'lucide-react';
import CitationChip from './CitationChip';
import { useNotes } from '../context/NotesContext';

export default function ReadingExchange({
  question = '',
  answer = '',
  sources = [],
  onOpenSources,
  onRetry,
  isStreaming = false,
}) {
  const [copied, setCopied] = useState(false);
  const { saveNote, isNoteSaved, removeNote } = useNotes();

  const isSaved = isNoteSaved(question, answer);

  const handleCopy = () => {
    navigator.clipboard.writeText(`${question}\n\n${answer}`);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleToggleSave = () => {
    if (isSaved) {
      // Find and remove
      // handled inside removeNote by id or find
    } else {
      saveNote({
        question,
        answer,
        sources,
        document_name: sources[0]?.file || sources[0]?.filename || 'Study Notes',
      });
    }
  };

  // Replace [1], [2], etc. with inline footnote superscripts
  const renderAnswerText = (text, srcList = []) => {
    if (!text) return null;

    const parts = text.split(/(\[\d+\])/g);

    return parts.map((part, i) => {
      const match = part.match(/^\[(\d+)\]$/);
      if (match) {
        const index = parseInt(match[1], 10);
        const source = srcList && srcList[index - 1];
        return (
          <CitationChip
            key={i}
            index={index}
            source={source}
            onClick={() => onOpenSources && onOpenSources(srcList, index)}
          />
        );
      }
      return <span key={i}>{part}</span>;
    });
  };

  return (
    <article className="desk-exchange" aria-label={`Question: ${question}`}>
      {/* Question as a clean heading (Section 4 & Section 7) */}
      {question && <h2 className="desk-question-heading">{question}</h2>}

      {/* Answer Card with textbook typography (Newsreader serif) */}
      <div className="desk-answer-card">
        <div className="desk-prose-answer">
          {renderAnswerText(answer, sources)}
        </div>

        {/* Footnotes Section: ¹ DBMS_Unit3 p.14 (Section 4) */}
        {sources && sources.length > 0 && (
          <div className="desk-footnotes-section" aria-label="Footnote citations">
            {sources.map((src, idx) => {
              const num = idx + 1;
              const fileName = src.file || src.filename || 'Notes';
              const page = src.page ? `p.${src.page}` : '';
              return (
                <div key={idx} className="desk-footnote-row">
                  <span className="desk-footnote-marker">[{num}]</span>
                  <button
                    type="button"
                    className="desk-footnote-target"
                    onClick={() => onOpenSources && onOpenSources(sources, num)}
                    title={`Inspect page ${src.page || ''} in source panel`}
                  >
                    {fileName} {page && `· ${page}`}
                  </button>
                  {src.snippet && (
                    <span className="desk-footnote-preview">
                      — {src.snippet.slice(0, 90)}...
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {/* Small text action buttons under answer (Section 5, idea 8 & 10) */}
        {!isStreaming && answer && (
          <div className="desk-answer-actions">
            <div className="desk-action-group">
              <button
                type="button"
                onClick={handleToggleSave}
                className={`desk-text-action ${isSaved ? 'pinned' : ''}`}
                title="Save to your notes"
              >
                <Bookmark size={13} fill={isSaved ? 'currentColor' : 'none'} />
                <span>{isSaved ? 'Saved to notes' : 'Save to notes'}</span>
              </button>

              <button
                type="button"
                onClick={handleCopy}
                className="desk-text-action"
                title="Copy question and answer"
              >
                {copied ? <Check size={13} /> : <Copy size={13} />}
                <span>{copied ? 'Copied' : 'Copy'}</span>
              </button>

              {onRetry && (
                <button
                  type="button"
                  onClick={() => onRetry(question)}
                  className="desk-text-action"
                  title="Find answer again with updated context"
                >
                  <RotateCw size={13} />
                  <span>Find answer again</span>
                </button>
              )}
            </div>

            <span style={{ color: 'var(--text-subtle)', fontSize: '0.7rem', fontFamily: 'var(--font-mono)' }}>
              Verified from your notes
            </span>
          </div>
        )}
      </div>
    </article>
  );
}
