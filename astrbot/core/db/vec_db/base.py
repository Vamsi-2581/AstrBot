"""Vector store contract shared by every knowledge-base backend.

The interface is intentionally small and matches the operations the knowledge
base performs: insert, batch insert, retrieve, delete, count, and close. The
default backend is FAISS; additional backends only need to implement this
contract and be selected by config.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import numpy as np

from .result import Result


@runtime_checkable
class EmbeddingStorageBackend(Protocol):
    """Vector-index storage surface shared by FAISS and the exact backend."""

    dimension: int

    async def insert(self, vector: np.ndarray, id: int) -> None: ...

    async def insert_batch(self, vectors: np.ndarray, ids: list[int]) -> None: ...

    async def search(self, vector: np.ndarray, k: int) -> tuple: ...

    async def delete(self, ids: list[int]) -> None: ...

    async def save_index(self) -> None: ...


@runtime_checkable
class VectorStore(Protocol):
    """Operations a knowledge-base vector store must provide."""

    async def initialize(self) -> None: ...

    @property
    def dimension(self) -> int: ...

    async def insert(
        self,
        content: str,
        metadata: dict | None = None,
        id: str | None = None,
    ) -> int: ...

    async def insert_batch(
        self,
        contents: list[str],
        metadatas: list[dict] | None = None,
        ids: list[str] | None = None,
        batch_size: int = 32,
        tasks_limit: int = 3,
        max_retries: int = 3,
        progress_callback=None,
    ) -> list[int]: ...

    async def retrieve(
        self,
        query: str,
        k: int = 5,
        fetch_k: int = 20,
        rerank: bool = False,
        metadata_filters: dict | None = None,
    ) -> list[Result]: ...

    async def delete(self, doc_id: str) -> None: ...

    async def delete_documents(self, metadata_filters: dict) -> None: ...

    async def count_documents(self, metadata_filter: dict | None = None) -> int: ...

    async def get_documents(
        self,
        metadata_filters: dict | None = None,
        ids: list | None = None,
        offset: int | None = 0,
        limit: int | None = 100,
    ) -> list[dict]: ...

    async def list_kb_doc_ids(self) -> set[str]: ...

    async def relabel_kb_doc_id(self, from_doc_id: str, to_doc_id: str) -> None: ...

    async def close(self) -> None: ...
