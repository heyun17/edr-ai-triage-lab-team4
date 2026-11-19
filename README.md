# EDR AI 트리아지 에이전트 실습 (2인 1조 · 3일)

> 모든 데이터와 문서는 실습용 가상 자료입니다.

## 읽는 순서

| 순서 | 문서 | 내용 |
|---|---|---|
| 1 | [`docs/prep/01_edr_soc_intro.md`](docs/prep/01_edr_soc_intro.md) | EDR과 보안관제 입문, 예시 알림, **역할 정하기** (🔍 기록 담당 / 📘 문서 담당) |
| 2 | [`docs/prep/01b_story_to_system.md`](docs/prep/01b_story_to_system.md) | 이야기를 부품으로, 고장 나는 곳 |
| 3 | [`docs/prep/02_troubleshooting.md`](docs/prep/02_troubleshooting.md) | 트러블슈팅 순서, 깨 보기, 런북, 고장 예상표 |
| 4 | [`docs/prep/03_references.md`](docs/prep/03_references.md) | 역할별 참고 링크 |
| 5 | [`docs/guide/00_overview.md`](docs/guide/00_overview.md) | 실습 안내: 역할, 작업 형태, 3일 흐름 |
| 6 | [`DAY1`](docs/guide/DAY1.md) · [`DAY2`](docs/guide/DAY2.md) · [`DAY3`](docs/guide/DAY3.md) | 일차별 따라하기 |
| 7 | [`docs/guide/INFRA_STAGES.md`](docs/guide/INFRA_STAGES.md) | 인프라 0~7단계: 직접 작성 + 깨 보기 |
| 8 | [`docs/guide/WORK_SPEC.md`](docs/guide/WORK_SPEC.md) | 작업 명세서: 사전 자료~3일차 체크리스트, 결과물, 완료 기준 |

## 자료

| 폴더 | 내용 | 주로 쓰는 사람 |
|---|---|---|
| [`data/telemetry/`](data/telemetry/) | 가상 회사 PC의 활동 기록 샘플 | 🔍 기록 담당 |
| [`data/kb/`](data/kb/README.md) | 대응 정책·플레이북 PDF 9종, RAG 평가 질문 21개 | 📘 문서 담당 |

## 팀 문서 (실습 중에 채움)

| 문서 | 언제 |
|---|---|
| `docs/CONTRACT.md` | 1일차: 도구 계약 |
| `docs/ARCHITECTURE.md` | 1일차: 에이전트 설계도 → 2일차: 배포 구성도 |
| `docs/DECISIONS.md` | 매일: 결정과 그 이유, 평가 점수 |
| `docs/RUNBOOK.md` | 깨 보기를 할 때마다 |
| `docs/CAPACITY.md` | 2일차: 인프라 2단계 전 |
| `docs/DEPLOYMENT.md`, `docs/POSTMORTEM.md` | 3일차 |
| `docs/teachback/` | 매일 마지막 |
| [`docs/PROGRESS_2026-11-17.md`](docs/PROGRESS_2026-11-17.md) | **팀4 Day1 완료 현황(11/17~18)·Day2 인계** |
| `docs/advanced/` | 3일차: 고도화 기록 |

## 최종 제출·검증 (팀4 / 2026-11-19)

- [강사 확인용 Day1~Day3 최종 인계](docs/FINAL_HANDOFF_2026-11-19.md) — **실제 수행·미완료 구분, 측정 수치, 확인 근거, 보안 정리 사항**
- [🔍 개인 노트: Day1~Day3 최종 정리](https://app.notion.com/p/41dbfc520588812da31cc9296640e430) — 학생 기록 담당의 개인 정리
- [MSP 클라우드 운영 포트폴리오용 기술서](docs/PORTFOLIO_MSP_CLOUD_OPERATIONS.md) — Kubernetes·CI/CD·장애 대응 중심
- [Day3 개인 티치백](docs/teachback/day3.md) — 팀원 상호 질의가 아닌 1인 발표 대비 자료
- [Day3 결정·최종 점수](docs/DECISIONS.md), [Runbook](docs/RUNBOOK.md), [Deployment](docs/DEPLOYMENT.md)

> 이 저장소의 실습 데이터는 가상 자료이며 고객 운영 환경이 아닙니다. Day3 고도화 2개와 격리 장애 실습은 개인 실습 범위에서 수행했고, Dify Cloud 연결·2인 종합 드릴·옆 팀 검증·팀 발표는 완료하지 않았습니다. 서버에 남은 임시 Dify 터널·키의 실제 제거 여부는 [최종 인계의 보안 점검](docs/FINAL_HANDOFF_2026-11-19.md)을 따로 확인해야 합니다.
