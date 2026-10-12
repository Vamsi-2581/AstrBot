"""Real local tool lifecycle across wrappers and runner stop/cancellation."""

import asyncio
from types import SimpleNamespace

import anyio
import pytest

from astrbot.core.agent.run_context import ContextWrapper
from astrbot.core.agent.runners.tool_loop_agent_runner import (
    AgentStopRequested,
    ToolLoopAgentRunner,
)
from astrbot.core.agent.tool import FunctionTool
from astrbot.core.agent.tool_image_cache import ToolImageCache
from astrbot.core.astr_agent_tool_exec import FunctionToolExecutor, call_local_llm_tool


@pytest.mark.asyncio
@pytest.mark.parametrize("layer", ["handler_wrapper", "local", "execute", "runner"])
@pytest.mark.parametrize("exit_mode", ["close", "exhaust", "error"])
async def test_real_handler_cleanup_and_output(layer, exit_mode, tmp_path):
    tasks = set(asyncio.all_tasks())
    cleanup = []
    advanced = []
    owners = []
    error = ValueError("controlled tool error")

    async def implementation():
        token_task = asyncio.current_task()
        with anyio.CancelScope():
            try:
                owners.append(token_task)
                yield "first"
                advanced.append("next")
                owners.append(asyncio.current_task())
                if exit_mode == "error":
                    raise error
                yield "second"
            finally:
                await asyncio.sleep(0)
                owners.append(asyncio.current_task())
                cleanup.append("closed")

    handler_generator = implementation()

    def handler(event):
        return handler_generator

    run_context = ContextWrapper(context=SimpleNamespace(event=SimpleNamespace()))
    tool = FunctionTool(
        name="cleanup_probe",
        description="controlled tool lifecycle probe",
        parameters={"type": "object", "properties": {}},
        handler=handler,
    )
    runner = ToolLoopAgentRunner(ToolImageCache(tmp_path / "tool_images"))
    runner._abort_signal = asyncio.Event()
    executor = None
    if layer == "handler_wrapper":
        results = call_local_llm_tool(run_context, handler, "decorator_handler")
    elif layer == "local":
        results = FunctionToolExecutor._execute_local(tool, run_context)
    else:
        executor = FunctionToolExecutor._execute_local(tool, run_context)
        results = (
            runner._iter_tool_executor_results(executor)
            if layer == "runner"
            else executor
        )
    try:
        first = await anext(results)
        assert (
            first if layer == "handler_wrapper" else first.content[0].text
        ) == "first"
        await asyncio.sleep(0)
        assert not advanced and not cleanup
        if exit_mode == "exhaust":
            second = await anext(results)
            assert (
                second if layer == "handler_wrapper" else second.content[0].text
            ) == "second"
            with pytest.raises(StopAsyncIteration):
                await anext(results)
        elif exit_mode == "error":
            with pytest.raises(Exception, match="controlled tool error"):
                await anext(results)
        await results.aclose()
        assert cleanup == ["closed"]
        assert all(owner is owners[0] for owner in owners)
    finally:
        await results.aclose()
        if executor is not None:
            await executor.aclose()
        await handler_generator.aclose()
    assert not (set(asyncio.all_tasks()) - tasks)


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["stop_yielded", "stop_pending", "cancel", "timeout"])
async def test_real_handler_stop_cancel_timeout_wait_for_cleanup(mode, tmp_path):
    tasks = set(asyncio.all_tasks())
    started = asyncio.Event()
    closed = []

    async def handler(event):
        try:
            if mode == "stop_yielded":
                yield "first"
            started.set()
            await asyncio.Future()
            yield "unreachable"
        finally:
            await asyncio.sleep(0)
            closed.append("closed")

    run_context = ContextWrapper(context=SimpleNamespace(event=SimpleNamespace()))
    tool = FunctionTool(
        name="blocked_probe",
        description="controlled blocking tool",
        parameters={"type": "object", "properties": {}},
        handler=handler,
    )
    runner = ToolLoopAgentRunner(ToolImageCache(tmp_path / "tool_images"))
    runner._abort_signal = asyncio.Event()
    executor = (
        FunctionToolExecutor._execute_local(tool, run_context, tool_call_timeout=0.01)
        if mode == "timeout"
        else FunctionToolExecutor._execute_local(tool, run_context)
    )
    results = (
        executor if mode == "timeout" else runner._iter_tool_executor_results(executor)
    )
    pending = None
    try:
        if mode == "stop_yielded":
            assert (await anext(results)).content[0].text == "first"
            runner.request_stop()
            with pytest.raises(AgentStopRequested):
                await anext(results)
        else:
            pending = asyncio.create_task(anext(results))
            await asyncio.wait_for(started.wait(), 1)
            if mode == "cancel":
                pending.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await asyncio.wait_for(pending, 1)
            elif mode == "timeout":
                with pytest.raises(Exception, match="execution timeout"):
                    await asyncio.wait_for(pending, 1)
            else:
                runner.request_stop()
                with pytest.raises(AgentStopRequested):
                    await asyncio.wait_for(pending, 1)
        assert closed == ["closed"]
    finally:
        if pending is not None:
            pending.cancel()
            await asyncio.gather(pending, return_exceptions=True)
        await results.aclose()
        await executor.aclose()
    assert not (set(asyncio.all_tasks()) - tasks)


@pytest.mark.asyncio
async def test_runner_repeated_cancel_waits_for_real_cleanup(tmp_path):
    tasks = set(asyncio.all_tasks())
    started = asyncio.Event()
    cleanup_started = asyncio.Event()
    release = asyncio.Event()
    closed = []

    async def handler(event):
        try:
            started.set()
            await asyncio.Future()
            yield "unreachable"
        finally:
            cleanup_started.set()
            await release.wait()
            closed.append("closed")

    context = ContextWrapper(context=SimpleNamespace(event=SimpleNamespace()))
    tool = FunctionTool(
        name="repeat_cancel_probe",
        description="controlled repeated cancellation",
        parameters={"type": "object", "properties": {}},
        handler=handler,
    )
    runner = ToolLoopAgentRunner(ToolImageCache(tmp_path / "tool_images"))
    runner._abort_signal = asyncio.Event()
    results = runner._iter_tool_executor_results(
        FunctionToolExecutor._execute_local(tool, context)
    )
    pending = asyncio.create_task(anext(results))
    try:
        await asyncio.wait_for(started.wait(), 1)
        pending.cancel()
        await asyncio.wait_for(cleanup_started.wait(), 1)
        pending.cancel()
        await asyncio.sleep(0)
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await asyncio.wait_for(pending, 1)
        assert closed == ["closed"]
    finally:
        release.set()
        await asyncio.gather(pending, return_exceptions=True)
        await results.aclose()
    assert not (set(asyncio.all_tasks()) - tasks)


@pytest.mark.asyncio
async def test_runner_reports_real_handler_cleanup_error(tmp_path):
    error = OSError("controlled tool cleanup failure")

    async def handler(event):
        try:
            yield "first"
        finally:
            raise error

    context = ContextWrapper(context=SimpleNamespace(event=SimpleNamespace()))
    tool = FunctionTool(
        name="cleanup_error_probe",
        description="controlled cleanup failure",
        parameters={"type": "object", "properties": {}},
        handler=handler,
    )
    runner = ToolLoopAgentRunner(ToolImageCache(tmp_path / "tool_images"))
    runner._abort_signal = asyncio.Event()
    results = runner._iter_tool_executor_results(
        FunctionToolExecutor._execute_local(tool, context)
    )
    assert (await anext(results)).content[0].text == "first"
    with pytest.raises(Exception, match="controlled tool cleanup failure"):
        await results.aclose()


@pytest.mark.asyncio
async def test_background_real_generator_cancel_closes_before_return(monkeypatch):
    started = asyncio.Event()
    closed = []
    wakeups = []

    async def handler(event):
        try:
            yield "partial"
            started.set()
            await asyncio.Future()
        finally:
            await asyncio.sleep(0)
            closed.append("closed")

    async def wake(**kwargs):
        wakeups.append(kwargs)

    monkeypatch.setattr(
        FunctionToolExecutor, "_wake_main_agent_for_background_result", wake
    )
    context = ContextWrapper(context=SimpleNamespace(event=SimpleNamespace()))
    tool = FunctionTool(
        name="background_cleanup_probe",
        description="controlled background cleanup",
        parameters={"type": "object", "properties": {}},
        handler=handler,
    )
    pending = asyncio.create_task(
        FunctionToolExecutor._execute_background(tool, context, "task")
    )
    try:
        await asyncio.wait_for(started.wait(), 1)
        pending.cancel()
        with pytest.raises(asyncio.CancelledError):
            await asyncio.wait_for(pending, 1)
        assert closed == ["closed"]
        assert wakeups == []
    finally:
        pending.cancel()
        await asyncio.gather(pending, return_exceptions=True)
