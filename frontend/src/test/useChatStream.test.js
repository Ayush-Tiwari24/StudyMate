import { renderHook, act } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { useChatStream } from '../hooks/useChatStream';
import * as chatApi from '../api/chat';

describe('useChatStream hook', () => {
  it('accumulates plain tokens and completes on done', async () => {
    const onMessageComplete = vi.fn();

    // Mock streamQuestion implementation
    vi.spyOn(chatApi, 'streamQuestion').mockImplementation(async ({ onToken, onDone }) => {
      onToken('Hello');
      onToken(' world');
      onDone({ message_id: 101, latency_ms: 320 });
    });

    const { result } = renderHook(() =>
      useChatStream({ chatId: 1, onMessageComplete })
    );

    expect(result.current.isStreaming).toBe(false);

    await act(async () => {
      await result.current.ask({ question: 'Test question', documentIds: [1] });
    });

    expect(result.current.isStreaming).toBe(false);
    expect(result.current.streamedText).toBe('Hello world');
    expect(onMessageComplete).toHaveBeenCalledWith({
      content: 'Hello world',
      messageId: 101,
      latencyMs: 320,
    });
  });

  it('handles stream error event properly', async () => {
    vi.spyOn(chatApi, 'streamQuestion').mockImplementation(async ({ onError }) => {
      onError(new Error('Rate limit exceeded. Please wait 10s.'));
    });

    const { result } = renderHook(() =>
      useChatStream({ chatId: 1, onMessageComplete: vi.fn() })
    );

    await act(async () => {
      await result.current.ask({ question: 'Fail test', documentIds: [1] });
    });

    expect(result.current.isStreaming).toBe(false);
    expect(result.current.error).toBe('Rate limit exceeded. Please wait 10s.');
  });
});
