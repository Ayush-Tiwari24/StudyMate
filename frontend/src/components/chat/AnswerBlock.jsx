import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import NotFoundNotice from './NotFoundNotice';
import AnswerActions from './AnswerActions';

export default function AnswerBlock({
  messageId,
  question = '',
  answer = '',
  onRetry,
  isStreaming = false,
  onSelectMoreDocuments,
}) {
  // Check if answer is a "not found" state
  const isNotFound =
    answer &&
    (answer.toLowerCase().includes("couldn't find this in the provided documents") ||
      answer.toLowerCase().includes('nothing in your notes covers this') ||
      answer.toLowerCase().includes('nothing in your selected notes covers this'));

  return (
    <article className="flex flex-col gap-2.5 pb-8 border-b border-[var(--line-subtle)] last:border-b-0">
      {question && (
        <h2 className="font-sans text-xl font-semibold text-[var(--ink)] tracking-tight">
          {question}
        </h2>
      )}

      <div className="bg-[var(--surface)] border border-[var(--line)] rounded-[6px] p-6 flex flex-col gap-4 shadow-sm">
        {!answer && !isStreaming ? (
          <div className="flex flex-col gap-2.5 py-1">
            <p className="text-xs text-[var(--muted)]">Could not retrieve answer. The server may have been waking up or timed out.</p>
            {onRetry && (
              <div>
                <button
                  type="button"
                  onClick={onRetry}
                  className="px-3 py-1.5 rounded-[4px] bg-[var(--surface-muted)] border border-[var(--line)] text-xs text-[var(--ink)] hover:border-[var(--accent)] hover:text-[var(--accent)] transition-colors inline-flex items-center gap-1.5 font-medium"
                >
                  <span>Retry Question ↺</span>
                </button>
              </div>
            )}
          </div>
        ) : isNotFound ? (
          <NotFoundNotice onSelectMore={onSelectMoreDocuments} />
        ) : (
          <div className="prose-answer">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                table: ({ node, ...props }) => (
                  <div className="table-wrapper">
                    <table {...props} />
                  </div>
                ),
                td: ({ node, children, ...props }) => {
                  const formatCellChild = (child) => {
                    if (typeof child === 'string' && (/<br\s*\/?>/i.test(child) || /\\n/.test(child))) {
                      const parts = child.replace(/\\n/g, '<br/>').split(/<br\s*\/?>/gi);
                      return parts.map((part, idx) => (
                        <React.Fragment key={idx}>
                          {idx > 0 && <br />}
                          {part}
                        </React.Fragment>
                      ));
                    }
                    return child;
                  };

                  const formatted = React.Children.map(children, (c) => {
                    if (React.isValidElement(c) && c.props && c.props.children) {
                      return React.cloneElement(c, {
                        children: React.Children.map(c.props.children, formatCellChild),
                      });
                    }
                    return formatCellChild(c);
                  });

                  return <td {...props}>{formatted}</td>;
                },
                a: ({ href, children }) => (
                  <a
                    href={href}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-[var(--accent)] underline"
                  >
                    {children}
                  </a>
                ),
              }}
            >
              {answer}
            </ReactMarkdown>
          </div>
        )}

        {!isStreaming && answer && (
          <AnswerActions
            messageId={messageId}
            question={question}
            answer={answer}
            onRetry={onRetry}
          />
        )}
      </div>
    </article>
  );
}
