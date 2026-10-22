from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from astrbot.core.message.components import Plain, Reply
from astrbot.core.pipeline.content_safety_check.stage import ContentSafetyCheckStage
from astrbot.core.pipeline.scheduler import PipelineScheduler
from astrbot.core.pipeline.stage import Stage


class _BlockedEvent:
    def __init__(self) -> None:
        self.result = None
        self.stopped = False
        self.sent = []
        self.extras: dict[str, object] = {}

    def get_message_str(self):
        return "blocked message"

    def get_messages(self):
        return []

    def get_extra(self, key, default=None):
        return self.extras.get(key, default)

    def set_result(self, result) -> None:
        self.result = result

    def get_result(self):
        return self.result

    def clear_result(self) -> None:
        self.result = None

    def stop_event(self) -> None:
        self.stopped = True

    def is_stopped(self) -> bool:
        return self.stopped

    async def send(self, message) -> None:
        self.sent.append(message)


class _DownstreamProbe(Stage):
    called = False

    async def initialize(self, ctx) -> None:
        return None

    async def process(self, event):
        self.called = True


@pytest.mark.asyncio
async def test_blocked_message_stops_before_downstream_and_sends_once():
    event = _BlockedEvent()
    stage = ContentSafetyCheckStage()
    stage.strategy_selector = SimpleNamespace(
        check=AsyncMock(return_value=(False, "blocked"))
    )
    probe = _DownstreamProbe()
    scheduler = PipelineScheduler(SimpleNamespace())
    scheduler.stages = [stage, probe]

    await scheduler._process_stages(event)

    assert event.stopped is True
    assert event.result is None
    assert len(event.sent) == 1
    assert probe.called is False


@pytest.mark.asyncio
async def test_blocked_response_check_sends_once_and_clears_result():
    event = _BlockedEvent()
    event.result = SimpleNamespace(chain=[Plain("model output")])
    stage = ContentSafetyCheckStage()
    stage.strategy_selector = SimpleNamespace(
        check=AsyncMock(return_value=(False, "blocked"))
    )

    async for _ in stage.process(event, check_text="model output"):
        pass

    assert event.stopped is True
    assert event.result is None
    assert len(event.sent) == 1


@pytest.mark.asyncio
async def test_content_safety_checks_inbound_reply_text_once() -> None:
    event = SimpleNamespace(
        get_message_str=lambda: "current message",
        get_messages=lambda: [Reply(id="1", message_str="quoted message")],
        stop_event=Mock(),
    )
    stage = ContentSafetyCheckStage()
    stage.strategy_selector = SimpleNamespace(check=AsyncMock(return_value=(True, "")))

    async for _ in stage.process(event):
        pass

    stage.strategy_selector.check.assert_awaited_once_with(
        "current message\nquoted message"
    )


@pytest.mark.asyncio
async def test_content_safety_does_not_include_quotes_for_result_checks() -> None:
    event = SimpleNamespace(
        get_message_str=lambda: "current message",
        get_messages=lambda: [Reply(id="1", chain=[Plain("quoted message")])],
        stop_event=Mock(),
    )
    stage = ContentSafetyCheckStage()
    stage.strategy_selector = SimpleNamespace(check=AsyncMock(return_value=(True, "")))

    async for _ in stage.process(event, check_text="model response"):
        pass

    stage.strategy_selector.check.assert_awaited_once_with("model response")
