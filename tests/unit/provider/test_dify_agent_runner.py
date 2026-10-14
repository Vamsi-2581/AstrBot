import pytest

from astrbot.core.agent.llm_types import ProviderRequest
from astrbot.core.agent.runners.dify.dify_agent_runner import DifyAgentRunner


class _Preferences:
    async def get_async(self, **kwargs):
        return kwargs.get("default")

    async def put_async(self, **kwargs):
        return None


class _Client:
    def __init__(self, chunks):
        self._chunks = chunks

    def workflow_run(self, **kwargs):
        async def iterate():
            for chunk in self._chunks:
                yield chunk

        return iterate()


def _workflow_runner(chunks):
    runner = DifyAgentRunner.__new__(DifyAgentRunner)
    runner.req = ProviderRequest(
        prompt="hi", session_id="session", system_prompt="system"
    )
    runner.streaming = False
    runner.preferences = _Preferences()
    runner.api_type = "workflow"
    runner.workflow_output_key = "out"
    runner.dify_query_input_key = "q"
    runner.variables = {}
    runner.timeout = 5
    runner.api_client = _Client(chunks)
    return runner


@pytest.mark.asyncio
async def test_dify_workflow_error_event_raises():
    runner = _workflow_runner(
        [
            {
                "event": "error",
                "status": 500,
                "code": "x",
                "message": "boom",
            }
        ]
    )

    with pytest.raises(Exception, match="Dify workflow execution failed"):
        async for _ in runner._execute_dify_request():
            pass


@pytest.mark.asyncio
async def test_dify_workflow_failed_status_raises():
    runner = _workflow_runner(
        [
            {
                "event": "workflow_finished",
                "workflow_run_id": "w",
                "data": {"status": "failed", "error": "bad", "outputs": {}},
            }
        ]
    )

    with pytest.raises(Exception, match="Dify workflow execution failed"):
        async for _ in runner._execute_dify_request():
            pass


@pytest.mark.asyncio
async def test_dify_workflow_incomplete_stream_raises():
    runner = _workflow_runner([{"event": "workflow_started", "workflow_run_id": "w"}])

    with pytest.raises(Exception, match="ended without a successful"):
        async for _ in runner._execute_dify_request():
            pass
