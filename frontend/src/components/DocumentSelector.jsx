import React from 'react';
import { CheckSquare, Square, FileText, AlertCircle } from 'lucide-react';

export default function DocumentSelector({
  documents = [],
  selectedDocIds = [],
  onChange,
}) {
  const readyDocs = documents.filter((d) => d.status === 'ready');

  const handleToggle = (id) => {
    if (selectedDocIds.includes(id)) {
      onChange(selectedDocIds.filter((item) => item !== id));
    } else {
      onChange([...selectedDocIds, id]);
    }
  };

  const handleSelectAll = () => {
    onChange(readyDocs.map((d) => d.id));
  };

  const handleClearAll = () => {
    onChange([]);
  };

  return (
    <div className="doc-selector-container">
      <div className="doc-selector-header">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold uppercase tracking-wider text-gray-400">
            Search In ({selectedDocIds.length}/{readyDocs.length})
          </span>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={handleSelectAll}
              className="text-xs text-indigo-400 hover:text-indigo-300"
            >
              All
            </button>
            <span className="text-gray-600">|</span>
            <button
              type="button"
              onClick={handleClearAll}
              className="text-xs text-gray-400 hover:text-gray-300"
            >
              None
            </button>
          </div>
        </div>
      </div>

      {readyDocs.length === 0 ? (
        <div className="empty-selector-state">
          <AlertCircle className="w-4 h-4 text-amber-400 mr-2 flex-shrink-0" />
          <p className="text-xs text-gray-400">
            No ready PDFs available. Upload files in the Library first.
          </p>
        </div>
      ) : (
        <div className="doc-selector-list">
          {readyDocs.map((doc) => {
            const isChecked = selectedDocIds.includes(doc.id);
            return (
              <label
                key={doc.id}
                className={`doc-checkbox-item ${isChecked ? 'selected' : ''}`}
              >
                <input
                  type="checkbox"
                  checked={isChecked}
                  onChange={() => handleToggle(doc.id)}
                  style={{ display: 'none' }}
                />
                <span className="checkbox-box">
                  {isChecked ? (
                    <CheckSquare className="w-4 h-4 text-indigo-400" />
                  ) : (
                    <Square className="w-4 h-4 text-gray-500" />
                  )}
                </span>
                <span className="doc-item-title" title={doc.filename}>
                  {doc.filename}
                </span>
              </label>
            );
          })}
        </div>
      )}

      {readyDocs.length > 0 && selectedDocIds.length === 0 && (
        <div className="alert-banner alert-warning mt-2 text-xs py-1.5">
          <AlertCircle className="w-3.5 h-3.5 mr-1.5 flex-shrink-0" />
          <span>Select at least 1 document to ask questions.</span>
        </div>
      )}
    </div>
  );
}
