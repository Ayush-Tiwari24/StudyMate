let mockChatsStore = [
  {
    id: 101,
    title: 'Normalization & Functional Dependencies',
    document_ids: [1],
    created_at: new Date(Date.now() - 3600000 * 2).toISOString(),
    updated_at: new Date(Date.now() - 3600000 * 2).toISOString(),
    message_count: 2,
    messages: [
      {
        id: 1,
        role: 'user',
        content: 'What is normalization and why is it used?',
        created_at: new Date(Date.now() - 3600000 * 2).toISOString(),
      },
      {
        id: 2,
        role: 'assistant',
        content:
          'Normalization organizes database tables to reduce data redundancy and improve data integrity [1]. The primary goal is to isolate data so that additions, deletions, and modifications of an attribute can be made in just one table and then propagated throughout the rest of the database via defined relationships [2].',
        sources: [
          {
            id: 1,
            file: 'DBMS_Unit3_Normalization.pdf',
            document_id: 1,
            page: 14,
            score: 0.89,
            snippet:
              'Normalization is the formal process of systematically decomposing relation schemas to minimize redundancy and avoid insertion, deletion, and update anomalies.',
            bboxes: [{ x0: 0.1, y0: 0.2, x1: 0.9, y1: 0.35 }],
          },
          {
            id: 2,
            file: 'DBMS_Unit3_Normalization.pdf',
            document_id: 1,
            page: 15,
            score: 0.84,
            snippet:
              'First Normal Form (1NF) establishes the rule that the domain of each attribute must contain only atomic (indivisible) values, and the value of each attribute must be a single value from that domain.',
            bboxes: [{ x0: 0.1, y0: 0.4, x1: 0.85, y1: 0.55 }],
          },
        ],
        created_at: new Date(Date.now() - 3600000 * 2).toISOString(),
      },
    ],
  },
];

export async function mockListChats() {
  await new Promise((r) => setTimeout(r, 200));
  return { data: { chats: mockChatsStore, total: mockChatsStore.length } };
}

export async function mockGetChat(id) {
  await new Promise((r) => setTimeout(r, 150));
  const chat = mockChatsStore.find((c) => c.id === Number(id));
  if (!chat) {
    throw new Error('Chat session not found');
  }
  return { data: chat };
}

export async function mockCreateChat({ title, document_ids }) {
  await new Promise((r) => setTimeout(r, 250));
  const newChat = {
    id: Date.now(),
    title: title || 'New Study Session',
    document_ids: document_ids || [],
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    messages: [],
  };
  mockChatsStore = [newChat, ...mockChatsStore];
  return { data: newChat };
}

export async function mockDeleteChat(id) {
  await new Promise((r) => setTimeout(r, 150));
  mockChatsStore = mockChatsStore.filter((c) => c.id !== Number(id));
  return { data: { message: 'Deleted' } };
}

export async function mockUpdateChat(id, updates) {
  await new Promise((r) => setTimeout(r, 150));
  const chat = mockChatsStore.find((c) => c.id === Number(id));
  if (chat) {
    Object.assign(chat, updates);
  }
  return { data: chat };
}

/**
 * Mock SSE streaming fetch for /api/chats/{id}/ask
 */
export async function mockStreamAsk({ question, document_ids, onToken, onSources, onDone, onError }) {
  const isUnknown = (question || '').toLowerCase().includes('unknown');

  // Realistic timing
  await new Promise((r) => setTimeout(r, 450));

  if (isUnknown) {
    // Section 10: "A question containing 'unknown' triggers the calm not-found state."
    const notFoundText = "I couldn't find this in the provided documents. Nothing in your selected notes covers this topic.";
    for (const char of notFoundText) {
      onToken(char);
      await new Promise((r) => setTimeout(r, 18));
    }
    onSources([]);
    onDone({ message_id: Date.now(), latency_ms: 1200 });
    return;
  }

  // Answer tokens
  const sampleAnswer =
    'Based on your selected notes, this concept is explained in detail with reference to structural complexity and operational efficiency [1]. Specifically, dividing the workload into independent subproblems allows systematic execution with logarithmic asymptotic upper bounds [2].';

  const words = sampleAnswer.split(' ');
  for (const word of words) {
    onToken(word + ' ');
    await new Promise((r) => setTimeout(r, 35));
  }

  // Sources event
  const sampleSources = [
    {
      id: 1,
      file: 'DBMS_Unit3_Normalization.pdf',
      document_id: 1,
      page: 14,
      score: 0.88,
      snippet:
        'The structural complexity of relation schemas can be characterized by functional dependencies and multi-valued dependencies.',
      bboxes: [{ x0: 0.1, y0: 0.2, x1: 0.9, y1: 0.35 }],
    },
    {
      id: 2,
      file: 'DBMS_Unit3_Normalization.pdf',
      document_id: 1,
      page: 15,
      score: 0.82,
      snippet:
        'Decompositions are said to be lossless-join if the natural join of the decomposed relations yields exactly the original relation without spurious tuples.',
      bboxes: [{ x0: 0.1, y0: 0.4, x1: 0.85, y1: 0.55 }],
    },
  ];

  onSources(sampleSources);
  onDone({ message_id: Date.now(), latency_ms: 1450 });
}
