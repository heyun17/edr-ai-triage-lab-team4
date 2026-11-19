"""Dify 연결 테스트 (3일차, TODO[DIFY-1])."""
from fastapi.testclient import TestClient

from soc.api.dify import normalize_scores
from soc.api.main import app


def test_normalize_scores():
    out = normalize_scores([{"score": 0.032}, {"score": 0.016}, {"score": 0.0}])
    assert [h["score"] for h in out] == [1.0, 0.5, 0.0]
    assert normalize_scores([{"score": 0.0}])[0]["score"] == 0.0
    assert normalize_scores([]) == []
    assert [h["score"] for h in normalize_scores([{"score": 0.0}, {"score": 0.0}])] == [0.0, 0.0]
    assert normalize_scores([{"score": -1.0}, {"score": 2.0}])[0]["score"] == 0.0
    original = [{"score": 0.016, "source": "one.pdf"}]
    normalized = normalize_scores(original)
    assert normalized == [{"score": 1.0, "source": "one.pdf"}]
    assert original[0]["score"] == 0.016  # input is not mutated


def test_retrieval_endpoint():
    c = TestClient(app)
    assert c.post("/dify/retrieval", json={"query": "격리"}).status_code == 403
    r = c.post("/dify/retrieval", headers={"Authorization": "Bearer change-me"},
               json={"query": "격리 승인권자", "retrieval_setting": {"top_k": 3, "score_threshold": 0.5}})
    assert r.status_code == 200
    recs = r.json()["records"]
    assert recs and recs[0]["score"] == 1.0 and recs[0]["title"].endswith(".pdf")
