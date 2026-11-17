"""📘 2단계 청킹: 요소들을 검색 단위(청크)로 묶고, OpenSearch에 넣을 레코드로 바꿉니다.

chunk_by_title: 제목(Title)이 나오면 새 청크를 시작하고,
길이 제한 안에서 요소를 이어 붙입니다.

- max_characters    : 청크의 최대 길이
- new_after_n_chars : 이 길이를 넘으면 다음 제목 전이라도 새 청크 시작
"""
from __future__ import annotations

import hashlib
import re

from ..config import settings


_NUMBERED_START = re.compile(
    r"^\d+(?:\.\d+)*\.\s+\S+"
)

_ASCII_LOWER_START = re.compile(
    r"^[a-z]"
)


def _normalize_text(text: str) -> str:
    return " ".join(
        (text or "").split()
    )


def _ends_sentence(text: str) -> bool:
    """일반적인 문장 종결 부호로 끝나는지 확인합니다."""

    return (text or "").rstrip().endswith(
        (
            ".",
            "?",
            "!",
            "。",
            "？",
            "！",
        )
    )


def _looks_like_section_heading(
    text: str,
) -> bool:
    """번호가 붙은 짧은 소제목 형태인지 확인합니다."""

    text = _normalize_text(text)

    if not _NUMBERED_START.match(text):
        return False

    if len(text) > 80:
        return False

    if _ends_sentence(text):
        return False

    return True


def _title_is_fragment_continuation(
    left: str,
    right: str,
) -> bool:
    """Title이 실제 제목이 아니라 앞 문장의 파편인지 판단합니다.

    복구 대상 예:
        사용자 문서 폴 + 더를 대상으로
        걸린 시 + 간을 반드시 기록한다.
        recovery depends on + backup integrity.

    보존 대상 예:
        Run 키에 숨는 공격자
        T1486 / T1490 — Ransomware Impact
        4. 복구
    """

    left = (left or "").rstrip()
    right = (right or "").lstrip()

    if not left or not right:
        return False

    # 번호형 제목은 진짜 제목으로 유지
    if _looks_like_section_heading(right):
        return False

    last_token = left.split()[-1]

    # 한국어 등에서 한 글자짜리 단어 조각이
    # 다음 Title 요소와 이어진 경우
    #
    # 폴 + 더
    # 시 + 간
    if len(last_token) == 1:
        return True

    # 영어 문장의 마지막 조각이 Title로 잘못 분류된 경우
    #
    # recovery depends on
    # + backup integrity.
    #
    # 정상 영문 제목은 보통 대문자/기법 번호 등으로 시작하므로
    # 소문자로 시작하면서 문장부호로 끝나는 경우만 복구
    if (
        _ASCII_LOWER_START.match(right)
        and _ends_sentence(right)
    ):
        return True

    return False


def _join_fragments(
    left: str,
    right: str,
    right_category: str,
) -> str:
    """PDF 파싱 과정에서 찢어진 문장 조각을 다시 연결합니다."""

    left = (left or "").rstrip()
    right = (right or "").lstrip()

    if not left:
        return right

    if not right:
        return left

    last_token = left.split()[-1]

    if right_category == "Title":
        # 한 글자짜리 한국어 단어 파편은 공백 없이 연결
        #
        # 폴 + 더 -> 폴더
        # 시 + 간 -> 시간
        if len(last_token) == 1:
            return left + right

        # 영어 문장 파편 등은 정상 단어 경계를 유지
        #
        # depends on + backup integrity.
        # -> depends on backup integrity.
        return left + " " + right

    # "많" + "다." 같은 어미 분리
    if (
        len(last_token) == 1
        and right.startswith(
            (
                "다.",
                "다?",
                "다!",
                "며.",
                "고.",
            )
        )
    ):
        return left + right

    return left + " " + right


def repair_broken_text(
    elements: list,
) -> list:
    """파싱 과정에서 한 문장이 여러 요소로 찢어진 경우 복구합니다.

    원칙
    - 진짜 소제목은 본문과 합치지 않음
    - 새로운 번호 목록 항목은 앞 문장과 합치지 않음
    - Title도 문장 파편이라고 판단할 근거가 있을 때만 합침
    """

    if not elements:
        return elements

    repaired = []

    for current in elements:
        current_text = (
            current.text or ""
        ).strip()

        if not current_text:
            continue

        if not repaired:
            repaired.append(current)
            continue

        previous = repaired[-1]

        previous_text = (
            previous.text or ""
        ).strip()

        same_page = (
            previous.metadata.page_number
            == current.metadata.page_number
        )

        previous_is_body = (
            previous.category
            in {
                "NarrativeText",
                "UncategorizedText",
                "ListItem",
            }
        )

        previous_is_section_heading = (
            previous.category == "ListItem"
            and _looks_like_section_heading(
                previous_text
            )
        )

        current_starts_new_item = bool(
            _NUMBERED_START.match(
                _normalize_text(
                    current_text
                )
            )
        )

        current_can_continue_body = (
            current.category
            in {
                "NarrativeText",
                "UncategorizedText",
                "Title",
            }
        )

        previous_is_unfinished = (
            not _ends_sentence(
                previous_text
            )
        )

        if current.category == "Title":
            current_is_continuation = (
                _title_is_fragment_continuation(
                    previous_text,
                    current_text,
                )
            )
        else:
            current_is_continuation = True

        if (
            same_page
            and previous_is_body
            and not previous_is_section_heading
            and previous_is_unfinished
            and current_can_continue_body
            and not current_starts_new_item
            and current_is_continuation
        ):
            merged_text = _join_fragments(
                previous_text,
                current_text,
                current.category,
            )

            repaired[-1] = type(previous)(
                text=merged_text,
                metadata=previous.metadata,
            )

            continue

        repaired.append(current)

    return repaired


def _find_last_section_heading(
    text: str,
) -> str | None:
    """청크 안의 마지막 번호형 섹션 제목을 찾습니다."""

    last_heading = None

    for line in (
        text or ""
    ).splitlines():
        line = _normalize_text(line)

        if _looks_like_section_heading(
            line
        ):
            last_heading = line

    return last_heading


def add_table_context(
    chunks: list,
) -> list:
    """Table 청크에 직전 섹션 제목을 검색 문맥으로 붙입니다."""

    from unstructured.documents.elements import (
        Table,
    )

    result = []
    current_section = None

    for chunk in chunks:
        text = (
            chunk.text or ""
        ).strip()

        if chunk.category != "Table":
            heading = (
                _find_last_section_heading(
                    text
                )
            )

            if heading:
                current_section = heading

        if (
            chunk.category == "Table"
            and current_section
        ):
            if not text.startswith(
                current_section
            ):
                text = (
                    f"{current_section}\n\n"
                    f"{text}"
                )

            chunk = Table(
                text=text,
                metadata=chunk.metadata,
            )

        result.append(chunk)

    return result


def make_chunks(
    elements: list,
    max_characters: int | None = None,
    new_after_n_chars: int | None = None,
) -> list:
    from unstructured.chunking.title import (
        chunk_by_title,
    )

    max_characters = (
        max_characters
        or settings.chunk_max_characters
    )

    new_after_n_chars = (
        new_after_n_chars
        or min(
            settings.chunk_new_after_n_chars,
            max_characters,
        )
    )

    # 1. 파싱 과정에서 찢어진 본문 복구
    elements = repair_broken_text(
        elements
    )

    # 2. 기본 청킹
    chunks = chunk_by_title(
        elements,
        max_characters=max_characters,
        new_after_n_chars=new_after_n_chars,
    )

    # 3. 표 청크에 섹션 제목 문맥 추가
    chunks = add_table_context(
        chunks
    )

    return chunks


def to_records(
    chunks: list,
    source: str,
) -> list[dict]:
    """청크를 OpenSearch 저장용 레코드로 변환합니다."""

    out = []

    for i, ch in enumerate(chunks):
        text = (
            ch.text or ""
        ).strip()

        if not text:
            continue

        md = ch.metadata

        out.append(
            {
                "id": hashlib.sha1(
                    f"{source}:{i}".encode()
                ).hexdigest()[:16],

                "text": text,
                "source": source,
                "page": md.page_number,
                "category": ch.category,
                "chunk_index": i,

                "text_as_html": getattr(
                    md,
                    "text_as_html",
                    None,
                ),
            }
        )

    return out