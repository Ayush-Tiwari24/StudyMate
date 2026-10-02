import React from 'react';
import { BookOpen, Plus, FolderOpen } from 'lucide-react';
import StatusDot from '../library/StatusDot';
import { useNavigate } from 'react-router-dom';

export default function Shelf({
  documents = [],
  selectedDocIds = [],
  onToggleDoc,
  chats = [],
  activeChatId,
  onSelectChat,
  onNewQuestion,
  className = '',
}) {
  const navigate = useNavigate();

  return (
    <aside
      className={`w-full bg-[var(--surface-muted)] border-r border-[var(--line)] flex flex-col h-full overflow-hidden select-none ${className}`}
      aria-label="The Shelf"
    >
      <div className="p-3.5 border-b border-[var(--line)] flex items-center justify-between">
        <div className="flex items-center gap-2">
          <BookOpen size={16} strokeWidth={2} className="text-[var(--accent)]" />
          <span className="font-mono text-xs font-semibold uppercase tracking-wider text-[var(--ink)]">
            The Shelf
          </span>
        </div>
        <span className="font-mono text-xs px-2 py-0.5 rounded-[4px] bg-[var(--paper)] border border-[var(--line)] text-[var(--muted)]">
          {selectedDocIds.length} on desk
        </span>
      </div>

      <div className="flex-1 overflow-y-auto p-3 flex flex-col gap-5">
        <div>
          <div className="flex items-center justify-between mb-2 px-1">
            <span className="font-mono text-[11px] font-semibold text-[var(--muted)] uppercase tracking-wider">
              Documents
            </span>
            <button
              type="button"
              onClick={() => navigate('/library')}
              className="text-xs text-[var(--muted)] hover:text-[var(--accent)] inline-flex items-center gap-1 font-medium"
              title="Add documents to shelf"
            >
              <Plus size={12} /> Add
            </button>
          </div>

          <div className="flex flex-col gap-1">
            {documents.length === 0 ? (
              <div className="p-3 text-xs text-[var(--muted)] text-center bg-[var(--surface)] border border-[var(--line)] rounded-[6px]">
                No documents on your shelf.{' '}
                <button
                  type="button"
                  onClick={() => navigate('/library')}
                  className="text-[var(--accent)] hover:underline block mx-auto mt-1"
                >
                  Add PDF notes →
                </button>
              </div>
            ) : (
              documents.map((doc) => {
                const isReady = doc.status === 'ready';
                const isSelected = selectedDocIds.includes(doc.id);

                return (
                  <label
                    key={doc.id}
                    className={`flex items-start gap-2.5 p-2 rounded-[6px] border transition-colors cursor-pointer ${
                      isSelected
                        ? 'bg-[var(--surface)] border-[var(--accent)]'
                        : 'bg-[var(--surface)] border-[var(--line-subtle)] hover:bg-[var(--surface-hover)]'
                    } ${!isReady ? 'opacity-60 cursor-not-allowed' : ''}`}
                  >
                    <input
                      type="checkbox"
                      disabled={!isReady}
                      checked={isSelected}
                      onChange={() => isReady && onToggleDoc(doc.id)}
                      className="mt-0.5 accent-[var(--accent)] cursor-pointer"
                    />
                    <div className="flex-1 min-w-0">
                      <span
                        className="block text-xs font-medium text-[var(--ink)] truncate"
                        title={doc.filename}
                      >
                        {doc.filename}
                      </span>
                      <div className="flex items-center gap-2 mt-1">
                        <StatusDot
                          status={doc.status}
                          labelOverride={isReady ? `${doc.pages || 0} pages` : undefined}
                        />
                      </div>
                    </div>
                  </label>
                );
              })
            )}
          </div>
        </div>

        <div>
          <div className="flex items-center justify-between mb-2 px-1">
            <span className="font-mono text-[11px] font-semibold text-[var(--muted)] uppercase tracking-wider">
              Recent Questions
            </span>
          </div>

          <div className="flex flex-col gap-0.5">
            {chats.length === 0 ? (
              <span className="text-xs text-[var(--subtle)] px-1">
                No past questions yet.
              </span>
            ) : (
              chats.slice(0, 10).map((c) => {
                const isActive = activeChatId === c.id;
                return (
                  <button
                    key={c.id}
                    type="button"
                    onClick={() => onSelectChat(c.id)}
                    className={`text-left text-xs px-2.5 py-1.5 rounded-[6px] truncate transition-colors ${
                      isActive
                        ? 'bg-[var(--surface)] text-[var(--ink)] font-medium border border-[var(--line)]'
                        : 'text-[var(--muted)] hover:text-[var(--ink)] hover:bg-[var(--surface-hover)]'
                    }`}
                    title={c.title}
                  >
                    {c.title}
                  </button>
                );
              })
            )}
          </div>
        </div>
      </div>

      <div className="p-3 border-t border-[var(--line)] bg-[var(--surface)]">
        <button
          type="button"
          onClick={onNewQuestion}
          className="w-full inline-flex items-center justify-center gap-1.5 py-1.5 px-3 rounded-[6px] border border-[var(--line)] bg-[var(--surface)] hover:bg-[var(--surface-hover)] text-xs font-medium text-[var(--ink)] transition-colors"
        >
          <Plus size={13} />
          <span>New question</span>
        </button>
      </div>
    </aside>
  );
}
