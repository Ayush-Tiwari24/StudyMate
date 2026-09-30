import React, { useState, useRef, useEffect } from 'react';
import {
  Send,
  Square,
  Sparkles,
  AlertCircle,
  FileText,
  HelpCircle,
  ArrowDown,
  Loader2,
} from 'lucide-react';
import MessageBubble from './MessageBubble';
import SourcePanel from './SourcePanel';

export default function ChatWindow({
  chat,
  messages = [],
  isStreaming = false,
  streamedText = '',
  streamedSources = [],
  error = null,
  onSendMessage,
  onAbort,
  selectedDocCount = 0,
}) {
  const [inputText, setInputText] = useState('');
  const [sourcesPanelOpen, setSourcesPanelOpen] = useState(false);
  const [panelSources, setPanelSources] = useState([]);
  const [activeCitationIndex, setActiveCitationIndex] = useState(null);
  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);

  // Auto-scroll to bottom on new messages or streamed tokens
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamedText]);

  // Adjust textarea height automatically
  const handleInput = (e) => {
    setInputText(e.target.value);
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 180)}px`;
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleSubmit = (e) => {
    e?.preventDefault();
    if (!inputText.trim() || isStreaming || selectedDocCount === 0) return;
    onSendMessage(inputText.trim());
    setInputText('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleOpenSources = (sources, activeIndex = 1) => {
    setPanelSources(sources || []);
    setActiveCitationIndex(activeIndex);
    setSourcesPanelOpen(true);
  };

  const starterQuestions = [
    'Summarize the key concepts covered in these documents.',
    'What are the core definitions and terms explained here?',
    'Give me a 5-question study quiz based on this material.',
    'Highlight the most important formulas or principles.',
  ];

  return (
    <div className="chat-window-container">
      {/* Messages list */}
      <div className="chat-messages-area">
        {messages.length === 0 && !isStreaming ? (
          <div className="chat-empty-state">
            <div className="empty-state-icon">
              <Sparkles className="w-10 h-10 text-indigo-400" />
            </div>
            <h3 className="text-xl font-semibold text-white mb-2">
              Ready to study?
            </h3>
            <p className="text-gray-400 text-sm max-w-md text-center mb-6">
              Ask questions about your uploaded materials. Every answer includes verified inline citations directly from your PDF pages.
            </p>

            <div className="starter-prompts-grid">
              {starterQuestions.map((q, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => {
                    if (selectedDocCount > 0) {
                      onSendMessage(q);
                    } else {
                      setInputText(q);
                    }
                  }}
                  className="starter-prompt-card"
                >
                  <HelpCircle className="w-4 h-4 text-indigo-400 flex-shrink-0" />
                  <span>{q}</span>
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="messages-flow">
            {messages.map((msg, idx) => (
              <MessageBubble
                key={msg.id || idx}
                message={msg}
                onOpenSources={handleOpenSources}
              />
            ))}

            {/* Currently streaming bubble */}
            {isStreaming && (
              <div className="message-bubble-wrapper assistant-wrapper">
                <div className="message-avatar">
                  <div className="avatar-icon assistant-icon animate-pulse">
                    <Sparkles className="w-4 h-4 text-indigo-400" />
                  </div>
                </div>
                <div className="message-content-container assistant-container">
                  <div className="message-sender-meta">
                    <span className="sender-name">StudyMate AI</span>
                    <span className="meta-badge text-indigo-300">
                      <Loader2 className="w-3 h-3 inline mr-1 animate-spin" />
                      Thinking & retrieving...
                    </span>
                  </div>
                  <div className="message-body streaming-text">
                    {streamedText}
                    <span className="streaming-cursor">▍</span>
                  </div>
                  {streamedSources.length > 0 && (
                    <div className="message-sources-summary mt-2">
                      <button
                        type="button"
                        className="sources-toggle-btn"
                        onClick={() => handleOpenSources(streamedSources, 1)}
                      >
                        <span>{streamedSources.length} sources retrieved</span>
                      </button>
                    </div>
                  )}
                </div>
              </div>
            )}

            {error && (
              <div className="alert-banner alert-error my-3">
                <AlertCircle className="w-4 h-4 mr-2 flex-shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Input Form Bar */}
      <div className="chat-input-bar">
        {selectedDocCount === 0 && (
          <div className="doc-warning-banner">
            <AlertCircle className="w-3.5 h-3.5 mr-1.5 flex-shrink-0" />
            <span>Please select at least 1 document from the sidebar to query.</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="chat-input-form">
          <textarea
            ref={textareaRef}
            rows={1}
            value={inputText}
            onChange={handleInput}
            onKeyDown={handleKeyDown}
            placeholder={
              selectedDocCount === 0
                ? 'Select documents in the sidebar first...'
                : 'Type your academic question (Press Enter to send, Shift+Enter for new line)...'
            }
            disabled={isStreaming || selectedDocCount === 0}
            className="chat-textarea"
          />

          <div className="chat-input-actions">
            {isStreaming ? (
              <button
                type="button"
                onClick={onAbort}
                className="btn-abort"
                title="Stop generating"
              >
                <Square className="w-4 h-4 text-white" />
              </button>
            ) : (
              <button
                type="submit"
                disabled={!inputText.trim() || selectedDocCount === 0}
                className="btn-send"
                title="Send question"
              >
                <Send className="w-4 h-4" />
              </button>
            )}
          </div>
        </form>
      </div>

      {/* Citations Drawer */}
      <SourcePanel
        isOpen={sourcesPanelOpen}
        onClose={() => setSourcesPanelOpen(false)}
        sources={panelSources}
        activeIndex={activeCitationIndex}
      />
    </div>
  );
}
