import React, { useEffect } from 'react';
import { X } from 'lucide-react';

export default function KeyboardShortcutsModal({ isOpen, onClose }) {
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const shortcuts = [
    { key: '/', description: 'Focus the question input bar' },
    { key: 'Enter', description: 'Submit current question to reading desk' },
    { key: 'Shift + Enter', description: 'Insert a new line in question input' },
    { key: '1 – 9', description: 'Jump directly to source citation 1 through 9' },
    { key: 'Esc', description: 'Close evidence source panel or this dialog' },
    { key: '?', description: 'Open this keyboard shortcuts cheatsheet' },
  ];

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-[1px] p-4"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label="Keyboard Shortcuts"
    >
      <div
        className="w-full max-w-md bg-[var(--surface)] border border-[var(--line)] rounded-[6px] shadow-lg p-5 flex flex-col gap-4"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-[var(--line-subtle)] pb-3">
          <div className="flex items-center gap-2">
            <span className="font-serif font-semibold text-base text-[var(--ink)]">
              Keyboard Shortcuts
            </span>
            <span className="font-mono text-[10px] text-[var(--muted)] px-1.5 py-0.5 rounded bg-[var(--surface-muted)] border border-[var(--line)]">
              Desk Cheatsheet
            </span>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded text-[var(--muted)] hover:text-[var(--ink)] hover:bg-[var(--surface-hover)]"
            title="Close dialog (Esc)"
          >
            <X size={15} />
          </button>
        </div>

        <div className="flex flex-col gap-2">
          {shortcuts.map((sc, i) => (
            <div
              key={i}
              className="flex items-center justify-between py-1.5 px-2 rounded-[4px] hover:bg-[var(--surface-hover)] text-xs transition-colors"
            >
              <span className="text-[var(--muted)] font-sans">{sc.description}</span>
              <kbd className="font-mono text-[11px] font-medium bg-[var(--surface-muted)] text-[var(--ink)] border border-[var(--line)] px-2 py-0.5 rounded-[4px] shadow-xs">
                {sc.key}
              </kbd>
            </div>
          ))}
        </div>

        <div className="pt-2 border-t border-[var(--line-subtle)] text-right">
          <button
            onClick={onClose}
            className="px-3 py-1.5 text-xs font-sans font-medium text-[var(--muted)] hover:text-[var(--ink)] hover:bg-[var(--surface-muted)] rounded-[4px] transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
