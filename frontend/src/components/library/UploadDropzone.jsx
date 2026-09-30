import React, { useState, useRef } from 'react';
import { BookOpen, AlertCircle, Check } from 'lucide-react';

const MAX_FILE_SIZE_MB = 50;
const MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024;

export default function UploadDropzone({ onUploadSuccess, className = '' }) {
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [statusMessage, setStatusMessage] = useState(null);
  const [errorMessage, setErrorMessage] = useState(null);
  const fileInputRef = useRef(null);

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      processFile(files[0]);
    }
  };

  const processFile = async (file) => {
    setErrorMessage(null);
    setStatusMessage(null);

    // Validate PDF
    if (file.type !== 'application/pdf' && !file.name.toLowerCase().endsWith('.pdf')) {
      setErrorMessage('Only PDF notes are supported.');
      return;
    }

    // Validate size (50MB)
    if (file.size > MAX_FILE_SIZE_BYTES) {
      setErrorMessage(`File exceeds the ${MAX_FILE_SIZE_MB}MB limit.`);
      return;
    }

    setUploading(true);
    setStatusMessage(`Adding ${file.name} to your shelf…`);

    try {
      await onUploadSuccess(file);
      setStatusMessage('Added to shelf. Ready for reading.');
      setTimeout(() => {
        setStatusMessage(null);
        setUploading(false);
      }, 3500);
    } catch (err) {
      console.error('Upload failed:', err);
      setErrorMessage("That upload didn't finish. Try again?");
      setUploading(false);
    }
  };

  return (
    <div
      className={`border-2 border-dashed rounded-[6px] p-8 text-center cursor-pointer transition-all duration-150 select-none ${
        isDragging
          ? 'border-[var(--accent)] bg-[var(--accent-subtle)]'
          : 'border-[var(--line)] bg-[var(--surface)] hover:border-[var(--muted)] hover:bg-[var(--surface-hover)]'
      } ${className}`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      onClick={() => fileInputRef.current?.click()}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          fileInputRef.current?.click();
        }
      }}
      aria-label="Drop your notes here or click to browse"
    >
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,application/pdf"
        className="hidden"
        onChange={(e) => {
          if (e.target.files?.length > 0) {
            processFile(e.target.files[0]);
          }
        }}
      />

      <div className="flex flex-col items-center gap-3">
        <div className="w-10 h-10 rounded-full bg-[var(--surface-muted)] flex items-center justify-center text-[var(--accent)]">
          <BookOpen size={20} strokeWidth={1.75} />
        </div>

        <div className="flex flex-col gap-1">
          <span className="font-serif text-lg font-medium text-[var(--ink)]">
            {uploading ? statusMessage : 'Drop your notes here'}
          </span>
          <span className="text-xs text-[var(--muted)] font-sans">
            or click to browse your computer (PDF up to 50MB)
          </span>
        </div>

        {errorMessage && (
          <div className="flex items-center gap-1.5 text-xs text-[var(--status-failed)] mt-1 font-sans">
            <AlertCircle size={14} />
            <span>{errorMessage}</span>
          </div>
        )}

        {statusMessage && !errorMessage && !uploading && (
          <div className="flex items-center gap-1.5 text-xs text-[var(--status-ready)] mt-1 font-sans">
            <Check size={14} />
            <span>{statusMessage}</span>
          </div>
        )}
      </div>
    </div>
  );
}
