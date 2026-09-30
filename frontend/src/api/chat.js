import client, { getToken } from './client';
import {
  mockListChats,
  mockGetChat,
  mockCreateChat,
  mockDeleteChat,
  mockUpdateChat,
  mockStreamAsk,
} from './mock/chat';

const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true';

export const createChat = (params) => {
  if (USE_MOCK) return mockCreateChat(params);
  // Support both (doc_ids, title) and { document_ids, title }
  const payload = Array.isArray(params)
    ? { document_ids: params, title: 'New Study Session' }
    : params;
  return client.post('/chats', payload);
};

export const listChats = () => {
  if (USE_MOCK) return mockListChats();
  return client.get('/chats');
};

export const getChat = (chatId) => {
  if (USE_MOCK) return mockGetChat(chatId);
  return client.get(`/chats/${chatId}`);
};

export const updateChat = (chatId, data) => {
  if (USE_MOCK) return mockUpdateChat(chatId, data);
  return client.patch(`/chats/${chatId}`, data);
};

export const deleteChat = (chatId) => {
  if (USE_MOCK) return mockDeleteChat(chatId);
  return client.delete(`/chats/${chatId}`);
};

export const exportChat = (chatId, format = 'markdown') =>
  client.get(`/chats/${chatId}/export`, {
    params: { format },
    responseType: 'blob',
  });

export const getHistory = (search = '') => {
  if (USE_MOCK) return mockListChats();
  return client.get('/history', { params: { search } });
};

export const submitFeedback = (messageId, value, comment = '') =>
  client.post(`/messages/${messageId}/feedback`, { value, comment });

/**
 * Streams answer via SSE from POST /api/chats/{chatId}/ask
 */
export async function streamQuestion({
  chatId,
  question,
  documentIds = [],
  top_k,
  signal,
  onToken,
  onSources,
  onDone,
  onError,
}) {
  if (USE_MOCK) {
    return mockStreamAsk({
      question,
      document_ids: documentIds,
      onToken,
      onSources,
      onDone,
      onError,
    });
  }

  const token = getToken();
  const base = import.meta.env.VITE_API_URL
    ? `${import.meta.env.VITE_API_URL.replace(/\/$/, '')}/api`
    : '/api';

  try {
    const response = await fetch(`${base}/chats/${chatId}/ask`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({
        question,
        document_ids: documentIds,
        ...(top_k ? { top_k } : {}),
      }),
      signal,
    });

    if (!response.ok) {
      const errJson = await response.json().catch(() => ({}));
      const msg = errJson.detail || errJson.error?.message || `Server responded with ${response.status}`;
      throw new Error(msg);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const blocks = buffer.split('\n\n');
      buffer = blocks.pop() || '';

      for (const block of blocks) {
        if (!block.trim()) continue;

        let eventType = 'message';
        let dataStr = '';

        for (const line of block.split('\n')) {
          if (line.startsWith('event:')) {
            eventType = line.slice(6).trim();
          } else if (line.startsWith('data:')) {
            dataStr = line.slice(5).trim();
          }
        }

        if (!dataStr) continue;

        try {
          const parsed = JSON.parse(dataStr);
          if (eventType === 'token') {
            onToken && onToken(parsed.text || parsed.token || '');
          } else if (eventType === 'sources') {
            onSources && onSources(parsed.sources || []);
          } else if (eventType === 'done') {
            onDone && onDone(parsed);
          } else if (eventType === 'error') {
            onError && onError(new Error(parsed.error?.message || 'Streaming failed'));
          } else if (parsed.text) {
            onToken && onToken(parsed.text);
          }
        } catch {
          // If raw text
          if (eventType === 'token') {
            onToken && onToken(dataStr);
          }
        }
      }
    }
  } catch (err) {
    if (err.name === 'AbortError') {
      console.log('Stream aborted by user');
      return;
    }
    onError && onError(err);
    throw err;
  }
}
