# Notion '오늘 한 줄 (각자)' — 4조 🔍 기록 담당 복붙용

> 실제 4조 Day1·Day2·Day3 Notion 표에서 **기록 담당의 4개 셀만** 채웠다. 📘 문서 담당과 강사 확인란은 변경하지 않음. 각 셀 내용은 아래와 같으며, [개인 최종 기록](https://app.notion.com/p/41dbfc520588812da31cc9296640e430)으로 연결된다.

## Day1

| 원본 표의 항목 | 🔍 기록 담당에 넣은 내용 |
| --- | --- |
| 오늘 내가 만든 것 | OpenSearch 합성 로그 3,161건 적재·조회, 조사 도구 3개 구현(8 passed), 그래프 설계 참여 |
| 막힌 것 | 인덱스 매핑 들여쓰기·properties 오류, Docker Compose 포트 5432 충돌 수정 |
| 도움이 필요한 것 | 조사 도구의 event_id 근거 추적 교차 검토와 Day2 승인·복구 검증 |
| 오늘 정리 글 링크 (노션·블로그) | [개인 Day1~Day3 최종 기록](https://app.notion.com/p/41dbfc520588812da31cc9296640e430) |

## Day2

| 원본 표의 항목 | 🔍 기록 담당에 넣은 내용 |
| --- | --- |
| 오늘 내가 만든 것 | k3s·OpenSearch·PostgreSQL·API/Worker/Generator 구축, 체크포인트 승인 재개·503 장애 복구 |
| 막힌 것 | DB Secret 인증 불일치, Service selector 오타로 503, ErrImagePull 진단 명령 학습 |
| 도움이 필요한 것 | Secret 변경 절차 검증, 팀원 티치백·교차 인프라 확인 |
| 오늘 정리 글 링크 (노션·블로그) | [개인 Day1~Day3 최종 기록](https://app.notion.com/p/41dbfc520588812da31cc9296640e430) |

## Day3

| 원본 표의 항목 | 🔍 기록 담당에 넣은 내용 |
| --- | --- |
| 오늘 내가 만든 것 | GHCR 배포·롤백, parent_name FakeLLM 10/12→12/12, OCR Hybrid 18/21→19/21, 6-1·7-1 장애 복구 |
| 막힌 것 | PDF06 한글 OCR 오인식 보정, Dify Cloud 등록 실패(내부 API는 정상) |
| 도움이 필요한 것 | 교차 언어 검색·OCR 영속화, 팀원/옆 팀 최종 검증 |
| 오늘 정리 글 링크 (노션·블로그) | [개인 Day1~Day3 최종 기록](https://app.notion.com/p/41dbfc520588812da31cc9296640e430) |

## Day3 고도화 4개 표

| 고도화 | 만든 사람 | 영역 (내/상대) | 증명할 숫자 | 기준점 → 결과 | 기록 링크 |
| --- | --- | --- | --- | --- | --- |
| parent_name 문맥 보존 | 진승호 | 🔍 내 영역 | FakeLLM 판정 정확도(합성 12건) | 10/12 → 12/12 | [parent_name](advanced/parent_name.md) |
| PDF06 직접 OCR 보완 | 진승호(개인 실습) | 📘 상대 영역 | Hybrid Recall@3(21문항) | 18/21 → 19/21 | [ocr_pdf_06](advanced/ocr_pdf_06.md) |
| 나머지 ③ | 미확인 | — | — | — | — |
| 나머지 ④ | 미확인 | — | — | — | — |

- D3-3 Dify 백엔드 자체는 구현·테스트했지만 Cloud 앱 연동은 실패. 완료로 체크하지 않음.
- D3-9 개인 숫자 해석은 [DECISIONS](DECISIONS.md)에 기록했으나 **2인 상호 나눔**은 미실시.
- D3-10 고장 예상표는 [개인 기록](advanced/day3_failure_predictions.md)으로 작성 완료.
- D3-7 2인 무작위 종합 드릴, D3-4 팀 합계 4개 선정·합의, D3-11 옆 팀 검증, D3-13 발표는 미완료.
- 강사 확인 칸은 본인이 대신 체크하지 않는다.
