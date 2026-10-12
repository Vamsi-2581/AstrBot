"""Pluggable knowledge-base vector stores.

FAISS remains the default. ``create_vector_store`` selects a backend by config
and returns an object satisfying the ``VectorStore`` protocol.
"""

from .base import VectorStore
from .result import Result

_FAISS_BACKENDS = frozenset({"faiss", ""})
_EXACT_BACKENDS = frozenset({"exact", "numpy", "exact-numpy"})


def normalize_vector_store(backend: str | None) -> str:
    """Return the canonical backend name for a configured value."""

    normalized = (backend or "faiss").strip().lower()
    if normalized in _EXACT_BACKENDS:
        return "exact"
    return "faiss"


def vector_index_filename(backend: str | None) -> str:
    """Return the persisted index filename for a backend."""

    return "index.npz" if normalize_vector_store(backend) == "exact" else "index.faiss"


def create_vector_store(
    backend: str | None,
    *,
    doc_store_path: str,
    index_store_path: str,
    embedding_provider,
    rerank_provider=None,
) -> VectorStore:
    """Build the configured vector store.

    Args:
        backend: Configured backend name; unknown values fall back to FAISS.
        doc_store_path: SQLite document-store path.
        index_store_path: Persisted index path.
        embedding_provider: Provider used to embed text.
        rerank_provider: Optional rerank provider.

    Returns:
        A ``VectorStore`` implementation.
    """
    if normalize_vector_store(backend) == "exact":
        from .exact import ExactVecDB

        return ExactVecDB(
            doc_store_path,
            index_store_path,
            embedding_provider,
            rerank_provider,
        )

    from .faiss import FaissVecDB

    return FaissVecDB(
        doc_store_path,
        index_store_path,
        embedding_provider,
        rerank_provider,
    )


__all__ = [
    "Result",
    "VectorStore",
    "create_vector_store",
    "normalize_vector_store",
    "vector_index_filename",
]
