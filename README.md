# 📚 StudyMate RAG — Academic Question Answering System

> Upload your study PDFs. Ask questions. Get cited answers.

StudyMate RAG is a web application where students upload study materials (textbooks, lecture notes, research papers) and chat with them using Retrieval-Augmented Generation. Every answer is **grounded in the uploaded documents** with **page-level citations**.

## ✨ Features

- 📄 **PDF Upload & Management** — Drag-and-drop upload with processing status
- 💬 **Chat with Documents** — Ask questions in natural language
- 📖 **Cited Answers** — Every response includes clickable `[1] [2]` source citations
- 🔍 **Document Scoping** — Choose which PDFs to search for each chat
- 🔄 **Follow-up Questions** — Conversation context is maintained
- ⚡ **Streaming Responses** — Watch answers appear in real-time (SSE)
- 🔐 **User Isolation** — Each user's data is completely private
- 📊 **Chat History** — Search, rename, export, and manage past chats
- 👍👎 **Feedback** — Rate answers for evaluation

## 🏗 Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React + Vite + Tailwind CSS |
| Backend | FastAPI (Python) |
| LLM | OpenAI GPT-4o-mini / Ollama (local) |
| Embeddings | all-MiniLM-L6-v2 (384-dim, local) |
| Vector DB | ChromaDB |
| Database | SQLite (dev) / PostgreSQL (prod) |
| Auth | JWT + bcrypt |
| PDF Parsing | PyMuPDF |
| Orchestration | LangChain |

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- OpenAI API key (or Ollama for local LLM)

### Backend Setup

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate
# Linux/macOS
source venv/bin/activate

pip install -r requirements.txt
```

### Configuration

```bash
# From project root
cp .env.example .env
# Edit .env — add your OpenAI API key and set JWT_SECRET
```

### Run Backend

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

API docs will be available at: http://localhost:8000/docs

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Frontend will be at: http://localhost:5173

### Optional: Local LLM (Ollama)

```bash
ollama pull llama3.2:3b
# Set LLM_PROVIDER=ollama in .env
```

## 📁 Project Structure

```
studymate-rag/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app entry point
│   │   ├── core/                # Config, security, logging
│   │   ├── api/routes/          # REST API endpoints
│   │   ├── models/              # SQLAlchemy database models
│   │   ├── schemas/             # Pydantic request/response models
│   │   ├── db/                  # Database session & base
│   │   └── services/
│   │       ├── ingestion/       # PDF → chunks → vectors pipeline
│   │       ├── retrieval/       # Vector search + reranker
│   │       └── generation/      # LLM prompts + RAG chain
│   ├── tests/                   # pytest test suite
│   ├── scripts/                 # CLI tools (bulk ingest, ask)
│   └── evaluation/              # RAGAS evaluation
├── frontend/                    # React + Vite app
├── .env.example                 # Environment variables template
└── docker-compose.yml           # Container orchestration
```

## 📡 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/auth/register` | Create account |
| POST | `/api/auth/login` | Get JWT tokens |
| GET | `/api/auth/me` | Current user profile |
| POST | `/api/documents/upload` | Upload PDF |
| GET | `/api/documents` | List documents |
| GET | `/api/documents/{id}/status` | Processing status |
| DELETE | `/api/documents/{id}` | Delete document |
| POST | `/api/chats` | Create chat |
| POST | `/api/chats/{id}/ask` | Ask question (SSE) |
| GET | `/api/chats/{id}` | Get chat with messages |
| POST | `/api/messages/{id}/feedback` | Submit feedback |
| GET | `/api/health` | Health check |

## 🧪 Testing

```bash
cd backend
pytest tests/ -v
```

## 🐳 Docker

```bash
docker-compose up --build
```

## 📝 License

This project is for academic purposes.
