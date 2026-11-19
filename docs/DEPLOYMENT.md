# Day3 배포 가이드 — EDR AI Triage (실습용, 2026-11-19)

> 작성: 1인 압축 실습 정리. **교안의 옆 팀 교차 검증은 미실시**. 기존 `edr-team4` Ubuntu + k3s 서버에서 직접 확인한 흐름을 기준으로 한다. 완전히 새 서버에 처음부터 설치하는 절차 전체는 재검증하지 않았다.
>
> **보안:** PDF와 텔레메트리는 실습용 가상 데이터. API/Ingress는 인증·TLS 등 운영 보안 구성이 검증되지 않았으므로 공용 서비스로 사용하지 않는다. 키, DSN, Secret 내용을 GitHub/화면/로그에 공개하지 않는다.

## 0. 준비물

- Ubuntu 서버, 관리자(SSH/sudo) 접근, k3s, 네트워크/방화벽 규칙
- 코드 저장소: https://github.com/heyun17/edr-ai-triage-lab-team4
- `soc` namespace, OpenSearch 3.9.0, PostgreSQL 16
- 앱 이미지 `ghcr.io/heyun17/edr-ai-triage-lab-team4:cd273e8` (검증된 복원 버전)
- 별도 PDF 처리 이미지 `ghcr.io/heyun17/edr-ai-triage-lab-team4:kb-day3-20261119` (k3s에 직접 import하여 사용)
- OpenAI API 키 및 데이터베이스 비밀번호. 유출된 키는 폐기·교체한다.

## 1. 서버·k3s 기본 점검

서버에서 현재 상태:
```bash
sudo k3s kubectl get nodes -o wide
sudo k3s kubectl -n soc get pods,svc,pvc,ingress,jobs
sudo sysctl vm.max_map_count
df -h /
```

초기 구성 참고: `infra/scripts/bootstrap.sh`는 방화벽/UFW, `vm.max_map_count=262144`, swap 해제 등을 설정한다. **서버 SSH 접속 IP를 정확히 확인한 뒤** 적용해야 한다. 실제 k3s 설치·새 서버 생성은 별도 초기 설치 절차를 따른다. 본 문서의 확인 명령은 기존 실습 서버에서 실행했다.

## 2. 네임스페이스·설정·Secret

```bash
sudo k3s kubectl apply -f infra/k8s/10-namespace.yaml
sudo k3s kubectl apply -f infra/k8s/31-config.yaml
sudo k3s kubectl -n soc get configmap soc-config
sudo k3s kubectl -n soc get secret soc-secrets soc-openai
```

- `soc-config`: `BACKEND=real`, `OPENSEARCH_URL=http://opensearch:9200`, `TELEMETRY_TOOLS=real`, `KB_TOOLS=mock`, `FAKE_LLM=true`, `CHECKPOINTER=postgres` (현재 서버 실습 모드).
- `soc-secrets`: 데이터베이스 연결에 필요한 `POSTGRES_PASSWORD`, `POSTGRES_DSN` 등을 실제 환경 값으로 **사전에 안전하게 생성**한다. `30-postgres.yaml`은 `POSTGRES_PASSWORD` 키에 의존하고 API/Worker는 `envFrom`으로 Secret을 읽는다.
- `soc-openai`: 별도 PDF 임베딩 Job용 Secret, `OPENAI_API_KEY` 키를 포함한다. 평가 Job에도 사용한다. **키 값·디코딩된 출력은 공유하지 않는다.**
- 두 Secret은 Git에 커밋하지 않는다. 이미 초기화된 PostgreSQL의 비밀번호와 Secret이 다른 경우 API는 인증 실패할 수 있다. Secret 변경만으로 기존 DB 비밀번호가 바뀌지 않는다.

## 3. 상태 저장 계층 (OpenSearch, PostgreSQL)

Secret/ConfigMap 준비 후:
```bash
sudo k3s kubectl apply -f infra/k8s/20-opensearch.yaml
sudo k3s kubectl apply -f infra/k8s/30-postgres.yaml
sudo k3s kubectl -n soc get statefulsets,pvc
sudo k3s kubectl -n soc rollout status statefulset/opensearch --timeout=300s
sudo k3s kubectl -n soc rollout status statefulset/postgres --timeout=300s
```
- OpenSearch `opensearch-0`: PVC 10Gi, JVM 2Gi, 메모리 제한 4Gi, 클러스터 확인 `/_cluster/health`.
- PostgreSQL `postgres-0`: PVC 5Gi, 포트 5432.
- 영속 데이터가 있어 삭제/재설치를 함부로 하지 않는다. Day2에서 OpenSearch 파드를 삭제·복구한 뒤 PVC 데이터 보존을 확인했다.

## 4. API·워커·생성기·Ingress

```bash
sudo k3s kubectl apply -f infra/k8s/11-api.yaml
sudo k3s kubectl apply -f infra/k8s/41-worker.yaml
sudo k3s kubectl apply -f infra/k8s/40-generator.yaml
sudo k3s kubectl apply -f infra/k8s/50-ingress.yaml
sudo k3s kubectl -n soc get deployments,pods,ingress
sudo k3s kubectl -n soc exec deployment/api -- python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/readyz').read().decode())"
```

실측 준비 상태: `{"ready":true,"opensearch":true,"postgres":true}`.

- API: `/healthz`(생존), `/readyz`(OpenSearch·PostgreSQL 준비)
- Worker: 알림 처리 및 PostgreSQL 체크포인트 복원
- Generator: 실습 알림 자동 생성
- Ingress: `http://soc.1.201.110.22.nip.io` (현재 예제 서버 주소, 접근 제어/인증 운영용 검증 전)
- Ingress 502/503이면 `sudo k3s kubectl -n soc get endpointslices -l kubernetes.io/service-name=api` 확인: Service selector와 API 파드 라벨이 맞아야 한다.

## 5. 일회성 Job — 인덱스 초기화·PDF 적재

```bash
sudo k3s kubectl apply -f infra/k8s/60-setup-job.yaml
sudo k3s kubectl -n soc wait --for=condition=complete job/soc-index-setup --timeout=180s
sudo k3s kubectl -n soc logs job/soc-index-setup
```

- PDF용 이미지 빌드: Windows 프로젝트 루트에서 `docker build -f Dockerfile.kb -t ghcr.io/heyun17/edr-ai-triage-lab-team4:kb-day3-20261119 .` 실행 후 `docker save` → `scp` → 서버 `sudo k3s ctr images import <tar 경로>`로 전송·등록한다. 현재 서버에서는 약 900MiB 이미지 등록에 성공했다.
- `soc-openai` Secret이 있어야 한다.
- **주의:** `61-kb-ingest-job.yaml`이 실행하는 `soc.kb.ingest`는 `ensure_index(recreate=True)`로 **기존 `kb-playbooks` 인덱스를 삭제하고 다시 만든다.** 기존 KB가 있는 서버에서는 백업/운영 영향 검토 없이 재실행하지 않는다.

```bash
sudo k3s kubectl apply -f infra/k8s/61-kb-ingest-job.yaml
sudo k3s kubectl -n soc wait --for=condition=complete job/soc-kb-ingest --timeout=900s
sudo k3s kubectl -n soc logs job/soc-kb-ingest --tail=25
sudo k3s kubectl -n soc exec deploy/api -- python -c "from soc.osclient import get_client; print('KB documents:', get_client().count(index='kb-playbooks')['count'])"
```

**실제 결과:** 인덱스 설정 Job Complete, 적재 Job Complete(76초), PDF 9종 처리, **25청크 저장/KB documents: 25**. 06번 스캔 PDF의 OCR 미적용으로 0청크이다.

## 6. RAG 검색 품질 평가 (21문항)

```bash
sudo k3s kubectl apply -f infra/k8s/62-rag-eval-job.yaml
sudo k3s kubectl -n soc logs job/soc-rag-eval
```

실측(Recall@3): 키워드 **0.905 (19/21)** / 벡터 **0.857 (18/21)** / 하이브리드 **0.857 (18/21)**. Day2와 동일하다. **RAG 평가 Job은 OpenAI 임베딩으로 조회하지만 앱 자체는 `KB_TOOLS=mock`, `FAKE_LLM=true` 모드이므로 엔드투엔드 실제 RAG 에이전트 연동을 완료했다고 해석하면 안 된다.**

## 7. GitHub Actions CI/CD, 수동 배포와 롤백

- 워크플로: `.github/workflows/build-ghcr.yml`; 자동 테스트 → Docker 빌드 → GHCR push, 이미지 태그는 커밋 SHA 앞 7자리. Dify 미구현 테스트는 선택 실습으로 제외, 나머지 테스트 필수.
- 검증 성공: https://github.com/heyun17/edr-ai-triage-lab-team4/actions/runs/44464039404
- 앱 이미지는 GHCR에 올라가지만 **서버의 `kubectl set image` 및 롤백은 수동 실행**했다. 'GitHub에서 서버까지 완전 자동 배포'라고 주장하지 않는다.

```bash
sudo k3s crictl pull ghcr.io/heyun17/edr-ai-triage-lab-team4:752fccd
sudo k3s kubectl -n soc set image deployment/api api=ghcr.io/heyun17/edr-ai-triage-lab-team4:752fccd
sudo k3s kubectl -n soc rollout status deployment/api --timeout=180s
sudo k3s kubectl -n soc exec deployment/api -- python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/readyz').read().decode())"
sudo k3s kubectl -n soc rollout undo deployment/api
sudo k3s kubectl -n soc rollout status deployment/api --timeout=180s
sudo k3s kubectl -n soc get deployment api -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'
```

**실제 결과:** `752fccd` 신규 배포·준비 상태 확인 성공, `rollout undo` 후 **`cd273e8` 복원**. `kubectl rollout undo`의 last-applied annotation 경고는 정상 롤백을 막지 않았다. 이후 `kubectl apply -f infra/k8s/11-api.yaml` 실행 시 manifest의 고정 이미지 `cd273e8`로 다시 바뀔 수 있음을 기억한다.

## 8. 장애 대응 첫 확인

```bash
sudo k3s kubectl -n soc get pods,svc,pvc,jobs
sudo k3s kubectl -n soc get events --sort-by=.lastTimestamp | tail -20
sudo k3s kubectl -n soc get endpointslices -l kubernetes.io/service-name=api
sudo k3s kubectl -n soc logs deployment/api --tail=50
```

이전 장애 및 복구 절차: [RUNBOOK.md](RUNBOOK.md). PostgreSQL 비밀번호 불일치(3-2), 워커 중단(4-3), 강제 종료 후 체크포인트 복구(4-5), Ingress selector 오타(5-2)를 참고한다.

## 검증·범위

| 항목 | 현재 상태 |
|---|---|
| 기존 실습 서버에서 PDF 적재 Job 및 25개 저장 | 확인 |
| GitHub Actions 테스트/빌드/푸시 및 API 롤백 | 확인 |
| 서버 RAG 21문항 Recall@3 | 확인 |
| 새로운 서버에서 문서만 보고 처음부터 설치 | **미검증** |
| 옆 팀 교차 검증 | **미실시** |
| 장애 주입 6-1·7-1, Dify 연동, 실서비스 RAG 에이전트 | **미실시/미검증** |
