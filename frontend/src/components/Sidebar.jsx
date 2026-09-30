import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Plus,
  MessageSquare,
  Trash2,
  Edit2,
  Check,
  X,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import DocumentSelector from './DocumentSelector';

export default function Sidebar({
  chats = [],
  activeChatId,
  onSelectChat,
  onNewChat,
  onDeleteChat,
  onRenameChat,
  documents = [],
  selectedDocIds = [],
  onSelectedDocsChange,
  isCollapsed = false,
  onToggleCollapse,
}) {
  const navigate = useNavigate();
  const [editingId, setEditingId] = useState(null);
  const [editTitle, setEditTitle] = useState('');

  const startRename = (chat, e) => {
    e.stopPropagation();
    setEditingId(chat.id);
    setEditTitle(chat.title);
  };

  const saveRename = async (chatId, e) => {
    e.stopPropagation();
    if (editTitle.trim()) {
      await onRenameChat(chatId, editTitle.trim());
    }
    setEditingId(null);
  };

  const cancelRename = (e) => {
    e.stopPropagation();
    setEditingId(null);
  };

  return (
    <aside className={`chat-sidebar ${isCollapsed ? 'collapsed' : ''}`}>
      <div className="sidebar-header">
        <button
          type="button"
          onClick={onNewChat}
          className="btn-primary-gradient w-full flex items-center justify-center gap-2 py-2.5"
        >
          <Plus className="w-4 h-4" />
          <span>New Chat</span>
        </button>
      </div>

      {/* Document Scope Selector */}
      <div className="sidebar-section">
        <DocumentSelector
          documents={documents}
          selectedDocIds={selectedDocIds}
          onChange={onSelectedDocsChange}
        />
      </div>

      {/* Chat History List */}
      <div className="sidebar-section sidebar-chat-list">
        <div className="text-xs font-semibold uppercase tracking-wider text-gray-400 px-3 py-2">
          Recent Chats ({chats.length})
        </div>

        <div className="chat-nav-scroll">
          {chats.length === 0 ? (
            <p className="text-xs text-gray-500 px-3 py-4 text-center">
              No conversations yet.
            </p>
          ) : (
            chats.map((chat) => {
              const isActive = activeChatId === chat.id;
              const isEditing = editingId === chat.id;

              return (
                <div
                  key={chat.id}
                  onClick={() => !isEditing && onSelectChat(chat.id)}
                  className={`chat-nav-item ${isActive ? 'active' : ''}`}
                >
                  <MessageSquare className="w-4 h-4 text-indigo-400 flex-shrink-0" />

                  {isEditing ? (
                    <div className="chat-rename-form" onClick={(e) => e.stopPropagation()}>
                      <input
                        type="text"
                        value={editTitle}
                        onChange={(e) => setEditTitle(e.target.value)}
                        className="rename-input"
                        autoFocus
                      />
                      <button
                        type="button"
                        onClick={(e) => saveRename(chat.id, e)}
                        className="btn-icon-tiny text-emerald-400"
                        title="Save"
                      >
                        <Check className="w-3.5 h-3.5" />
                      </button>
                      <button
                        type="button"
                        onClick={cancelRename}
                        className="btn-icon-tiny text-gray-400"
                        title="Cancel"
                      >
                        <X className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  ) : (
                    <>
                      <span className="chat-nav-title" title={chat.title}>
                        {chat.title}
                      </span>
                      <div className="chat-nav-actions">
                        <button
                          type="button"
                          onClick={(e) => startRename(chat, e)}
                          className="btn-icon-tiny"
                          title="Rename chat"
                        >
                          <Edit2 className="w-3 h-3" />
                        </button>
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            if (window.confirm('Delete this conversation?')) {
                              onDeleteChat(chat.id);
                            }
                          }}
                          className="btn-icon-tiny hover:text-rose-400"
                          title="Delete chat"
                        >
                          <Trash2 className="w-3 h-3" />
                        </button>
                      </div>
                    </>
                  )}
                </div>
              );
            })
          )}
        </div>
      </div>
    </aside>
  );
}
