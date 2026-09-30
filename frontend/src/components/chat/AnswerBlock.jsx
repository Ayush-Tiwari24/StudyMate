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

  // Convert plain text [1], [2] to citation markdown links [1](#cite-1)
  const processedAnswer = (answer || '').replace(/\[(\d+)\]/g, '[$1](#cite-$1)');

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
            onSelectCitation={onSelectCitation}
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
