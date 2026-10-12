"""Tests for the opt-in observability registry and runtime facade."""

from __future__ import annotations

import asyncio
from contextlib import suppress
from unittest.mock import AsyncMock, MagicMock

import pytest

from astrbot.core import observability as observability_module
from astrbot.core.agent.llm_types import TokenUsage
from astrbot.core.agent.response import AgentStats
from astrbot.core.event_bus import EventBus
from astrbot.core.observability import Observability
from astrbot.core.observability.metrics import GaugeSample, MetricsRegistry


def test_counter_renders_prometheus_text() -> None:
    registry = MetricsRegistry()
    counter = registry.counter("demo_total", "Demo counter.")
    counter.inc({"platform": "webchat"})
    counter.inc({"platform": "webchat"})

    text = registry.render()

    assert "# TYPE demo_total counter" in text
    assert 'demo_total{platform="webchat"} 2' in text


def test_histogram_renders_cumulative_buckets() -> None:
    registry = MetricsRegistry()
    registry.histogram("demo_seconds", "Demo.", buckets=(1.0, 2.0)).observe(
        {"k": "v"}, 1.5
    )

    text = registry.render()

    assert "# TYPE demo_seconds histogram" in text
    assert 'demo_seconds_bucket{k="v",le="1"} 0' in text
    assert 'demo_seconds_bucket{k="v",le="2"} 1' in text
    assert 'demo_seconds_bucket{k="v",le="+Inf"} 1' in text
    assert 'demo_seconds_count{k="v"} 1' in text


def test_label_values_are_escaped() -> None:
    registry = MetricsRegistry()
    registry.counter("demo_total", "Demo.").inc({"label": 'a"b\\c\nd'})

    text = registry.render()

    assert 'label="a\\"b\\\\c\\nd"' in text


def test_gauge_collector_samples_are_rendered() -> None:
    registry = MetricsRegistry()
    registry.add_collector(
        lambda _registry: [GaugeSample("demo_gauge", "Demo gauge.", 5.0, {})]
    )

    text = registry.render()

    assert "# TYPE demo_gauge gauge" in text
    assert "demo_gauge 5" in text


def test_broken_collector_does_not_break_scrape() -> None:
    registry = MetricsRegistry()

    def boom(_registry: MetricsRegistry) -> list[GaugeSample]:
        raise RuntimeError("boom")

    registry.add_collector(boom)
    registry.counter("demo_total", "Demo.").inc()

    assert "demo_total 1" in registry.render()


def test_disabled_observability_is_a_noop() -> None:
    observability = Observability()

    observability.record_event("webchat")
    observability.record_event_processed()
    observability.record_agent_step()
    observability.record_llm_call("openai")
    observability.record_agent_run(AgentStats(), "openai")
    with observability.span("demo") as span:
        assert span is None

    assert observability.render_metrics().strip() == ""


def test_enabled_observability_records_agent_metrics() -> None:
    observability = Observability(enabled=True, metrics_enabled=True)
    observability.record_event("webchat")
    observability.record_event_processed()
    observability.record_agent_step()
    observability.record_llm_call("openai")
    stats = AgentStats(
        token_usage=TokenUsage(input_other=10, input_cached=2, output=5),
        time_to_first_token=0.25,
        start_time=100.0,
        end_time=101.5,
    )

    observability.record_agent_run(stats, "openai")
    text = observability.render_metrics()

    assert 'astrbot_events_received_total{platform="webchat"} 1' in text
    assert "astrbot_events_processed_total 1" in text
    assert "astrbot_agent_steps_total 1" in text
    assert 'astrbot_llm_calls_total{provider="openai"} 1' in text
    assert 'astrbot_llm_tokens_total{provider="openai",type="input"} 12' in text
    assert 'astrbot_llm_tokens_total{provider="openai",type="output"} 5' in text
    assert "astrbot_llm_call_duration_seconds_count" in text


def test_tracing_span_does_not_raise() -> None:
    observability = Observability(enabled=True, tracing_enabled=True)

    with observability.span("demo", {"k": "v"}) as span:
        assert span is not None


def test_configure_and_reset_observability() -> None:
    configured = observability_module.configure_observability(
        {"observability": {"enable": True, "metrics_enable": True}}
    )
    try:
        assert configured.metrics_enabled is True
        assert configured.tracing_enabled is False
        assert observability_module.get_observability() is configured
    finally:
        observability_module.reset_observability()

    assert observability_module.get_observability().metrics_enabled is False


@pytest.mark.asyncio
async def test_event_bus_records_event_metrics() -> None:
    configured = observability_module.configure_observability(
        {"observability": {"enable": True, "metrics_enable": True}}
    )
    try:
        queue: asyncio.Queue = asyncio.Queue()
        scheduler = MagicMock()
        scheduler.execute = AsyncMock()
        config_manager = MagicMock()
        config_manager.get_conf_info = MagicMock(
            return_value={"id": "conf", "name": "conf"}
        )
        event_bus = EventBus(queue, {"conf": scheduler}, config_manager)

        processed = asyncio.Event()

        async def execute(_event) -> None:
            processed.set()

        scheduler.execute.side_effect = execute
        event = MagicMock()
        event.unified_msg_origin = "webchat:FriendMessage:session"
        event.get_platform_name.return_value = "webchat"
        event.get_extra.return_value = None
        await queue.put(event)

        task = asyncio.create_task(event_bus.dispatch())
        try:
            await asyncio.wait_for(processed.wait(), timeout=1.0)
            for _ in range(50):
                if "astrbot_events_processed_total 1" in configured.render_metrics():
                    break
                await asyncio.sleep(0.01)
        finally:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task

        text = configured.render_metrics()
        assert 'astrbot_events_received_total{platform="webchat"} 1' in text
        assert "astrbot_events_processed_total 1" in text
    finally:
        observability_module.reset_observability()
