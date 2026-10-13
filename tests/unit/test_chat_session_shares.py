from datetime import UTC, datetime, timedelta

import pytest

from astrbot.core.db.sqlite import SQLiteDatabase
from astrbot.core.platform_message_history_mgr import PlatformMessageHistoryManager
from astrbot.dashboard.services.chat_service import (
    ChatService,
    ChatServiceError,
    hash_share_token,
    normalize_transcript_text,
)


def _chat_service(db: SQLiteDatabase) -> ChatService:
    service = ChatService.__new__(ChatService)
    service.db = db
    service.platform_history_mgr = PlatformMessageHistoryManager(db)
    return service


async def _seed_session(db: SQLiteDatabase, *, creator: str = "owner") -> str:
    session = await db.create_platform_session(
        creator=creator,
        platform_id="webchat",
        display_name="Shared session",
    )
    return session.session_id


def test_normalize_transcript_text_strips_media_tokens() -> None:
    content = {
        "message": [
            {"type": "plain", "text": "hello"},
            {"type": "image", "text": "[Image]"},
            {"type": "plain", "text": "world"},
        ]
    }

    assert normalize_transcript_text(content) == "hello\n[Image]\nworld"
    assert normalize_transcript_text("plain string") == "plain string"
    assert normalize_transcript_text(None) == ""


@pytest.mark.asyncio
async def test_create_and_resolve_share(temp_db: SQLiteDatabase):
    service = _chat_service(temp_db)
    session_id = await _seed_session(temp_db)

    created = await service.create_share("owner", session_id, expires_in_days=7)
    assert created["token"]
    assert created["share_id"]
    assert created["expires_at"] is not None

    stored = await temp_db.get_conversation_share_by_token_hash(
        hash_share_token(created["token"])
    )
    assert stored is not None
    assert stored.session_id == session_id
    assert stored.token_hash != created["token"]

    transcript = await service.get_shared_transcript(created["token"])
    assert transcript["title"] == "Shared session"
    assert transcript["messages"] == []
    assert transcript["truncated"] is False


@pytest.mark.asyncio
async def test_transcript_is_text_only_and_ordered(temp_db: SQLiteDatabase):
    service = _chat_service(temp_db)
    session_id = await _seed_session(temp_db)
    manager = PlatformMessageHistoryManager(temp_db)
    await manager.insert(
        platform_id="webchat",
        user_id=session_id,
        content={
            "message": [
                {"type": "plain", "text": "hi"},
                {"type": "file", "text": "[File]"},
            ]
        },
        role="user",
    )
    await manager.insert(
        platform_id="webchat",
        user_id=session_id,
        content={"message": [{"type": "plain", "text": "hello"}]},
        role="assistant",
    )

    created = await service.create_share("owner", session_id, expires_in_days=1)
    transcript = await service.get_shared_transcript(created["token"])

    assert [message["role"] for message in transcript["messages"]] == [
        "user",
        "assistant",
    ]
    assert transcript["messages"][0]["text"] == "hi\n[File]"
    assert transcript["messages"][1]["text"] == "hello"


@pytest.mark.asyncio
async def test_non_owner_cannot_manage_or_read(temp_db: SQLiteDatabase):
    service = _chat_service(temp_db)
    session_id = await _seed_session(temp_db, creator="owner")

    with pytest.raises(ChatServiceError, match="Permission denied"):
        await service.create_share("intruder", session_id, expires_in_days=7)
    with pytest.raises(ChatServiceError, match="Permission denied"):
        await service.list_shares("intruder", session_id)

    created = await service.create_share("owner", session_id, expires_in_days=7)
    with pytest.raises(ChatServiceError, match="Permission denied"):
        await service.revoke_share("intruder", created["share_id"])


@pytest.mark.asyncio
async def test_invalid_expiry_is_rejected(temp_db: SQLiteDatabase):
    service = _chat_service(temp_db)
    session_id = await _seed_session(temp_db)

    with pytest.raises(ChatServiceError, match="Invalid share expiry"):
        await service.create_share("owner", session_id, expires_in_days=2)


@pytest.mark.asyncio
async def test_revoked_and_expired_tokens_are_unreadable(temp_db: SQLiteDatabase):
    service = _chat_service(temp_db)
    session_id = await _seed_session(temp_db)

    revoked = await service.create_share("owner", session_id, expires_in_days=7)
    await service.revoke_share("owner", revoked["share_id"])
    with pytest.raises(ChatServiceError, match="Share not found"):
        await service.get_shared_transcript(revoked["token"])

    expired = await temp_db.create_conversation_share(
        token_hash=hash_share_token("expired-token"),
        session_id=session_id,
        creator="owner",
        expires_at=datetime.now(UTC) - timedelta(days=1),
    )
    assert expired.share_id
    with pytest.raises(ChatServiceError, match="Share not found"):
        await service.get_shared_transcript("expired-token")


@pytest.mark.asyncio
async def test_unknown_token_is_unreadable(temp_db: SQLiteDatabase):
    service = _chat_service(temp_db)

    with pytest.raises(ChatServiceError, match="Share not found"):
        await service.get_shared_transcript("does-not-exist")


@pytest.mark.asyncio
async def test_list_shares_reports_active_state(temp_db: SQLiteDatabase):
    service = _chat_service(temp_db)
    session_id = await _seed_session(temp_db)

    created = await service.create_share("owner", session_id, expires_in_days=30)
    listed = await service.list_shares("owner", session_id)
    assert [share["share_id"] for share in listed["shares"]] == [created["share_id"]]
    assert listed["shares"][0]["active"] is True

    await service.revoke_share("owner", created["share_id"])
    listed_after = await service.list_shares("owner", session_id)
    assert listed_after["shares"][0]["active"] is False
