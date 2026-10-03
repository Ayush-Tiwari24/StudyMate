import { useState, useRef, useCallback } from 'react';
import { streamQuestion } from '../api/chat';

export function useChatStream({ chatId, onMessageComplete }) {
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamedText, setStreamedText] = useState('');
  const [streamedSources, setStreamedSources] = useState([]);
  const [error, setError] = useState(null);
  const abortControllerRef = useRef(null);

  const ask = useCallback(
    async (questionOrObj, docIdsParam = [], explicitChatId = null) => {
      let question = '';
      let documentIds = [];
      let targetChatId = explicitChatId || chatId;

      if (typeof questionOrObj === 'object' && questionOrObj !== null) {
        question = questionOrObj.question || '';
        documentIds = questionOrObj.documentIds || questionOrObj.document_ids || [];
        if (questionOrObj.chatId) {
          targetChatId = questionOrObj.chatId;
        }
      } else {
        question = questionOrObj || '';
        documentIds = docIdsParam;
      }

      if (!targetChatId) {
        console.warn('Cannot stream question without a chatId');
        return;
      }

      setIsStreaming(true);
      setStreamedText('');
      setStreamedSources([]);
      setError(null);

      abortControllerRef.current = new AbortController();

      let accumulatedText = '';
      let receivedSources = [];
      const sendTime = performance.now();
      let firstTokenLogged = false;

      try {
        await streamQuestion({
          chatId: targetChatId,
          question,
          documentIds,
          signal: abortControllerRef.current.signal,
          onToken: (token) => {
            if (!firstTokenLogged && token) {
              firstTokenLogged = true;
              const ttft = (performance.now() - sendTime).toFixed(1);
              if (import.meta.env.DEV) {
                console.info(`[Perf] TTFT (Send -> First Token): ${ttft} ms`);
              }
            }
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
