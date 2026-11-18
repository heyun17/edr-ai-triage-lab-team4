"""📘 4단계 저장: kb-playbooks 인덱스의 매핑을 정하고 청크를 넣습니다."""
from __future__ import annotations

from ..config import settings
from ..osclient import bulk_index, get_client


def index_body() -> dict:
    """kb-playbooks 인덱스의 검색·벡터·출처 필드 매핑을 반환합니다."""

    return {
        "settings": {
            "index": {
                "knn": True,
                "number_of_replicas": 0,
            }
        },
        "mappings": {
            "properties": {
                "id": {
                    "type": "keyword",
                },
                "text": {
                    "type": "text",
                },
                "embedding": {
                    "type": "knn_vector",
                    "dimension": settings.embed_dim,
                    "method": {
                        "name": "hnsw",
                        "space_type": "cosinesimil",
                        "engine": "lucene",
                    },
                },
                "source": {
                    "type": "keyword",
                },
                "page": {
                    "type": "integer",
                },
                "category": {
                    "type": "keyword",
                },
                "chunk_index": {
                    "type": "integer",
                },
                "text_as_html": {
                    "type": "text",
                    "index": False,
                },
            }
        },
    }


def ensure_index(client=None, recreate: bool = False) -> None:
    client = client or get_client()

    if client.indices.exists(index=settings.index_kb):
        if not recreate:
            return

        client.indices.delete(
            index=settings.index_kb
        )

    client.indices.create(
        index=settings.index_kb,
        body=index_body(),
    )


def save(
    records: list[dict],
    vectors: list[list[float]],
    client=None,
) -> int:
    client = client or get_client()

    docs = [
        {
            **record,
            "embedding": vector,
        }
        for record, vector in zip(
            records,
            vectors,
            strict=True,
        )
    ]

    return bulk_index(
        client,
        settings.index_kb,
        docs,
        id_field="id",
    )