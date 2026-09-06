# aikit

Shared platform layer for a suite of AI-backend systems (LLM eval platform,
inference gateway, agent-memory service). Publishes clean, SOLID interfaces
and reusable infrastructure so each downstream service depends on contracts,
not implementations.

> Rename `aikit` to a unique name before publishing to PyPI.

## Modules
| Module | Contract | Notes |
|---|---|---|
| `model_client` | `ModelClient` | async LLM backend: `complete` / `stream` / `health` |
| `embeddings` | `EmbeddingService` | local batched embeddings + cosine |
| `db` | async SQLAlchemy base | filled during Project 1 |
| `jobqueue` | `JobQueue` | Redis/arq or Postgres-backed |
| `observability` | `MetricsSink`, logging | structlog + prometheus |
| `config` | `BaseServiceSettings` | env-driven |

## Install
Core is light. Heavy deps are extras:
```bash
pip install "aikit[eval]"      # or [gateway], [memory]
pip install "aikit[embeddings,db,queue,observability,http]"  # à la carte
```
Consume from GitHub before the first PyPI release:
```bash
pip install "aikit @ git+https://github.com/Aaryan123456679/aikit@v0.1.0"
```

## Develop
```bash
make install && make all
```

## Release
Tag-driven. `git tag v0.1.0 && git push --tags` → CI builds and publishes to
PyPI via trusted publishing (OIDC, no secrets).
