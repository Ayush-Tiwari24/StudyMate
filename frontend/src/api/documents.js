import client from './client';
import {
  mockListDocuments,
  mockUploadDocument,
  mockGetDocumentStatus,
  mockDeleteDocument,
  mockRetryDocument,
  mockGetDocumentFileUrl,
} from './mock/documents';

const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true';

export const uploadDocument = (file, onUploadProgress) => {
  if (USE_MOCK) return mockUploadDocument(file);
  const formData = new FormData();
  formData.append('file', file);
  return client.post('/documents/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    onUploadProgress,
  });
};

export const listDocuments = () => {
  if (USE_MOCK) return mockListDocuments();
  return client.get('/documents');
};

export const getDocumentStatus = (documentId) => {
  if (USE_MOCK) return mockGetDocumentStatus(documentId);
  return client.get(`/documents/${documentId}/status`);
};

export const deleteDocument = (documentId) => {
  if (USE_MOCK) return mockDeleteDocument(documentId);
  return client.delete(`/documents/${documentId}`);
};

export const retryDocument = (documentId) => {
  if (USE_MOCK) return mockRetryDocument(documentId);
  return client.post(`/documents/${documentId}/retry`);
};

export const getDocumentFileUrl = (documentId) => {
  if (USE_MOCK) return mockGetDocumentFileUrl(documentId);
  const base = import.meta.env.VITE_API_URL
    ? `${import.meta.env.VITE_API_URL.replace(/\/$/, '')}/api`
    : '/api';
  return `${base}/documents/${documentId}/file`;
};

export const fetchDocumentBlob = (documentId) => {
  return client.get(`/documents/${documentId}/file`, {
    responseType: 'blob',
  });
};

export const getStorageUsage = () => {
  return client.get('/documents/usage');
};

