"""A tiny, dependency-free metrics registry with Prometheus text rendering.

The registry is intentionally minimal: counters, histograms, and scrape-time
gauge collectors. It is safe to mutate from the event loop thread; a lock keeps
concurrent access (for example, a metrics scrape racing an event dispatch)
consistent.
"""

from __future__ import annotations

import threading
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field

DEFAULT_HISTOGRAM_BUCKETS: tuple[float, ...] = (
    0.005,
    0.01,
    0.025,
    0.05,
    0.1,
    0.25,
    0.5,
    1.0,
    2.5,
    5.0,
    10.0,
    30.0,
    60.0,
)


def _escape_label_value(value: str) -> str:
    """Escape a label value for the Prometheus text exposition format."""

    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def _format_labels(labels: dict[str, str]) -> str:
    if not labels:
        return ""
    rendered = ",".join(
        f'{key}="{_escape_label_value(str(value))}"'
        for key, value in sorted(labels.items())
    )
    return "{" + rendered + "}"


def _format_value(value: float) -> str:
    if value == int(value):
        return str(int(value))
    return repr(float(value))


def _label_key(labels: dict[str, str]) -> tuple[tuple[str, str], ...]:
    return tuple(sorted((str(key), str(value)) for key, value in labels.items()))


@dataclass(frozen=True, slots=True)
class GaugeSample:
    """One gauge value produced by a scrape-time collector."""

    name: str
    help: str
    value: float
    labels: dict[str, str] = field(default_factory=dict)


class Counter:
    """A monotonically increasing counter with optional labels."""

    def __init__(self, name: str, help_text: str) -> None:
        self.name = name
        self.help = help_text
        self._values: dict[tuple[tuple[str, str], ...], float] = {}

    def inc(self, labels: dict[str, str] | None = None, amount: float = 1.0) -> None:
        key = _label_key(labels or {})
        self._values[key] = self._values.get(key, 0.0) + amount

    def _render(self) -> list[str]:
        lines = [f"# HELP {self.name} {self.help}", f"# TYPE {self.name} counter"]
        for key, value in sorted(self._values.items()):
            lines.append(
                f"{self.name}{_format_labels(dict(key))} {_format_value(value)}"
            )
        return lines


class Histogram:
    """A cumulative histogram over fixed buckets."""

    def __init__(
        self,
        name: str,
        help_text: str,
        buckets: tuple[float, ...] = DEFAULT_HISTOGRAM_BUCKETS,
    ) -> None:
        self.name = name
        self.help = help_text
        self.buckets = tuple(sorted(buckets))
        self._counts: dict[tuple[tuple[str, str], ...], list[int]] = {}
        self._sums: dict[tuple[tuple[str, str], ...], float] = {}
        self._totals: dict[tuple[tuple[str, str], ...], int] = {}

    def observe(self, labels: dict[str, str] | None, value: float) -> None:
        key = _label_key(labels or {})
        counts = self._counts.setdefault(key, [0] * (len(self.buckets) + 1))
        for index, bound in enumerate(self.buckets):
            if value <= bound:
                counts[index] += 1
                break
        counts[-1] += 1
        self._sums[key] = self._sums.get(key, 0.0) + value
        self._totals[key] = self._totals.get(key, 0) + 1

    def _render(self) -> list[str]:
        lines = [f"# HELP {self.name} {self.help}", f"# TYPE {self.name} histogram"]
        for key, counts in sorted(self._counts.items()):
            labels = dict(key)
            cumulative = 0
            for index, bound in enumerate(self.buckets):
                cumulative += counts[index]
                bucket_labels = {**labels, "le": _format_value(bound)}
                lines.append(
                    f"{self.name}_bucket{_format_labels(bucket_labels)} {cumulative}"
                )
            inf_labels = {**labels, "le": "+Inf"}
            lines.append(
                f"{self.name}_bucket{_format_labels(inf_labels)} {self._totals[key]}"
            )
            lines.append(
                f"{self.name}_sum{_format_labels(labels)} "
                f"{_format_value(self._sums[key])}"
            )
            lines.append(
                f"{self.name}_count{_format_labels(labels)} {self._totals[key]}"
            )
        return lines


class MetricsRegistry:
    """Owns counters, histograms, and scrape-time gauge collectors."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: dict[str, Counter] = {}
        self._histograms: dict[str, Histogram] = {}
        self._gauges: dict[
            str, tuple[str, dict[tuple[tuple[str, str], ...], float]]
        ] = {}
        self._collectors: list[Callable[[MetricsRegistry], Iterable[GaugeSample]]] = []

    def counter(self, name: str, help_text: str) -> Counter:
        with self._lock:
            counter = self._counters.get(name)
            if counter is None:
                counter = Counter(name, help_text)
                self._counters[name] = counter
            return counter

    def histogram(
        self,
        name: str,
        help_text: str,
        buckets: tuple[float, ...] = DEFAULT_HISTOGRAM_BUCKETS,
    ) -> Histogram:
        with self._lock:
            histogram = self._histograms.get(name)
            if histogram is None:
                histogram = Histogram(name, help_text, buckets)
                self._histograms[name] = histogram
            return histogram

    def gauge(
        self,
        name: str,
        help_text: str,
        value: float,
        labels: dict[str, str] | None = None,
    ) -> None:
        with self._lock:
            _help, values = self._gauges.setdefault(name, (help_text, {}))
            values[_label_key(labels or {})] = value

    def add_collector(
        self,
        collector: Callable[[MetricsRegistry], Iterable[GaugeSample]],
    ) -> None:
        with self._lock:
            self._collectors.append(collector)

    def render(self) -> str:
        with self._lock:
            lines: list[str] = []
            for counter in self._counters.values():
                lines.extend(counter._render())
            for histogram in self._histograms.values():
                lines.extend(histogram._render())
            collectors = list(self._collectors)

        for collector in collectors:
            try:
                # Collectors must run outside the lock; ``gauge`` re-locks.
                for sample in collector(self):
                    self.gauge(sample.name, sample.help, sample.value, sample.labels)
            except Exception:
                # A broken collector must never break a scrape.
                continue

        with self._lock:
            for name in sorted(self._gauges):
                help_text, values = self._gauges[name]
                lines.append(f"# HELP {name} {help_text}")
                lines.append(f"# TYPE {name} gauge")
                for key, value in sorted(values.items()):
                    lines.append(
                        f"{name}{_format_labels(dict(key))} {_format_value(value)}"
                    )
        return "\n".join(lines) + "\n"
