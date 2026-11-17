"""🔍 조사 도구: 에이전트가 PC 기록을 조사할 때 부르는 함수들.

도구 계약 (docs/CONTRACT.md)
- 모든 결과의 기록 하나하나에 `event_id`가 있다 → 가드레일이 판정 근거를 검증하는 데 씀
- 명령줄은 앞부분만 (요약) → LLM에게 넘기는 글자 수가 곧 비용과 속도

함수의 설명(docstring)은 LLM이 '어떤 도구를 부를지' 고를 때 읽는 글입니다. 신경 써서 쓰세요.

    pytest tests/test_telemetry_tools.py -q
"""
from __future__ import annotations

from datetime import datetime, timedelta

from langchain_core.tools import tool

from ..config import settings
from ..osclient import get_client

EVENTS = f"{settings.index_events}-*"
CMD_MAX = 120           # 명령줄 요약 길이
MAX_ANCESTORS = 5
TIMELINE_LIMIT = 100


def _search(body: dict) -> list[dict]:
    res = get_client().search(index=EVENTS, body=body)
    return [h["_source"] for h in res["hits"]["hits"]]


def summarize(e: dict) -> dict:
    """기록 하나를 LLM에게 넘길 모양으로 줄입니다. (이미 만들어 둔 도우미)"""
    p = e.get("process", {})
    out = {"event_id": e["event_id"], "ts": e["ts"], "type": e["type"],
           "pid": p.get("pid"), "ppid": p.get("ppid"), "name": p.get("name"),
           "cmdline": (p.get("cmdline") or "")[:CMD_MAX], "user": p.get("user"), "signed": p.get("signed")}
    if e.get("network"):
        n = e["network"]
        out["detail"] = f"{n['dst_ip']}:{n['dst_port']} ({n.get('bytes_out', 0)} bytes)"
    elif e.get("file"):
        f = e["file"]
        out["detail"] = f"{f['action']} {f['path']}" + (f" → {f['new_path']}" if f.get("new_path") else "")
    elif e.get("registry"):
        out["detail"] = f"{e['registry']['key']} = {e['registry']['value']}"
    elif e.get("script_text"):
        out["detail"] = e["script_text"][:200]
    return out


def _parse_ts(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def _iso(t: datetime) -> str:
    return t.isoformat().replace("+00:00", "Z")


def _find_process(host: str, pid: int) -> dict | None:
    """host에서 pid를 가진 '프로세스 생성' 기록 하나."""
    rows = _search({"size": 1, "sort": [{"ts": "desc"}], "query": {"bool": {"filter": [
        {"term": {"host": host}}, {"term": {"type": "process"}}, {"term": {"process.pid": pid}}]}}})
    return rows[0] if rows else None


def get_process_tree(host: str, pid: int) -> dict:
    """지정된 PC에서 프로세스의 부모와 자식 실행 기록을 조회합니다.

    Args:
        host: PC 이름 (예: WS-007)
        pid: 프로세스 번호
    """
    process = _find_process(host, pid)
    ancestors: list[dict] = []
    children: list[dict] = []
    result = {"host": host, "pid": pid, "process": summarize(process) if process else None,
              "ancestors": ancestors, "children": children}
    if not process:
        return result

    # 부모의 pid를 역으로 따라 올라갑니다. 같은 host만 조회해야 다른 PC 로그와 섞이지 않습니다.
    parent_pid = process.get("process", {}).get("ppid")
    visited = {pid}
    for _ in range(MAX_ANCESTORS):
        if parent_pid is None or parent_pid in visited:
            break
        visited.add(parent_pid)
        parent = _find_process(host, parent_pid)
        if not parent:
            result["note"] = f"부모 프로세스(pid {parent_pid})의 생성 기록이 없습니다."
            break
        ancestors.append(summarize(parent))
        parent_pid = parent.get("process", {}).get("ppid")

    # pid가 현재 프로세스의 자식을 가리키는 생성 기록만 가져옵니다.
    rows = _search({
        "size": 50,
        "sort": [{"ts": "asc"}],
        "query": {"bool": {"filter": [
            {"term": {"host": host}},
            {"term": {"type": "process"}},
            {"term": {"process.ppid": pid}},
        ]}},
    })
    children.extend(summarize(e) for e in rows)
    return result


def get_process_activity(host: str, pid: int) -> dict:
    """지정된 PC의 프로세스가 만든 통신, 파일, 레지스트리, 스크립트 기록을 시간순으로 조회합니다.

    Args:
        host: PC 이름 (예: WS-007)
        pid: 프로세스 번호
    """
    rows = _search({
        "size": 50,
        "sort": [{"ts": "asc"}],
        "query": {"bool": {"filter": [
            {"term": {"host": host}},
            {"term": {"process.pid": pid}},
            {"terms": {"type": ["network", "file", "registry", "script"]}},
        ]}},
    })
    return {"host": host, "pid": pid, "events": [summarize(e) for e in rows]}


def get_host_timeline(host: str, around_ts: str, minutes: int = 10) -> dict:
    """지정된 PC에서 특정 시각 전후에 발생한 모든 기록을 시간순으로 조회합니다.

    Args:
        host: PC 이름 (예: WS-007)
        around_ts: 기준 시각 (ISO 형식, 예: 2026-11-16T09:12:02Z)
        minutes: 기준 시각 앞뒤로 조사할 분 단위 범위
    """
    center = _parse_ts(around_ts)
    start = _iso(center - timedelta(minutes=minutes))
    end = _iso(center + timedelta(minutes=minutes))
    # 1건 더 조회해서 제한을 넘겼는지 판단합니다.
    rows = _search({
        "size": TIMELINE_LIMIT + 1,
        "sort": [{"ts": "asc"}],
        "query": {"bool": {"filter": [
            {"term": {"host": host}},
            {"range": {"ts": {"gte": start, "lte": end}}},
        ]}},
    })
    return {"host": host, "from": start, "to": end,
            "events": [summarize(e) for e in rows[:TIMELINE_LIMIT]],
            "truncated": len(rows) > TIMELINE_LIMIT}



TELEMETRY_TOOLS = [tool(get_process_tree), tool(get_process_activity), tool(get_host_timeline)]
