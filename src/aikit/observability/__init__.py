"""Observability — structured logging + metrics + health.

Impl requires the `observability` extra. Framework-agnostic helpers so any
FastAPI service wires them identically.
"""
from __future__ import annotations

import logging
import sys
from typing import Protocol

import structlog
from prometheus_client import CONTENT_TYPE_LATEST as PROMETHEUS_CONTENT_TYPE
from prometheus_client import CollectorRegistry, Counter, Histogram, generate_latest

__all__ = [
    "MetricsSink",
    "PrometheusMetricsSink",
    "PROMETHEUS_CONTENT_TYPE",
    "configure_logging",
    "get_logger",
]


class MetricsSink(Protocol):
    def incr(self, name: str, **labels: str) -> None: ...
    def observe(self, name: str, value: float, **labels: str) -> None: ...


def configure_logging(level: str = "INFO") -> None:
    """Call once at process start. Renders JSON lines to stdout."""
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=level)
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(level) if isinstance(level, str) else level
        ),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)  # type: ignore[no-any-return]


class PrometheusMetricsSink:
    """Counter/Histogram-backed MetricsSink. Series are created lazily on
    first use, keyed by name; the label set of the first call fixes that
    series' label names for its lifetime."""

    def __init__(self, registry: CollectorRegistry | None = None):
        self._registry = registry or CollectorRegistry(auto_describe=True)
        self._counters: dict[str, Counter] = {}
        self._histograms: dict[str, Histogram] = {}

    def incr(self, name: str, **labels: str) -> None:
        counter = self._counters.get(name)
        if counter is None:
            counter = Counter(name, name, labelnames=sorted(labels), registry=self._registry)
            self._counters[name] = counter
        (counter.labels(**labels) if labels else counter).inc()

    def observe(self, name: str, value: float, **labels: str) -> None:
        hist = self._histograms.get(name)
        if hist is None:
            hist = Histogram(name, name, labelnames=sorted(labels), registry=self._registry)
            self._histograms[name] = hist
        (hist.labels(**labels) if labels else hist).observe(value)

    def render(self) -> bytes:
        return generate_latest(self._registry)
