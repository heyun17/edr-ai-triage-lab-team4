"""Dify 외부 지식(External Knowledge API) 연결: Dify가 📘 플레이북 검색을 부를 수 있게 합니다. (3일차)

Dify 요청: POST /dify/retrieval
    {"knowledge_id": "...", "query": "...", "retrieval_setting": {"top_k": 3, "score_threshold": 0.5}}
    헤더 Authorization: Bearer <DIFY_API_KEY>
응답: {"records": [{"content", "score"(0~1), "title", "metadata"}]}
"""
from __future__ import annotations

import hmac

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from ..config import settings

router = APIRouter()


class RetrievalSetting(BaseModel):
    top_k: int = 3
    score_threshold: float = 0.0


class RetrievalRequest(BaseModel):
    knowledge_id: str = ""
    query: str
    retrieval_setting: RetrievalSetting = Field(default_factory=RetrievalSetting)


def normalize_scores(hits: list[dict]) -> list[dict]:
    """우리 검색 점수(RRF 등)를 Dify가 쓰는 0~1 범위로 바꿉니다."""
    # Dify expects 0..1 relevance scores. Raw RRF scores (~0.016)
    # would otherwise be removed by its score_threshold setting.
    if not hits:
        return []

    maximum = max(max(float(hit.get("score") or 0.0), 0.0) for hit in hits)
    if maximum == 0:
        return [{**hit, "score": 0.0} for hit in hits]

    return [
        {**hit, "score": min(1.0, max(0.0, float(hit.get("score") or 0.0)) / maximum)}
        for hit in hits
    ]


@router.post("/dify/retrieval")
def retrieval(req: RetrievalRequest, authorization: str = Header(default="")):
    # Never accept the example password on a real, networked deployment.
    if settings.backend == "real" and settings.dify_api_key in {"", "change-me"}:
        raise HTTPException(status_code=503, detail="DIFY_API_KEY 설정이 필요합니다")
    if not settings.dify_api_key or not hmac.compare_digest(
        authorization, f"Bearer {settings.dify_api_key}"
    ):
        raise HTTPException(status_code=403, detail={"error_code": 1002, "error_msg": "인증 실패"})
    from ..agent.toolset import search_playbook_fn

    hits = normalize_scores(search_playbook_fn()(req.query, req.retrieval_setting.top_k))
    records = [{"content": h["text"], "score": h["score"], "title": h.get("source") or "",
                "metadata": {"source": h.get("source"), "page": h.get("page"), "category": h.get("category")}}
               for h in hits if h["score"] >= req.retrieval_setting.score_threshold]
    return {"records": records}
