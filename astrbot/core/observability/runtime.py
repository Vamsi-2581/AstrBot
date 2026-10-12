"""Runtime observability facade: metrics recording and optional OTel tracing.

Everything is off by default. When disabled, every method returns before doing
work, so instrumentation in hot paths stays cheap and behavior is unchanged.
Tracing uses ``opentelemetry-api`` lazily; without an SDK or an
``opentelemetry-instrument`` bootstrap the API returns a no-op tracer.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from astrbot import logger
from astrbot.core.observability.metrics import GaugeSample, MetricsRegistry

if TYPE_CHECKING:
    from astrbot.core.agent.response import AgentStats


@dataclass
class Observability:
    """Configured observability state for one runtime."""

    enabled: bool = False
    metrics_enabled: bool = False
    tracing_enabled: bool = False
    service_name: str = "astrbot"
    registry: MetricsRegistry = field(default_factory=MetricsRegistry)
    _tracer: Any = None
    _tracer_resolved: bool = False

    def record_event(self, platform: str) -> None:
        """Count one inbound platform event."""

        if not self.metrics_enabled:
            return
        self.registry.counter(
            "astrbot_events_received_total",
            "Platform events received by the event bus.",
        ).inc({"platform": platform or "unknown"})

    def record_event_processed(self) -> None:
        """Count one completed pipeline execution."""

        if not self.metrics_enabled:
            return
        self.registry.counter(
            "astrbot_events_processed_total",
            "Pipeline executions completed.",
        ).inc()

    def record_agent_step(self) -> None:
        """Count one agent tool-loop step."""

        if not self.metrics_enabled:
            return
        self.registry.counter(
            "astrbot_agent_steps_total",
            "Agent tool-loop steps.",
        ).inc()

    def record_llm_call(self, provider_id: str | None = None) -> None:
        """Count one completed model call reported by ``agent_stats``."""

        if not self.metrics_enabled:
            return
        self.registry.counter(
            "astrbot_llm_calls_total",
            "Completed model calls.",
        ).inc({"provider": provider_id or "unknown"})

    def record_agent_run(
        self,
        stats: AgentStats,
        provider_id: str | None = None,
    ) -> None:
        """Record one finished agent run's cumulative usage.

        ``agent_stats`` carries cumulative token usage, TTFT, and duration for
        the whole run, so this is called once per run rather than per model
        call to avoid double counting.
        """

        provider = provider_id or "unknown"
        if self.metrics_enabled:
            labels = {"provider": provider}
            usage = stats.token_usage
            tokens = self.registry.counter(
                "astrbot_llm_tokens_total",
                "Tokens reported by completed agent runs.",
            )
            tokens.inc({**labels, "type": "input"}, usage.input)
            tokens.inc({**labels, "type": "output"}, usage.output)
            self.registry.histogram(
                "astrbot_llm_time_to_first_token_seconds",
                "Time to first token of an agent run.",
            ).observe(labels, stats.time_to_first_token)
            self.registry.histogram(
                "astrbot_llm_call_duration_seconds",
                "Duration of an agent run.",
            ).observe(labels, stats.duration)
        if self.tracing_enabled:
            self.emit_span(
                "agent.run",
                {
                    "provider": provider,
                    "tokens.total": str(usage.total),
                    "tokens.input": str(usage.input),
                    "tokens.output": str(usage.output),
                    "ttft.seconds": f"{stats.time_to_first_token:.6f}",
                    "duration.seconds": f"{stats.duration:.6f}",
                },
            )

    def register_backlog_source(self, source: Callable[[], int]) -> None:
        """Register a scrape-time collector for the event-bus backlog."""

        def collect(_registry: MetricsRegistry) -> list[GaugeSample]:
            return [
                GaugeSample(
                    name="astrbot_event_bus_backlog",
                    help="Events waiting in the event bus queue.",
                    value=float(source()),
                )
            ]

        self.registry.add_collector(collect)

    def register_webchat_queue_source(self, source: Callable[[], int]) -> None:
        """Register a scrape-time collector for the WebChat queue depth."""

        def collect(_registry: MetricsRegistry) -> list[GaugeSample]:
            return [
                GaugeSample(
                    name="astrbot_webchat_queue_depth",
                    help="Pending WebChat responses waiting in response queues.",
                    value=float(source()),
                )
            ]

        self.registry.add_collector(collect)

    @contextmanager
    def span(
        self,
        name: str,
        attributes: Mapping[str, str] | None = None,
    ) -> Iterator[Any]:
        """Open an OpenTelemetry span when tracing is enabled."""

        tracer = self._resolve_tracer()
        if tracer is None:
            yield None
            return
        with tracer.start_as_current_span(name, attributes=dict(attributes or {})) as (
            active_span
        ):
            yield active_span

    def emit_span(
        self,
        name: str,
        attributes: Mapping[str, str] | None = None,
    ) -> None:
        """Emit a zero-duration span for a point-in-time event."""

        if not self.tracing_enabled:
            return
        with self.span(name, attributes):
            pass

    def render_metrics(self) -> str:
        """Render all metrics as Prometheus text."""

        return self.registry.render()

    def _resolve_tracer(self) -> Any:
        if not self.tracing_enabled:
            return None
        if self._tracer_resolved:
            return self._tracer
        self._tracer_resolved = True
        try:
            from opentelemetry import trace as otel_trace
        except Exception:
            logger.warning(
                "OpenTelemetry tracing is enabled but opentelemetry-api is not "
                "installed; tracing is disabled."
            )
            self.tracing_enabled = False
            return None
        self._tracer = otel_trace.get_tracer(self.service_name)
        return self._tracer


_DISABLED = Observability()
_OBSERVABILITY: Observability = _DISABLED


def configure_observability(config: Mapping[str, Any] | None) -> Observability:
    """Build and install the runtime observability state from configuration."""

    global _OBSERVABILITY
    section: Mapping[str, Any] = {}
    if config is not None:
        raw = config.get("observability")
        if isinstance(raw, Mapping):
            section = raw
    enabled = bool(section.get("enable", False))
    _OBSERVABILITY = Observability(
        enabled=enabled,
        metrics_enabled=enabled and bool(section.get("metrics_enable", False)),
        tracing_enabled=enabled and bool(section.get("tracing_enable", False)),
        service_name=str(section.get("service_name") or "astrbot"),
    )
    return _OBSERVABILITY


def get_observability() -> Observability:
    """Return the process-wide observability state."""

    return _OBSERVABILITY


def reset_observability() -> None:
    """Restore the disabled default (used by tests)."""

    global _OBSERVABILITY
    _OBSERVABILITY = _DISABLED
