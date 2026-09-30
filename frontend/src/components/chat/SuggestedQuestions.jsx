import React from 'react';

const DEFAULT_QUESTIONS = [
  'Summarize the core topics and principles explained in these notes.',
  'What are the primary definitions and technical terms introduced here?',
  'Explain the key formulas, theorems, or algorithmic steps.',
  'Generate a 5-question study quiz based on this material.',
];

export default function SuggestedQuestions({
  questions,
  onSelectQuestion,
  className = '',
}) {
  const list = questions && questions.length > 0 ? questions : DEFAULT_QUESTIONS;

  return (
    <div className={`flex flex-col gap-2 w-full max-w-xl mx-auto ${className}`}>
      <span className="text-xs text-[var(--muted)] font-mono uppercase tracking-wider text-left">
        Suggested questions
      </span>
      <div className="grid grid-cols-1 gap-2">
        {list.map((q, idx) => (
          <button
            key={idx}
            type="button"
            onClick={() => onSelectQuestion(q)}
            className="text-left p-3 rounded-[6px] bg-[var(--surface)] border border-[var(--line)] text-sm text-[var(--ink)] hover:border-[var(--accent)] hover:bg-[var(--surface-hover)] transition-all leading-snug"
          >
            {q}
          </button>
        ))}
      </div>
    </div>
  );
}
