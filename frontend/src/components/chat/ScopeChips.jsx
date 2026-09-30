import React from 'react';
import Chip from '../ui/Chip';

export default function ScopeChips({
  selectedDocIds = [],
  documents = [],
  onRemoveDoc,
  onSelectAll,
  className = '',
}) {
  const selectedDocs = documents.filter((d) => selectedDocIds.includes(d.id));

  return (
    <div className={`flex items-center gap-1.5 flex-wrap ${className}`}>
      <span className="text-xs text-[var(--muted)] font-medium select-none">
        Searching:
      </span>

      {selectedDocs.length === 0 ? (
        <span className="text-xs text-[var(--status-failed)] font-medium">
          No documents on desk.{' '}
          {onSelectAll && (
            <button
              type="button"
              onClick={onSelectAll}
              className="underline hover:text-[var(--accent)] cursor-pointer"
            >
              Select all
            </button>
          )}
        </span>
      ) : (
        selectedDocs.map((doc) => (
          <Chip
            key={doc.id}
            label={doc.filename}
            onRemove={() => onRemoveDoc && onRemoveDoc(doc.id)}
          />
        ))
      )}
    </div>
  );
}
