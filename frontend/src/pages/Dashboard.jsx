import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useDocuments } from '../hooks/useDocuments';
import { listChats } from '../api/chat';
import { Plus, MessageSquare, ArrowRight, BookOpen, Clock } from 'lucide-react';
import StatusDot from '../components/library/StatusDot';

export default function Dashboard() {
  const { user } = useAuth();
  const { documents, readyDocuments } = useDocuments();
  const [chats, setChats] = useState([]);
  const navigate = useNavigate();

  useEffect(() => {
    async function loadChats() {
      try {
        const res = await listChats();
        setChats(res.data.chats || []);
      } catch (err) {
        console.error('Failed to load chats:', err);
      }
    }
    loadChats();
  }, []);

  const totalPages = documents.reduce((acc, doc) => acc + (doc.pages || 0), 0);
  const lastChat = chats[0];

  return (
    <div className="flex-1 overflow-y-auto bg-[var(--paper)] p-6 md:p-10">
      <div className="max-w-4xl mx-auto flex flex-col gap-8">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[var(--line-subtle)]">
          <div>
            <h1 className="font-serif text-2xl md:text-3xl font-semibold text-[var(--ink)] tracking-tight">
              Welcome to your reading desk
            </h1>
            <p className="text-xs md:text-sm text-[var(--muted)] font-sans mt-1">
              Study your course materials with page-level citations.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => navigate('/library')}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-[6px] bg-[var(--accent)] text-white text-xs font-medium hover:bg-[var(--accent-hover)] transition-colors shadow-xs"
            >
              <Plus size={14} />
              <span>Add to your shelf</span>
            </button>

            <button
              onClick={() => navigate('/chat')}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-[6px] border border-[var(--line)] bg-[var(--surface)] hover:bg-[var(--surface-hover)] text-xs font-sans font-medium text-[var(--ink)] transition-colors shadow-xs"
            >
              <MessageSquare size={14} />
              <span>Ask notes</span>
            </button>
          </div>
        </div>

        {/* Continue where you left off card */}
        {lastChat ? (
          <div className="bg-[var(--surface)] border border-[var(--line)] rounded-[6px] p-6 shadow-sm flex flex-col gap-3">
            <div className="flex items-center justify-between">
              <span className="font-mono text-xs uppercase tracking-wider text-[var(--muted)] font-semibold">
                Continue where you left off
              </span>
              <span className="text-xs font-mono text-[var(--subtle)]">
                {new Date(lastChat.updated_at || lastChat.created_at).toLocaleDateString()}
              </span>
            </div>

            <h3 className="font-serif text-xl font-medium text-[var(--ink)]">
              {lastChat.title}
            </h3>

            <div className="pt-2">
              <button
                onClick={() => navigate(`/chat/${lastChat.id}`)}
                className="inline-flex items-center gap-1.5 text-xs font-medium text-[var(--accent)] hover:underline"
              >
                <span>Resume study session</span>
                <ArrowRight size={13} />
              </button>
            </div>
          </div>
        ) : null}

        {/* Overview Stats */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="bg-[var(--surface)] border border-[var(--line)] rounded-[6px] p-4 flex flex-col gap-1">
            <span className="text-xs text-[var(--muted)] font-sans">Documents Indexed</span>
            <span className="font-mono text-2xl font-bold text-[var(--ink)]">
              {documents.length}
            </span>
            <span className="text-[11px] text-[var(--subtle)] font-mono">
              {readyDocuments.length} ready for reading
            </span>
          </div>

          <div className="bg-[var(--surface)] border border-[var(--line)] rounded-[6px] p-4 flex flex-col gap-1">
            <span className="text-xs text-[var(--muted)] font-sans">Total Pages</span>
            <span className="font-mono text-2xl font-bold text-[var(--ink)]">
              {totalPages}
            </span>
            <span className="text-[11px] text-[var(--subtle)] font-mono">
              Across all course notes
            </span>
          </div>

          <div className="bg-[var(--surface)] border border-[var(--line)] rounded-[6px] p-4 flex flex-col gap-1">
            <span className="text-xs text-[var(--muted)] font-sans">Study Sessions</span>
            <span className="font-mono text-2xl font-bold text-[var(--ink)]">
              {chats.length}
            </span>
            <span className="text-[11px] text-[var(--subtle)] font-mono">
              Recorded in history
            </span>
          </div>
        </div>

        {/* Shelf Quick Peek */}
        <div className="flex flex-col gap-3">
          <div className="flex items-center justify-between">
            <span className="font-mono text-xs uppercase tracking-wider text-[var(--muted)] font-semibold">
              On Your Shelf
            </span>
            <Link
              to="/library"
              className="text-xs text-[var(--accent)] hover:underline font-medium inline-flex items-center gap-1"
            >
              <span>Manage Shelf</span>
              <ArrowRight size={12} />
            </Link>
          </div>

          <div className="bg-[var(--surface)] border border-[var(--line)] rounded-[6px] divide-y divide-[var(--line-subtle)]">
            {documents.length === 0 ? (
              <div className="p-8 text-center text-xs text-[var(--muted)]">
                Your shelf is currently empty.{' '}
                <Link to="/library" className="text-[var(--accent)] hover:underline ml-1">
                  Upload notes →
                </Link>
              </div>
            ) : (
              documents.slice(0, 5).map((doc) => (
                <div key={doc.id} className="p-3.5 flex items-center justify-between gap-4">
                  <div className="flex items-center gap-2.5 min-w-0">
                    <BookOpen size={16} className="text-[var(--accent)] flex-shrink-0" />
                    <span className="text-xs font-medium text-[var(--ink)] truncate" title={doc.filename}>
                      {doc.filename}
                    </span>
                  </div>

                  <div className="flex items-center gap-3 flex-shrink-0">
                    <span className="font-mono text-[11px] text-[var(--muted)]">
                      {doc.pages ? `${doc.pages} pages` : '—'}
                    </span>
                    <StatusDot status={doc.status} />
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
