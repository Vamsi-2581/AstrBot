from types import SimpleNamespace

import pytest

from astrbot.api.event import MessageChain
from astrbot.api.message_components import File, Json
from astrbot.core.webchat.emitter import emit_webchat_response
from astrbot.core.webchat.message_parts import (
    build_webchat_message_parts,
    create_attachment_part_from_existing_file,
)
from astrbot.core.webchat.queue_manager import WebChatQueueManager


@pytest.mark.asyncio
async def test_webchat_file_send_keeps_original_filename(tmp_path):
    """WebChat file payloads should carry both stored and display filenames."""
    attachments_dir = tmp_path / "attachments"
    attachments_dir.mkdir()
    source_file = tmp_path / "source.txt"
    source_file.write_text("hello", encoding="utf-8")
    queue_manager = WebChatQueueManager()
    queue = queue_manager.get_or_create_back_queue("message-1")
    await emit_webchat_response(
        queue_manager,
        "message-1",
        MessageChain([File(name="report.txt", file=str(source_file))]),
        attachments_dir=attachments_dir,
    )

    payload = await queue.get()
    stored_name, display_name = payload["data"].removeprefix("[FILE]").split("|", 1)

    assert payload["type"] == "file"
    assert display_name == "report.txt"
    assert stored_name != display_name
    assert (attachments_dir / stored_name).exists()


@pytest.mark.asyncio
async def test_webchat_llm_sources_emit_deduplicated_refs_payload(tmp_path):
    queue_manager = WebChatQueueManager()
    queue = queue_manager.get_or_create_back_queue("message-refs")
    await emit_webchat_response(
        queue_manager,
        "message-refs",
        MessageChain(
            type="llm_sources",
            chain=[
                Json(
                    data={
                        "citations": [
                            {"url": "https://example.com", "title": "Citation"}
                        ],
                        "sources": [
                            {
                                "url": "https://example.com",
                                "title": "Duplicate source",
                            },
                            {"url": "https://second.example", "snippet": "Source"},
                        ],
                    }
                )
            ],
        ),
        attachments_dir=tmp_path,
    )

    payload = await queue.get()
    assert payload == {
        "type": "refs",
        "data": {
            "used": [
                {
                    "url": "https://example.com",
                    "title": "Citation",
                    "snippet": None,
                    "start_index": None,
                    "end_index": None,
                    "source_type": None,
                },
                {
                    "url": "https://second.example",
                    "title": None,
                    "snippet": "Source",
                    "start_index": None,
                    "end_index": None,
                    "source_type": None,
                },
            ]
        },
        "streaming": False,
        "chain_type": "llm_sources",
        "message_id": "message-refs",
    }


@pytest.mark.asyncio
async def test_attachment_part_uses_display_filename_with_stored_filename(tmp_path):
    """Attachment parts should show the display name while keeping the stored name."""
    stored_file = tmp_path / "uuid.txt"
    stored_file.write_text("payload", encoding="utf-8")

    async def insert_attachment(path, type, mime_type):
        return SimpleNamespace(
            attachment_id="attachment-1",
            path=path,
            type=type,
            mime_type=mime_type,
        )

    part = await create_attachment_part_from_existing_file(
        stored_file.name,
        attach_type="file",
        insert_attachment=insert_attachment,
        attachments_dir=tmp_path,
        display_name="../nested/report.txt",
    )

    assert part == {
        "type": "file",
        "attachment_id": "attachment-1",
        "filename": "report.txt",
        "stored_filename": "uuid.txt",
    }


@pytest.mark.asyncio
async def test_build_webchat_message_parts_preserves_payload_filename(tmp_path):
    """Attachment lookup should not overwrite the payload filename with disk name."""
    stored_file = tmp_path / "uuid.txt"
    stored_file.write_text("payload", encoding="utf-8")
    attachment = SimpleNamespace(
        attachment_id="attachment-1",
        path=str(stored_file),
        type="file",
    )

    async def get_attachment_by_id(attachment_id):
        assert attachment_id == "attachment-1"
        return attachment

    parts = await build_webchat_message_parts(
        [
            {
                "type": "file",
                "attachment_id": "attachment-1",
                "filename": r"C:\fakepath\report.txt",
            }
        ],
        get_attachment_by_id=get_attachment_by_id,
        strict=True,
    )

    assert parts == [
        {
            "type": "file",
            "attachment_id": "attachment-1",
            "filename": "report.txt",
            "path": str(stored_file),
            "stored_filename": "uuid.txt",
        }
    ]


def test_webchat_create_event_does_not_promote_declared_username(tmp_path):
    from astrbot.core.platform.astrbot_message import AstrBotMessage, MessageMember
    from astrbot.core.platform.message_type import MessageType
    from astrbot.core.platform.sources.webchat.webchat_adapter import WebChatAdapter

    adapter = WebChatAdapter.__new__(WebChatAdapter)
    adapter.metadata = SimpleNamespace(id="webchat", name="webchat")
    adapter._webchat_queue_manager = WebChatQueueManager()
    adapter.attachments_dir = tmp_path
    message = AstrBotMessage()
    message.type = MessageType.FRIEND_MESSAGE
    message.session_id = "webchat!admin!cid"
    message.sender = MessageMember("admin", "admin")
    message.raw_message = ("admin", "cid", {"username": "admin", "role": "owner"})
    message.message_str = "hello"
    message.message = []
    event = adapter.create_event(message)
    assert event.platform_member_role == "member"
    assert event.platform_role_source == "none"
    assert event.get_extra("explicit_surface") is True
    assert event.message_str == "hello"


def test_webchat_create_event_propagates_nested_request_flags(tmp_path):
    from astrbot.core.platform.astrbot_message import AstrBotMessage, MessageMember
    from astrbot.core.platform.message_type import MessageType
    from astrbot.core.platform.sources.webchat.webchat_adapter import WebChatAdapter

    adapter = WebChatAdapter.__new__(WebChatAdapter)
    adapter.metadata = SimpleNamespace(id="webchat", name="webchat")
    adapter._webchat_queue_manager = WebChatQueueManager()
    adapter.attachments_dir = tmp_path
    flags = {
        "enable_inline_genui": False,
        "enable_default_system_prompt": False,
        "enable_streaming": False,
        "enable_reasoning": False,
    }
    message = AstrBotMessage()
    message.type = MessageType.FRIEND_MESSAGE
    message.session_id = "webchat!admin!cid"
    message.sender = MessageMember("admin", "admin")
    message.raw_message = ("admin", "cid", {"flags": flags})
    message.message_str = "hello"
    message.message = []

    event = adapter.create_event(message)

    assert event.get_extra("flags") == flags
    for key, value in flags.items():
        assert event.get_extra(key) is value


def test_webchat_create_event_defaults_flag_extras(tmp_path):
    from astrbot.core.platform.astrbot_message import AstrBotMessage, MessageMember
    from astrbot.core.platform.message_type import MessageType
    from astrbot.core.platform.sources.webchat.webchat_adapter import WebChatAdapter

    adapter = WebChatAdapter.__new__(WebChatAdapter)
    adapter.metadata = SimpleNamespace(id="webchat", name="webchat")
    adapter._webchat_queue_manager = WebChatQueueManager()
    adapter.attachments_dir = tmp_path
    message = AstrBotMessage()
    message.type = MessageType.FRIEND_MESSAGE
    message.session_id = "webchat!admin!cid"
    message.sender = MessageMember("admin", "admin")
    message.raw_message = ("admin", "cid", {"enable_streaming": False})
    message.message_str = "hello"
    message.message = []

    event = adapter.create_event(message)

    assert event.get_extra("enable_streaming") is False
    assert event.get_extra("enable_reasoning") is True
    assert event.get_extra("enable_default_system_prompt") is True


@pytest.mark.asyncio
async def test_webchat_reply_history_is_scoped_to_the_current_conversation():
    from astrbot.api.message_components import Reply
    from astrbot.core.platform.sources.webchat.webchat_adapter import WebChatAdapter

    histories = {
        2: SimpleNamespace(
            platform_id="webchat",
            user_id="other-conversation",
            sender_id="other",
            sender_name="other",
            content={"message": [{"type": "plain", "text": "other secret"}]},
        )
    }

    class FakeDatabase:
        async def get_platform_message_history_by_id(self, message_id):
            return histories.get(message_id)

    adapter = object.__new__(WebChatAdapter)
    adapter.database = FakeDatabase()
    reply_part = {"type": "reply", "message_id": 2, "selected_text": ""}

    cross_components, _ = await adapter._parse_message_parts(
        [reply_part],
        "current-conversation",
    )
    assert cross_components[0].message_str == ""
    assert cross_components[0].chain == []

    histories[2].user_id = "current-conversation"
    same_components, _ = await adapter._parse_message_parts(
        [reply_part],
        "current-conversation",
    )
    assert isinstance(same_components[0], Reply)
    assert same_components[0].message_str == "other secret"

    # Thread conversations keep their own history namespace while sharing the
    # WebChat conversation id check.
    histories[2].platform_id = "webchat_thread"
    thread_components, _ = await adapter._parse_message_parts(
        [reply_part],
        "current-conversation",
    )
    assert isinstance(thread_components[0], Reply)
    assert thread_components[0].message_str == "other secret"

    # A foreign platform reusing the same id must not resolve.
    histories[2].platform_id = "napcat"
    foreign_components, _ = await adapter._parse_message_parts(
        [reply_part],
        "current-conversation",
    )
    assert foreign_components[0].message_str == ""
    assert foreign_components[0].chain == []
