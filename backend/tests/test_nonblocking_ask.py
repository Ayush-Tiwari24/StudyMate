"""
Test that CPU/IO-bound work running via asyncio.to_thread does not block
the FastAPI async event loop, allowing concurrent health requests to return in <200ms.
"""

import time
import asyncio
import httpx
from app.main import app


def test_concurrent_health_during_retrieval_remains_fast():
    """Fire 5 concurrent /api/health requests while a 1.5s synchronous blocking call

    runs in a worker thread. Assert health checks return swiftly (<200ms each).
    """
    async def _run():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            # First ensure health check is warm
            warmup = await client.get("/api/health/ready")
            assert warmup.status_code == 200

            # Start a simulated slow thread task (representing embed_query / retrieval)
            slow_task = asyncio.create_task(asyncio.to_thread(time.sleep, 1.0))

            # Small yield to let slow task start on worker thread
            await asyncio.sleep(0.05)

            # Fire 5 concurrent health requests during slow task execution
            async def fetch_health():
                t0 = time.perf_counter()
                r = await client.get("/api/health/ready")
                t1 = time.perf_counter()
                return r.status_code, (t1 - t0) * 1000

            health_results = await asyncio.gather(*[fetch_health() for _ in range(5)])
            await slow_task

            for status, elapsed_ms in health_results:
                assert status == 200
                assert elapsed_ms < 200.0, f"Health check blocked on event loop! Took {elapsed_ms}ms"

    asyncio.run(_run())
