# 사후 회고 — Ingress Service selector 오타로 API 503 발생

> 2026-11-19 작성. 장애 자체는 2026-11-18 Day2 실습에서 **의도적으로 주입**했다. 가상 실습 환경에서 1인 기록한 비난 없는 회고다. 실제 고객 영향, 사고 소요 시간, 2인 교차 검증은 확인되지 않았다.

## 요약

- **무슨 일이 있었나:** Kubernetes Service `api`의 selector를 `app: api`에서 `app: apii`로 바꾸자 Ingress를 통한 `/healthz` 요청이 **HTTP 503 Service Unavailable**을 반환했다.
- **사용자 관찰 증상:** 외부 API에 접근할 수 없었고 응답 본문에 `no available server`가 표시됐다.
- **범위:** 실습용 `soc` namespace의 API 경로. 다른 실제 서비스·고객의 영향은 측정하거나 확인하지 않았다.
- **상태:** Service selector 복원 후 외부 `/healthz`가 **HTTP 200**으로 돌아왔다.
- **참고:** 원래 교안 예상 상태코드는 502였으나, 실제 Traefik 환경에서는 503이 관찰됐다. 원인은 같다.

## 사건 흐름 (기록에 있는 확인 사실)

1. **장애 주입:** `sudo k3s kubectl -n soc patch service api -p '{"spec":{"selector":{"app":"apii"}}}'`
2. **증상 발견:** 외부 `GET /healthz`에서 `503 Service Unavailable`, 본문 `no available server`.
3. **진단:** `sudo k3s kubectl -n soc get endpointslices -l kubernetes.io/service-name=api` 실행. EndpointSlice의 연결 가능한 대상 및 포트가 `<unset>`으로 표시됨.
4. **가설 검증:** Service가 `app: apii`를 요구하지만 실제 API Pod의 라벨은 `app: api`여서 선택된 파드가 없음을 확인.
5. **조치:** selector를 `app: api`로 복원.
6. **복구 확인:** EndpointSlice에 API 대상 포트 8000과 엔드포인트가 나타났고, 외부 요청이 **HTTP 200 OK**가 됨.

> 복구 소요 시간은 검증 가능한 기록이 없어 기재하지 않는다. 의도적 장애 실습이므로 실제 운영 사고로 과장하지 않는다.

## '왜?' 다섯 번 — 기술적 실패 경로

1. **왜 503이 발생했나?** Ingress가 연결할 수 있는 API 서비스 대상이 없었기 때문이다.
2. **왜 연결 대상이 없었나?** Service에 매칭되는 API Pod 엔드포인트가 생성되지 않았기 때문이다.
3. **왜 매칭되지 않았나?** Service selector 값 `app: apii`가 Pod의 실제 라벨 `app: api`와 달랐기 때문이다.
4. **왜 Kubernetes가 잘못된 설정을 허용했나?** Service selector는 유효한 형식이면 적용되지만, 선택 대상이 반드시 존재해야 한다고 강제하지 않기 때문이다.
5. **왜 문제를 즉시 사전에 차단하지 못했나?** 이 실습에서는 selector 변경 후 연결 가능한 EndpointSlice와 외부 응답을 자동으로 확인하는 검증 단계가 없었기 때문이다.

**근본 원인:** 의도적으로 주입한 Service-to-Pod 라벨 불일치. 일반화하면, **설정값이 문법적으로 올바르더라도 실제 트래픽 연결이 성립하는지는 별도로 검증해야 한다**는 문제다.

## 잘한 점

- Ingress가 503을 반환한다고 애플리케이션 내부 오류로 단정하지 않았다.
- `EndpointSlice`를 조회하여 Service와 Pod 간 연결이 끊긴 지점을 찾아냈다.
- selector 원복과 외부 HTTP 200을 **같이 확인**해 복구를 검증했다.

## 개선할 점 및 재발 방지

| 할 일 | 담당/상태 |
|---|---|
| Ingress 502/503 발생 시 Service → EndpointSlice → Pod 라벨 순으로 점검하는 절차 유지 | 1인 실습 / RUNBOOK 기록 완료 |
| Service selector와 Deployment `spec.template.metadata.labels` 일치 여부 배포 전 검토 | 후속 과제 |
| 배포 후 `/healthz`, `/readyz` 및 외부 라우팅 확인을 CI/CD 또는 운영 체크리스트에 연결 | 후속 과제 |
| 실제 운영 배포에서는 인증/TLS 및 장애 시 경보 체계 별도 설계 | 후속 과제 |

## 최초 진단 명령

```bash
sudo k3s kubectl -n soc get pods,svc,ingress
sudo k3s kubectl -n soc get endpointslices -l kubernetes.io/service-name=api
sudo k3s kubectl -n soc describe service api
```

관련 원본 관찰 기록: [RUNBOOK.md](RUNBOOK.md) `[5-2] Ingress 뒤 Service selector 오타`.

## 범위와 한계

- 이것은 **Day2에서 재현해 해결한 장애를 Day3 문서로 회고한 것**이다.
- Day3 필수 신규 장애 주입 6-1 및 7-1을 수행했다고 주장하지 않는다.
- 옆 팀/짝의 실제 리뷰는 미실시했다.
