from __future__ import annotations

from pathlib import Path

import pytest

from astrbot.core.db.vec_db import (
    create_vector_store,
    normalize_vector_store,
    vector_index_filename,
)
from astrbot.core.db.vec_db.base import VectorStore
from astrbot.core.db.vec_db.exact import ExactVecDB
from astrbot.core.db.vec_db.faiss import FaissVecDB


class _FakeEmbeddingProvider:
    """Deterministic 2-D embeddings for round-trip tests."""

    def get_dim(self) -> int:
        return 2

    async def get_embedding(self, text: str) -> list[float]:
        return self._vector(text)

    async def get_embeddings_batch(
        self,
        texts: list[str],
        batch_size: int = 32,
        tasks_limit: int = 3,
        max_retries: int = 3,
        progress_callback=None,
    ) -> list[list[float]]:
        return [self._vector(text) for text in texts]

    @staticmethod
    def _vector(text: str) -> list[float]:
        table = {
            "north": [1.0, 0.0],
            "east": [0.0, 1.0],
            "south": [-1.0, 0.0],
        }
        return table.get(text, [0.0, 0.0])


def test_normalize_and_filename() -> None:
    assert normalize_vector_store(None) == "faiss"
    assert normalize_vector_store("faiss") == "faiss"
    assert normalize_vector_store("numpy") == "exact"
    assert normalize_vector_store("unknown") == "faiss"
    assert vector_index_filename("exact") == "index.npz"
    assert vector_index_filename("faiss") == "index.faiss"


def test_create_vector_store_selects_backend(tmp_path: Path) -> None:
    provider = _FakeEmbeddingProvider()

    exact = create_vector_store(
        "exact",
        doc_store_path=str(tmp_path / "exact" / "doc.db"),
        index_store_path=str(tmp_path / "exact" / "index.npz"),
        embedding_provider=provider,
    )
    faiss = create_vector_store(
        "faiss",
        doc_store_path=str(tmp_path / "faiss" / "doc.db"),
        index_store_path=str(tmp_path / "faiss" / "index.faiss"),
        embedding_provider=provider,
    )

    assert isinstance(exact, ExactVecDB)
    assert isinstance(exact, VectorStore)
    assert isinstance(faiss, FaissVecDB)


@pytest.mark.asyncio
async def test_exact_backend_round_trip(tmp_path: Path) -> None:
    provider = _FakeEmbeddingProvider()
    store = create_vector_store(
        "exact",
        doc_store_path=str(tmp_path / "doc.db"),
        index_store_path=str(tmp_path / "index.npz"),
        embedding_provider=provider,
    )
    await store.initialize()

    await store.insert("north", {"tag": "a"})
    await store.insert_batch(
        ["east", "south"],
        metadatas=[{"tag": "b"}, {"tag": "c"}],
    )
    assert await store.count_documents() == 3

    results = await store.retrieve("north", k=1)
    assert results and results[0].data["text"] == "north"

    results = await store.retrieve("east", k=1)
    assert results and results[0].data["text"] == "east"

    docs = await store.document_storage.get_documents(metadata_filters={"tag": "b"})
    await store.delete(docs[0]["doc_id"])
    assert await store.count_documents() == 2

    await store.delete_documents({"tag": "c"})
    assert await store.count_documents() == 1

    await store.close()


@pytest.mark.asyncio
async def test_exact_backend_persists_across_reopen(tmp_path: Path) -> None:
    provider = _FakeEmbeddingProvider()
    kwargs = {
        "doc_store_path": str(tmp_path / "doc.db"),
        "index_store_path": str(tmp_path / "index.npz"),
        "embedding_provider": provider,
    }
    store = create_vector_store("exact", **kwargs)
    await store.initialize()
    await store.insert("north", {"tag": "a"})
    await store.close()

    reopened = create_vector_store("exact", **kwargs)
    await reopened.initialize()
    results = await reopened.retrieve("north", k=1)
    assert results and results[0].data["text"] == "north"
    await reopened.close()
