from __future__ import annotations

import httpx

from aikit.model_client import ChatMessage, Usage
from aikit.model_client.hosted import HostedClient


def _client_with_transport(handler) -> HostedClient:
    client = HostedClient("http://hosted.local", "sk-test", default_model="gpt-4o-mini")
    client._client = httpx.AsyncClient(
        base_url="http://hosted.local",
        headers={"Authorization": "Bearer sk-test"},
        transport=httpx.MockTransport(handler),
    )
    return client


async def test_complete_parses_openai_response():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer sk-test"
        assert request.url.path == "/chat/completions"
        return httpx.Response(
            200,
            json={
                "model": "gpt-4o-mini",
                "choices": [{"message": {"content": "hi there"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 3},
            },
        )

    client = _client_with_transport(handler)
    result = await client.complete([ChatMessage(role="user", content="hello")])
    assert result.content == "hi there"
    assert result.model == "gpt-4o-mini"
    assert result.tokens_in == 10
    assert result.tokens_out == 3


async def test_stream_yields_text_then_exactly_one_terminal_usage():
    """SSE shape per the OpenAI-compatible spec with stream_options.include_usage."""
    sse_lines = [
        'data: {"choices":[{"delta":{"content":"hi"},"finish_reason":null}]}',
        'data: {"choices":[{"delta":{"content":" there"},"finish_reason":"stop"}]}',
        'data: {"choices":[],"usage":{"prompt_tokens":10,"completion_tokens":2}}',
        "data: [DONE]",
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="\n\n".join(sse_lines) + "\n\n")

    client = _client_with_transport(handler)
    events = [event async for event in client.stream([ChatMessage(role="user", content="hi")])]

    assert events[:-1] == ["hi", " there"]
    assert events[-1] == Usage(tokens_in=10, tokens_out=2, finish_reason="stop")
    assert sum(isinstance(e, Usage) for e in events) == 1


async def test_health_true_on_200():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": []})

    client = _client_with_transport(handler)
    assert await client.health() is True


async def test_health_false_on_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    client = _client_with_transport(handler)
    assert await client.health() is False
