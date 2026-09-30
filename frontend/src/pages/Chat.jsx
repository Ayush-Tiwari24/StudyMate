import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useDocuments } from '../hooks/useDocuments';
import { useChatStream } from '../hooks/useChatStream';
import { useHotkeys } from '../hooks/useHotkeys';
import Shelf from '../components/chat/Shelf';
import AnswerBlock from '../components/chat/AnswerBlock';
import ChatInput from '../components/chat/ChatInput';
import ScopeChips from '../components/chat/ScopeChips';
import SuggestedQuestions from '../components/chat/SuggestedQuestions';
import SourcePanel from '../components/source/SourcePanel';
import KeyboardShortcutsModal from '../components/chat/KeyboardShortcutsModal';
import { listChats, getChat, createChat } from '../api/chat';
import { PanelLeft, PanelLeftClose, HelpCircle } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

export default function Chat() {
  const { chatId } = useParams();
  const navigate = useNavigate();
  const { documents, readyDocuments } = useDocuments();

  const [chats, setChats] = useState([]);
  const [currentChat, setCurrentChat] = useState(null);
  const [messages, setMessages] = useState([]);
  const [selectedDocIds, setSelectedDocIds] = useState([]);

  // Desktop layout toggles
  const [shelfOpen, setShelfOpen] = useState(true);
  const [sourcePanelOpen, setSourcePanelOpen] = useState(false);
  const [activeSources, setActiveSources] = useState([]);
  const [activeCitationIndex, setActiveCitationIndex] = useState(1);
  const [lastQuery, setLastQuery] = useState('');

  // Mobile layout state (< 900px)
  const [mobileTab, setMobileTab] = useState('answer'); // 'shelf' | 'answer' | 'source'
  const [isMobile, setIsMobile] = useState(window.innerWidth < 900);

  // Keyboard shortcut modal
  const [shortcutsModalOpen, setShortcutsModalOpen] = useState(false);

  // Input state
  const [questionText, setQuestionText] = useState('');
  const textareaRef = useRef(null);
  const scrollAnchorRef = useRef(null);
  const isSendingRef = useRef(false);
  const currentChatRef = useRef(null);

  // Handle window resize for mobile breakpoint
  useEffect(() => {
    const handleResize = () => {
      const mobile = window.innerWidth < 900;
      setIsMobile(mobile);
      if (mobile && sourcePanelOpen && mobileTab !== 'source') {
        // on mobile keep source panel controlled by mobile tab
      }
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [sourcePanelOpen, mobileTab]);

  // Load chat list
  const loadChatsList = useCallback(async () => {
    try {
      const res = await listChats();
      setChats(res.data.chats || []);
    } catch (err) {
      console.error('Failed to load chat sessions:', err);
    }
  }, []);

  useEffect(() => {
    loadChatsList();
  }, [loadChatsList]);

  // Auto-select ready documents if none selected initially
  useEffect(() => {
    if (selectedDocIds.length === 0 && readyDocuments.length > 0) {
      setSelectedDocIds(readyDocuments.map((d) => d.id));
    }
  }, [readyDocuments, selectedDocIds.length]);

  // Load specific chat if in URL
  useEffect(() => {
    async function loadCurrentChat() {
      if (!chatId) {
        currentChatRef.current = null;
        setCurrentChat(null);
        setMessages([]);
        return;
      }

      // If we already have this chat session in memory, don't wipe active in-flight messages
      if (currentChatRef.current && String(currentChatRef.current.id) === String(chatId)) {
        return;
      }

      try {
        const res = await getChat(chatId);
        currentChatRef.current = res.data;
        setCurrentChat(res.data);
        setMessages(res.data.messages || []);
        if (res.data.document_ids && res.data.document_ids.length > 0) {
          setSelectedDocIds(res.data.document_ids);
        }
      } catch (err) {
        console.error('Failed to load chat session:', err);
        navigate('/chat', { replace: true });
      }
    }

    loadCurrentChat();
  }, [chatId, navigate]);

  // Auto-scroll when messages or streamed text changes
  useEffect(() => {
    scrollAnchorRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Handle message completion from streaming hook
  const handleMessageComplete = useCallback(
    ({ content, sources, messageId }) => {
      setMessages((prev) => [
        ...prev,
        {
          id: messageId || Date.now(),
          role: 'assistant',
          content,
          sources: sources || [],
          created_at: new Date().toISOString(),
        },
      ]);

      if (sources && sources.length > 0) {
        setActiveSources(sources);
        setActiveCitationIndex(1);
        setSourcePanelOpen(true);
      }
      loadChatsList();
    },
    [loadChatsList]
  );

  const { ask, isStreaming, streamedText, streamedSources } = useChatStream({
    chatId: currentChat?.id,
    onMessageComplete: handleMessageComplete,
  });

  // Whenever streamed sources arrive during generation, show them in panel
  useEffect(() => {
    if (streamedSources && streamedSources.length > 0) {
      setActiveSources(streamedSources);
      setActiveCitationIndex(1);
      setSourcePanelOpen(true);
    }
  }, [streamedSources]);

  // Send question handler
  const handleSendQuestion = async (overrideText) => {
    const q = (overrideText || questionText).trim();
    if (!q || isStreaming || isSendingRef.current || selectedDocIds.length === 0) return;

    isSendingRef.current = true;
    try {
      setLastQuery(q);
      let activeChatId = currentChat?.id;

      if (!activeChatId) {
        try {
          const res = await createChat({
            title: q.slice(0, 36),
            document_ids: selectedDocIds,
          });
          const newChat = res.data;
          currentChatRef.current = newChat;
          setCurrentChat(newChat);
          activeChatId = newChat.id;
          navigate(`/chat/${newChat.id}`, { replace: true });
        } catch (err) {
          console.error('Failed to create new chat session:', err);
        }
      }

      // Add user message to UI immediately
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now(),
          role: 'user',
          content: q,
          created_at: new Date().toISOString(),
        },
      ]);
      setQuestionText('');

      if (isMobile) {
        setMobileTab('answer');
      }

      await ask({
        chatId: activeChatId,
        question: q,
        documentIds: selectedDocIds,
      });
    } finally {
      isSendingRef.current = false;
    }
  };

  // Open citation in source panel
  const handleSelectCitation = (source, index) => {
    if (source) {
      // Find source index in activeSources
      const idx = activeSources.findIndex((s) => s.id === source.id || (s.file === source.file && s.page === source.page));
      setActiveCitationIndex(idx !== -1 ? idx + 1 : index || 1);
    } else {
      setActiveCitationIndex(index || 1);
    }
    setSourcePanelOpen(true);
    if (isMobile) {
      setMobileTab('source');
    }
  };

  // Toggle document selection
  const handleToggleDoc = (docId) => {
    setSelectedDocIds((prev) =>
      prev.includes(docId) ? prev.filter((id) => id !== docId) : [...prev, docId]
    );
  };

  const handleRemoveDocScope = (docId) => {
    setSelectedDocIds((prev) => prev.filter((id) => id !== docId));
  };

  // Register hotkeys (/ focus, Esc close, 1-9 jump citation, ? help)
  useHotkeys(
    {
      '/': () => textareaRef.current?.focus(),
      Escape: () => {
        if (shortcutsModalOpen) setShortcutsModalOpen(false);
        else setSourcePanelOpen(false);
      },
      '?': () => setShortcutsModalOpen((prev) => !prev),
      1: () => activeSources[0] && handleSelectCitation(activeSources[0], 1),
      2: () => activeSources[1] && handleSelectCitation(activeSources[1], 2),
      3: () => activeSources[2] && handleSelectCitation(activeSources[2], 3),
      4: () => activeSources[3] && handleSelectCitation(activeSources[3], 4),
      5: () => activeSources[4] && handleSelectCitation(activeSources[4], 5),
      6: () => activeSources[5] && handleSelectCitation(activeSources[5], 6),
      7: () => activeSources[6] && handleSelectCitation(activeSources[6], 7),
      8: () => activeSources[7] && handleSelectCitation(activeSources[7], 8),
      9: () => activeSources[8] && handleSelectCitation(activeSources[8], 9),
    },
    [shortcutsModalOpen, activeSources]
  );

  // Group messages into Q&A exchanges
  const exchanges = [];
  for (let i = 0; i < messages.length; i++) {
    const msg = messages[i];
    if (msg.role === 'user') {
      const nextMsg = messages[i + 1]?.role === 'assistant' ? messages[i + 1] : null;
      // If streaming and this is the active user message waiting for assistant response,
      // skip it from completed exchanges so it is NOT rendered twice (it renders in the active streaming block below)
      if (isStreaming && !nextMsg && i === messages.length - 1) {
        continue;
      }
      exchanges.push({
        id: msg.id,
        question: msg.content,
        answer: nextMsg ? nextMsg.content : '',
        sources: nextMsg ? nextMsg.sources || [] : [],
        isComplete: !!nextMsg,
      });
      if (nextMsg) i++;
    } else {
      exchanges.push({
        id: msg.id,
        question: '',
        answer: msg.content,
        sources: msg.sources || [],
        isComplete: true,
      });
    }
  }

  // Active selected document objects for ScopeChips
  const selectedDocs = documents.filter((d) => selectedDocIds.includes(d.id));

  // Determine currently streaming question
  const lastUserMessage = [...messages].reverse().find((m) => m.role === 'user');

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden bg-[var(--paper)]">
      {/* Mobile Tab Bar (< 900px) */}
      {isMobile && (
        <div className="h-10 bg-[var(--surface)] border-b border-[var(--line)] flex items-center justify-around text-xs font-mono select-none flex-shrink-0">
          <button
            onClick={() => setMobileTab('shelf')}
            className={`flex-1 h-full border-b-2 font-medium transition-colors ${
              mobileTab === 'shelf'
                ? 'border-[var(--accent)] text-[var(--accent)]'
                : 'border-transparent text-[var(--muted)]'
            }`}
          >
            Shelf ({selectedDocIds.length})
          </button>
          <button
            onClick={() => setMobileTab('answer')}
            className={`flex-1 h-full border-b-2 font-medium transition-colors ${
              mobileTab === 'answer'
                ? 'border-[var(--accent)] text-[var(--accent)]'
                : 'border-transparent text-[var(--muted)]'
            }`}
          >
            Answer Desk
          </button>
          <button
            onClick={() => setMobileTab('source')}
            className={`flex-1 h-full border-b-2 font-medium transition-colors ${
              mobileTab === 'source'
                ? 'border-[var(--accent)] text-[var(--accent)]'
                : 'border-transparent text-[var(--muted)]'
            }`}
          >
            Source ({activeSources.length})
          </button>
        </div>
      )}

      {/* Main Reading Desk Body */}
      <div className="flex-1 flex overflow-hidden relative">
        {/* COLUMN 1: THE SHELF (Left) */}
        {(!isMobile || mobileTab === 'shelf') && (
          <div className={`${isMobile ? 'w-full' : shelfOpen ? 'w-72' : 'w-0 hidden'} flex-shrink-0 transition-all duration-150`}>
            <Shelf
              documents={documents}
              selectedDocIds={selectedDocIds}
              onToggleDoc={handleToggleDoc}
              chats={chats}
              activeChatId={currentChat?.id}
              onSelectChat={(id) => navigate(`/chat/${id}`)}
              onNewQuestion={() => {
                currentChatRef.current = null;
                navigate('/chat');
                setMessages([]);
                setCurrentChat(null);
                if (isMobile) setMobileTab('answer');
              }}
              className="h-full"
            />
          </div>
        )}

        {/* COLUMN 2: THE ANSWER DESK (Center) */}
        {(!isMobile || mobileTab === 'answer') && (
          <main className="flex-1 flex flex-col h-full overflow-hidden bg-[var(--paper)] min-w-0">
            {/* Answer Desk Top Toolbar */}
            <div className="h-10 px-4 border-b border-[var(--line-subtle)] flex items-center justify-between flex-shrink-0">
              <div className="flex items-center gap-2">
                {!isMobile && (
                  <button
                    onClick={() => setShelfOpen(!shelfOpen)}
                    className="p-1 rounded text-[var(--muted)] hover:text-[var(--ink)] hover:bg-[var(--surface-hover)] transition-colors"
                    title={shelfOpen ? 'Collapse shelf' : 'Expand shelf'}
                  >
                    {shelfOpen ? <PanelLeftClose size={15} /> : <PanelLeft size={15} />}
                  </button>
                )}
                <span className="font-mono text-xs text-[var(--muted)] truncate">
                  {selectedDocIds.length} notes active
                </span>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={() => setShortcutsModalOpen(true)}
                  className="inline-flex items-center gap-1 text-xs font-mono text-[var(--muted)] hover:text-[var(--ink)] p-1 rounded hover:bg-[var(--surface-hover)] transition-colors"
                  title="Keyboard shortcuts (?)"
                >
                  <HelpCircle size={13} />
                  <span className="hidden sm:inline">Shortcuts</span>
                </button>
              </div>
            </div>

            {/* Scrollable Answers Area */}
            <div className="flex-1 overflow-y-auto px-4 md:px-12 py-6 flex flex-col gap-6">
              {/* Empty State: Suggested Questions */}
              {messages.length === 0 && !isStreaming && (
                <div className="my-auto max-w-2xl mx-auto w-full py-8">
                  <div className="text-center mb-8">
                    <h1 className="font-serif text-3xl font-medium text-[var(--ink)] tracking-tight mb-2">
                      A reading desk for your study notes.
                    </h1>
                    <p className="text-sm text-[var(--muted)] font-sans max-w-md mx-auto">
                      Ask any question about your uploaded PDFs. Every answer is grounded directly in the text with verified page citations.
                    </p>
                  </div>

                  <SuggestedQuestions
                    onSelectQuestion={(q) => handleSendQuestion(q)}
                  />
                </div>
              )}

              {/* Completed Answer Exchanges */}
              {exchanges.map((ex, i) => (
                <AnswerBlock
                  key={ex.id || i}
                  messageId={ex.id}
                  question={ex.question}
                  answer={ex.answer}
                  sources={ex.sources}
                  onSelectCitation={handleSelectCitation}
                  onRetry={() => handleSendQuestion(ex.question)}
                  onSelectMoreDocuments={() => {
                    if (isMobile) setMobileTab('shelf');
                    else setShelfOpen(true);
                  }}
                />
              ))}

              {/* Active Streaming Answer Block */}
              {isStreaming && (
                <div className="flex flex-col gap-2.5 pb-8 animate-fadeIn">
                  {lastUserMessage && (
                    <h2 className="font-sans text-xl font-semibold text-[var(--ink)] tracking-tight">
                      {lastUserMessage.content}
                    </h2>
                  )}

                  <div className="bg-[var(--surface)] border border-[var(--line)] rounded-[6px] p-6 shadow-sm flex flex-col gap-4">
                    {!streamedText ? (
                      <div className="flex items-center gap-2 text-xs font-mono text-[var(--muted)]">
                        <div className="w-2 h-2 rounded-full bg-[var(--accent)] animate-pulse" />
                        <span>Searching {selectedDocIds.length} documents…</span>
                      </div>
                    ) : (
                      <div className="prose-answer">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                          {streamedText}
                        </ReactMarkdown>
                      </div>
                    )}
                  </div>
                </div>
              )}

              <div ref={scrollAnchorRef} />
            </div>

            {/* Bottom Input Area */}
            <div className="p-4 bg-[var(--paper)] border-t border-[var(--line-subtle)] flex flex-col items-center flex-shrink-0">
              <ScopeChips
                selectedDocIds={selectedDocIds}
                documents={documents}
                onRemoveDoc={handleRemoveDocScope}
                onSelectAll={() => setSelectedDocIds(readyDocuments.map((d) => d.id))}
              />

              <ChatInput
                value={questionText}
                onChange={setQuestionText}
                onSubmit={() => handleSendQuestion()}
                isStreaming={isStreaming}
                selectedDocCount={selectedDocIds.length}
                textareaRef={textareaRef}
              />
            </div>
          </main>
        )}

        {/* COLUMN 3: THE SOURCE EVIDENCE (Right) */}
        {(!isMobile || mobileTab === 'source') && (
          <div className={`${isMobile ? 'w-full' : sourcePanelOpen ? 'flex' : 'hidden'} flex-shrink-0 h-full`}>
            <SourcePanel
              isOpen={isMobile ? true : sourcePanelOpen}
              onClose={() => {
                if (isMobile) setMobileTab('answer');
                else setSourcePanelOpen(false);
              }}
              sources={activeSources}
              activeCitationIndex={activeCitationIndex}
              onSelectCitation={(src, idx) => {
                setActiveCitationIndex(idx);
              }}
              query={lastQuery}
            />
          </div>
        )}
      </div>

      {/* Keyboard Shortcuts Dialog Modal */}
      <KeyboardShortcutsModal
        isOpen={shortcutsModalOpen}
        onClose={() => setShortcutsModalOpen(false)}
      />
    </div>
  );
}
