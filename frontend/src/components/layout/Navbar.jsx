import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { useTheme } from '../../context/ThemeContext';
import {
  FolderOpen,
  MessageSquare,
  Bookmark,
  Clock,
  Settings as SettingsIcon,
  Sun,
  Moon,
  LogOut,
} from 'lucide-react';

export default function Navbar() {
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const location = useLocation();

  const navItems = [
    { label: 'The Shelf', path: '/library', icon: FolderOpen },
    { label: 'Reading Desk', path: '/chat', icon: MessageSquare },
    { label: 'Notes', path: '/notes', icon: Bookmark },
    { label: 'History', path: '/history', icon: Clock },
    { label: 'Settings', path: '/settings', icon: SettingsIcon },
  ];

  return (
    <header className="h-12 bg-[var(--surface)] border-b border-[var(--line)] px-4 flex items-center justify-between select-none z-30 flex-shrink-0">
      {/* Brand: "a reading desk, not a chatbot" */}
      <div className="flex items-center gap-6">
        <Link to="/chat" className="flex items-center gap-2.5 group">
          <div className="w-6 h-6 rounded-[6px] overflow-hidden flex-shrink-0 flex items-center justify-center shadow-xs group-hover:scale-105 transition-transform">
            <img src="/favicon.svg" alt="StudyMate icon" className="w-full h-full object-contain" />
          </div>
          <span className="font-serif font-semibold text-lg text-[var(--ink)] tracking-tight group-hover:text-[var(--accent)] transition-colors">
            StudyMate
          </span>
          <span className="font-mono text-[10px] uppercase tracking-wider text-[var(--muted)] px-1.5 py-0.5 rounded bg-[var(--paper)] border border-[var(--line)]">
            Desk
          </span>
        </Link>

        {/* Navigation Links */}
        <nav className="hidden sm:flex items-center gap-1" aria-label="Main Navigation">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname.startsWith(item.path);
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-[6px] text-xs font-sans font-medium transition-colors ${
                  isActive
                    ? 'bg-[var(--surface-muted)] text-[var(--ink)] border border-[var(--line)]'
                    : 'text-[var(--muted)] hover:text-[var(--ink)] hover:bg-[var(--surface-hover)]'
                }`}
              >
                <Icon size={14} strokeWidth={1.75} />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>
      </div>

      {/* Right Actions: Theme Toggle + User Info + Logout */}
      <div className="flex items-center gap-3">
        {/* Night Reading Toggle */}
        <button
          onClick={toggleTheme}
          type="button"
          className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-[6px] text-xs font-mono text-[var(--muted)] hover:text-[var(--ink)] hover:bg-[var(--surface-hover)] border border-[var(--line-subtle)] transition-colors"
          title={theme === 'light' ? 'Switch to Night Reading' : 'Switch to Paper Reading'}
          aria-label="Toggle reading theme"
        >
          {theme === 'light' ? (
            <Moon size={13} strokeWidth={1.75} />
          ) : (
            <Sun size={13} strokeWidth={1.75} />
          )}
          <span>{theme === 'light' ? 'Night' : 'Paper'}</span>
        </button>

        {user && (
          <span className="hidden md:inline-block text-xs font-mono text-[var(--muted)] max-w-[120px] truncate">
            {user.name?.split(' ')[0] || user.email?.split('@')[0]}
          </span>
        )}

        <button
          onClick={logout}
          type="button"
          className="p-1.5 rounded-[6px] text-[var(--muted)] hover:text-[var(--status-failed)] hover:bg-[var(--surface-hover)] transition-colors"
          title="Sign out"
          aria-label="Sign out"
        >
          <LogOut size={14} strokeWidth={1.75} />
        </button>
      </div>
    </header>
  );
}
