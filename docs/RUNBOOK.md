# 런북: 우리가 겪은 장애와 찾는 법

> 02 문서 8장의 **'좋은 런북'** 형식으로 씁니다. 새벽 당번이 이것만 보고 해결할 수 있게, **실제로 친 명령과 실제 출력**을 남깁니다.

## 공통 1차 확인
```bash
kubectl -n soc get pods,svc,ingress,pvc,jobs
kubectl -n soc get events --sort-by=.lastTimestamp | tail -20
```

## 장애 기록

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

#### 5. 재발 방지
- OpenSearch 배포 전 vm.max_map_count 확인
- PVC 상태와 OpenSearch 로그 확인
- 장애 발생 시 파드 상태와 이벤트를 먼저 조사
- 커널 설정을 복구한 후 클러스터 상태 재확인

**다음에 같은 장애가 발생하면 처음 확인할 명령**
`sudo k3s kubectl -n soc logs opensearch-0 --tail=50`
