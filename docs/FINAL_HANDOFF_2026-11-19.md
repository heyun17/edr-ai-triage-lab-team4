# 팀4 EDR AI Triage — 강사 확인용 Day1~Day3 최종 인계

작성일: 2026-11-19. 가상 EDR·실습용 문서 사용. 실습자가 제시한 출력과 저장소 기록에 근거하며 강사의 검증을 대신하지 않는다.

## 1. 강사가 확인할 핵심 자료

| 확인 | 위치 | 실습 결과 |
| --- | --- | --- |
| Day1 보안 기록·도구 | [Day1 티치백](teachback/day1.md), [tools.py](../src/soc/telemetry/tools.py), [CONTRACT](CONTRACT.md) | 가상 보안 로그 3,161건, 조사 도구 3개, 테스트 8 passed |
| Day1 그래프 | [ARCHITECTURE](ARCHITECTURE.md), [graph.py](../src/soc/agent/graph.py) | State·Node·Edge / Mermaid·테스트 |
| Day2 인프라 | [CAPACITY](CAPACITY.md), [k8s 매니페스트](../infra/k8s), [RUNBOOK](RUNBOOK.md) | Ubuntu/k3s, OpenSearch·Postgres, API·Worker·Generator, Service·Ingress |
| Day2 승인·티치백 | [Day2 티치백](teachback/day2.md), [nodes.py](../src/soc/agent/nodes.py) | PostgreSQL 체크포인트, 사람 승인·거절, 1인 대체 기록 |
| Day3 CI/CD | [GitHub Actions](../.github/workflows/build-ghcr.yml), [배포 가이드](DEPLOYMENT.md) | 테스트/이미지 빌드/ GHCR 푸시 성공, 수동 Kubernetes 배포·롤백 |
| D3-5 기록 맥락 고도화 | [parent_name](advanced/parent_name.md) | FakeLLM 12건 10/12→12/12, Worker 롤아웃 |
| D3-6 스캔 PDF OCR 고도화 | [ocr_pdf_06](advanced/ocr_pdf_06.md) | Hybrid Recall@3 18/21→19/21, Keyword 19/21→20/21 |
| D3-1·2 필수 깨 보기 | [RUNBOOK 6-1·7-1](RUNBOOK.md) | OpenSearch URL 오타 실패·복구, 깨진 이미지 새 파드 Error→롤백 |
| Dify | [Dify 기록](advanced/dify.md) | 백엔드 내부 403/200·PDF 3개 성공, Cloud UI 연결 미완료 |
| 개인 고장 예상표 | [Day3 고장 기록](advanced/day3_failure_predictions.md) | 예상·실제 비교/다음에 칠 명령 |
| 회고 | [POSTMORTEM](POSTMORTEM.md) | Day2 HTTP 503 Service selector 오타 5 Whys |
| 개인 Notion | [Day1~Day3 최종 개인 정리](https://app.notion.com/p/41dbfc520588812da31cc9296640e430) | 4조 기록 담당 개인 노트 하위 페이지 |

## 2. 작업 범위와 체크 시 주의

| 항목 | 관찰된 개인 실습 | 원 교안의 남은 조건 |
| --- | --- | --- |
| Day1 | 도구 계약, 실제 가상 로그 조회, 파싱·RAG·그래프 공동 기록, 티치백 | 팀원 개별 구현을 본인의 단독 개발로 주장하지 않음 |
| Day2 | 가드레일·승인·Postgres 체크포인트, k3s 인프라와 장애 대응 | 2인 티치백 미실시(1인 대체), OpenSearch 2-1 동일 장애 미재현 |
| D3-1·D3-2 | PDF Job/CI와 격리된 6-1·7-1 장애 재현·복구 | 2인 출제·교차 진단·나눔 미실시, 운영 리소스에는 장애 미주입 |
| D3-3 | Dify External Knowledge API 구현, 인증·실제 OpenSearch 내부 스모크 테스트 성공 | Dify Cloud 등록 실패, 챗봇 vs 자체 에이전트 답변 비교 미실시 |
| D3-4~6 | 본인(🔍) parent_name, 상대 영역(📘) OCR 두 고도화 실습 | 팀 합계 4개 선정·원래 담당자 코드 리뷰·동의 미실시 |
| D3-7 | 이전 단계 필수 장애 2건은 실습 | 단계 미공개/역할 교체 2인 종합 드릴 미실시 |
| D3-8 | 12건 FakeLLM 에이전트 평가, 21문항 RAG 재평가 | 실제 LLM·운영 RAG E2E·독립 질문셋 미검증 |
| D3-9·D3-10 | 개인 수치 해석·고장 예상표 문서 작성 | 2인 숫자 해석 나눔은 미실시 |
| D3-11·12 | DEPLOYMENT·POSTMORTEM 작성 | 옆 팀 배포 검증과 2인 회고 검토 미실시 |
| D3-13 | 기술 설명/발표 참고 자료 작성 | 팀 발표·시연 미실시 |

**완료 체크 규칙:** 학생 실습 체크는 개인 수행 사실에 맞추고, 강사 확인란은 강사가 직접 검증한 뒤 표시한다. 팀원 리뷰·합의는 미실시인 경우 빈칸을 유지한다.

## 3. 최종 수치와 정확한 해석

| 지표 | 기준점 | OCR/도구 고도화 후 | 조건 |
| --- | --- | --- | --- |
| Keyword Recall@3 | 19/21 (90.5%) | 20/21 (95.2%) | OCR 실험 KB |
| Vector Recall@3 | 18/21 (85.7%) | 19/21 (90.5%) | OCR 실험 KB |
| Hybrid Recall@3 | 18/21 (85.7%) | 19/21 (90.5%) | OCR 실험 KB, 기존 RRF |
| FakeLLM 판정 정확도 | 10/12 (83.3%) | 12/12 (100%) | 동일 가상 12건 |
| FakeLLM 알림당 추정 비용 | $0.00052 | $0.00055 | 테스트 가정, 실비 아님 |

- 06번 스캔 PDF의 OCR 정답 문구 ‘세 번’을 실제 청크에서 확인했고, 세 가지 검색 방식 모두 k10의 정답 PDF가 Top3에 들어왔다.
- Recall@3는 **정답 문서 포함 비율**이지 전체 정답 생성 정확도가 아니다.
- OCR 보정은 별도 26청크 실험 인덱스의 PDF06 **1개 청크 수동 갱신**이다. 운영 25청크 KB 및 전체 ingest 소스의 영구 변경과 다르다.
- FakeLLM 100%는 **합성 12건의 회귀 평가**, 상용 AI 판정 정확도와 무관하다.
- 기존 21문항 반복 평가로 가중치 등을 탐색했으므로 독립 평가셋에서 일반화 검증이 필요하다.

## 4. 서버 마지막 검증과 미완료 보안 정리

장애 실습 리소스 삭제 후 확인된 상태: api / generator / worker Deployment 각각 **1/1**, API **ready:true, opensearch:true, postgres:true**.

이후 Dify를 위해 별도 soc-dify-kb와 공개 Quick Tunnel을 배포했으나 **사용자가 실제로 제거한 로그는 아직 없다.** Dify 인증키가 채팅에 노출되었으므로 재사용하지 않고 키와 외부 노출을 중단해야 한다. **아래는 미완료 확인 대상**이다.

- Kubernetes soc namespace의 임시 soc-dify-https-tunnel Deployment 삭제
- soc-dify-kb Deployment·Service 삭제
- 노출된 soc-dify-key Secret 삭제 또는 인증키 교체
- 수업 종료 후 서버 보존/삭제는 강사 지침 확인. 삭제한 것으로 가정하지 않음
- 실제 운영 API의 인증·TLS·방화벽은 별도 검증 필요

## 5. 취업/포트폴리오에 쓸 수 있는 정직한 표현

Ubuntu k3s 환경에서 API·Worker·Generator 및 OpenSearch·PostgreSQL을 구성하고, GitHub Actions 테스트/이미지 푸시 후 Kubernetes 수동 롤아웃·롤백을 검증했다. OpenSearch 접속 URL 오타, 신규 컨테이너 즉시 종료, Service selector 불일치를 격리 실습으로 재현하고 Pod 상태·로그·EndpointSlice·헬스체크로 진단 및 정상화했다. 실제 MSP 고객 운영이 아닌 가상 EDR 서비스 운영 실습임을 명시한다.

[프로젝트 README](../README.md) · [배포 가이드](DEPLOYMENT.md) · [MSP 포트폴리오용 요약](PORTFOLIO_MSP_CLOUD_OPERATIONS.md)
