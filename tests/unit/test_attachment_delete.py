from pathlib import Path
from types import SimpleNamespace

import pytest

from astrbot.dashboard.services.chat_service import ChatService


class _AttachmentDb:
    def __init__(self, attachment) -> None:
        self.attachment = attachment
        self.deleted: list[str] = []

    async def get_attachments(self, attachment_ids: list[str]) -> list[object]:
        if (
            self.attachment is None
            or self.attachment.attachment_id not in attachment_ids
        ):
            return []
        return [self.attachment]

    async def is_attachment_path_referenced(
        self, path: str, *, exclude_attachment_id: str = ""
    ) -> bool:
        _ = path, exclude_attachment_id
        return False

    async def delete_attachment(self, attachment_id: str) -> bool:
        self.deleted.append(attachment_id)
        return True


def _service(db: _AttachmentDb) -> ChatService:
    service = ChatService.__new__(ChatService)
    service.db = db
    service.attachments_dir = ""
    return service


@pytest.mark.asyncio
async def test_delete_attachment_removes_file_and_record(tmp_path: Path) -> None:
    file_path = tmp_path / "attachment.bin"
    file_path.write_bytes(b"payload")
    attachment = SimpleNamespace(
        attachment_id="att-1",
        path=str(file_path),
        mime_type="application/octet-stream",
    )
    db = _AttachmentDb(attachment)

    assert await _service(db).delete_attachment("att-1") is True
    assert not file_path.exists()
    assert db.deleted == ["att-1"]


@pytest.mark.asyncio
async def test_delete_attachment_returns_false_when_absent(tmp_path: Path) -> None:
    db = _AttachmentDb(None)

    assert await _service(db).delete_attachment("missing") is False
    assert db.deleted == []


@pytest.mark.asyncio
async def test_delete_attachment_removes_the_record_even_if_unlink_fails(
    tmp_path: Path,
) -> None:
    attachment = SimpleNamespace(
        attachment_id="att-1",
        path=str(tmp_path),
        mime_type="application/octet-stream",
    )
    db = _AttachmentDb(attachment)

    assert await _service(db).delete_attachment("att-1") is True
    assert db.deleted == ["att-1"]


@pytest.mark.asyncio
async def test_delete_attachment_keeps_shared_file_for_other_records(
    tmp_path: Path,
) -> None:
    shared = tmp_path / "shared.bin"
    shared.write_bytes(b"payload")
    attachment = SimpleNamespace(
        attachment_id="att-1",
        path=str(shared),
        mime_type="application/octet-stream",
    )
    db = _AttachmentDb(attachment)

    async def referenced(path: str, *, exclude_attachment_id: str = "") -> bool:
        _ = path, exclude_attachment_id
        return True

    db.is_attachment_path_referenced = referenced

    assert await _service(db).delete_attachment("att-1") is True
    assert shared.exists()
    assert db.deleted == ["att-1"]
