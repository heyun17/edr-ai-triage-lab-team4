"""D3-6: PDF 파일 종류별 파싱 전략을 검증합니다.

이 단위 테스트는 OCR 엔진 자체를 실행하지 않습니다.
실제 인식 결과와 Recall은 k3s Job을 다시 실행해 검증합니다.
"""
from soc.kb.parse import choose_strategy


def test_scanned_pdf_06_uses_ocr():
    assert choose_strategy("06_false_positive_guide_scanned.pdf") == "ocr_only"


def test_existing_table_pdf_remains_high_resolution():
    assert choose_strategy("09_response_matrix_complex_tables.pdf") == "hi_res"


def test_other_pdf_remains_fast():
    assert choose_strategy("02_playbook_credential_dump.pdf") == "fast"


def test_explicit_override_is_preserved():
    assert choose_strategy("06_false_positive_guide_scanned.pdf", "fast") == "fast"
