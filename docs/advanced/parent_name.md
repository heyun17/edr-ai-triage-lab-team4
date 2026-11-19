# D3-5 — 조사 도구의 부모 프로세스 이름 보존

**작업일:** 2026-11-19 · **영역:** 🔍 기록/조사 · **형태:** 1인 압축 실습

## 목표와 기존 문제

Day2 동일 12개 합성 알림(FakeLLM) 평가에서 정상 IT 관리 스크립트 `it_inventory_script` 2건을 `suspicious`로 잘못 판단해 정확도 **10/12 = 0.833**이었다.

가설: `process.parent_name`에는 `ccmexec.exe` 등 정상 관리 프로그램 정보가 있어도, `src/soc/telemetry/tools.py`의 `summarize()`가 이를 에이전트에 전달하지 않아 오판이 발생한다.

## 수정

- `src/soc/telemetry/tools.py`: `summarize()` 반환 객체에 `parent_name` 필드 추가.
- 기존 `event_id`, `cmdline` 120자 제한은 그대로 유지.
- `tests/test_telemetry_tools.py`: 부모 프로세스 보존/명령줄 길이/이벤트 ID 확인 테스트 추가.
- CI: `a8dc79a` 커밋에 대한 GitHub Actions 테스트·빌드·GHCR 게시 성공.

## 평가 방식

`infra/k8s/63-agent-advanced-eval.yaml`의 두 격리된 Job에서 **동일 `seed=42`, `n=12`** 평가.

- 전: `ghcr.io/heyun17/edr-ai-triage-lab-team4:cd273e8`
- 후: `ghcr.io/heyun17/edr-ai-triage-lab-team4:a8dc79a`
- `BACKEND=memory`, `TELEMETRY_TOOLS=real`, `KB_TOOLS=mock`, `FAKE_LLM=true`. 실 운영 OpenSearch 인덱스에 이벤트를 기록하지 않는다.

| 지표 | 기존 | 수정 후 | 비교 |
|---|---:|---:|---|
| 정확도 | 0.833 (10/12) | **1.000 (12/12)** | **+0.167 (약 16.7%p)** |
| 오판 | 2건 | **0건** | -2건 |
| 지어낸 근거 비율 | 0.000 | 0.000 | 동일 |
| 승인 요청 비율 | 0.667 | 0.667 | 동일 |
| 평균 응답 속도 | 0.05초 | 0.05초 | 동일 |
| 최대 응답 속도 | 0.08초 | 0.07초 | 0.01초 단축 |
| 알림당 비용(추정) | $0.00052 | $0.00055 | 약 5.8% 증가 |

오판 2건 모두 `it_inventory_script`였다. 수정 후 12건 모두 정답. 출력된 점수는 **FakeLLM + 합성 알림 12건**에 한정되며 실제 LLM의 정확도가 100%라는 뜻이 아니다. 비용도 실제 청구 비용이 아닌 계산된 추정치다.

## 서버 반영 상태

- 평가 Job의 새 이미지 `a8dc79a` 실행 및 점수 확인: **완료**
- 상시 실행 중인 Worker Deployment에 새 이미지 배포·롤백 가능 여부: **별도 확인 필요** (평가 Job 실행과 운영 Worker 배포는 다른 작업)

## 설명할 수 있어야 할 점

- **왜 부모 이름이 중요한가?** 동일한 PowerShell 실행도 `ccmexec.exe` 등 IT 관리 프로세스에서 시작된 경우 정상 업무 가능성을 판단하는 단서가 된다.
- **보안상 주의:** 정상 도구가 부모라고 해서 모든 자식 행위가 안전한 것은 아니다. 실제 운영에서는 서명·명령줄·이벤트 연쇄 등을 함께 확인해야 한다.
- **남은 과제:** 실제 LLM/더 큰 독립 데이터셋으로 정확도·오탐률 재평가.
