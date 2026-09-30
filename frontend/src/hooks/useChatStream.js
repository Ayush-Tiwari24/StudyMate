import { useState, useRef, useCallback } from 'react';
import { streamQuestion } from '../api/chat';

export function useChatStream({ chatId, onMessageComplete }) {
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamedText, setStreamedText] = useState('');
  const [streamedSources, setStreamedSources] = useState([]);
  const [error, setError] = useState(null);
  const abortControllerRef = useRef(null);

  const ask = useCallback(
    async (questionOrObj, docIdsParam = []) => {
      let question = '';
      let documentIds = [];

      if (typeof questionOrObj === 'object' && questionOrObj !== null) {
        question = questionOrObj.question || '';
        documentIds = questionOrObj.documentIds || questionOrObj.document_ids || [];
      } else {
        question = questionOrObj || '';
        documentIds = docIdsParam;
      }

      if (!chatId) return;

      setIsStreaming(true);
      setStreamedText('');
      setStreamedSources([]);
      setError(null);

      abortControllerRef.current = new AbortController();

      let accumulatedText = '';
      let receivedSources = [];

      try {
        await streamQuestion({
          chatId,
          question,
          documentIds,
          signal: abortControllerRef.current.signal,
          onToken: (token) => {
            accumulatedText += token;
            setStreamedText((prev) => prev + token);
          },
          onSources: (data) => {
            const sourcesList = Array.isArray(data) ? data : data.sources || [];
            receivedSources = sourcesList;
            setStreamedSources(sourcesList);
          },
          onDone: (data) => {
            setIsStreaming(false);
            onMessageComplete?.({
              content: accumulatedText,
              sources: receivedSources,
              messageId: data?.message_id,
              latencyMs: data?.latency_ms,
            });
          },
          onError: (err) => {
            console.error('Chat stream error:', err);
            setError(err.message || 'Error generating response');
            setIsStreaming(false);
          },
        });
      } catch (err) {
        if (err.name !== 'AbortError') {
          setError(err.message || 'Request failed');
        }
        setIsStreaming(false);
      }
    },
    [chatId, onMessageComplete]
  );

  const abort = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      setIsStreaming(false);
    }
  }, []);

  return {
    ask,
    abort,
    isStreaming,
    streamedText,
    streamedSources,
    error,
  };
}
