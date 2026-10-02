FROM python:3.11-slim

WORKDIR /app

# Set environment variables for production optimization and predictable memory usage
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TORCH_NUM_THREADS=2 \
    HF_HOME=/app/.cache/huggingface \
    PORT=8000

# Install system dependencies for PyMuPDF, OCR, and Postgres clients
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    tesseract-ocr \
    ocrmypdf \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root application user
RUN useradd -m -u 1000 appuser

# Install CPU-only PyTorch first to avoid multi-gigabyte CUDA bloat on 2GB Render instance
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Install remaining Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create necessary directories and pre-download HuggingFace embedding model into image
RUN mkdir -p /app/.cache/huggingface data/raw_pdfs data/vector_store && \
    python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"

# Copy application code
COPY . .

# Set correct ownership for non-root user
RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

# Run migrations if enabled, then launch uvicorn with dynamic Render PORT and exec signal forwarding
CMD ["sh", "-c", "if [ \"$RUN_MIGRATIONS_ON_START\" = \"true\" ]; then alembic upgrade head; fi && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
