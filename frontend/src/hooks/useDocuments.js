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
  const pollTimerRef = useRef(null);

  const fetchDocs = useCallback(async () => {
    try {
      const res = await listDocuments();
      setDocuments(res.data.documents || []);
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
    refresh: fetchDocs,
    upload,
    remove,
    retry,
  };
}
