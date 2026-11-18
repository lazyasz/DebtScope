"""When Gemini is busy, the Copilot must still answer from the workspace data, never just fail."""
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock
import httpx
from backend.services.copilot_llm import GeminiCopilotAdapter


def test_busy_gemini_falls_back_to_data_answer():
    registry = MagicMock()
    registry.execute_tool.return_value = {"items": [], "total_items": 0}
    busy = httpx.Response(503, text='{"error":"high demand"}')
    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=busy)):
        adapter = GeminiCopilotAdapter(api_key="x" * 40)
        async def run():
            return [ev async for ev in adapter.stream_chat([{"role": "user", "content": "What are my hotspots?"}], registry)]
        events = asyncio.run(run())
    kinds = [e.event_type for e in events]
    assert "error" not in kinds
    text = "".join(e.data for e in events if e.event_type == "token")
    assert "straight from your scan data" in text and len(text) > 80
