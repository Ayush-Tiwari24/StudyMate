let processingCallCount = 0;

let mockDocumentsStore = [
  {
    id: 1,
    filename: 'DBMS_Unit3_Normalization.pdf',
    pages: 45,
    chunk_count: 102,
    size_bytes: 4200000,
    status: 'ready',
    error_message: null,
    uploaded_at: new Date(Date.now() - 3600000 * 24).toISOString(),
  },
  {
    id: 2,
    filename: 'Machine_Learning_Lecture_Notes.pdf',
    pages: 28,
    chunk_count: 0,
    size_bytes: 2800000,
    status: 'processing', // advances to ready on status polling
    error_message: null,
    uploaded_at: new Date(Date.now() - 1800000).toISOString(),
  },
  {
    id: 3,
    filename: 'Scanned_Syllabus_Handout.pdf',
    pages: 4,
    chunk_count: 0,
    size_bytes: 1200000,
    status: 'failed',
    error_message: 'No readable text found',
    uploaded_at: new Date(Date.now() - 3600000 * 48).toISOString(),
  },
];

export async function mockListDocuments() {
  await new Promise((r) => setTimeout(r, 200));
  return {
    data: {
      documents: mockDocumentsStore,
      total: mockDocumentsStore.length,
    },
  };
}

export async function mockUploadDocument(file) {
  await new Promise((r) => setTimeout(r, 600));
  const newDoc = {
    id: Date.now(),
    filename: file.name,
    pages: 18,
    chunk_count: 0,
    size_bytes: file.size,
    status: 'processing',
    error_message: null,
    uploaded_at: new Date().toISOString(),
  };
  mockDocumentsStore = [newDoc, ...mockDocumentsStore];
  return {
    data: {
      document_id: newDoc.id,
      filename: newDoc.filename,
      status: newDoc.status,
    },
  };
}

export async function mockGetDocumentStatus(id) {
  await new Promise((r) => setTimeout(r, 150));
  const doc = mockDocumentsStore.find((d) => d.id === Number(id));
  if (!doc) {
    return { data: { document_id: id, status: 'failed', error_message: 'Document not found' } };
  }

  // If doc is processing, advance to ready after 2 calls
  if (doc.status === 'processing') {
    processingCallCount++;
    if (processingCallCount >= 2) {
      doc.status = 'ready';
      doc.chunk_count = 64;
    }
  }

  return {
    data: {
      document_id: doc.id,
      status: doc.status,
      pages: doc.pages,
      chunks: doc.chunk_count,
      error_message: doc.error_message,
      progress: doc.status === 'processing' ? 'Reading page 18 of 28…' : null,
    },
  };
}

export async function mockDeleteDocument(id) {
  await new Promise((r) => setTimeout(r, 200));
  mockDocumentsStore = mockDocumentsStore.filter((d) => d.id !== Number(id));
  return { data: { message: 'Deleted' } };
}

export async function mockRetryDocument(id) {
  await new Promise((r) => setTimeout(r, 200));
  const doc = mockDocumentsStore.find((d) => d.id === Number(id));
  if (doc) {
    doc.status = 'processing';
    doc.error_message = null;
  }
  return { data: { document_id: id, status: 'processing' } };
}
