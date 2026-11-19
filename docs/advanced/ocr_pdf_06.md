# D3-6 — 스캔 PDF OCR 고도화 (2026-11-19)

**실습 방식:** 1인 압축 실습, 📘 문서·검색 영역. 상대 담당자의 상호 리뷰는 미실시.

## 1. 문제와 목표

기존 `06_false_positive_guide_scanned.pdf`는 이미지 스캔본으로 `fast` 파싱 시 **요소 0개·청크 0개**였다. 평가 질문 **k10**(동일 패턴의 오탐이 몇 번 종결되면 룰 예외 등록을 요청하는가?)에서 정답 PDF를 Recall@3 상위 3개에 포함하지 못했다.

목표: `ocr_only` 파싱을 적용하여 스캔 PDF를 청킹·임베딩·검색 가능하게 만들고, 기존 동일 21문항 평가로 결과를 확인한다.

## 2. 구현

- `src/soc/config.py`: `KB_OCR_FILES=06_false_positive_guide_scanned.pdf` 기본값 추가.
- `src/soc/kb/parse.py`: `choose_strategy()`가 지정 스캔 PDF에 `ocr_only`를 선택하도록 변경. 직접 `strategy`를 지정하면 그 값을 우선한다.
- `tests/test_kb_ocr_strategy.py`: 스캔본 OCR 선택, 일반 문서 fast 유지, 복잡 표 hi_res 유지 및 명시적 override 확인 테스트.
- `Dockerfile.kb`: 기존 Tesseract(`tesseract-ocr`, `tesseract-ocr-kor`) 포함 이미지로 신규 코드 빌드.
- `infra/k8s/64-kb-ocr-job.yaml`: 원본 `kb-playbooks`와 분리된 `kb-playbooks-ocr` 실험 인덱스에 PDF 적재.
- `infra/k8s/65-rag-ocr-eval-job.yaml`: 같은 OCR 인덱스에서 21문항 검색 평가.

> **데이터 보존:** `soc.kb.ingest`는 지정된 인덱스를 `recreate=True`로 재생성한다. 따라서 실험은 `INDEX_KB=kb-playbooks-ocr`로 분리했고, 기존 운영 `kb-playbooks` 25개 청크는 삭제하지 않았다.

## 3. 실제 서버 결과

- 이미지 `ghcr.io/heyun17/edr-ai-triage-lab-team4:kb-ocr-day3-20261119`를 Windows Docker Desktop에서 빌드, 약 900MB tar 전송, k3s containerd 등록 확인(`linux/amd64`).
- `soc-kb-ocr-ingest`: **Complete 1/1**, 실행 77초.
- 06번 PDF: **요소 0 → 34**, **청크 0 → 1** (OCR 구간 5.1초).
- 전체 PDF 청크: **25 → 26**.
- `soc-rag-ocr-eval`에서 기존 **21개 질문·Recall@3**으로 측정.

| 검색 방식 | OCR 전 | OCR 후 | 변화 |
|---|---:|---:|---|
| 키워드(BM25) | 0.905 (19/21) | **0.952 (20/21)** | **+0.047, 약 +4.8%p** |
| 벡터 | 0.857 (18/21) | 0.857 (18/21) | 0 |
| 하이브리드(RRF) | 0.857 (18/21) | 0.857 (18/21) | 0 |

- **k10:** OCR 전 3방식 모두 실패 → OCR 후 **키워드만 성공**, 벡터·하이브리드는 계속 실패.
- k13은 키워드만 성공, k14는 모든 방식 실패. 복잡 표 09번 PDF(k15~k21)는 7/7 검색 성공 유지.
- **의미:** OCR 적용으로 PDF 검색 가능성 자체가 개선됐다. 다만 하이브리드 검색은 Keyword/Vector 순위를 동등 가중 RRF로 합치므로, 키워드의 성공을 최종 Top3에 반영하지 못했다.
- **한계:** Recall@3은 정답 *문서*가 Top 3에 들어왔는지 확인하며, 질문의 정답 문구가 정확히 추출되었는지 자체를 평가하지 않는다. 벡터·하이브리드 실패는 OCR 자체 실패와 구분한다.

## 4. 추가 실험 및 후속 과제

1. 동등 가중 RRF(`1:1`) 대신 Keyword 비중을 높인 RRF를 **별도 평가 Job**에서 실험해 k10 및 전체 검색 성능을 비교한다.
2. 개선될 경우 새로운 질문 묶음에서도 성능을 확인한 후 운영 적용 여부를 결정한다. 기존 21문항에 맞춘 가중치 최적화는 과적합 위험이 있다.
3. OCR 정확도를 검증하려면 06번의 실제 추출 텍스트 중 '세 번' 등 정답 표현 포함 여부를 별도로 점검한다.
4. Kubernetes 앱의 `KB_TOOLS=mock` / `FAKE_LLM=true`는 기존 상태 그대로이며, **실제 RAG 에이전트 엔드투엔드 연동은 완료하지 않았다.**


## 5. 가중 RRF 후속 실측

`soc-rag-rrf-weights` Job으로 같은 21문항과 OCR 인덱스의 `keyword:vector = 1:1, 1.5:1, 2:1, 3:1, 5:1, 10:1`을 비교했다. **모든 가중치에서 18/21 = 0.857**, 실패 문항은 **k10·k13·k14**로 동일했다.

- **k10:** BM25 1위 / 벡터 상위 10개 내 미포함 / 융합 Top3 실패.
- **k13:** BM25 3위 / 벡터 상위 10개 내 미포함 / 융합 Top3 실패.
- **k14:** BM25 6위 / 벡터 상위 10개 내 미포함 / 융합 Top3 실패.
- **결정:** 가중치 10:1은 기존 동등 가중치 대비 개선되지 않았으므로 운영 검색에 반영하지 않는다.
- **추가 확인 계획:** `infra/k8s/67-rag-fusion-diagnostics-job.yaml`에서 30·100·1000:1 등 높은 가중치의 순위와 점수를 검사한다. 개선되지 않거나 사실상 키워드 검색만 남는다면 하이브리드를 억지로 적용하지 않는다.

> 동일 21문항으로 실험했으므로 어떤 가중치가 높게 나와도 **독립 평가셋에서의 재검증**이 필요하다.


## 6. 순위·점수 상세 진단 (67번 Job 실측)

`soc-rag-fusion-diagnostics` 결과 (동일 21문항, OCR 인덱스):

| 검색 방식 | Recall@3 |
|---|---:|
| keyword | **0.952 (20/21)** |
| vector | 0.857 (18/21) |
| RRF 1:1 | 0.857 (18/21) |
| RRF 10:1 | 0.857 (18/21) |
| RRF 30:1 | 0.905 (19/21) |
| RRF 100:1 | **0.952 (20/21)** |
| RRF 1000:1 | **0.952 (20/21)** |

- k10: BM25 1위, 벡터 검색 상위 10개에 없음. RRF 10:1에서는 융합 5위였으나 100:1에서는 융합 1위.
- k13: BM25 3위, 벡터 검색 상위 10개에 없음. 100:1에서는 융합 3위.
- k14: BM25 6위, 벡터 검색 상위 10개에 없음. 100:1에서도 상위 3개에 포함되지 않음.
- **판단:** 높은 Keyword 가중치는 기존 21문항에서 BM25 성능을 복원하지만 **BM25보다 나아지지 않는다**. 사실상 키워드 기반 검색이므로 `100:1`을 운영 기본값으로 바꾸지 않고 기존 로직 유지.
- **다음 개선 방향:** 교차 언어 검색(k14)에는 영어 질의 보강/임베딩 모델 비교 등 별도 실험이 필요하다. 높은 가중치만으로 해결되지 않는다.
- **평가 한계:** 이 21문항은 여러 가중치 검토에 반복 활용된 세트다. 개선안을 배포하려면 별도 평가셋으로 일반화 가능성을 확인해야 한다.


## 7. 실제 OCR 텍스트 품질 확인 — 추가 한계 발견

동일 k3s 서버에서 OpenSearch `count`를 직접 확인했다: **기존 `kb-playbooks` 25개, 실험 `kb-playbooks-ocr` 26개**. PDF06 `source`로 조회하면 **청크 1개**가 반환됐다.

그러나 청크 본문에는 `OF 처리 가이`, `906-60-002 - 20264 개정`, `스크립트 AB7tCAIT`처럼 **한국어 OCR 오인식과 글자 손실이 많았다**. `ExecutionPolicy Bypass=`, `ccmexec.exe` 등 일부 토큰만 살아 있다. 따라서 **OCR 처리 실행과 저장 성공은 확인되지만, 내용의 정확한 인식 및 k10 정답 문구('세 번')의 재현은 아직 확인되지 않았다**. **키워드 Recall@3 20/21은 정답 PDF의 순위에 관한 지표일 뿐 정답 추출 품질 증거가 아니다.**

`data/kb/README.md`가 권고하는 직접 Tesseract `300dpi + kor+eng + --psm 6` 방법을 `infra/k8s/72-ocr-tesseract-quality-job.yaml`의 읽기 전용 Job으로 비교할 계획이다. 이 진단 Job은 인덱스를 변경하지 않는다. 결과가 확인되기 전에는 운영 인덱스에 OCR 내용을 반영하지 않는다.

## 8. 직접 Tesseract OCR 개선 검증 (실험 인덱스에 적용됨)

- `soc-ocr-quality-check` (72번 Job): 스캔 PDF 1쪽을 `pdftoppm -r 300`으로 렌더링한 다음 `tesseract -l kor+eng --psm 6` 수행. 결과에서 **`같은 패턴이 세 번 이상 오탐으로 종결되면`** 문장을 확인하고 `ANSWER_PHRASE_FOUND` 출력. 다만 나머지 일부 한글·영문은 오인식.
- `soc-kb-ocr-direct-patch` (73번 Job): **594자 OCR 결과**, 정답 표현 `세 번` 확인 후 OpenAI `text-embedding-3-small` 모델로 한 청크 재임베딩. OpenSearch의 **`kb-playbooks-ocr` 인덱스 내 PDF06 청크 1개만** 텍스트와 embedding 갱신.
- 성공 로그: `PATCH SUCCESS: production KB 25, OCR KB 26; one isolated chunk updated`. 운영 `kb-playbooks` 및 Kubernetes 운영 Deployment는 변경하지 않음.
- **아직 미확인:** 수정된 임베딩으로 기존 21문항 Recall@3가 어떻게 변했는지. 후속 `infra/k8s/74-rag-ocr-direct-eval-job.yaml` 평가가 준비돼 있음.
- **지속성 한계:** 이번 개선은 기존 컨테이너 내 소스 코드 전체에 반영된 새로운 적재 파이프라인이 아니라 **실험 인덱스의 1개 청크를 수동 갱신하는 Job**이다. 기존 `64-kb-ocr-job.yaml`을 재실행하면 `recreate=True`로 수정 내용이 사라질 수 있어, 정식 운영 적용을 주장할 수 없다.
