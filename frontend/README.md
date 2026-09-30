# StudyMate AI — Frontend

> **"A reading desk, not a chatbot."**  
> StudyMate AI is a focused study environment where students upload course PDFs and ask questions. Every answer is grounded directly in the text and accompanied by interactive, verifiable page-level citations.

---

## 1. Design Direction & Philosophy

Traditional AI chatbots present information as conversational bubbles with playful animations, sparkles, and glowing orbs. StudyMate AI rejects generic chatbot tropes in favor of an **academic reading desk**:

1. **Evidence First**: Every answer sits alongside the exact PDF page and passage it was drawn from. Citations are superscripts (`¹`, `²`) with 200ms preview tooltips.
2. **Calm and Readable**:
   - **Paper palette**: Warm off-white canvas (`#FAF8F4`), clean surfaces (`#FFFFFF`), dark ink text (`#1E1E24`), terracotta accent (`#C8553D`), and highlighter yellow (`#FFE9A8`).
   - **Night reading**: Dedicated nocturnal mode (`#1B1A18` paper, `#EDE8DF` ink).
   - **Textbook typography**: Newsreader serif for answers, IBM Plex Sans for interface chrome, and JetBrains Mono for page numbers, footnotes, and code.
3. **Honest & Grounded**: When notes do not cover a topic, the system states clearly: *"Nothing in your selected notes covers this. Try selecting more documents."* No hallucinated guesses.

---

## 2. Desktop & Mobile Architecture

### The Three-Column Reading Desk (Desktop)

```
┌─────────────────┬──────────────────────────────────┬─────────────────┐
│   THE SHELF     │         THE ANSWER DESK          │ SOURCE EVIDENCE │
│   (Column 1)    │           (Column 2)             │   (Column 3)    │
├─────────────────┼──────────────────────────────────┼─────────────────┤
│ • Doc Checklist │ • Question Heading               │ • File name & p#│
│   [✓] Notes.pdf │ • Textbook Serif Markdown Answer │ • Tab switchers │
│   [✓] Book.pdf  │   "Divide & conquer has 3 steps¹"│   [1] p.14      │
│                 │ • Footnote List                  │   [2] p.88      │
│ • Status Dots   │   [1] Notes.pdf · p.14           │ • Native PDF    │
│   ● Ready       │ • Actions: Keep, Copy, Thumbs    │   Page View with│
│   ● Reading…    │ ──────────────────────────────── │   Highlighter   │
│                 │ • Active Scope Chips             │   Overlays      │
│ • Recent Chats  │ • ChatInput ("Ask your notes…")  │ • Open Full PDF │
└─────────────────┴──────────────────────────────────┴─────────────────┘
```

### Mobile Layout (< 900px)
Collapses seamlessly into 3 dedicated tabs:
- **Shelf**: Select documents and view previous study sessions.
- **Answer Desk**: Read grounded answers and submit questions.
- **Source**: Inspect the cited PDF page. Tapping any citation in an answer automatically switches to this tab.

---

## 3. Getting Started

### Prerequisites
- Node.js 18+ (tested with Node 20+)
- npm or yarn

### Installation
```bash
# Navigate to the frontend directory
cd frontend

# Install dependencies
npm install
```

### Development Server
```bash
npm run dev
```
Open [http://localhost:5173](http://localhost:5173) in your browser.

### Automated Test Suite
Run unit and integration tests powered by Vitest and React Testing Library:
```bash
npm test
```

### Production Build
```bash
npm run build
npm run preview
```

---

## 4. Environment Variables & Modes

Create a `.env` file in the `frontend/` directory (see `.env.example`):

```bash
# Live Backend API URL
VITE_API_URL=http://localhost:8000

# Mock Mode Toggle (true: completely self-contained offline mode)
VITE_USE_MOCK=false
```

### Mock Mode (`VITE_USE_MOCK=true`)
When running without a live FastAPI backend:
1. **Documents**: Returns 3 realistic pre-populated documents (*Algorithms & Data Structures*, *Operating Systems Notes*, and *Failed Scan*). Simulates 2-second processing transitions from `processing` to `ready`.
2. **Chat & Citations**: Streams simulated SSE tokens with chunked latency (30ms/word) and full bounding box citations for `sample.pdf`.
3. **Not-Found Handling**: Asking questions containing *"quantum"*, *"weather"*, or *"unknown"* triggers the calm *"Nothing in your selected notes covers this"* state.
4. **PDF Inspection**: Renders `public/sample.pdf` with yellow highlight overlays (`--mark`).

---

## 5. Keyboard Shortcuts

| Shortcut | Action |
| :--- | :--- |
| <kbd>/</kbd> | Focus the question input bar from anywhere |
| <kbd>Enter</kbd> | Submit question |
| <kbd>Shift</kbd> + <kbd>Enter</kbd> | Insert a new line |
| <kbd>1</kbd> – <kbd>9</kbd> | Open source panel and jump to citation 1 through 9 |
| <kbd>Esc</kbd> | Close evidence source panel or active dialog |
| <kbd>?</kbd> | Open keyboard shortcuts cheatsheet modal |

---

## 6. Directory Structure

```
frontend/
├── src/
│   ├── api/
│   │   ├── client.js          # Axios interceptors, JWT handling, error normalisation
│   │   ├── auth.js            # Authentication endpoints (login, register, me)
│   │   ├── documents.js       # PDF upload, document listing, delete, retry
│   │   ├── chat.js            # SSE streaming reader, chat sessions, notes
│   │   ├── settings.js        # User settings & retrieval depth preferences
│   │   └── mock/              # Self-contained mock data and SSE generator
│   │       ├── auth.js
│   │       ├── documents.js
│   │       └── chat.js
│   ├── components/
│   │   ├── ui/                # Button, Input, Chip, Toast, EmptyState, Skeleton
│   │   ├── layout/            # AppShell, Navbar, ProtectedRoute
│   │   ├── library/           # UploadDropzone, DocumentTable, StatusDot
│   │   ├── chat/              # Shelf, AnswerBlock, ChatInput, FootnoteMarker,
│   │   │                      # FootnoteList, ScopeChips, SuggestedQuestions,
│   │   │                      # AnswerActions, NotFoundNotice, KeyboardShortcutsModal
│   │   └── source/            # SourcePanel, PdfPageView, HighlightOverlay
│   ├── context/
│   │   ├── AuthContext.jsx    # User session, JWT persistence with "Remember me"
│   │   ├── ThemeContext.jsx   # Paper / Night reading toggle & font size scaling
│   │   ├── NotesContext.jsx   # Pinned answers & Markdown export
│   │   └── ToastContext.jsx   # Bottom-left minimal status toasts
│   ├── hooks/
│   │   ├── useDocuments.js    # Document state management with 2s polling
│   │   ├── useChatStream.js   # SSE streaming with token & source listeners
│   │   └── useHotkeys.js      # Global keyboard shortcuts
│   ├── pages/
│   │   ├── Login.jsx          # Academic login with "Remember me"
│   │   ├── Register.jsx       # Registration
│   │   ├── Library.jsx        # The Shelf management & PDF dropzone
│   │   ├── Chat.jsx           # Core 3-column Reading Desk
│   │   ├── Notes.jsx          # Saved notes with Markdown export
│   │   ├── History.jsx        # Chronological session history
│   │   ├── Settings.jsx       # Theme, text size, and retrieval preferences
│   │   └── Dashboard.jsx      # Overview of documents, recent sessions, and stats
│   ├── styles/
│   │   └── index.css          # Design tokens, CSS variables, Newsreader typography
│   ├── test/                  # Automated Vitest test suite
│   ├── App.jsx                # Router & context providers
│   └── main.jsx
├── index.html                 # Google Fonts preconnection
├── tailwind.config.js         # Token definitions
└── vite.config.js             # Proxy configuration & jsdom test environment
```

---

## 7. API Contract Alignment

The frontend adheres strictly to the backend API contract:
- `POST /api/auth/token` (OAuth2 password form request)
- `GET /api/documents` & `POST /api/documents/upload` (multipart/form-data)
- `POST /api/chat/stream` (`text/event-stream` SSE with `token`, `sources`, `done`, `error`)
- `GET /api/documents/{id}/file` (blob PDF stream for inline page rendering)
