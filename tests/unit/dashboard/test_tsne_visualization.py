import base64
from types import SimpleNamespace

import pytest

pytest.importorskip("matplotlib")
pytest.importorskip("sklearn")

from astrbot.dashboard.utils import generate_tsne_visualization


class _EmbeddingProvider:
    async def get_embedding(self, _text: str) -> list[float]:
        return [0.1, 0.2]


class _KBManager:
    def __init__(self, helper: SimpleNamespace) -> None:
        self.helper = helper

    async def get_kb_by_name(self, _name: str) -> SimpleNamespace:
        return self.helper


@pytest.mark.asyncio
async def test_tsne_visualization_reads_exact_numpy_index(tmp_path) -> None:
    import numpy as np

    index_path = tmp_path / "index.npz"
    with index_path.open("wb") as handle:
        np.savez(
            handle,
            ids=np.array([1, 2, 3], dtype=np.int64),
            vectors=np.array(
                [[0.1, 0.2], [0.2, 0.3], [0.3, 0.4]],
                dtype=np.float32,
            ),
        )

    vec_db = SimpleNamespace(
        index_store_path=str(index_path),
        embedding_provider=_EmbeddingProvider(),
    )
    helper = SimpleNamespace(
        kb=SimpleNamespace(kb_name="exact-kb"),
        kb_dir=tmp_path,
        vec_db=vec_db,
    )

    result = await generate_tsne_visualization(
        "query", ["exact-kb"], _KBManager(helper)
    )

    assert isinstance(result, str)
    assert base64.b64decode(result).startswith(b"\x89PNG")
