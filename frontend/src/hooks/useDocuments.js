import { useState, useEffect, useCallback, useRef } from 'react';
import {
  listDocuments,
  uploadDocument as apiUpload,
  deleteDocument as apiDelete,
  retryDocument as apiRetry,
  getDocumentStatus,
} from '../api/documents';

export function useDocuments() {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [storage, setStorage] = useState({
    usedBytes: 0,
    quotaBytes: 50 * 1024 * 1024,
    usedMb: 0,
    quotaMb: 50,
    percentUsed: 0,
    isWarning: false,
    isFull: false,
  });
  const pollTimerRef = useRef(null);

  const fetchDocs = useCallback(async () => {
    try {
      const res = await listDocuments();
      setDocuments(res.data.documents || []);

      if (res.data) {
        const usedMb = res.data.storage_used_mb ?? 0;
        const quotaMb = res.data.storage_quota_mb ?? 50;
        const percentUsed = res.data.storage_percent_used ?? 0;
        setStorage({
          usedBytes: res.data.storage_used_bytes || 0,
          quotaBytes: res.data.storage_quota_bytes || 50 * 1024 * 1024,
          usedMb,
          quotaMb,
          percentUsed,
          isWarning: percentUsed >= 80,
          isFull: percentUsed >= 100,
        });
      }

      setError(null);
      return res.data.documents || [];
    } catch (err) {
      console.error('Failed to list documents:', err);
      setError(err.response?.data?.detail || 'Failed to load documents');
      return [];
    } finally {
      setLoading(false);
    }
  }, []);

  const documentsRef = useRef(documents);
  useEffect(() => {
    documentsRef.current = documents;
  }, [documents]);

  // Initial fetch on mount
  useEffect(() => {
    fetchDocs();
  }, [fetchDocs]);

  // Polling logic for documents in progress
  useEffect(() => {
    const checkPendingStatus = async () => {
      const currentDocs = documentsRef.current || [];
      const pendingDocs = currentDocs.filter(
        (d) => d.status === 'uploaded' || d.status === 'processing'
      );

      if (pendingDocs.length === 0) return;

      let changed = false;
      const updatedList = [...currentDocs];

      for (const doc of pendingDocs) {
        try {
          const res = await getDocumentStatus(doc.id);
          const current = res.data;
          if (current.status !== doc.status || current.pages !== doc.pages) {
            changed = true;
            const idx = updatedList.findIndex((d) => d.id === doc.id);
            if (idx !== -1) {
              updatedList[idx] = {
                ...updatedList[idx],
                status: current.status,
                pages: current.pages,
                chunk_count: current.chunks,
                error_message: current.error_message,
              };
            }
          }
        } catch (e) {
          console.error(`Error polling status for doc ${doc.id}`, e);
        }
      }

      if (changed) {
        setDocuments(updatedList);
      }
    };

    pollTimerRef.current = setInterval(checkPendingStatus, 3000);

    return () => {
      if (pollTimerRef.current) clearInterval(pollTimerRef.current);
    };
  }, []);

  const upload = async (file, onProgress) => {
    const res = await apiUpload(file, onProgress);
    await fetchDocs();
    return res.data;
  };

  const remove = async (id) => {
    await apiDelete(id);
    setDocuments((prev) => prev.filter((d) => d.id !== id));
  };

  const retry = async (id) => {
    await apiRetry(id);
    await fetchDocs();
  };

  const readyDocuments = documents.filter((d) => d.status === 'ready');

  return {
    documents,
    readyDocuments,
    loading,
    error,
    storage,
    refresh: fetchDocs,
    upload,
    remove,
    retry,
  };
}
