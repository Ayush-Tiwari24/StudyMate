import React, { useRef, useEffect } from 'react';
import { Send } from 'lucide-react';

const MAX_QUESTION_LENGTH = 1000;

export default function ChatInput({
  value = '',
  onChange,
  onSubmit,
  isStreaming = false,
  selectedDocCount = 0,
  textareaRef,
}) {
  const localRef = useRef(null);
  const inputRef = textareaRef || localRef;

  const currentLength = value.length;
  const isNearLimit = currentLength > MAX_QUESTION_LENGTH * 0.8;
  const isOverLimit = currentLength > MAX_QUESTION_LENGTH;
  const canSubmit = value.trim().length > 0 && !isStreaming && selectedDocCount > 0 && !isOverLimit;

  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.style.height = 'auto';
      inputRef.current.style.height = `${Math.min(inputRef.current.scrollHeight, 180)}px`;
    }
  }, [value, inputRef]);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (canSubmit) {
        onSubmit();
      }
    }
  };

  return (
    <div className="w-full flex flex-col items-center">
      <div className="w-full max-w-3xl bg-[var(--surface)] border border-[var(--line)] rounded-[6px] shadow-sm transition-colors focus-within:border-[var(--accent)] flex flex-col">
        <textarea
          ref={inputRef}
          rows={1}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isStreaming || selectedDocCount === 0}
          placeholder={
            selectedDocCount === 0
              ? 'Select at least one document on the shelf to ask'
              : 'Ask your notes…'
          }
          className="w-full p-3 text-sm text-[var(--ink)] placeholder-[var(--subtle)] bg-transparent resize-none outline-none leading-relaxed min-h-[50px] max-h-[180px]"
          aria-label="Ask your notes"
        />

        <div className="flex items-center justify-between px-3 py-2 border-t border-[var(--line-subtle)] text-xs text-[var(--subtle)] font-mono">
          <div className="flex items-center gap-3">
            <span>
              <kbd className="px-1.5 py-0.5 rounded bg-[var(--surface-muted)] border border-[var(--line)] text-[10px]">
                /
              </kbd>{' '}
              focus
            </span>
            <span>
              <kbd className="px-1.5 py-0.5 rounded bg-[var(--surface-muted)] border border-[var(--line)] text-[10px]">
                Enter
              </kbd>{' '}
              send
            </span>
            <span>
              <kbd className="px-1.5 py-0.5 rounded bg-[var(--surface-muted)] border border-[var(--line)] text-[10px]">
                Shift+Enter
              </kbd>{' '}
              new line
            </span>
          </div>

          <div className="flex items-center gap-3">
            {isNearLimit && (
              <span className={`text-[11px] ${isOverLimit ? 'text-[var(--status-failed)] font-semibold' : ''}`}>
                {currentLength}/{MAX_QUESTION_LENGTH}
              </span>
            )}

            <button
              type="button"
              disabled={!canSubmit}
              onClick={onSubmit}
              className="inline-flex items-center gap-1.5 bg-[var(--accent)] text-white hover:bg-[var(--accent-hover)] disabled:opacity-40 disabled:cursor-not-allowed px-3 py-1.5 rounded-[6px] font-sans font-medium text-xs transition-colors"
            >
              <span>Find answer</span>
              <Send size={12} />
            </button>
          </div>
        </div>
      </div>

      <p className="text-[11px] text-[var(--subtle)] font-sans text-center mt-2 select-none">
        Answers come only from your documents.
      </p>
    </div>
  );
}
