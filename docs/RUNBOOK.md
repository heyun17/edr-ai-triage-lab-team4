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