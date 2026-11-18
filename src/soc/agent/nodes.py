"""에이전트의 노드들. 노드 하나 = 상태를 받아 '바꿀 부분'을 돌려주는 함수.

    조사 ⇄ 도구 → 판정 → 가드레일 → 권고 → 승인 → 리포트

운전 규칙 (1일차 4-2): 상대가 만든 도구를 내가 연결합니다.
- 조사 노드(🔍 도구를 씀)는 📘 문서 담당이 운전  → TODO[AG-1]
- 권고 노드(📘 검색을 씀)는 🔍 기록 담당이 운전  → TODO[AG-2]
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.types import interrupt

from ..config import settings
from . import guardrail
from .llm import cost_usd, get_llm, usage_of
from .prompts import prompt
from .state import DANGEROUS_ACTIONS, Recommendation, TriageState, Verdict
from .toolset import search_playbook_fn, telemetry_tools


def _alert_message(alert: dict) -> HumanMessage:
    keep = (
        "alert_id",
        "ts",
        "host",
        "rule_id",
        "title",
        "severity",
        "techniques",
        "event_ids",
        "pid",
    )
    data = {k: alert.get(k) for k in keep}
    return HumanMessage(
        content=f"알림:\n```json\n{json.dumps(data, ensure_ascii=False, indent=1)}\n```"
    )


def _ids(obj) -> list[str]:
    """도구 결과 안의 모든 event_id를 꺼냅니다 (가드레일이 '실제로 조회한 기록'으로 씀)."""
    if isinstance(obj, dict):
        return [
            v
            for k, v in obj.items()
            if k == "event_id" and isinstance(v, str)
        ] + [
            i
            for k, v in obj.items()
            if k != "event_id"
            for i in _ids(v)
        ]

    if isinstance(obj, list):
        return [i for v in obj for i in _ids(v)]

    return []


# ---------------------------------------------------------------------------- 조사
def investigate(state: TriageState) -> dict:
    """조사 노드: LLM이 필요한 🔍 기록 조회 도구를 고릅니다. (AG-1, 운전 📘)"""
    history = list(state.get("messages", []))
    first_message = [_alert_message(state["alert"])] if not history else []

    llm = get_llm().bind_tools(telemetry_tools())
    response = llm.invoke(
        [SystemMessage(content=prompt("investigate"))]
        + history
        + first_message
    )

    return {
        "messages": first_message + [response],
        "trace": ["조사"],
        "usage": usage_of(response),
    }


def run_tools(state: TriageState) -> dict:
    """도구 노드: LLM이 요청한 도구를 실행하고, 결과의 event_id를 '실제로 조회한 기록'으로 남깁니다."""
    tools = {t.name: t for t in telemetry_tools()}
    last: AIMessage = state["messages"][-1]

    msgs = []
    seen = []

    for call in last.tool_calls:
        t = tools.get(call["name"])

        try:
            result = (
                t.invoke(call["args"])
                if t
                else {"error": f"없는 도구: {call['name']}"}
            )
        except Exception as e:  # noqa: BLE001
            result = {"error": f"{type(e).__name__}: {e}"}

        seen += _ids(result)

        msgs.append(
            ToolMessage(
                content=json.dumps(
                    result,
                    ensure_ascii=False,
                    default=str,
                ),
                tool_call_id=call["id"],
            )
        )

    return {
        "messages": msgs,
        "seen_event_ids": seen,
        "tool_rounds": state.get("tool_rounds", 0) + 1,
        "trace": ["도구"],
    }


def after_investigate(state: TriageState) -> str:
    last = state["messages"][-1]

    if (
        getattr(last, "tool_calls", None)
        and state.get("tool_rounds", 0) < settings.max_tool_rounds
    ):
        return "tools"

    return "judge"


# ---------------------------------------------------------------------------- 판정과 가드레일
def judge(state: TriageState) -> dict:
    llm = get_llm().with_structured_output(
        Verdict,
        include_raw=True,
    )

    msgs = (
        [SystemMessage(content=prompt("judge"))]
        + list(state["messages"])
        + [HumanMessage(content="판정하세요.")]
    )

    out = llm.invoke(msgs)

    return {
        "verdict": out["parsed"].model_dump(),
        "trace": ["판정"],
        "usage": usage_of(out["raw"]),
    }


def check_guardrail(state: TriageState) -> dict:
    result = guardrail.check(
        state["verdict"],
        state.get("seen_event_ids", []),
        state["alert"],
    )

    out: dict = {
        "guardrail": result,
        "guardrail_log": [result],
        "trace": ["가드레일"],
    }

    if result["ok"]:
        return out

    retries = state.get("guardrail_retries", 0)

    if (
        settings.guardrail_on_fail == "retry"
        and retries < settings.max_guardrail_retries
    ):
        out["guardrail_retries"] = retries + 1
        out["messages"] = [
            HumanMessage(
                content=(
                    "판정이 검증을 통과하지 못했습니다: "
                    + "; ".join(result["problems"])
                    + ". 도구로 근거를 더 확인하고, 실제로 조회한 event_id만 쓰세요."
                )
            )
        ]
        return out

    v = dict(state["verdict"])

    known = (
        set(state.get("seen_event_ids", []))
        | set(state["alert"].get("event_ids", []))
    )

    v["evidence_event_ids"] = [
        i
        for i in v.get("evidence_event_ids", [])
        if i in known
    ]

    if v["verdict"] == "malicious":
        v["verdict"] = "suspicious"

    v["needs_review"] = True
    out["verdict"] = v

    return out


def after_guardrail(state: TriageState) -> str:
    g = state.get("guardrail", {})

    if (
        not g.get("ok")
        and state["messages"]
        and isinstance(state["messages"][-1], HumanMessage)
    ):
        return "investigate"

    return "recommend"


# ---------------------------------------------------------------------------- 권고
def recommend(state: TriageState) -> dict:
    """권고 노드: 📘 플레이북을 검색하고 근거가 있는 권고를 만듭니다. (AG-2, 운전 🔍)"""
    verdict = state["verdict"]
    alert = state["alert"]

    techniques = (
        verdict.get("techniques")
        or alert.get("techniques", [])
    )

    query = (
        f"{alert.get('title', '')} "
        f"{' '.join(techniques)} 대응 절차 승인권자"
    )

    playbook = search_playbook_fn()(
        query=query,
        k=3,
    )

    context = {
        "alert": alert,
        "verdict": verdict,
        "playbook": playbook,
    }

    message = HumanMessage(
        content=(
            "다음 판정과 플레이북을 근거로 대응을 권고하세요.\n"
            + "```json\n"
            + json.dumps(
                context,
                ensure_ascii=False,
                default=str,
            )
            + "\n```"
        )
    )

    llm = get_llm().with_structured_output(
        Recommendation,
        include_raw=True,
    )

    output = llm.invoke(
        [
            SystemMessage(content=prompt("recommend")),
            message,
        ]
    )

    return {
        "playbook": playbook,
        "recommendation": output["parsed"].model_dump(),
        "trace": ["권고"],
        "usage": usage_of(output["raw"]),
    }


# ---------------------------------------------------------------------------- 승인
def approval(state: TriageState) -> dict:
    """위험한 조치가 있으면 멈추고 사람의 결정을 기다립니다.

    interrupt()가 호출되면 현재 상태를 체크포인터에 저장하고 실행을 멈춥니다.
    Command(resume=...)으로 재개하면 interrupt()가 사람의 결정을 반환합니다.

    재개 시 이 노드는 처음부터 다시 실행되므로 interrupt() 앞에는
    한 번만 실행되어야 하는 외부 쓰기 작업을 두지 않습니다.
    """
    actions = state["recommendation"]["actions"]

    risky = [
        action
        for action in actions
        if action["action"] in DANGEROUS_ACTIONS
    ]

    if not risky:
        return {
            "approval": {
                "required": False,
                "approved": True,
                "decision": "not_required",
            },
            "trace": ["승인"],
        }

    alert = state["alert"]
    verdict = state["verdict"]

    request = {
        "alert_id": alert["alert_id"],
        "host": alert["host"],
        "verdict": verdict["verdict"],
        "confidence": verdict["confidence"],
        "techniques": verdict.get("techniques", []),
        "evidence_event_ids": verdict.get(
            "evidence_event_ids",
            [],
        ),
        "actions": risky,
    }

    decision = interrupt(request)

    approval_result = {
        "required": True,
        "approved": bool(decision.get("approved")),
        "approver": decision.get("approver"),
        "comment": decision.get("comment"),
        "decision": (
            "approved"
            if decision.get("approved")
            else "rejected"
        ),
    }

    return {
        "approval": approval_result,
        "trace": ["승인"],
    }


# ---------------------------------------------------------------------------- 리포트
def report(state: TriageState) -> dict:
    alert = state["alert"]
    v = state["verdict"]
    usage = state.get("usage", {})

    rep = {
        "alert_id": alert["alert_id"],
        "host": alert["host"],
        "title": alert.get("title"),
        "severity": alert.get("severity"),
        "verdict": v["verdict"],
        "confidence": v["confidence"],
        "techniques": v.get("techniques", []),
        "evidence_event_ids": v.get(
            "evidence_event_ids",
            [],
        ),
        "reasoning": v.get("reasoning"),
        "needs_review": v.get(
            "needs_review",
            False,
        ),
        "guardrail": state.get(
            "guardrail",
            {},
        ),
        "guardrail_log": state.get(
            "guardrail_log",
            [],
        ),
        "recommendation": state.get(
            "recommendation",
            {},
        ),
        "sources": sorted(
            {
                h["source"]
                for h in state.get(
                    "playbook",
                    [],
                )
                if h.get("source")
            }
        ),
        "approval": state.get(
            "approval",
            {},
        ),
        "tool_rounds": state.get(
            "tool_rounds",
            0,
        ),
        "usage": usage,
        "cost_usd": cost_usd(usage),
        "trace": state.get(
            "trace",
            [],
        )
        + ["리포트"],
    }

    return {
        "report": rep,
        "trace": ["리포트"],
    }