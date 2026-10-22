"""Session waiters are dispatched by the core pipeline after access checks."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from astrbot.core.message.components import Plain
from astrbot.core.pipeline.process_stage.stage import ProcessStage
from astrbot.core.pipeline.waking_check.stage import WakingCheckStage
from astrbot.core.platform.astr_message_event import AstrMessageEvent
from astrbot.core.platform.astrbot_message import AstrBotMessage, MessageMember
from astrbot.core.platform.message_type import MessageType
from astrbot.core.platform.platform_metadata import PlatformMetadata
from astrbot.core.utils.session_waiter import (
    SessionWaiterRegistry,
)


def _event(text: str = "next", *, private: bool = True) -> AstrMessageEvent:
    """Create one inbound event for waiter dispatch tests."""
    message = AstrBotMessage()
    message.type = MessageType.FRIEND_MESSAGE if private else MessageType.GROUP_MESSAGE
    message.sender = MessageMember(user_id="user", nickname="User")
    message.message = [Plain(text)]
    return AstrMessageEvent(
        text,
        message,
        PlatformMetadata(id="test", name="test", description="Test"),
        "session",
    )


async def _register_waiter(registry: SessionWaiterRegistry, event):
    """Register a wait and return its handler and controller."""
    handler = AsyncMock()
    task = asyncio.create_task(registry.wait_for(event, handler, timeout_seconds=30))
    for _ in range(100):
        if registry.has_active_waiter(event):
            break
        await asyncio.sleep(0)
    controller = next(iter(registry._sessions.values())).session_controller
    return task, handler, controller


def _process_stage(registry: SessionWaiterRegistry) -> ProcessStage:
    """Build a ProcessStage with only the collaborator surface it uses."""
    stage = object.__new__(ProcessStage)
    stage.ctx = SimpleNamespace(
        execution_context=SimpleNamespace(session_waiter_registry=registry),
        astrbot_config={"provider_settings": {"enable": True}},
    )
    stage.conversation_loop = None

    async def no_handlers(event):
        if False:
            yield None

    stage.star_request_sub_stage = SimpleNamespace(process=no_handlers)
    stage.agent_sub_stage = SimpleNamespace(process=no_handlers)
    return stage


@pytest.mark.asyncio
async def test_process_stage_consumes_matching_waiter():
    """A matching wait consumes input and stops the event before plugins."""
    registry = SessionWaiterRegistry()
    event = _event()
    task, handler, _ = await _register_waiter(registry, event)
    stage = _process_stage(registry)
    try:
        async for _ in stage.process(event):
            pass
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        await registry.terminate()

    handler.assert_awaited_once()
    assert event.is_stopped()
    assert (
        stage.ctx.execution_context.session_waiter_registry.has_active_waiter(event)
        is False
    )


@pytest.mark.asyncio
async def test_process_stage_ignores_expired_waiter():
    """An already completed wait no longer consumes later input."""
    registry = SessionWaiterRegistry()
    event = _event("next")
    task, handler, controller = await _register_waiter(registry, event)
    controller.stop()
    await asyncio.gather(task, return_exceptions=True)
    await registry.terminate()

    stage = _process_stage(registry)
    event.set_extra("should_run_llm", True)
    async for _ in stage.process(event):
        pass

    handler.assert_not_awaited()


def test_waking_stage_admits_only_active_waiter():
    """Wake admission matches the same registry used by process dispatch."""
    registry = SessionWaiterRegistry()
    event = _event()
    stage = object.__new__(WakingCheckStage)
    stage.ctx = SimpleNamespace(
        execution_context=SimpleNamespace(session_waiter_registry=registry)
    )
    assert stage._admit_active_waiter(event) is False
    assert event.is_wake is False

    # A finished wait must not keep admitting follow-up input.
    async def exercise():
        task, _, controller = await _register_waiter(registry, event)
        assert stage._admit_active_waiter(event) is True
        assert event.is_wake is True
        controller.stop()
        await asyncio.gather(task, return_exceptions=True)
        event.is_wake = False
        assert stage._admit_active_waiter(event) is False
        await registry.terminate()

    asyncio.run(exercise())


@pytest.mark.asyncio
async def test_waking_stage_does_not_stop_admitted_waiter(monkeypatch):
    """Route.stop must not end an event whose active waiter still owns it."""
    from astrbot.core.pipeline.waking_check import stage as waking_module

    registry = SessionWaiterRegistry()
    event = _event("hello")
    stage = object.__new__(WakingCheckStage)
    stage.ctx = SimpleNamespace(
        execution_context=SimpleNamespace(
            session_waiter_registry=registry,
            turn_window_manager=None,
        ),
        astrbot_config={"platform_settings": {}},
        astrbot_config_id="test",
        plugin_catalog=SimpleNamespace(),
    )
    stage.command_prefixes = ()
    stage.command_catalog = SimpleNamespace(snapshot=())
    stage.session_plugins = SimpleNamespace(
        filter_handlers_by_session=AsyncMock(return_value=[])
    )
    stage._umo_auto_name_recorder = SimpleNamespace(schedule=lambda _event: None)
    stage._attach_authorization = AsyncMock()
    stage._is_bot_self_message = lambda _event: False
    stage._resolve_reply_senders = AsyncMock()
    stage._llm_access_for_event = lambda _event: {}
    stage._collect_activated_handlers = AsyncMock(return_value=([], {}, False))
    monkeypatch.setattr(
        waking_module,
        "route_turn",
        lambda _input: SimpleNamespace(
            message_str="hello",
            should_run_command=False,
            should_run_llm=False,
            route_kind="drop",
            wake_reasons=set(),
            resolution=None,
            stop=True,
        ),
    )

    task = asyncio.create_task(
        registry.wait_for(event, AsyncMock(), timeout_seconds=30)
    )
    for _ in range(100):
        if registry.has_active_waiter(event):
            break
        await asyncio.sleep(0)
    try:
        await stage.process(event)
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        await registry.terminate()

    assert event.is_wake is True
    assert event.is_stopped() is False
