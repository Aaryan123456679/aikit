from __future__ import annotations

import httpx

from aikit.model_client import ChatMessage, Usage
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


async def test_stream_yields_text_then_exactly_one_terminal_usage():
    """Response lines captured verbatim from a real Ollama server (see
    aikit v0.2.0's HLD/LLD B.0 - live-validated separately against a real
    llama3.1:8b before this mock was written)."""
    lines = [
        '{"model":"llama3.2:latest","message":{"role":"assistant","content":"Hi"},"done":false}',
        '{"model":"llama3.2:latest","message":{"role":"assistant","content":" there"},'
        '"done":false}',
        '{"model":"llama3.2:latest","message":{"role":"assistant","content":"!"},"done":false}',
        '{"model":"llama3.2:latest","message":{"role":"assistant","content":""},'
        '"done":true,"done_reason":"stop","prompt_eval_count":32,"eval_count":4}',
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="\n".join(lines))

    client = _client_with_transport(handler)
    events = [event async for event in client.stream([ChatMessage(role="user", content="hi")])]

    assert events[:-1] == ["Hi", " there", "!"]
    assert events[-1] == Usage(tokens_in=32, tokens_out=4, finish_reason="stop")
    assert sum(isinstance(e, Usage) for e in events) == 1


async def test_health_true_on_200():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"models": []})

    client = _client_with_transport(handler)
    assert await client.health() is True
