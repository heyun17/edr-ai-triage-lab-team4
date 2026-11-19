# 용량 산정 (16GB 서버 기준)

> 2일차 인프라 2단계를 시작하기 전에 계산합니다. 2단계 운전자(🔍 기록 담당)가 주도하고, 📘 문서 담당이 검토합니다.

## 서버 실측 (인프라 1단계, 2026-11-17)

- 서버: `edr-team4` (Ubuntu 24.04, 가비아)
- `nproc`: **4** (CPU 4 vCore)
- `free -h`: **Mem total 15Gi**, used **470Mi**, free **14Gi**, available **15Gi**
- `free -h`: **Swap total 0B** (스왑 미설정)
- 위 값은 서버 SSH 접속 직후 실측한 값입니다. 아래 워크로드별 requests/limits는 인프라 2단계에서 산정합니다.


| 워크로드 | 종류 | CPU req | Mem req / limit | 힙 | 근거 |
|---|---|---|---|---|---|
| OS + k3s + Traefik | 시스템 | 0.5 CPU 예약 | 2Gi 예약 | - | 운영체제와 클러스터 여유 |
| opensearch | StatefulSet | 1 CPU | 3Gi / 4Gi | 2Gi | 검색 및 로그 저장, 힙은 limit의 50% |
| postgres | StatefulSet | 0.25 CPU | 512Mi / 1Gi | - | 승인 상태 저장 |
| api | Deployment | 0.25 CPU | 256Mi / 768Mi | - | HTTP 요청 처리 |
| worker | Deployment | 0.5 CPU | 512Mi / 1Gi | - | AI 에이전트 실행 |
| generator | Deployment | 0.25 CPU | 256Mi / 512Mi | - | 보안 이벤트 생성 |
| kb-ingest | Job | 0.5 CPU | 2Gi / 3Gi | - | PDF 처리용, 일시적으로 실행 |
| 합계 | | 3.25 CPU | 8.5Gi / 12.25Gi | - | 시스템 예약 포함 |
| 남는 여유 | | 0.75 CPU | 최대 할당 기준 2.75Gi | - | 서버 전체 4 CPU / 15Gi 기준 |

### 산정 이유
- OpenSearch는 검색과 로그 저장을 담당하므로 가장 많은 메모리를 배정한다.
- OpenSearch 힙은 메모리 limit 4Gi의 약 50%인 2Gi로 설정한다.
- PostgreSQL은 AI 승인 대기 상태를 영구 저장한다.
- API와 Worker는 역할을 분리해 운영한다.
- kb-ingest는 PDF를 처리할 때만 실행하는 Job이다.
- 시스템 운영을 위해 CPU와 메모리 여유를 남긴다.

### 확인 사항
- 위 수치는 초기 배포를 위한 계획값이며 실제 사용량 측정값은 아니다.
- 배포 후 kubectl top nodes, kubectl top pods로 사용량을 확인한다.
- 메모리 부족이나 OOMKilled가 발생하면 requests/limits를 재조정한다.
