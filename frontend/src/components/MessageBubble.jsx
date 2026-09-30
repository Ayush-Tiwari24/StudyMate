import ReadingExchange from './ReadingExchange';

export default function MessageBubble({ message, onOpenSources }) {
  if (message.role === 'user') {
    return <h2 className="desk-question-heading">{message.content}</h2>;
  }

  return (
    <ReadingExchange
      question=""
      answer={message.content}
      sources={message.sources || []}
      onOpenSources={onOpenSources}
    />
  );
}
