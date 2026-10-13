import pytest

from astrbot.core.db.sqlite import SQLiteDatabase
from astrbot.core.platform_message_history_mgr import PlatformMessageHistoryManager
from astrbot.dashboard.services.chat_service import ChatService


def test_parse_branch_validates_metadata() -> None:
    assert ChatService._parse_branch(None) is None
    assert ChatService._parse_branch("nope") is None
    assert ChatService._parse_branch({"group_id": "g", "index": 2, "total": 2}) is None
    assert ChatService._parse_branch({"group_id": "g", "index": 0, "total": 9}) is None
    assert ChatService._parse_branch({"group_id": "", "index": 0, "total": 2}) is None

    parsed = ChatService._parse_branch(
        {"group_id": "g", "index": 1, "total": 2, "provider": "p", "model": "m"}
    )
    assert parsed == {
        "group_id": "g",
        "index": 1,
        "total": 2,
        "provider": "p",
        "model": "m",
    }


@pytest.mark.asyncio
async def test_save_bot_message_persists_branch(temp_db: SQLiteDatabase) -> None:
    service = ChatService.__new__(ChatService)
    service.platform_history_mgr = PlatformMessageHistoryManager(temp_db)
    branch = {
        "group_id": "g",
        "index": 1,
        "total": 2,
        "provider": "p",
        "model": "m",
    }

    record = await service.save_bot_message(
        "sess-1",
        [{"type": "plain", "text": "hi"}],
        {},
        {},
        branch=branch,
    )

    assert record.content["branch"] == branch
    assert record.content["type"] == "bot"


@pytest.mark.asyncio
async def test_save_bot_message_without_branch(temp_db: SQLiteDatabase) -> None:
    service = ChatService.__new__(ChatService)
    service.platform_history_mgr = PlatformMessageHistoryManager(temp_db)

    record = await service.save_bot_message(
        "sess-2",
        [{"type": "plain", "text": "hi"}],
        {},
        {},
    )

    assert "branch" not in record.content
