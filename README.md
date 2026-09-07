# aikit

*The shared library behind three AI-backend services — see the [AI Infrastructure Suite overview](https://github.com/Aaryan123456679/ai-infrastructure-suite).*

Shared platform layer for a suite of AI-backend systems (LLM eval platform,
inference gateway, agent-memory service). Publishes clean, SOLID interfaces
and reusable infrastructure so each downstream service depends on contracts,
not implementations.

## Modules
| Module | Contract | Concrete implementation |
|---|---|---|
| `model_client` | `ModelClient` | `OllamaClient`, `HostedClient` (OpenAI-compatible) — `complete` / `stream` (text + terminal `Usage`) / `health` / `aclose` |
| `embeddings` | `EmbeddingService` | `SentenceTransformerEmbeddingService` — local batched embeddings + cosine |
| `db` | async SQLAlchemy `Base` | `make_engine` / `make_sessionmaker` / `session_scope` |
| `jobqueue` | `JobQueue` | `ArqJobQueue` (Redis/arq) |
| `observability` | `MetricsSink`, logging | `PrometheusMetricsSink`, structlog JSON |
| `config` | `BaseServiceSettings` | env-driven |

## Status

**v0.1.0** validated end-to-end by `eval-platform`'s live Docker smoke test:
a real Postgres migration + advisory-lock-guarded prompt versioning +
CAS-guarded run finalization, a real Redis-backed arq worker actually
dispatching jobs, and a real Ollama model producing a scored, completed run
through the API. That process caught and fixed real bugs — not just code
review findings:

- `sentence-transformers` version drift breaking `EmbeddingService`'s
  structural match (`dim` typed wider than `int` in a newer release).
- `ArqJobQueue` never dispatched a single job — arq names a job function by
  `coroutine.__qualname__`, not `__name__`, so every registration collided
  under the same closure qualname regardless of task name.
- CI installed only `dev` extras, so it silently only ever type-checked and
  tested the core Protocol stubs, never the concrete implementations.

**v0.2.0** (breaking: `stream()` now yields `str | Usage`, terminal `Usage`
carries `tokens_in`/`tokens_out`/`finish_reason` — additive to `complete()`,
`eval-platform` stays pinned at v0.1.0 and is unaffected since it never
calls `stream()`). Adds `HostedClient` (OpenAI-compatible: OpenAI, Groq,
Together, Fireworks, OpenRouter, ...) for `inference-gateway`. Both closed
gaps `eval-platform`'s status page called out:

- `OllamaClient.stream()` is now **live-validated** against a real running
  Ollama server, including a production-sized model (`llama3.1:8b`, not
  just the small model used for eval-platform's fast smoke run) — text
  deltas followed by exactly one terminal `Usage`, asserted live and
  pinned down as a regression test replaying the real captured response.
- `HostedClient` is new and mock-tested against the OpenAI-compatible wire
  format (including the `stream_options.include_usage` SSE shape); it has
  **not** been live-validated against a real hosted provider (needs a real
  API key) — that's `inference-gateway`'s job before it goes live there.

**Still open**: `JudgeScorer` (in eval-platform) has no live-model test.

## Install
Published on PyPI as `aikit-platform` (the import name is still `aikit` -
only the distribution name differs, because the name `aikit` itself is
already taken by an unrelated package). Core is light; heavy deps are
extras:
```bash
pip install "aikit-platform[eval]"      # or [gateway], [memory]
pip install "aikit-platform[embeddings,db,queue,observability,http]"  # à la carte
```
```python
import aikit  # same import either way
```
Pin an exact tag from GitHub instead, if you want the git history alongside
the code (this is what eval-platform/gateway/agent-memory all do):
```bash
pip install "aikit-platform[gateway] @ git+https://github.com/Aaryan123456679/aikit@v0.2.0"
```

## Develop
```bash
make install && make all
```

## Release
Tag-driven: `git tag vX.Y.Z && git push origin vX.Y.Z` → CI builds and
publishes to PyPI via trusted publishing (OIDC, no secrets in the repo).
