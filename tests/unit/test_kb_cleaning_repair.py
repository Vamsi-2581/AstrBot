from types import SimpleNamespace

import pytest

from astrbot.core.knowledge_base._kb_helper_cleaning import (
    RateLimiter,
    _extract_repaired_chunks,
    repair_and_translate_chunk_with_retry,
)


def test_malformed_repair_output_is_not_treated_as_discard():
    assert _extract_repaired_chunks("not a valid response") is None
    assert _extract_repaired_chunks("<repaired_text></repaired_text>") is None
    assert _extract_repaired_chunks("<discard_chunk />") == []
    assert _extract_repaired_chunks("<repaired_text>cleaned</repaired_text>") == [
        "cleaned"
    ]


class _RepairProvider:
    def __init__(self, responses: list[str | None]) -> None:
        self.responses = responses
        self.calls = 0

    async def text_chat(self, *, prompt, system_prompt):
        _ = prompt, system_prompt
        response = self.responses[min(self.calls, len(self.responses) - 1)]
        self.calls += 1
        return SimpleNamespace(completion_text=response)


@pytest.mark.asyncio
async def test_malformed_reply_retries_then_returns_the_original_chunk():
    provider = _RepairProvider(["malformed", "still malformed"])

    result = await repair_and_translate_chunk_with_retry(
        "original chunk",
        provider,
        RateLimiter(0),
        max_retries=1,
    )

    assert result == ["original chunk"]
    assert provider.calls == 2


@pytest.mark.asyncio
async def test_malformed_reply_then_valid_reply_uses_the_valid_repair():
    provider = _RepairProvider(["malformed", "<repaired_text>fixed</repaired_text>"])

    result = await repair_and_translate_chunk_with_retry(
        "original chunk",
        provider,
        RateLimiter(0),
        max_retries=1,
    )

    assert result == ["fixed"]
    assert provider.calls == 2
