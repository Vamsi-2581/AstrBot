import asyncio
from types import SimpleNamespace

import pytest

from astrbot.core.utils import process_tree as pt


def test_bind_is_a_noop_without_a_windows_job(monkeypatch) -> None:
    monkeypatch.setattr(pt, "_KERNEL32", None)
    started: list[object] = []

    class FakeThread:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def start(self) -> None:
            started.append(self)

    monkeypatch.setattr(pt.threading, "Thread", FakeThread)
    pt.ProcessTree.create()._bind(1)
    pt.ProcessTree()._bind(1)
    assert started == []


def test_bind_blocking_is_a_noop_without_kernel32(monkeypatch) -> None:
    monkeypatch.setattr(pt, "_KERNEL32", None)
    pt.ProcessTree()._bind_blocking(1)


@pytest.mark.asyncio
async def test_assigner_waits_for_a_pid_across_a_slow_arm_to_spawn_gap(
    monkeypatch,
) -> None:
    monkeypatch.setattr(pt, "_ASSIGNER_CLOSE_TIMEOUT", 0.05)
    assigner = pt.ThreadAssigner(SimpleNamespace(_job=1))
    assigned: list[tuple[int, int]] = []
    monkeypatch.setattr(
        pt.ThreadAssigner,
        "_assign",
        lambda _self, job, pid: assigned.append((job, pid)),
    )
    assigner.start()
    try:
        assert await assigner.ready() is True
        await asyncio.sleep(0.15)

        assert await assigner.assign(4242) is True
        assert assigned == [(1, 4242)]
    finally:
        await assigner.close()


@pytest.mark.asyncio
async def test_assigner_resumes_the_child_when_no_listener_is_available(
    monkeypatch,
) -> None:
    resumed: list[int] = []
    monkeypatch.setattr(pt, "_resume", lambda pid: resumed.append(pid))
    assigner = pt.ThreadAssigner(SimpleNamespace(_job=1))
    assigner.start()
    assert await assigner.ready() is True
    await assigner.close()

    assert await assigner.assign(77) is False
    assert resumed == [77]
