import asyncio
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app, history, history_lock


@pytest.fixture(autouse=True)
def reset_chat_history():
    """Ensure conversation history is clean before and after each test."""
    history.clear()
    yield
    history.clear()


@pytest.mark.asyncio
async def test_empty_message_returns_400():
    """Empty or whitespace-only messages should return HTTP 400."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Empty string
        resp = await client.post("/api/chat", content="", headers={"Content-Type": "text/plain"})
        assert resp.status_code == 400
        assert "empty" in resp.json()["detail"].lower()

        # Whitespace-only string
        resp2 = await client.post("/api/chat", content="   \n\t  ", headers={"Content-Type": "text/plain"})
        assert resp2.status_code == 400
        assert "empty" in resp2.json()["detail"].lower()


@pytest.mark.asyncio
async def test_streaming_chat_success(monkeypatch):
    """Successful /api/chat streaming returns generated text chunk-by-chunk."""
    class MockDeltaEvent:
        type = "response.output_text.delta"
        def __init__(self, delta: str):
            self.delta = delta

    class MockDoneEvent:
        type = "response.completed"

    class MockAsyncStream:
        def __init__(self):
            self.events = [
                MockDeltaEvent("Namaste! "),
                MockDeltaEvent("Kedarkantha is "),
                MockDeltaEvent("a scenic winter trek."),
                MockDoneEvent(),
            ]
            self.closed = False

        def __aiter__(self):
            self.idx = 0
            return self

        async def __anext__(self):
            if self.idx < len(self.events):
                ev = self.events[self.idx]
                self.idx += 1
                await asyncio.sleep(0.005)
                return ev
            raise StopAsyncIteration

        async def close(self):
            self.closed = True

    mock_stream = MockAsyncStream()

    async def mock_responses_create(*args, **kwargs):
        assert kwargs.get("stream") is True
        return mock_stream

    from app import main
    monkeypatch.setattr(main.client.responses, "create", mock_responses_create)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        async with client.stream(
            "POST",
            "/api/chat",
            content="Tell me about Kedarkantha",
            headers={"Content-Type": "text/plain"},
        ) as response:
            assert response.status_code == 200
            assert "text/plain" in response.headers["content-type"]
            chunks = []
            async for chunk in response.aiter_text():
                chunks.append(chunk)

            full_text = "".join(chunks)
            assert full_text == "Namaste! Kedarkantha is a scenic winter trek."

    # Stream should be closed cleanly
    assert mock_stream.closed is True


@pytest.mark.asyncio
async def test_conversation_history_updates_after_success(monkeypatch):
    """Conversation history should record both user and assistant message on success."""
    class MockDeltaEvent:
        type = "response.output_text.delta"
        def __init__(self, delta: str):
            self.delta = delta

    class MockAsyncStream:
        def __init__(self):
            self.events = [MockDeltaEvent("Hampta Pass is best visited from June to September.")]

        def __aiter__(self):
            self.idx = 0
            return self

        async def __anext__(self):
            if self.idx < len(self.events):
                ev = self.events[self.idx]
                self.idx += 1
                return ev
            raise StopAsyncIteration

        async def close(self):
            pass

    async def mock_responses_create(*args, **kwargs):
        return MockAsyncStream()

    from app import main
    monkeypatch.setattr(main.client.responses, "create", mock_responses_create)

    user_query = "What is the best season for Hampta Pass?"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        async with client.stream(
            "POST",
            "/api/chat",
            content=user_query,
            headers={"Content-Type": "text/plain"},
        ) as response:
            assert response.status_code == 200
            async for _ in response.aiter_text():
                pass

    async with history_lock:
        assert len(history) == 2
        assert history[0] == {"role": "user", "content": user_query}
        assert history[1] == {
            "role": "assistant",
            "content": "Hampta Pass is best visited from June to September.",
        }


@pytest.mark.asyncio
async def test_failed_streaming_does_not_save_partial_response(monkeypatch):
    """Incomplete/failed streaming should not store partial responses or leave orphan user messages."""
    class MockFailingStream:
        def __init__(self):
            self.yielded_first = False

        def __aiter__(self):
            return self

        async def __anext__(self):
            if not self.yielded_first:
                self.yielded_first = True
                class MockDelta:
                    type = "response.output_text.delta"
                    delta = "Partial text before crash..."
                return MockDelta()
            # Simulate unexpected network drop / model error mid-stream
            raise RuntimeError("Connection terminated unexpectedly")

        async def close(self):
            pass

    async def mock_responses_create(*args, **kwargs):
        return MockFailingStream()

    from app import main
    monkeypatch.setattr(main.client.responses, "create", mock_responses_create)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        with pytest.raises(Exception):
            async with client.stream(
                "POST",
                "/api/chat",
                content="Tell me about Roopkund",
                headers={"Content-Type": "text/plain"},
            ) as response:
                async for _ in response.aiter_text():
                    pass

    # Ensure incomplete response did NOT corrupt or leave entries in history
    async with history_lock:
        assert len(history) == 0


@pytest.mark.asyncio
async def test_delete_api_clears_history():
    """DELETE /api should reset the conversation history buffer."""
    async with history_lock:
        history.append({"role": "user", "content": "Sample trek question"})
        history.append({"role": "assistant", "content": "Sample trek guidance"})

    async with history_lock:
        assert len(history) == 2

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.delete("/api")
        assert resp.status_code == 200

    async with history_lock:
        assert len(history) == 0


@pytest.mark.asyncio
async def test_cors_allows_deployed_frontend():
    """CORS should allow the deployed frontend origin https://trekbuddy-26.netlify.app."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Preflight OPTIONS request
        resp = await client.options(
            "/api/chat",
            headers={
                "Origin": "https://trekbuddy-26.netlify.app",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )
        assert resp.status_code == 200
        allow_origin = resp.headers.get("access-control-allow-origin")
        assert allow_origin in ["https://trekbuddy-26.netlify.app", "*"]
