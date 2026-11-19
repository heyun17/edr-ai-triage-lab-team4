# D3-10 — 고장 예상표 마무리 (1인 압축 기록, 2026-11-19)

이 표는 **개인 사전 예상표 원본이 아니라 강사 교안 `docs/guide/INFRA_STAGES.md`의 '깨 보기' 예상 증상**과 사용자가 서버에서 확인한 **실제 출력**을 비교한 것이다. 사전에 직접 예측하지 않은 내용을 자기 예측으로 주장하지 않는다.

| 실습 | 교안 예상 / 확인 기준 | 실제 관찰 | 결과·교훈 |
|---|---|---|---|
| 6-1 OpenSearch 주소 오타 | Job 오류·재시도 후 `BackoffLimitExceeded` | 별도 연결 확인 Job에서 `opensearhc:9200`, `OpenSearch reachable: False`, Job `Failed 0/1`(43초). 정상 주소 `opensearch:9200` 재실행 시 `Complete`·`True` | **실패·복구 확인.** 원본 적재 Job 대신 데이터 비파괴 격리 Job 사용. `BackoffLimitExceeded` 이벤트의 문자열 자체는 미수집 |
| 7-1 시작 즉시 죽는 새 이미지 | 롤아웃 멈춤, 구버전은 계속 응답 | 전용 실습 API에 종료 코드 1의 `busybox:1.36` 적용. 새 파드 `0/1 Error`, 기존 `1/1 Running`; `/healthz` 정상. `rollout undo` 성공, 1/1 Running 유지 | **증상·복구 일치.** `maxUnavailable: 0`이 구버전을 보호함. 실제 운영 `deployment/api`는 미변경 |
| PDF 06 스캔 본문 | OCR 없으면 텍스트 추출 불가 | 종전 요소 0/청크 0, `ocr_only` 후 요소 **34/청크 1**, Job Complete | **OCR 추출 개선 확인.** OCR 결과 내 정답 문구 존재 여부는 별도 검증 필요 |
| PDF 06 검색 k10 | OCR 전 RAG에서 누락 | 키워드 Recall@3 k10 실패→성공, 벡터·동등 RRF에서는 계속 실패 | **OCR만으로 하이브리드 성능 향상은 보장되지 않음** |
| k13·k14 영어 문서 교차 언어 | 한국어 질의·영어 문서 경쟁 | k13 BM25 3위/벡터 10위 밖, k14 BM25 6위/벡터 10위 밖 | **교차 언어 검색 약점 유지** |
| RRF 키워드 가중치 | 비중을 높이면 BM25 결과가 상위권으로 복원될 가능성 | 1:1~10:1은 18/21, 30:1은 19/21, 100:1·1000:1은 20/21, BM25 단독 20/21 | **개선이 아니라 사실상 BM25와 동률**; 100:1은 운영 배포하지 않음 |

## 예상하지 못한 점

- 스캔 PDF의 OCR 성공 후에도 **기본 하이브리드 Recall@3는 18/21 그대로**였다. 검색 파이프라인의 취약점이 PDF 파싱에서 검색 결과 결합 방식으로 이동했다.
- 키워드 가중치가 **10:1**일 때까지는 개선이 없다가 **30:1에서 19/21, 100:1에서 20/21**이 됐다.
- `rollout undo`는 실제 성공했지만 **`last-applied-configuration` 경고**를 출력했다. 이후 `kubectl apply`와 명령형 롤백을 섞을 때 재적용 위험을 관리해야 한다.

## 다음에 처음 칠 명령

- **Job 오류:** `sudo k3s kubectl -n soc get jobs,pods` → `sudo k3s kubectl -n soc logs job/<name>` → URL/ConfigMap 확인
- **Deployment 새 파드 오류:** `sudo k3s kubectl -n soc get pods -l app=<label>` → `sudo k3s kubectl -n soc logs pod/<new-pod> --previous` → `sudo k3s kubectl -n soc rollout history deployment/<name>`
- **검색 품질:** 기존·개선 인덱스를 분리하고, 질문별 정답 PDF의 **BM25·벡터·최종 RRF 순위**를 각각 확인

## 아직 하지 않은 완료 조건

- 2인이 서로 출제해 **장애 유형을 모르는 상태에서 진단**하는 D3-7 종합 드릴과 진단 후 나눔은 미실시.
- D3-6 상대 담당자 코드 리뷰, D3-11 옆 팀 배포 검증도 미실시.
- 가중치 탐색에 사용한 21문항은 독립 테스트셋이 아니므로, 실전 일반화 성능 근거로 사용하지 않는다.
