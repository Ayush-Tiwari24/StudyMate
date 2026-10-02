import React, { useState, useRef } from 'react';
import { BookOpen, AlertCircle, Check, HardDrive } from 'lucide-react';

const MAX_FILE_SIZE_MB = 10;
const MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024;

export default function UploadDropzone({ onUploadSuccess, storage, className = '' }) {
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [statusMessage, setStatusMessage] = useState(null);
  const [errorMessage, setErrorMessage] = useState(null);
  const fileInputRef = useRef(null);

  const isStorageFull = storage?.isFull;

  const handleDragOver = (e) => {
    e.preventDefault();
    if (!isStorageFull) {
      setIsDragging(true);
    }
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    if (isStorageFull) {
      setErrorMessage("You've used all your storage. Delete a document to add more.");
      return;
    }
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      processFile(files[0]);
    }
  };

  const handleClick = () => {
    if (isStorageFull) {
      setErrorMessage("You've used all your storage. Delete a document to add more.");
      return;
    }
    fileInputRef.current?.click();
  };

  const processFile = async (file) => {
    setErrorMessage(null);
    setStatusMessage(null);

    if (isStorageFull) {
      setErrorMessage("You've used all your storage. Delete a document to add more.");
      return;
    }

    // Validate PDF
    if (file.type !== 'application/pdf' && !file.name.toLowerCase().endsWith('.pdf')) {
      setErrorMessage('Only PDF notes are supported.');
      return;
    }

    // Validate size (10MB)
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
      const detailMsg =
        err.response?.data?.detail ||
        err.normalized?.message ||
        "That upload didn't finish. Try again?";
      setErrorMessage(detailMsg);
      setUploading(false);
    }
  };

  return (
    <div
      className={`border-2 border-dashed rounded-[6px] p-8 text-center transition-all duration-150 select-none ${
        isStorageFull
          ? 'border-[var(--status-failed, #dc2626)] bg-[var(--surface)] opacity-85 cursor-not-allowed'
          : isDragging
          ? 'border-[var(--accent)] bg-[var(--accent-subtle)] cursor-pointer'
          : 'border-[var(--line)] bg-[var(--surface)] hover:border-[var(--muted)] hover:bg-[var(--surface-hover)] cursor-pointer'
      } ${className}`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      onClick={handleClick}
      role="button"
      tabIndex={isStorageFull ? -1 : 0}
      onKeyDown={(e) => {
        if (!isStorageFull && (e.key === 'Enter' || e.key === ' ')) {
          handleClick();
        }
      }}
      aria-label={
        isStorageFull
          ? "You've used all your storage. Delete a document to add more."
          : "Drop your notes here or click to browse"
      }
      aria-disabled={isStorageFull}
    >
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,application/pdf"
        disabled={isStorageFull}
        className="hidden"
        onChange={(e) => {
          if (e.target.files?.length > 0) {
            processFile(e.target.files[0]);
          }
        }}
      />

      <div className="flex flex-col items-center gap-3">
        <div
          className={`w-10 h-10 rounded-full flex items-center justify-center ${
            isStorageFull
              ? 'bg-[var(--accent-subtle)] text-[var(--status-failed)]'
              : 'bg-[var(--surface-muted)] text-[var(--accent)]'
          }`}
        >
          {isStorageFull ? <HardDrive size={20} strokeWidth={1.75} /> : <BookOpen size={20} strokeWidth={1.75} />}
        </div>

        <div className="flex flex-col gap-1">
          <span className="font-serif text-lg font-medium text-[var(--ink)]">
            {uploading
              ? statusMessage
              : isStorageFull
              ? 'Storage quota reached'
              : 'Drop your notes here'}
          </span>
          <span className="text-xs text-[var(--muted)] font-sans">
            {isStorageFull
              ? "You've used all your storage. Delete a document to add more."
              : 'or click to browse your computer (PDF up to 10MB)'}
          </span>
        </div>

        {errorMessage && (
          <div className="flex items-center gap-1.5 text-xs text-[var(--status-failed)] mt-1 font-sans">
            <AlertCircle size={14} className="flex-shrink-0" />
            <span>{errorMessage}</span>
          </div>
        )}

        {statusMessage && !errorMessage && !uploading && (
          <div className="flex items-center gap-1.5 text-xs text-[var(--status-ready)] mt-1 font-sans">
            <Check size={14} className="flex-shrink-0" />
            <span>{statusMessage}</span>
          </div>
        )}
      </div>
    </div>
  );
}
