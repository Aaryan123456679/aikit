from __future__ import annotations

from aikit.observability import PrometheusMetricsSink


def test_incr_and_observe_render_as_prometheus_text():
    sink = PrometheusMetricsSink()
    sink.incr("jobs_total", status="ok")
    sink.incr("jobs_total", status="ok")
    sink.observe("latency_ms", 12.5, backend="ollama")

    body = sink.render().decode()
    assert 'jobs_total{status="ok"} 2.0' in body
    assert "latency_ms_sum" in body
    assert 'backend="ollama"' in body
