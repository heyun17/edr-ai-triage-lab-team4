# D3-3 — Dify 외부 지식 연동 (2026-11-19, 1인 단계별 진행)

## 왜 필요한가

이 프로젝트는 OpenSearch에 플레이북을 저장하고 Python/LangGraph에서 `search_playbook()` 도구를 사용한다. Dify는 웹 UI에서 챗봇/RAG 앱을 구성하는 노코드·로우코드 플랫폼이며, **동일한 검색 기능을 Dify에서도 호출**할 수 있도록 연동하는 것이 D3-3의 목적이다.

- **우리 에이전트:** 조사 도구 호출, 근거 이벤트 추적, 승인 `interrupt()`, 보고서 생성 등 복잡한 보안 업무를 코드로 통제
- **Dify 챗봇:** 지식 검색에 근거한 자연어 질의응답 UI를 빠르게 구성
- Dify가 우리 에이전트의 조사/승인 기능을 자동으로 갖게 되는 것은 아니다.

## 교안 필수 요구사항과 진행 상태

| 기준 | 상태 | 근거 |
|---|---|---|
| `/dify/retrieval` External Knowledge API 계약 | **코드 구현** | `src/soc/api/dify.py` |
| DIFY-1 점수 정규화 | **코드 구현** | 최대 점수를 1.0, 나머지를 비율에 따라 0~1로 변환 |
| 인증 실패 403 및 성공 조회/임계치 테스트 | **단위·통합 테스트 작성** | `tests/test_dify.py` |
| CI 필수 테스트 포함 | **성공 확인** | [Actions 성공 44479065202](https://github.com/heyun17/edr-ai-triage-lab-team4/actions/runs/44479065202), SHA `27bbe52`, 전체 테스트 포함 |
| k3s 실제 OCR 인덱스를 통한 검색 | **성공 확인** | `soc-dify-internal-smoke`: 미인증 403, 인증 200, OpenSearch 200, OpenAI 임베딩 200, 3개 PDF 반환 |
| Dify Cloud UI External Knowledge API 등록 | **미실시** | 사용자 로그인·안전한 HTTPS 엔드포인트 필요 |
| Dify 앱 실제 질의·우리 에이전트 리포트 비교 | **미실시** | Dify UI 연결 완료 후 비교해야 함 |

## 현재 사용 가능한 검증용 k3s Job

`infra/k8s/75-dify-internal-smoke-job.yaml`은 CI에서 테스트를 통과한 앱 이미지 `27bbe52`를 이용한다. 실제 `kb-playbooks-ocr` OpenSearch 인덱스를 `KB_TOOLS=real`, `FAKE_LLM=false`로 검색하되, 공개 HTTP 서비스를 만들지 않는다.

- 매 실행 시 프로세스 내 **임시 난수 키**를 생성해 미인증 요청은 `403`, 인증 요청은 `200`인지 확인.
- `records` 개수·본문·0~1 점수·출처 메타데이터를 검사.
- `OPENAI_API_KEY`는 기존 Kubernetes `soc-openai` Secret에서 읽는다. API 키 출력 금지.
- 실제 Dify Cloud 계정과 연결한 것이 아니라 **우리 쪽 백엔드 계약 검증**이다.

실행:
```bash
curl -fsSL https://raw.githubusercontent.com/heyun17/edr-ai-triage-lab-team4/main/infra/k8s/75-dify-internal-smoke-job.yaml | sudo k3s kubectl apply -f -
sudo k3s kubectl -n soc logs -f job/soc-dify-internal-smoke
```

## 2026-11-19 서버 검증 결과 — 직접 관찰

- `soc-dify-internal-smoke` 로그: `Missing bearer token: 403`, 인증 요청 `Authorized retrieval HTTP status: 200`.
- OpenSearch `kb-playbooks-ocr/_search` 200, OpenAI `/v1/embeddings` 200.
- `Retrieved records: 3`; 반환한 출처는 `01_response_policy_tables.pdf`(score 1.0), `03_playbook_ransomware_header_footer.pdf`(약 0.9694), `04_playbook_macro_powershell_code.pdf`(약 0.9685).
- 마지막 로그 `DIFY BACKEND CONTRACT PASS (internal Job; NOT Dify Cloud UI)`.
- **이 시점에서 D3-3 API 백엔드 계약은 실제 데이터로 검증**, Dify Cloud 외부 서비스 연결과 LLM 답변 비교는 여전히 미확인.

실제 앱의 `deployment/api`는 이전 이미지와 `KB_TOOLS=mock` 설정을 유지하므로, Dify와 연결하려면 **별도 제한된 API 서비스**를 만들어야 한다. 운영 API를 통째로 외부에 노출하면 보안 알림·승인 엔드포인트도 노출될 수 있어 `src/soc/api/dify_only.py`(retrieval + healthz만 노출)와 `infra/k8s/76-dify-kb-minimal.yaml`(비공개 ClusterIP, 전용 DIFY_API_KEY Secret)을 추가했다. Cloud Dify와 연결하려면 향후 사용자 허락하에 임시 HTTPS 접근을 설정한다.

## API 계약

- 요청: `POST /dify/retrieval`
- 헤더: `Authorization: Bearer <DIFY_API_KEY>`
- 본문: `{"knowledge_id": "kb-playbooks-ocr", "query": "LSASS 덤프가 의심되면 격리는 누가 승인해?", "retrieval_setting": {"top_k": 3, "score_threshold": 0.5}}`
- 응답: `{"records": [{"content":"...", "score":1.0, "title":"01_response_policy_tables.pdf", "metadata":{"source":"...", "page":1, "category":"Table"}}]}`
- 실제 응답 문서와 점수는 입력 질문/인덱스에 따라 달라질 수 있다.
- `normalize_scores()`는 빈 목록/모든 0점/음수/입력 원본 불변을 검사하고 가장 높은 양수 점수를 1.0으로 정규화한다.
- Dify가 `/retrieval`을 자동으로 덧붙이므로 설정할 URL은 **`https://<public-host>/dify`**까지다.

## Dify UI에서 연결하는 순서 (외부 서비스 연결 단계)

1. 개인 Dify Cloud 워크스페이스에 로그인하거나 Dify를 안전한 환경에 자체 호스팅한다.
2. `Knowledge → External Knowledge API → Add`에서 **Name**, **HTTPS API Endpoint**(`https://<public-host>/dify`), **API Key**(`DIFY_API_KEY`의 값)를 설정한다.
3. `Knowledge → Connect to an External Knowledge Base`에서 API 연결을 선택하고 `External Knowledge ID`(예: `kb-playbooks-ocr`)를 등록한다.
4. 앱에서 해당 지식베이스를 검색하도록 추가한 뒤 예시 질문(“LSASS 덤프가 의심되면 격리는 누가 승인해?”)을 입력한다.
5. Dify 답변의 승인권자와 출처를 우리 에이전트 리포트의 `recommendation`·`sources`와 비교하고 실제 결과를 기록한다.

**현재 `soc.1.201.110.22.nip.io`는 HTTP만 검증됐으며 HTTPS/TLS 배포를 증명하지 않았다.** HTTP에 Bearer 키를 보내는 실습은 권하지 않는다. 기본 예시 암호 `change-me`는 실서비스에서 사용하지 말고 Kubernetes Secret의 별도 난수 키를 설정한다. 애플리케이션의 실제 보안, TLS, 인증·공개 범위의 운영 검증 없이 외부 공개하지 않는다.

## Dify와 자체 LangGraph 비교 관찰표 (미실측 부분은 공란)

| 비교 | 우리 LangGraph 에이전트 | Dify 앱 |
|---|---|---|
| 플레이북 검색 데이터 | OpenSearch 검색 도구 | 연결 시 동일 API 검색 결과 사용 가능 |
| 보안 이벤트 근거 추적 | `seen_event_ids`, 가드레일 구현 | 외부 Knowledge API만으로 구현되지 않음 |
| 사람 승인 | `interrupt()`, PostgreSQL 체크포인터 | Dify 앱에서 별도 승인 설계 필요 |
| 답변·출처 실제 비교 | 사용자 환경의 리포트 확인 필요 | UI 설정 후 실행 결과 기록 필요 |
| 개발 속도와 설정 편의성 | 코딩 필요 | UI 조합 가능; 실제 시간 미측정 |

## 참고

- 교안: `docs/guide/DAY3.md` 2절 Dify 연동
- Dify External Knowledge API 계약: https://docs.dify.ai/en/cloud/use-dify/knowledge/external-knowledge-api
- Dify 외부 지식 등록: https://docs.dify.ai/en/cloud/use-dify/knowledge/connect-external-knowledge-base

**완료 판정 주의:** 백엔드 API 코드 및 테스트가 성공해도 **Dify Cloud UI에 등록하고 동일 질의를 비교하기 전에는 D3-3 전체 완료 체크를 하지 않는다.**
