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
