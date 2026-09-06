from __future__ import annotations

import httpx

from aikit.model_client import ChatMessage
from aikit.model_client.ollama import OllamaClient


def _client_with_transport(handler) -> OllamaClient:
    client = OllamaClient(default_model="llama3.1")
    client._client = httpx.AsyncClient(
        base_url="http://ollama.local", transport=httpx.MockTransport(handler)
    )
    return client


async def test_complete_parses_ollama_response():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/chat"
        return httpx.Response(
            200,
            json={
                "message": {"role": "assistant", "content": "hi there"},
                "prompt_eval_count": 5,
                "eval_count": 3,
            },
        )

    client = _client_with_transport(handler)
    result = await client.complete([ChatMessage(role="user", content="hello")])
    assert result.content == "hi there"
    assert result.model == "llama3.1"
    assert result.tokens_in == 5
    assert result.tokens_out == 3
    assert result.latency_ms >= 0


async def test_health_false_on_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    client = _client_with_transport(handler)
    assert await client.health() is False


async def test_health_true_on_200():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"models": []})

    client = _client_with_transport(handler)
    assert await client.health() is True
