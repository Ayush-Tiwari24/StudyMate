"""
Test DB pool stability under concurrent streaming:
Verifies that 8 concurrent streaming questions do NOT exhaust the database pool
because sessions are released before streaming, and checkedout connections return to 0.
"""

import asyncio
from unittest.mock import patch
import httpx
from app.main import app
from app.db.session import SessionLocal, engine
from app.db.base import Base
from app.models.user import User
from app.models.document import Document
from app.core.security import create_access_token, hash_password


async def mock_astream(self, prompt):
    """Simulate a streaming LLM response with multiple delayed tokens."""
    for word in ["This", "is", "a", "fast", "answer."]:
        await asyncio.sleep(0.04)
        from langchain_core.messages import AIMessageChunk
        yield AIMessageChunk(content=word + " ")


def test_concurrent_streams_do_not_exhaust_db_pool():
    """Start 8 concurrent streams with a simulated slow LLM.

    Assert no request fails with a pool timeout, and engine.pool.checkedout() returns to 0.
    """
    # 0. Setup DB tables and test user & doc
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    user = db.query(User).filter(User.email == "pool_test@example.com").first()
    if not user:
        user = User(
            email="pool_test@example.com",
            password_hash=hash_password("password123"),
            name="Pool Test User",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    doc = db.query(Document).filter(Document.user_id == user.id, Document.filename == "pool_test.pdf").first()
    if not doc:
        doc = Document(
            user_id=user.id,
            filename="pool_test.pdf",
            file_path="dummy_path.pdf",
            file_hash="dummyhash123",
            size_bytes=1024,
            status="ready",
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

    user_id = user.id
    doc_id = doc.id
    db.close()

    auth_headers = {"Authorization": f"Bearer {create_access_token(data={'sub': str(user_id)})}"}

    async def _run():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Create a chat session
            chat_resp = await client.post(
                "/api/chats",
                headers=auth_headers,
                json={"title": "Pool Test Chat", "document_ids": [doc_id]},
            )
            assert chat_resp.status_code == 201, f"Failed to create chat: {chat_resp.text}"
            chat_id = chat_resp.json()["id"]

            # 2. Fire 8 concurrent ask requests with mocked streaming and retrieval
            with patch("langchain_openai.ChatOpenAI.astream", mock_astream), \
                 patch("app.services.generation.rag_chain.retrieve_chunks", return_value=[]):
                async def stream_one():
                    resp = await client.post(
                        f"/api/chats/{chat_id}/ask",
                        headers=auth_headers,
                        json={"question": "What is covered in this document?", "document_ids": [doc_id]},
                        timeout=30.0,
                    )
                    assert resp.status_code == 200, f"Ask failed: {resp.text}"
                    text = resp.text
                    assert "event: done" in text
                    return resp.status_code

                results = await asyncio.gather(*[stream_one() for _ in range(8)])
                assert len(results) == 8
                assert all(s == 200 for s in results)

            # 3. Assert pool connections are fully checked back in
            if hasattr(engine.pool, "checkedout"):
                assert engine.pool.checkedout() == 0, f"Leaked connections: {engine.pool.checkedout()}"

    asyncio.run(_run())
