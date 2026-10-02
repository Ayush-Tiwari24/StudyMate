import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getHistory, deleteChat, updateChat, exportChat } from '../api/chat';
import { Search, Trash2, Edit2, Check, Download, ArrowRight, Clock } from 'lucide-react';

export default function History() {
  const [chats, setChats] = useState([]);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [editingId, setEditingId] = useState(null);
  const [newTitle, setNewTitle] = useState('');
  const navigate = useNavigate();

  const loadHistory = async (searchTerm = '') => {
    setLoading(true);
    try {
      const res = await getHistory(searchTerm);
      setChats(res.data.chats || []);
    } catch (err) {
      console.error('Failed to load history:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const delayDebounce = setTimeout(() => {
      loadHistory(search);
    }, 250);
    return () => clearTimeout(delayDebounce);
  }, [search]);

  const handleDelete = async (id) => {
    if (window.confirm('Delete this study session from history?')) {
      try {
        await deleteChat(id);
        setChats((prev) => prev.filter((c) => c.id !== id));
      } catch (err) {
        console.error('Failed to delete chat:', err);
      }
    }
  };

  const handleRename = async (id) => {
    if (newTitle.trim()) {
      try {
        await updateChat(id, { title: newTitle.trim() });
        setChats((prev) =>
          prev.map((c) => (c.id === id ? { ...c, title: newTitle.trim() } : c))
        );
        setEditingId(null);
      } catch (err) {
        console.error('Failed to rename chat:', err);
      }
    }
  };

  const handleExport = async (id, title) => {
    try {
      const res = await exportChat(id);
      const blob = new Blob([JSON.stringify(res.data, null, 2)], {
        type: 'application/json',
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `studymate_chat_${id}_${title.slice(0, 20)}.json`;
      a.click();
    } catch (err) {
      console.error('Failed to export chat:', err);
    }
  };

  // Group by date: Today, This week, Earlier
  const groupChatsByDate = (list) => {
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
    const oneWeekAgo = today - 7 * 24 * 60 * 60 * 1000;

    const groups = {
      Today: [],
      'This week': [],
      Earlier: [],
    };

    list.forEach((chat) => {
      const chatTime = new Date(chat.updated_at || chat.created_at).getTime();
      if (chatTime >= today) {
        groups.Today.push(chat);
      } else if (chatTime >= oneWeekAgo) {
        groups['This week'].push(chat);
      } else {
        groups.Earlier.push(chat);
      }
    });

    return groups;
  };

  const grouped = groupChatsByDate(chats);

  return (
    <div className="flex-1 overflow-y-auto bg-[var(--paper)] p-6 md:p-10">
      <div className="max-w-4xl mx-auto flex flex-col gap-8">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[var(--line-subtle)]">
          <div>
            <h1 className="font-serif text-2xl md:text-3xl font-semibold text-[var(--ink)] tracking-tight">
              Session History
            </h1>
            <p className="text-xs md:text-sm text-[var(--muted)] font-sans mt-1">
              Past questions and reading notes grouped by date.
            </p>
          </div>

          <div className="flex items-center gap-2 bg-[var(--surface)] border border-[var(--line)] rounded-[6px] px-3 py-1.5 w-full max-w-xs shadow-xs focus-within:border-[var(--accent)] transition-colors">
            <Search size={14} className="text-[var(--muted)]" />
            <input
              type="text"
              placeholder="Search questions…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="text-xs bg-transparent border-none outline-none w-full text-[var(--ink)] placeholder-[var(--subtle)]"
            />
          </div>
        </div>

        {loading && chats.length === 0 ? (
          <div className="p-12 text-center text-xs font-mono text-[var(--muted)]">
            Loading your history…
          </div>
        ) : chats.length === 0 ? (
          <div className="bg-[var(--surface)] border border-[var(--line)] rounded-[6px] p-12 text-center flex flex-col items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-[var(--surface-muted)] flex items-center justify-center text-[var(--muted)]">
              <Clock size={20} strokeWidth={1.5} />
            </div>
            <h2 className="font-serif text-lg font-medium text-[var(--ink)]">
              No past questions found
            </h2>
            <p className="text-xs text-[var(--muted)] max-w-sm">
              Any question you ask at the reading desk will automatically be recorded here.
            </p>
            <button
              onClick={() => navigate('/chat')}
              className="mt-2 inline-flex items-center px-3.5 py-1.5 rounded-[6px] bg-[var(--accent)] text-white text-xs font-medium hover:bg-[var(--accent-hover)] transition-colors"
            >
              Open reading desk
            </button>
          </div>
        ) : (
          <div className="flex flex-col gap-6">
            {Object.entries(grouped).map(([groupTitle, items]) => {
              if (items.length === 0) return null;
              return (
                <div key={groupTitle} className="flex flex-col gap-3">
                  <span className="font-mono text-xs uppercase tracking-wider text-[var(--muted)] font-semibold px-1">
                    {groupTitle}
                  </span>

                  <div className="flex flex-col gap-2">
                    {items.map((chat) => (
                      <div
                        key={chat.id}
                        className="bg-[var(--surface)] border border-[var(--line)] rounded-[6px] p-4 flex items-center justify-between gap-4 hover:border-[var(--muted)] transition-colors shadow-xs"
                      >
                        <div className="flex-1 min-w-0">
                          {editingId === chat.id ? (
                            <div className="flex items-center gap-2">
                              <input
                                type="text"
                                value={newTitle}
                                onChange={(e) => setNewTitle(e.target.value)}
                                className="text-xs p-1.5 rounded border border-[var(--accent)] bg-[var(--paper)] text-[var(--ink)] outline-none w-full max-w-md"
                                autoFocus
                              />
                              <button
                                onClick={() => handleRename(chat.id)}
                                className="p-1.5 rounded bg-[var(--accent)] text-white text-xs hover:bg-[var(--accent-hover)]"
                              >
                                <Check size={13} />
                              </button>
                            </div>
                          ) : (
                            <div>
                              <h3
                                onClick={() => navigate(`/chat/${chat.id}`)}
                                className="font-serif text-base font-medium text-[var(--ink)] cursor-pointer hover:text-[var(--accent)] transition-colors truncate"
                                title={chat.title}
                              >
                                {chat.title}
                              </h3>
                              <span className="text-[11px] font-mono text-[var(--muted)] mt-1 block">
                                {new Date(chat.updated_at || chat.created_at).toLocaleTimeString([], {
                                  hour: '2-digit',
                                  minute: '2-digit',
                                })}
                                {chat.message_count ? ` · ${chat.message_count} messages` : ''}
                              </span>
                            </div>
                          )}
                        </div>

                        <div className="flex items-center gap-1.5 flex-shrink-0">
                          <button
                            onClick={() => {
                              setEditingId(chat.id);
                              setNewTitle(chat.title);
                            }}
                            className="p-1.5 rounded text-[var(--muted)] hover:text-[var(--ink)] hover:bg-[var(--surface-muted)] transition-colors"
                            title="Rename"
                          >
                            <Edit2 size={13} />
                          </button>

                          <button
                            onClick={() => handleExport(chat.id, chat.title)}
                            className="p-1.5 rounded text-[var(--muted)] hover:text-[var(--ink)] hover:bg-[var(--surface-muted)] transition-colors"
                            title="Export session"
                          >
                            <Download size={13} />
                          </button>

                          <button
                            onClick={() => handleDelete(chat.id)}
                            className="p-1.5 rounded text-[var(--muted)] hover:text-[var(--status-failed)] hover:bg-[var(--surface-muted)] transition-colors"
                            title="Delete session"
                          >
                            <Trash2 size={13} />
                          </button>

                          <button
                            onClick={() => navigate(`/chat/${chat.id}`)}
                            className="inline-flex items-center gap-1 text-xs font-medium text-[var(--accent)] hover:underline ml-2"
                          >
                            <span>Open</span>
                            <ArrowRight size={13} />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
