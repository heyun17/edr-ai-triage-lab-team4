"""체크포인터: 에이전트 상태를 저장하는 곳 (01b 문서의 '경비원의 수첩'). 2일차 1-3, 운전 🔍

- memory  : 프로세스 안의 메모리. 프로세스가 끝나면 사라짐
- postgres: Postgres 테이블. 파드가 바뀌어도 남음 → 승인 후 이어 가기, 처리 중 워커가 죽어도 이어 가기
"""
from __future__ import annotations

import logging
from functools import lru_cache

from langgraph.checkpoint.memory import InMemorySaver

from ..config import settings

log = logging.getLogger("checkpoint")


def _kind() -> str:
    if settings.checkpointer != "auto":
        return settings.checkpointer
    return "postgres" if settings.backend == "real" else "memory"




@lru_cache(maxsize=1)
def get_checkpointer():
    if _kind() == "memory":
        return InMemorySaver()

    import psycopg
    from psycopg.rows import dict_row
    from langgraph.checkpoint.postgres import PostgresSaver

    # 연결 풀 대신 PostgreSQL에 직접 연결
    conn = psycopg.connect(
        settings.postgres_dsn,
        autocommit=True,
        prepare_threshold=0,
        row_factory=dict_row,
        connect_timeout=5,
    )

    # 체크포인트 저장소 생성
    saver = PostgresSaver(conn)
    saver.setup()

    return saver



def ping() -> bool:
    """/readyz에서 씀: Postgres에 연결되는가."""
    if _kind() == "memory":
        return True
    try:
        import psycopg

        with psycopg.connect(settings.postgres_dsn, connect_timeout=3) as c:
            c.execute("select 1")
        return True
    except Exception:  # noqa: BLE001
        return False
