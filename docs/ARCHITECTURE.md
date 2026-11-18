# 아키텍처

> D1-13 **화이트보드 설계안** (2026-11-18). 🔍 진승호가 선택한 설정을 바탕으로 만든 팀 검토용 초안입니다. **D1-14 코드 구현/테스트 결과가 아닙니다.**
> 기준: `docs/guide/DAY1.md` 4-1, `docs/prep/01_edr_soc_intro.md` 5장, `src/soc/agent/state.py`, `docs/CONTRACT.md`.

## 1. 에이전트 설계도 (D1-13)

아래 Mermaid는 **직접 작성한 설계용 그림**입니다. `python -m soc.agent.graph`의 실행 출력은 아닙니다. 현재 `src/soc/agent/graph.py`의 `TODO[AG-3]` 때문에 이 명령은 `NotImplementedError`로 멈춥니다. D1-14 구현 후 실제 출력과 대조합니다.

```mermaid
flowchart TD
    START([보안 경보 접수]) --> investigate["① 조사<br/>조사할 로그 결정"]
    investigate --> need_tools{"추가 도구 호출?<br/>도구 실행 라운드 6회 미만?"}
    need_tools -->|예| tools["② 도구 실행<br/>프로세스 트리·활동·타임라인"]
    tools --> investigate
    need_tools -->|아니오| judge["③ 판정<br/>정상·의심·악성"]
    judge --> guardrail["④ 가드레일<br/>근거 event_id 검증"]
    guardrail --> passed{"검증 통과?"}
    passed -->|예| recommend["⑤ 권고<br/>플레이북 RAG 검색"]
    passed -->|아니오| retry{"재조사 1회 사용?"}
    retry -->|아직 안 함| investigate
    retry -->|이미 사용| lower["보수적 판정으로 낮춤<br/>needs_review 표시"]
    lower --> recommend
    recommend --> approval["⑥ 승인 단계"]
    approval --> risky{"위험한 조치 포함?"}
    risky -->|예| human["사람 승인·거절 기다림<br/>상태 저장 후 재개"]
    risky -->|아니오| report["⑦ 리포트 작성"]
    human --> report
    report --> END([완료])
```

### 1-1. 노드별 역할 / 읽는 상태 / 쓰는 상태

| 노드 | 하는 일 | 읽는 상태 | 쓰는 상태 | 쓰는 도구 | 담당 |
|---|---|---|---|---|---|
| 조사 (`investigate`) | 알림·이전 대화를 보고 필요한 로그 결정 | `alert`, `messages`, `tool_rounds` | `messages`, `trace`, `usage` | 도구 호출 계획 | 📘 (D1-14) |
| 도구 실행 (`tools`) | 프로세스·파일·시간대별 로그 조회 | `messages` | `messages`, `seen_event_ids`, `tool_rounds`, `trace` | 🔍 조사 도구 3개 | 👥 |
| 판정 (`judge`) | 정상·의심·악성, 신뢰도 판단 | `messages`, `seen_event_ids` | `verdict`, `trace`, `usage` | LLM | 👥 |
| 가드레일 (`guardrail`) | 인용 근거가 실제 조회 기록인지 확인 | `verdict`, `seen_event_ids`, `alert` | `guardrail`, `guardrail_log`, 실패 시 `guardrail_retries`·`verdict` | 근거 검증 | 📘 (Day2) |
| 권고 (`recommend`) | 플레이북 검색 후 대응 조치 권고 | `verdict`, `alert` | `playbook`, `recommendation`, `trace`, `usage` | 📘 `search_playbook` | 🔍 (D1-14) |
| 승인 (`approval`) | 위험 조치일 때 사람 승인 대기 | `recommendation` | `approval`, `trace` | 사람 승인(HITL) | 🔍 (Day2) |
| 리포트 (`report`) | 판정·로그 근거·정책·승인 결과 통합 | `alert`, `verdict`, `playbook`, `recommendation`, `approval`, `trace`, `usage` | `report`, `trace` | 결과 정리 | 👥 |

### 1-2. State: 공용 상태 정보

| 묶음 | State 필드 | 저장 내용 |
|---|---|---|
| 접수·조사 | `alert`, `messages`, `seen_event_ids`, `tool_rounds` | 알림, 대화, 실제 조회한 기록 ID, 도구 실행 라운드 수 |
| 판정·안전 | `verdict`, `guardrail`, `guardrail_log`, `guardrail_retries` | 판정, 근거 검증, 실패 이력과 재조사 수 |
| 대응·승인 | `playbook`, `recommendation`, `approval` | 매뉴얼 검색 결과, 권고, 사람 결정 |
| 산출·추적 | `report`, `trace`, `usage` | 보고서, 지나온 경로, 토큰 사용량 |

## 2. 갈림길 (Edge)

| 결정 | D1-13 설계안 | 코드 근거 |
|---|---|---|
| 조사 상한 | **도구 실행 라운드 최대 6회**. 추가 조사가 필요하면 `조사 → 도구 실행 → 조사` 반복 | `max_tool_rounds=6`. 라운드 한 번에 도구가 여럿 호출될 수도 있음 |
| 가드레일 실패 | **1회 재조사**. 재실패 시 확인 안 된 event_id는 제외하고 악성을 의심으로 낮추며 `needs_review` 표시 | `guardrail_on_fail="retry"`, `max_guardrail_retries=1` |
| 사람 승인 | 위험 조치만 대기: `block_ip`·`kill_process`·`isolate_host`·`reset_password`. 나머지는 승인 대기 없이 보고서로 | `DANGEROUS_ACTIONS` |

**아직 미구현:** `nodes.py`의 승인 함수는 현재 `not_implemented` 응답입니다. 위 사람 승인 경로는 목표 설계이며, 실제 승인/재개 성공을 의미하지 않습니다.

## 3. 배포 구성도 (2일차부터)

<!-- 01b 문서 2장의 그림을 실제 리소스(Deployment, StatefulSet, Job, Service, Ingress, Secret, ConfigMap)로 바꿔 그리기 -->

## D1-14 그래프 뼈대 구현 진행 (2026-11-18)

- **AG-1 조사 노드:** `nodes.py`의 `investigate()`에서 🔍 도구를 LLM에 연결하고 알림·대화·도구 메시지를 누적하도록 구현 (📘 운전 영역).
- **AG-2 권고 노드:** `recommend()`에서 📘 `search_playbook(query, k=3)`으로 정책 검색 후 LLM의 구조화된 `Recommendation` 생성 (🔍 운전 영역).
- **AG-3 Edge:** `graph.py`에서 7개 노드를 연결하고 **조사 ↔ 도구** 및 **가드레일 실패 시 재조사** 조건부 경로 구현.
- **정적 검사:** Python 소스 문법 검사 및 AST 구조 검사(노드 7개, 직접 Edge 6개, 조건 Edge 2개) 수행.
- **아직 미검증:** 프로젝트 의존 패키지가 없는 검사용 환경에서는 `pytest tests/test_graph_skeleton.py -q` 및 `python -m soc.agent.graph`를 실제 실행하지 못함. **D1-14 최종 완료 판정 보류.**

### 남은 실행 확인 (프로젝트 가상환경에서)

```bash
pytest tests/test_graph_skeleton.py -q
python -m soc.agent.graph
```

테스트가 통과하면 `trace`에 **조사 → 도구 → 조사 → 판정 → 권고 → 리포트** 순서가 나타나고, 생성된 Mermaid 코드를 위 D1-13 설계도와 비교합니다. **실제 출력이나 테스트 통과 결과는 확인 전이므로 임의로 기록하지 않습니다.**

> 가드레일 검사 G-1/G-2와 실제 승인 대기 H-1/H-2는 Day2 과제입니다. 현재 가드레일/승인 노드는 뼈대 경로에 포함돼 있지만 완성된 기능이 아닙니다.
