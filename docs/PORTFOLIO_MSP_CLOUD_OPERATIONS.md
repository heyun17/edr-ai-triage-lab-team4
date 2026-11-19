# MSP 클라우드 운영 엔지니어 지원용 프로젝트 기술서

> 작성 대상: 🔍 기록 담당의 **개인 수행/검증 범위**. 팀4의 EDR AI Triage 3일 실습으로, 실제 고객 서비스나 현업 운영 경력이 아니다. 포트폴리오·이력서로 옮길 때 반드시 **실습 프로젝트**라고 표기한다.

## 1. 프로젝트 개요

**프로젝트명:** Kubernetes 기반 EDR AI 트리아지 서비스 구축·운영 실습

**수행 기간:** 2026-11-17 ~ 2026-11-19 (3일 실습)

**프로젝트 형태:** 팀 4조 과제, 후반 Day2·Day3의 일부 고도화·장애 실습은 기록 담당 1인 진행.

**목적:** 가상의 PC 보안 알림을 수집·조사하고, 플레이북 검색과 사람 승인을 거쳐 대응 리포트를 만드는 서비스를 구성한다. 단순한 기능 개발보다 **클라우드 인프라 배포·서비스 가용성 확인·장애 대응·배포/복구 경험**을 MSP 직무 관점에서 강조한다.

### 기술 환경

| 계층 | 기술 | 사용 목적 |
| --- | --- | --- |
| 서버/OS | 가비아 가상 서버, Ubuntu 24.04 (4 vCPU / 16GB RAM / 50GB) | 실습용 Linux 서버 |
| 컨테이너/오케스트레이션 | Docker, k3s Kubernetes | 서비스 분리·배포·상태 확인 |
| 앱 | Python, FastAPI, Worker, Generator | 알림 API·비동기 처리·테스트 이벤트 |
| 데이터 계층 | OpenSearch, PostgreSQL, Kubernetes PVC | 로그·RAG 지식 검색, 승인 상태 영속화 |
| 배포 자동화 | GitHub Actions, GHCR | CI 테스트·이미지 빌드·레지스트리 푸시 |
| AI/검색 | LangGraph, OpenAI Embeddings, BM25/Vector/RRF | 조사·판정 실습, 플레이북 검색 |
| 운영 검증 | kubectl, Pod/Job/Deployment 로그, healthz/readyz | 장애 원인 분석·복구 확인 |

> **자동화 범위:** GitHub Actions에서 테스트·이미지 빌드·푸시를 자동 수행했다. Kubernetes 반영은 수동 set image / rollout status / rollout undo로 수행했다. GitHub → 실서버 무인 CD라고 기재하지 않는다.

## 2. 인프라 구성과 담당 역할

### 전체 서비스 흐름

~~~text
Simulator/Generator → OpenSearch (보안 이벤트/알림)
                                   ↓
                  Worker + LangGraph (조사→판정→가드레일→권고)
                                   ↓
             PostgreSQL Checkpointer (승인 대기·재개)
                                   ↓
           FastAPI (조회/사람 승인) → 대응 리포트

Knowledge PDF → Parse/Chunk/Embed → OpenSearch KB → RAG Tool
CI: GitHub → Actions 테스트/이미지 빌드 → GHCR → 수동 k3s 배포/롤백
~~~

**개인 참여/검증**
- 조사 도구 3개와 인덱스 매핑: host와 pid를 함께 조회해 PC 간 로그를 혼합하지 않고, event_id를 유지해 AI 판정 근거의 원본 조회가 가능하도록 설계했다.
- 인프라: Ubuntu/k3s에서 OpenSearch·PostgreSQL 및 API/Worker/Generator Deployment, Service·Ingress와 PVC 구성을 적용·검증했다.
- 운영: Pod 상태, readiness, OpenSearch·PostgreSQL 연결을 확인하고 장애를 주입·복구했다.
- Day3 고도화: 도구 요약의 parent_name 정보 보존과 OCR 실험 인덱스 보완을 각각 수치로 비교했다.

**팀 공동 범위:** RAG PDF 파싱/청킹·검색 및 Graph 설계는 팀 프로젝트 범위다. 원래 문서 담당자의 작업을 개인 단독 구현 성과로 기재하지 않는다.

## 3. 실무 관련 사례 — 장애 대응 3건

### 사례 ① Kubernetes Service selector 오류로 API 503

**증상:** 외부 /healthz 요청 시 HTTP **503 Service Unavailable**, 응답 본문 **no available server**.

**확인:** Kubernetes Service의 selector가 app:apii인 반면 실제 Pod 라벨은 app:api여서 트래픽을 받을 Endpoint가 없었다. EndpointSlice로 연결 대상 부재 확인.

**조치/결과:** selector를 app:api로 원복하고 EndpointSlice 복구·외부 HTTP **200** 확인.

**배운 점:** Pod Running만으로 서비스 정상이라고 판단할 수 없다. Service selector, EndpointSlice, Ingress, 최종 HTTP 응답을 순서대로 점검해야 한다.

**근거:** [RUNBOOK](RUNBOOK.md) / [POSTMORTEM](POSTMORTEM.md).

### 사례 ② OpenSearch 주소 오타로 Kubernetes Job 실패

**증상:** PDF 적재 경로와 동일한 연결을 시험하는 격리 Job의 OpenSearch 연결 확인이 False, Job Failed.

**확인:** OPENSEARCH_URL에 opensearhc:9200 오타가 있었다.

**조치/결과:** 올바른 opensearch:9200 주소로 독립 복구 Job을 실행해 Complete 및 연결 True 확인. 원본 KB 인덱스는 변경하지 않았다.

**배운 점:** Job은 Deployment와 달리 완료/실패 여부와 실행 로그를 같이 확인해야 한다.

### 사례 ③ 깨진 신규 컨테이너 배포 후 무중단 롤백

**증상:** 배포 테스트용 새 파드가 0/1 Error, 이전 정상 파드는 1/1 Running.

**확인:** 신규 컨테이너는 의도적으로 exit 1. 실패한 파드 이전 로그에 의도적 Crash 메시지가 남았다.

**조치/결과:** maxUnavailable=0 정책으로 구버전이 계속 서비스 응답을 제공. rollout undo 후 정상 단일 파드 1/1 및 /healthz 정상 응답 확인. 테스트용 Deployment/Service는 실습 뒤 삭제했다.

**배운 점:** Kubernetes RollingUpdate + Readiness 정책과 롤백은 서비스 중단을 줄이는 기본 운영 수단이다.

> 세 사례는 **의도적으로 만든 격리 실습 환경 장애**다. 실제 고객 영향, 장애시간(MTTR), SLA 성과를 임의 기재하지 않는다.

## 4. 보조 역량 — AI·RAG 운영 평가

| 개선 | 기존 | 변경 후 | 해석 |
| --- | --- | --- | --- |
| 조사 요약 parent_name 정보 보존 | 10/12 | 12/12 | **FakeLLM 합성 12건**에서 정상 업무 스크립트 2건 오판 감소 |
| PDF06 직접 Tesseract OCR·재임베딩 | Hybrid Recall@3 18/21 | 19/21 | **실험 인덱스**에서 스캔 문서 검색 개선 |
| Keyword Recall@3 | 19/21 | 20/21 | OCR로 검색 가능해진 정답 PDF가 Top3에 포함 |

정확도 100%는 실제 LLM의 성능이 아니다. Recall@3은 답변 내용의 정확도가 아니라 정답 **문서 검색 성공** 지표다.

## 5. 이력서에 바로 쓸 수 있는 경험 문장

**프로젝트 한 줄**

> Ubuntu k3s 환경에서 OpenSearch·PostgreSQL과 FastAPI/Worker 기반 서비스를 구성하고, CI 이미지 배포·롤백 및 Kubernetes 장애 주입·복구를 수행한 클라우드 운영 실습.

**담당 업무**
- Linux/k3s 기반 보안 알림 처리 서비스의 Deployment·StatefulSet·Service·PVC 상태 확인 및 OpenSearch·PostgreSQL 연결 검증
- GitHub Actions 자동 테스트/컨테이너 빌드/GHCR 푸시 결과 확인 후 수동 Kubernetes 롤아웃·롤백 수행
- Service selector 불일치(HTTP 503), OpenSearch 연결 오타(Job Failed), 신규 컨테이너 Crash(Error) 문제를 로그·EndpointSlice·헬스체크로 진단하고 복구
- 조사 도구의 이벤트 ID·프로세스 부모 정보 보존 및 합성 테스트 평가 개선

**면접에서 질문을 받으면**

Q. CI/CD 자동화는 어디까지 했나요?  
A. GitHub Actions에서 테스트와 이미지 빌드·GHCR 업로드가 자동화됐고, Kubernetes 이미지 반영과 롤백은 수동으로 실행했습니다. 자동화 범위를 구분해서 설명할 수 있습니다.

Q. Pod가 Running인데 서비스가 안 되면 어디부터 보나요?  
A. Deployment/Pod와 Readiness를 보고 Service selector → EndpointSlice → Ingress → 실제 HTTP 응답 순서로 확인합니다. 실습에서는 잘못된 selector 때문에 503이 발생했고 복구 후 200을 검증했습니다.

Q. AI 판정 정확도 100%인가요?  
A. 실서비스가 아니라 합성 알림 12건과 FakeLLM에서 10/12→12/12로 개선된 회귀 테스트입니다. 실제 LLM 성능이라고 쓰지는 않습니다.

Q. OpenSearch나 Postgres를 운영해봤나요?  
A. 실습 서버에 Kubernetes StatefulSet/PVC로 구성하고, 준비 상태·연결 오류·체크포인트 복원을 검증한 경험이 있습니다. 다중 노드 고가용성/백업·재해복구 운영까지 경험했다고 주장하지 않습니다.

## 6. 확인 가능한 증거 링크

- [최종 강사 확인용 인계](FINAL_HANDOFF_2026-11-19.md)
- [GitHub Actions](../.github/workflows/build-ghcr.yml)
- [RUNBOOK 장애 대응](RUNBOOK.md)
- [배포 가이드](DEPLOYMENT.md)
- [용량 산정](CAPACITY.md)
- [프로세스 도구 코드](../src/soc/telemetry/tools.py)
- [Day3 parent_name 고도화](advanced/parent_name.md)
- [Day3 OCR 고도화](advanced/ocr_pdf_06.md)

**미완료 및 보안 주의:** 실습용 공개 HTTPS 터널과 Dify 전용 API/Secret 삭제 여부는 서버에서 확인 필요. 실제 고객 데이터, 실제 MSP 고용·운영 경력, Dify Cloud 앱 연결 성공, 완전 자동 CD, 무중단 SLA는 근거가 없으므로 포트폴리오에 넣지 않는다.
