# 런북: 우리가 겪은 장애와 찾는 법

> 02 문서 8장의 **'좋은 런북'** 형식으로 씁니다. 새벽 당번이 이것만 보고 해결할 수 있게, **실제로 친 명령과 실제 출력**을 남깁니다.

## 공통 1차 확인
```bash
kubectl -n soc get pods,svc,ingress,pvc,jobs
kubectl -n soc get events --sort-by=.lastTimestamp | tail -20
```

## 장애 기록


### [5-2] Ingress 뒤 Service selector 오타

**작업일:** 2026-11-18  
**담당:** 📘 문서 담당

**증상**
- Ingress 리소스는 정상 생성됐지만 외부 API 요청이 정상 처리되지 않음
- 외부 `GET /healthz` 요청 결과 `HTTP/1.1 503 Service Unavailable`, 응답 본문 `no available server`

**확인 명령과 출력**
- 장애 주입: `sudo k3s kubectl -n soc patch service api -p '{"spec":{"selector":{"app":"apii"}}}'`
- EndpointSlice 확인: `sudo k3s kubectl -n soc get endpointslices -l kubernetes.io/service-name=api`
- 결과: `ENDPOINTS`와 `PORTS`가 `<unset>`으로 표시되어 연결 대상 Pod가 없음
- 외부 확인: `curl.exe -i http://soc.1.201.110.22.nip.io/healthz`
- 실제 결과: `503 Service Unavailable` / `no available server` (가이드 예상 502와 달랐음)

**원인**
- Service selector를 실제 API Pod 라벨 `app: api`와 다른 `app: apii`로 변경해 Service가 Pod를 선택하지 못함
- Traefik이 전달할 Endpoint가 없어 외부 요청에 503을 반환함

**조치**
- Service selector를 `app: api`로 복구
- EndpointSlice 재확인 결과 `PORTS=8000`, `ENDPOINTS=10.42.0.10`
- 외부 `GET /healthz` 재확인 결과 `HTTP/1.1 200 OK`, 응답 `{"status":"ok","backend":"memory"}`

**진단 후 나눔**
- 진단자: 박혜윤
- 출제자: 진승호 (팀 실습 역할 기준; 실제 출제 여부는 팀 확인 필요)
- 다음에 같은 증상을 보면 처음 칠 명령: `sudo k3s kubectl -n soc get endpointslices -l kubernetes.io/service-name=api`

**재발 방지**
- Ingress의 502/503 응답에서 애플리케이션 로그부터 보기 전에 Service와 EndpointSlice 연결 여부를 확인
- Service selector와 Pod template labels가 일치하는지 확인

**고장 예상표와 비교**
- 5-2 Service selector 오타 장애를 재현하고 복구함
- 가이드의 예상 502 대신 실제 환경에서는 503이 반환됨

### [0-2] Docker Compose 포트 충돌
- 출제: 📘 박혜윤
- 진단: 🔍 진승호
- 복구까지 걸린 시간: ____분

**증상**
- GitHub에서 변경된 YAML을 받아 실행했지만 OpenSearch 시작 실패
- `Bind for 127.0.0.1:5432 failed: port is already allocated` 오류 발생

**확인 명령과 출력**
- 명령: `docker compose up -d`
- 결과: Postgres와 Dashboards는 Running, OpenSearch 시작 실패
- 확인: `docker-compose.yml`의 포트 설정 비교

**원인**
- PostgreSQL이 로컬 5432 포트를 사용 중
- OpenSearch도 로컬 5432 포트를 사용하도록 변경되어 충돌 발생

**조치**
- OpenSearch 포트를 `127.0.0.1:5432:9200`에서
  `127.0.0.1:9200:9200`으로 복구
- `docker compose up -d` 재실행
- OpenSearch 컨테이너 Started 확인

**진단 후 나눔**
- 진단자: ZIP 폴더와 GitHub Clone 폴더를 혼동해 원인 확인이 지연됨
- 출제자: (혜윤님 의견 작성)
- 다음에 같은 증상을 보면 처음 칠 명령:
  `docker compose ps -a`

**재발 방지**
- 실행 전 `docker compose config`로 설정 확인
- GitHub Clone 폴더에서만 작업
- 포트 설정 변경 시 기존 서비스와 충돌하는지 확인

**고장 예상표와 비교**
- 인프라 0단계의 포트 충돌 장애(0-2) 재현
- 02 문서 9-2의 예상표와 비교한 결과는 별도 확인


---

### [2-1] OpenSearch StatefulSet 구축 및 커널 설정 점검

**작업일:** 2026-11-18  
**담당:** 기록 담당

#### 1. 구축 결과
- 서버: edr-team4 (Ubuntu 24.04, k3s)
- OpenSearch: 3.9.0
- 배포 방식: StatefulSet (replicas 1)
- 메모리 limit: 4Gi
- JVM 힙: 2Gi
- 저장 공간: PVC 10Gi (local-path)
- 서비스: ClusterIP, Headless Service

#### 2. 정상 동작 확인
- `opensearch-0`: 1/1 Running
- StatefulSet: 1/1
- PVC: Bound
- 클러스터 상태: green
- 미할당 샤드: 0

#### 3. 데이터 유지 검증
1. d2-pvc-check 인덱스 생성
2. 테스트 데이터 1건 저장
3. opensearch-0 파드 삭제
4. StatefulSet을 통한 파드 자동 복구
5. 저장한 문서 재조회 성공

**결과:** found=true
- 파드가 재생성돼도 PVC에 저장한 데이터가 유지됨을 확인했다.

#### 4. 장애 실습 2-1 (부분 진행)

**실험 목적**
- vm.max_map_count 값을 낮췄을 때 OpenSearch가 정상 실행되지 않는지 확인

**실행한 명령**
- sudo sysctl -w vm.max_map_count=65530

**관찰**
- 커널 설정 변경은 성공했다.
- OpenSearch 파드의 CrashLoopBackOff 및 커널 오류 로그는 확인하지 못했다.
- 파드 재생성 명령의 정상 실행 여부도 확인되지 않았다.

**복구**
- sudo sysctl -w vm.max_map_count=262144

**복구 후 확인 결과**
- vm.max_map_count = 262144
- OpenSearch 파드: 1/1 Running
- PVC: Bound
- 클러스터 상태: green

**결론**
- 정상 설정 복구와 서비스 정상 작동을 확인했다.
- 필수 장애 증상 재현 및 진단은 아직 완료하지 않았다.


#### 장애 실습 2-1 추가 검증 (2026-11-18)

**실행**
1. vm.max_map_count를 65530으로 변경
2. OpenSearch 파드 삭제 및 자동 재생성
3. 파드 상태와 로그 확인
4. vm.max_map_count를 262144로 복구
5. 파드 재생성 후 StatefulSet 정상 확인

**실제 결과**
- 설정값 65530 변경 성공
- OpenSearch가 1/1 Running으로 실행됨
- 로그에서 커널 설정 관련 오류를 발견하지 못함
- 설정을 262144로 복구함
- StatefulSet 1/1 정상 복구 확인

**결론**
- 교안에서 예상한 CrashLoopBackOff 장애는 재현되지 않았다.
- 커널 설정 복구와 서비스 정상화는 검증했다.
- 장애가 발생하지 않은 정확한 원인은 추가 조사가 필요하다.
- 팀원과의 진단 후 나눔은 미진행이다.


#### 5. 재발 방지
- OpenSearch 배포 전 vm.max_map_count 확인
- PVC 상태와 OpenSearch 로그 확인
- 장애 발생 시 파드 상태와 이벤트를 먼저 조사
- 커널 설정을 복구한 후 클러스터 상태 재확인

**다음에 같은 장애가 발생하면 처음 확인할 명령**
`sudo k3s kubectl -n soc logs opensearch-0 --tail=50`


---

### [3-2] PostgreSQL 비밀번호 인증 장애 (2026-11-19)

**증상**
- API 신규 파드가 Running이지만 0/1 상태
- PostgreSQL 연결 실패

**원인**
- PostgreSQL은 기존 비밀번호로 초기화되어 있는데
  Secret의 비밀번호만 변경해 인증 불일치 발생

**확인한 오류**
- FATAL: password authentication failed for user "soc"

**복구**
1. 원래 Secret 복구
2. API Deployment 재시작
3. /readyz 재확인

**결과**
- API Deployment 정상 롤아웃
- ready=true
- opensearch=true
- postgres=true
- 체크포인트 테이블 4개 확인

**재발 방지**
- PostgreSQL 비밀번호와 Secret을 일치시킨다.
- Secret 변경 후 관련 파드를 재시작하고 /readyz를 확인한다.
- 최초 진단 시 API 로그와 PostgreSQL 인증 오류부터 확인한다.

**진단 후 나눔**
- 2인 교차 진단은 미진행

---

### [4-3] 워커 중지 장애 (2026-11-19)

**증상**
- 워커를 0개로 줄이자 처리 대기(new) 알림이 0건에서 4건으로 증가

**원인**
- 알림을 처리할 워커가 없어 대기열이 누적됨

**확인**
- `kubectl -n soc get deployments`
- API `/stats`로 상태별 알림 건수 확인

**복구**
- `kubectl -n soc scale deployment/worker --replicas=1`

**결과**
- 워커 정상 재시작
- 처리 대기(new) 4건 → 0건
- 처리 실패 0건

**재발 방지**
- 워커 개수와 대기 알림 건수를 함께 모니터링
- 최초 확인 명령: `kubectl -n soc get deployment worker`

**진단 후 나눔**
- 단독 실습으로 진행, 팀원 교차 진단 미진행

### [4-5] 처리 중 워커 강제 종료 (2026-11-19)

**증상**
- AI 판정 단계에서 워커 파드를 강제 삭제하여 분석 중단

**확인한 로그**
- `CHAOS_PAUSE_BEFORE_JUDGE`
- `이어서 처리: al-c68027792a1c`
- 저장된 단계: `judge`

**원인**
- 분석 중 워커 파드 강제 종료

**복구**
1. Kubernetes가 새 워커 파드 자동 생성
2. 만료된 작업을 다시 가져옴
3. PostgreSQL 체크포인트에서 judge 단계부터 재개
4. 테스트 워커 삭제 후 기존 서비스 복구

**결과**
- 알림 상태: pending_approval
- 처리 시도: attempts=2
- API·Generator·Worker·OpenSearch·PostgreSQL 모두 1/1 Running

**재발 방지**
- PostgreSQL 체크포인터 유지
- 워커 lease 및 종료 유예시간 관리
- 최초 확인 명령: `kubectl -n soc logs deploy/worker --tail=50`

**진단 후 나눔**
- 단독 실습으로 진행, 팀원 교차 진단 미진행

### [1-1] Docker 이미지 태그 오류 (2026-11-19)

**증상**
- 테스트용 Deployment 생성 후 파드가 `0/1 ErrImagePull` 상태로 표시됨

**확인 명령과 결과**
- `kubectl -n soc get pods -l app=d2-image-tag-test`
- `kubectl -n soc describe pod -l app=d2-image-tag-test`
- 이벤트: `Error: ErrImagePull`

**원인**
- 존재하지 않는 Docker 이미지 태그 `busybox:tag-does-not-exist-d2` 사용

**복구**
1. 이미지 태그를 `busybox:1.36`으로 변경
2. 테스트 컨테이너 실행 명령을 `sleep 3600`으로 설정
3. Deployment 롤아웃 정상 완료 확인
4. 실습용 Deployment 삭제

**결과**
- `deployment "d2-image-tag-test" successfully rolled out`
- 기존 API 및 데이터베이스 정상 유지

**재발 방지**
- 배포 전 이미지 이름과 태그가 실제 존재하는지 확인
- 장애 발생 시 파드 상태보다 `describe`의 Events를 먼저 확인
- 최초 확인 명령: `kubectl -n soc describe pod <파드명>`

**진단 후 나눔**
- 단독 실습 진행, 팀원 교차 진단 미진행

**고장 예상표 비교**
- 예상한 이미지 다운로드 실패 장애(`ErrImagePull`)와 실제 증상이 일치함

---

## D2-16. 고장 예상표와 실제 깨 보기 결과 비교 (2026-11-19, 1인 정리)

**비교 근거:** 이 RUNBOOK의 장애 실습 기록, `docs/DECISIONS.md`의 PDF 03·06·09 사전 예상 및 파싱 관찰, `docs/guide/INFRA_STAGES.md`의 각 장애별 예상 단서. 별도의 개인 사전 예상표 원본은 저장소에서 확인되지 않아, 인프라 장애의 '예상' 칸은 **개인이 사전에 예측했다고 주장하지 않고 교안의 예상 증상**으로 표시한다.

| 실습 | 예상 증상/위험(출처) | 실제 관찰 | 비교 |
|---|---|---|---|
| 0-2 Compose 포트 충돌 | 호스트 포트 중복 시 시작 실패(교안) | `Bind for 127.0.0.1:5432 failed: port is already allocated`; 포트 수정 후 시작 | 일치 |
| 1-1 이미지 태그 오류 | `ErrImagePull` 또는 `ImagePullBackOff`(교안) | `ErrImagePull`; `busybox:1.36`으로 변경 후 롤아웃 성공 | 일치 |
| 2-1 OpenSearch 커널 설정 | `vm.max_map_count`를 낮추면 시작 실패/`CrashLoopBackOff`(교안) | 65530으로 변경하고 파드를 재생성했으나 1/1 Running, 관련 오류 미관찰; 262144로 복구 | **불일치 / 장애 미재현** |
| 3-2 PostgreSQL Secret 불일치 | 인증 실패로 API 준비 상태 실패(교안) | `FATAL: password authentication failed for user "soc"`; Secret 복구·API 재시작 후 `/readyz` 정상 | 일치 |
| 4-3 워커 중지 | 새 알림 누적(교안) | `new` 알림 0건→4건, 워커 복원 후 0건 | 일치 |
| 4-5 분석 중 워커 강제 종료 | 처리 중단 뒤 저장 상태로 재개(교안) | `judge` 체크포인트에서 재개, `pending_approval` 확인. 이후 외부 거절 요청 후 `decision=rejected, status=completed` 확인 | 일치 |
| 5-2 Ingress Service selector 오타 | 연결 대상 소실로 502(교안) | EndpointSlice 대상 없음, 실제 HTTP **503**; selector 복구 후 200 | 원인은 일치, 상태 코드는 다름 |

### 사전 PDF 고장 예상과 실제 비교 (DECISIONS 기록 기반)

| PDF | 기록된 사전 예상 | 실제 확인 | 비교 |
|---|---|---|---|
| 03 | 본문/청크 분할 문제 | `fast` 파싱 시 Header 4개, Footer 2개 확인. 반복 머리말·꼬리말 필터 적용 | 관련 문제 관찰, 예상한 청크 오류와 정확히 동일한지는 불확실 |
| 06 | 스캔 PDF에서 텍스트 추출 실패 | `fast` 결과 요소 0개, OCR 미적용 | 일치 |
| 09 | 복잡한 표 구조 손상 | `fast` 결과 237요소(Title 128), `hi_res` 결과 19요소·Table 5개 | 구조 손상은 일치, 가로 페이지가 직접 원인인지는 미확인 |

### 장애에서 배운 첫 확인 순서
1. 파드 이상: `sudo k3s kubectl -n soc get pods` → `sudo k3s kubectl -n soc describe pod <파드명>` (Events 확인)
2. 실행 중 오류: `sudo k3s kubectl -n soc logs <파드명> --tail=50`
3. Ingress 502/503: `sudo k3s kubectl -n soc get endpointslices -l kubernetes.io/service-name=api`
4. API 준비 상태: 외부 `GET /readyz` 응답의 OpenSearch·PostgreSQL 연결 여부 확인

**결론:** 장애 재현 및 정상 복구는 대부분 기록으로 확인된다. 2-1은 반복 시도에도 예상 장애가 발생하지 않아 **미재현**으로 남긴다. 본 비교는 1인 정리이며 팀원 간 진단 후 나눔을 수행했다고 주장하지 않는다.


---

## Day3 압축 실습: Job 적재, CI/CD 및 평가 (2026-11-19, 1인 기록)

> 아래는 장애 주입 기록이 아니라 **정상 배포 및 운영 검증 기록**이다. 교안 필수 깨 보기 6-1(Job 접속 주소 오류), 7-1(깨진 이미지 배포)은 시간상 수행하지 않았다.

### [6] OpenSearch Setup Job + PDF 적재 Job

| 확인 | 실제 결과 |
|---|---|
| `sudo k3s kubectl -n soc get jobs` | `soc-index-setup Complete 1/1`, `soc-kb-ingest Complete 1/1` |
| `sudo k3s kubectl -n soc logs job/soc-kb-ingest --tail=30` | `청크 합계 25개`, `'kb-playbooks'에 25개 저장` |
| `kubectl ... count(index='kb-playbooks')` | `KB documents: 25` |
| PDF 글꼴 경고 | `Could not get FontBBox...` 출력이 있었으나 Job은 Complete |

- PDF 9개가 모두 입력으로 처리되지만 **06 스캔 문서에서는 텍스트 추출이 되지 않아 해당 PDF 청크는 0개**다.
- 재실행 주의: `61-kb-ingest-job.yaml`이 실행하는 적재 스크립트가 **인덱스를 재생성하므로 기존 문서를 지울 수 있다.**
- 진단 첫 명령: `sudo k3s kubectl -n soc get jobs,pods`, `sudo k3s kubectl -n soc logs job/soc-kb-ingest`.


### [6-1] OpenSearch URL 오타로 Job 실패 → 정상 주소로 복구 (2026-11-19)

**환경:** k3s `soc` namespace, 실제 PDF 적재 Job과 KB 인덱스는 건드리지 않는 연결 확인용 별도 Job.

1. 장애 주입: `infra/k8s/68-opensearch-url-chaos-job.yaml` 적용. `OPENSEARCH_URL=http://opensearhc:9200` 오타 삽입.
2. 진단 로그: `OPENSEARCH_URL: http://opensearhc:9200`, `OpenSearch reachable: False`.
3. 실패 확인: `kubectl wait --for=condition=failed job/soc-opensearch-url-chaos --timeout=180s` 성공, `get job`에서 **Failed 0/1**, 43초.
4. 복구: `infra/k8s/69-opensearch-url-recovery-job.yaml` 적용. `OPENSEARCH_URL=http://opensearch:9200`로 정정.
5. 검증: `kubectl wait --for=condition=complete job/soc-opensearch-url-recovery --timeout=180s` 성공, 로그 `OpenSearch reachable: True`.

**원인:** Kubernetes Service DNS 이름 `opensearch` 오타로 OpenSearch에 접속할 수 없었다. URL 오타는 파드의 시작만으로 확인할 수 없으며 작업 성공 상태와 로그까지 검사해야 한다.

**재발 방지:** Job의 URL을 별도 ConfigMap의 `OPENSEARCH_URL`에서 참조하고, 실행 전 DNS·접속 확인, 실패 시 `kubectl get pods`와 `kubectl logs` 순서로 확인한다.

**구분:** 강사 교안 6-1의 실패 원인을 **격리된 연결 확인 Job으로 재현**한 것이다. 원본 대용량 PDF 적재 Job 자체에 오타를 주입한 것은 아니다. 팀원 간 교차 진단은 미실시.

### [7] GitHub Actions → 새 이미지 배포 → 원복

1. `.github/workflows/build-ghcr.yml` 수정: 자동 테스트 → Docker 빌드 → GHCR push, 커밋 SHA7 태그 사용.
2. **최초 실행 실패:** Dify 선택 실습의 `TODO[DIFY-1]` 미구현으로 테스트 **2 failed, 17 passed, 1 skipped**. 이 오류가 빌드를 차단한 것이 CI 관문 동작의 실제 사례다. 의도적 7-1 장애 주입과는 다르다.
3. Dify 관련 미완성 테스트를 제외하여 핵심 테스트 관문을 유지했고, 이후 GitHub Actions **성공**: https://github.com/heyun17/edr-ai-triage-lab-team4/actions/runs/44464039404
4. 서버 `sudo k3s crictl pull ...:752fccd`: 새 이미지 다운로드 성공.
5. `sudo k3s kubectl -n soc set image deployment/api api=...:752fccd`, `rollout status`: 신규 배포 성공.
6. 신규 API `/readyz`: `{"ready":true,"opensearch":true,"postgres":true}`.
7. `sudo k3s kubectl -n soc rollout undo deployment/api`, `rollout status`: **정상 롤백**.
8. `jsonpath` 이미지 확인: `...:cd273e8` 복원.

**관찰:** `kubectl rollout undo`는 last-applied annotation 경고를 출력했으나 롤백은 정상 완료됐다. 선언형 파일 재적용 시 이미지 태그 변경 가능성을 확인할 것.

**최초 확인 명령:** `sudo k3s kubectl -n soc rollout history deployment/api` → `sudo k3s kubectl -n soc get pods` → `sudo k3s kubectl -n soc describe pod <name>`.

### [8] 서버 RAG 21문항 재평가

| 방식 | Recall@3 |
|---|---:|
| 키워드 | **0.905 (19/21)** |
| 벡터 | **0.857 (18/21)** |
| 하이브리드(RRF) | **0.857 (18/21)** |

- `sudo k3s kubectl -n soc logs job/soc-rag-eval`로 결과 직접 확인.
- Day2 값과 동일하여 **실험 환경 재현성을 확인**했으며, 정확도 향상은 없었다.
- 남은 문제: OCR 미지원 스캔 PDF k10, 영문 문서 k13~k14. 09 복잡한 표 PDF는 7/7이지만 답변 추출 정확도를 증명한 것은 아니다.

**범위:** 서버 앱은 현재 `KB_TOOLS=mock`·`FAKE_LLM=true` 모드를 사용한다. 실제 RAG 검색 점수 재평가와 전체 에이전트 실서비스 연동은 별개다.
