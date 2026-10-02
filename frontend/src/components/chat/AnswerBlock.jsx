import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import FootnoteMarker from './FootnoteMarker';
import FootnoteList from './FootnoteList';
import NotFoundNotice from './NotFoundNotice';
import AnswerActions from './AnswerActions';

export default function AnswerBlock({
  messageId,
  question = '',
  answer = '',
  sources = [],
  onSelectCitation,
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

  // Normalize citations: [1], [^1], [1, 2], [1,2,3] -> [1](#cite-1), [2](#cite-2)
  const processAnswerText = (text) => {
    if (!text) return '';
    let formatted = text.replace(/\[\^(\d+)\]/g, '[$1]');
    formatted = formatted.replace(/\[([\d,\s]+)\]/g, (match, inner) => {
      const numbers = inner.split(',').map((n) => n.trim()).filter((n) => /^\d+$/.test(n));
      if (numbers.length === 0) return match;
      return numbers.map((n) => `[${n}](#cite-${n})`).join(', ');
    });
    return formatted;
  };

  const processedAnswer = processAnswerText(answer);

  return (
    <article className="flex flex-col gap-2.5 pb-8 border-b border-[var(--line-subtle)] last:border-b-0">
      {/* Question as clean heading */}
      {question && (
        <h2 className="font-sans text-xl font-semibold text-[var(--ink)] tracking-tight">
          {question}
        </h2>
      )}

      {/* Answer card with textbook serif */}
      <div className="bg-[var(--surface)] border border-[var(--line)] rounded-[6px] p-6 flex flex-col gap-4 shadow-sm">
        {isNotFound ? (
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
                a: ({ href, children }) => {
                  if (href && href.startsWith('#cite-')) {
                    const index = parseInt(href.replace('#cite-', ''), 10);
                    const source = sources && sources[index - 1];
                    return (
                      <FootnoteMarker
                        key={href}
                        index={index}
                        source={source}
                        onClick={() => onSelectCitation && onSelectCitation(source, index)}
                      />
                    );
                  }
                  return (
                    <a
                      href={href}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-[var(--accent)] underline"
                    >
                      {children}
                    </a>
                  );
                },
              }}
            >
              {processedAnswer}
            </ReactMarkdown>
          </div>
        )}

        {/* Footnotes list under answer */}
        {!isNotFound && sources && sources.length > 0 && (
          <FootnoteList
            sources={sources}
            onSelectCitation={(src, idx) => onSelectCitation && onSelectCitation(src, idx, sources)}
          />
        )}

        {/* Small text actions below answer */}
        {!isStreaming && answer && (
          <AnswerActions
            messageId={messageId}
            question={question}
            answer={answer}
            sources={sources}
            onRetry={onRetry}
          />
        )}
      </div>
    </article>
  );
}
