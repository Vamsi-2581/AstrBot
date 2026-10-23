import asyncio
import os
import stat
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest

from astrbot.dashboard.services import chunked_upload_service as chunked_module
from astrbot.dashboard.services.chat_service import (
    MAX_UPLOAD_FILE_SIZE_BYTES,
    ChatService,
    ChatServiceError,
)
from astrbot.dashboard.services.chunked_upload_service import (
    ChunkedUploadError,
    ChunkedUploadService,
)
from astrbot.dashboard.upload_utils import UploadLimitError

CHUNK_SIZE = 1024 * 1024


class _StubChunk:
    def __init__(self, data: bytes):
        self._data = data

    async def save(self, destination, *, max_bytes=None):
        if max_bytes is not None and len(self._data) > max_bytes:
            raise UploadLimitError(max_bytes)
        Path(destination).write_bytes(self._data)
        return len(self._data)


@pytest.fixture
def service(tmp_path):
    db = SimpleNamespace(inserted=None)

    async def insert_attachment(path, type, mime_type):
        db.inserted = {"path": path, "type": type, "mime_type": mime_type}
        return SimpleNamespace(attachment_id="att-1", path=path)

    db.insert_attachment = insert_attachment
    svc = ChatService.__new__(ChatService)
    svc.db = db
    svc.attachments_dir = str(tmp_path / "attachments")
    Path(svc.attachments_dir).mkdir(parents=True, exist_ok=True)
    svc.chunked_uploads = ChunkedUploadService(tmp_path / "webchat" / ".chunks")
    yield svc
    task = svc.chunked_uploads._cleanup_task
    if task is not None and not task.done():
        task.cancel()


class TestChatChunkedUpload:
    def test_upload_init_validates_input(self, service):
        session = service.upload_init(
            {"filename": "report.pdf", "total_size": CHUNK_SIZE * 2 + 100},
            owner="alice",
        )
        assert session["chunk_size"] == CHUNK_SIZE
        assert session["total_chunks"] == 3
        assert session["upload_id"]

        with pytest.raises(ChatServiceError, match="Missing key: filename"):
            service.upload_init({"total_size": 100}, owner="alice")
        with pytest.raises(ChatServiceError, match="Invalid file size"):
            service.upload_init({"filename": "a.txt", "total_size": 0}, owner="alice")
        with pytest.raises(ChatServiceError, match="File too large"):
            service.upload_init(
                {"filename": "a.bin", "total_size": MAX_UPLOAD_FILE_SIZE_BYTES + 1},
                owner="alice",
            )

    @pytest.mark.asyncio
    async def test_full_flow_merges_and_creates_attachment(self, service):
        part0 = b"x" * CHUNK_SIZE
        part1 = b"y" * 100
        session = service.upload_init(
            {
                "filename": "notes.txt",
                "total_size": len(part0) + len(part1),
                "content_type": "text/plain",
            },
            owner="alice",
        )
        upload_id = session["upload_id"]

        await service.upload_chunk(
            upload_id=upload_id,
            chunk_index_str="1",
            chunk_file=_StubChunk(part1),
            owner="alice",
        )
        await service.upload_chunk(
            upload_id=upload_id,
            chunk_index_str="0",
            chunk_file=_StubChunk(part0),
            owner="alice",
        )

        result = await service.upload_complete({"upload_id": upload_id}, owner="alice")

        assert result["attachment_id"] == "att-1"
        assert result["type"] == "file"
        assert service.db.inserted["mime_type"] == "text/plain"
        merged = Path(service.db.inserted["path"])
        assert merged.read_bytes() == part0 + part1
        assert not service.chunked_uploads.sessions
        assert not list(service.chunked_uploads.chunks_root.iterdir())

    @pytest.mark.asyncio
    async def test_sessions_bound_to_owner(self, service):
        session = service.upload_init(
            {"filename": "a.txt", "total_size": 100}, owner="alice"
        )
        upload_id = session["upload_id"]

        with pytest.raises(ChatServiceError, match="not found or expired"):
            await service.upload_chunk(
                upload_id=upload_id,
                chunk_index_str="0",
                chunk_file=_StubChunk(b"x" * 100),
                owner="mallory",
            )
        with pytest.raises(ChatServiceError, match="not found or expired"):
            service.upload_status({"upload_id": upload_id}, owner="mallory")
        with pytest.raises(ChatServiceError, match="not found or expired"):
            await service.upload_complete({"upload_id": upload_id}, owner="mallory")
        with pytest.raises(ChatServiceError, match="not found or expired"):
            await service.upload_abort({"upload_id": upload_id}, owner="mallory")

        result = await service.upload_chunk(
            upload_id=upload_id,
            chunk_index_str="0",
            chunk_file=_StubChunk(b"x" * 100),
            owner="alice",
        )
        assert result["received"] == 1

    @pytest.mark.asyncio
    async def test_status_reports_progress_without_extending_lifetime(self, service):
        session = service.upload_init(
            {"filename": "a.txt", "total_size": CHUNK_SIZE * 2}, owner="alice"
        )
        upload_id = session["upload_id"]
        await service.upload_chunk(
            upload_id=upload_id,
            chunk_index_str="1",
            chunk_file=_StubChunk(b"x" * CHUNK_SIZE),
            owner="alice",
        )

        inner = service.chunked_uploads.get_session(upload_id, owner="alice")
        inner.last_activity -= 100
        status = service.upload_status({"upload_id": upload_id}, owner="alice")

        assert status["received_chunks"] == [1]
        assert status["total_chunks"] == 2
        assert status["expires_in"] <= 3600 - 100 + 1
        assert (
            service.chunked_uploads.get_session(upload_id, owner="alice").last_activity
            == inner.last_activity
        )

    @pytest.mark.asyncio
    async def test_complete_rejects_missing_chunks(self, service):
        session = service.upload_init(
            {"filename": "a.txt", "total_size": CHUNK_SIZE + 1}, owner="alice"
        )
        upload_id = session["upload_id"]
        await service.upload_chunk(
            upload_id=upload_id,
            chunk_index_str="0",
            chunk_file=_StubChunk(b"x" * CHUNK_SIZE),
            owner="alice",
        )

        with pytest.raises(ChatServiceError, match="Chunks incomplete"):
            await service.upload_complete({"upload_id": upload_id}, owner="alice")

    @pytest.mark.asyncio
    async def test_abort_cleans_up_session(self, service):
        session = service.upload_init(
            {"filename": "a.txt", "total_size": 100}, owner="alice"
        )
        upload_id = session["upload_id"]
        await service.upload_chunk(
            upload_id=upload_id,
            chunk_index_str="0",
            chunk_file=_StubChunk(b"x" * 100),
            owner="alice",
        )

        await service.upload_abort({"upload_id": upload_id}, owner="alice")

        with pytest.raises(ChatServiceError, match="not found or expired"):
            service.upload_status({"upload_id": upload_id}, owner="alice")
        assert not list(service.chunked_uploads.chunks_root.iterdir())
        await service.upload_abort({"upload_id": upload_id}, owner="alice")


@pytest.mark.asyncio
async def test_assemble_offloads_merge_and_preserves_destination_on_failure(
    service, tmp_path, monkeypatch
):
    uploads = service.chunked_uploads
    session = uploads.init_session(
        owner="alice",
        purpose="backup",
        filename="backup.zip",
        original_filename="backup.zip",
        total_size=10,
    )
    (session.chunk_dir / "0.part").write_bytes(b"short")
    session.received_chunks.add(0)
    destination = tmp_path / "backup.zip"
    destination.write_bytes(b"previous")

    calls = []
    original_to_thread = asyncio.to_thread

    async def tracking_to_thread(function, *args, **kwargs):
        calls.append(function)
        return await original_to_thread(function, *args, **kwargs)

    monkeypatch.setattr(chunked_module.asyncio, "to_thread", tracking_to_thread)

    with pytest.raises(ChunkedUploadError, match="Merged size"):
        await uploads.assemble(session.id, destination)

    assert calls
    assert destination.read_bytes() == b"previous"
    assert not list(tmp_path.glob(".backup.zip.*"))


def _complete_upload(uploads, data: bytes = b"0123456789"):
    session = uploads.init_session(
        owner="alice",
        purpose="backup",
        filename="backup.zip",
        original_filename="backup.zip",
        total_size=len(data),
    )
    (session.chunk_dir / "0.part").write_bytes(data)
    session.received_chunks.add(0)
    return session


@pytest.mark.asyncio
async def test_concurrent_assembly_claims_the_session_once(service, tmp_path):
    uploads = service.chunked_uploads
    session = _complete_upload(uploads)
    destination = tmp_path / "backup.zip"

    results = await asyncio.gather(
        uploads.assemble(session.id, destination),
        uploads.assemble(session.id, destination),
        return_exceptions=True,
    )

    assert sorted(type(result).__name__ for result in results) == [
        "ChunkedUploadError",
        "int",
    ]
    assert session.id not in uploads.sessions
    assert not list(tmp_path.glob(".backup.zip.*"))


@pytest.mark.asyncio
async def test_cancelled_assembly_finishes_worker_and_cleans_up(
    service, tmp_path, monkeypatch
):
    uploads = service.chunked_uploads
    session = _complete_upload(uploads)
    destination = tmp_path / "backup.zip"
    entered = threading.Event()
    release = threading.Event()
    original = uploads._assemble_sync

    def slow_assemble(upload_session, dest_path):
        entered.set()
        assert release.wait(5)
        return original(upload_session, dest_path)

    monkeypatch.setattr(
        type(uploads),
        "_assemble_sync",
        staticmethod(slow_assemble),
    )
    task = asyncio.create_task(uploads.assemble(session.id, destination))
    assert await asyncio.to_thread(entered.wait, 2)
    task.cancel()
    release.set()

    with pytest.raises(asyncio.CancelledError):
        await task

    assert session.id not in uploads.sessions
    assert not session.chunk_dir.exists()
    assert not list(tmp_path.glob(".backup.zip.*"))


@pytest.mark.skipif(os.name == "nt", reason="Windows does not model POSIX file modes")
@pytest.mark.asyncio
async def test_assembly_preserves_restrictive_destination_mode(service, tmp_path):
    uploads = service.chunked_uploads
    session = _complete_upload(uploads)
    destination = tmp_path / "backup.zip"
    destination.write_bytes(b"old")
    destination.chmod(0o640)

    await uploads.assemble(session.id, destination)

    assert stat.S_IMODE(destination.stat().st_mode) == 0o640


@pytest.mark.asyncio
async def test_complete_rejects_path_traversal_without_deleting_foreign_files(service):
    chunks_root = service.chunked_uploads.chunks_root
    chunks_root.mkdir(parents=True, exist_ok=True)
    victim = chunks_root.parent / "victim.merged"
    victim.write_bytes(b"keep me")

    with pytest.raises(ChatServiceError, match="not found or expired"):
        await service.upload_complete({"upload_id": "../victim"}, owner="alice")

    assert victim.read_bytes() == b"keep me"
