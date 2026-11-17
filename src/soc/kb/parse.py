"""📘 1단계 파싱: PDF를 Unstructured '요소(Element)' 목록으로 바꿉니다.

요소 = Title, NarrativeText, ListItem, Table, Header, Footer … 처럼
'종류(category)'가 붙은 글 조각.

파싱 방법(strategy)
- fast
    PDF 안의 글자 층을 그대로 읽음.
    빠르지만 복잡한 표·다단 레이아웃에는 약함.

- hi_res
    레이아웃 모델로 페이지를 분석.
    표 구조와 요소 좌표를 활용할 수 있음.

- ocr_only
    이미지에서 글자를 인식.
    스캔본용.
"""
from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

from ..config import settings


_NUMBERED_HEADING = re.compile(
    r"^\d+(?:\.\d+)*\.\s+\S+"
)


def _normalize_text(text: str) -> str:
    return " ".join(
        (text or "").split()
    )


def _configured_files(value: str) -> set[str]:
    return {
        name.strip()
        for name in value.split(",")
        if name.strip()
    }


def _hi_res_files() -> set[str]:
    return _configured_files(
        settings.kb_hi_res_files
    )


def _two_column_files() -> set[str]:
    return _configured_files(
        settings.kb_two_column_files
    )


def choose_strategy(
    path: str | Path,
    strategy: str | None = None,
) -> str:
    """PDF별 파싱 전략을 결정합니다.

    우선순위
    1. 호출자가 직접 지정한 strategy
    2. 설정된 hi_res 대상 문서
    3. 기본 parse_strategy
    """

    if strategy:
        return strategy

    path = Path(path)

    if path.name in _hi_res_files():
        return "hi_res"

    return settings.parse_strategy


def iter_pdfs(
    root: str | Path | None = None,
):
    """KB 폴더의 PDF를 파일 이름순으로 반환합니다."""

    pdf_root = Path(
        root or settings.kb_pdf_dir
    )

    for path in sorted(
        pdf_root.glob("*.pdf")
    ):
        yield path


def _bbox(element):
    """Unstructured 요소의 좌표를 xmin, ymin, xmax, ymax로 반환합니다."""

    coordinates = getattr(
        element.metadata,
        "coordinates",
        None,
    )

    if (
        coordinates is None
        or not coordinates.points
    ):
        return None

    xs = [
        float(point[0])
        for point in coordinates.points
    ]

    ys = [
        float(point[1])
        for point in coordinates.points
    ]

    return (
        min(xs),
        min(ys),
        max(xs),
        max(ys),
    )


def _page_width(element) -> float | None:
    """요소가 속한 페이지 좌표계의 전체 너비를 반환합니다."""

    coordinates = getattr(
        element.metadata,
        "coordinates",
        None,
    )

    if coordinates is None:
        return None

    system = getattr(
        coordinates,
        "system",
        None,
    )

    if system is None:
        return None

    width = getattr(
        system,
        "width",
        None,
    )

    if width is None:
        return None

    return float(width)


def _promote_layout_heading(element):
    """레이아웃상 소제목처럼 보이는 짧은 요소를 Title로 보정합니다.

    특정 문구는 사용하지 않습니다.

    두 컬럼 문서에서 Unstructured가
    짧은 소제목을 UncategorizedText로 분류하는 경우를 보정합니다.
    """

    from unstructured.documents.elements import Title

    if element.category != "UncategorizedText":
        return element

    text = _normalize_text(
        element.text
    )

    if not text:
        return element

    # 긴 문자열은 제목으로 보지 않습니다.
    if len(text) > 40:
        return element

    bbox = _bbox(element)

    if bbox is None:
        return element

    _, ymin, _, ymax = bbox

    height = ymax - ymin

    # 실제 출력에서 소제목은 한 줄짜리 얇은 박스,
    # 본문은 수백 px 높이의 큰 박스로 잡혔습니다.
    #
    # 절대 좌표 위치가 아니라
    # "짧고 한 줄 높이"라는 레이아웃 특성을 사용합니다.
    if height <= 100:
        return Title(
            text=element.text,
            metadata=element.metadata,
        )

    return element


def _reorder_two_column_page(
    elements: list,
) -> list:
    """한 페이지의 두 컬럼 요소를 읽기 순서대로 재정렬합니다.

    순서:
        상단 공통 영역
        → 왼쪽 컬럼 위에서 아래
        → 오른쪽 컬럼 위에서 아래

    좌표의 절대 x값을 하드코딩하지 않고
    페이지 전체 너비를 기준으로 좌/우를 판단합니다.
    """

    positioned = []
    unpositioned = []

    for element in elements:
        bbox = _bbox(element)
        width = _page_width(element)

        if (
            bbox is None
            or width is None
            or width <= 0
        ):
            unpositioned.append(element)
            continue

        xmin, ymin, xmax, ymax = bbox

        element_width = xmax - xmin
        center_x = (
            xmin + xmax
        ) / 2

        width_ratio = (
            element_width / width
        )

        positioned.append(
            {
                "element": element,
                "xmin": xmin,
                "ymin": ymin,
                "xmax": xmax,
                "ymax": ymax,
                "center_x": center_x,
                "width_ratio": width_ratio,
                "page_width": width,
            }
        )

    if not positioned:
        return elements

    # 컬럼 폭 요소만 골라
    # 실제 본문 컬럼이 시작되는 y 위치를 구합니다.
    column_items = [
        item
        for item in positioned
        if item["width_ratio"] < 0.55
    ]

    if not column_items:
        return elements

    first_column_y = min(
        item["ymin"]
        for item in column_items
    )

    preamble = []
    left = []
    right = []
    other = []

    for item in positioned:
        element = item["element"]

        # 두 컬럼 위에 걸쳐 있는 제목·발행정보 등
        if (
            item["width_ratio"] >= 0.55
            and item["ymin"] < first_column_y
        ):
            preamble.append(item)
            continue

        # 나머지 넓은 요소는 일반 위치 요소로 보존
        if item["width_ratio"] >= 0.55:
            other.append(item)
            continue

        if (
            item["center_x"]
            < item["page_width"] / 2
        ):
            left.append(item)
        else:
            right.append(item)

    preamble.sort(
        key=lambda item: (
            item["ymin"],
            item["xmin"],
        )
    )

    left.sort(
        key=lambda item: (
            item["ymin"],
            item["xmin"],
        )
    )

    right.sort(
        key=lambda item: (
            item["ymin"],
            item["xmin"],
        )
    )

    other.sort(
        key=lambda item: (
            item["ymin"],
            item["xmin"],
        )
    )

    ordered = (
        [item["element"] for item in preamble]
        + [item["element"] for item in left]
        + [item["element"] for item in right]
        + [item["element"] for item in other]
        + unpositioned
    )

    return [
        _promote_layout_heading(element)
        for element in ordered
    ]


def _reorder_two_column_document(
    elements: list,
) -> list:
    """페이지별로 두 컬럼 읽기 순서를 보정합니다."""

    pages = defaultdict(list)
    no_page = []

    for element in elements:
        page = (
            element.metadata.page_number
        )

        if page is None:
            no_page.append(element)
        else:
            pages[page].append(element)

    ordered = []

    for page_number in sorted(pages):
        ordered.extend(
            _reorder_two_column_page(
                pages[page_number]
            )
        )

    ordered.extend(no_page)

    return ordered


def parse_pdf(
    path: str | Path,
    strategy: str | None = None,
) -> list:
    """PDF 하나를 Unstructured 요소 목록으로 바꿉니다."""

    from unstructured.partition.auto import partition

    path = Path(path)

    selected_strategy = choose_strategy(
        path,
        strategy,
    )

    elements = partition(
        filename=str(path),
        strategy=selected_strategy,
        languages=["kor", "eng"],
        infer_table_structure=True,
    )

    # 05 같은 두 컬럼 문서는 hi_res의 좌표를 이용해
    # 실제 읽기 순서대로 다시 정렬합니다.
    #
    # --strategy fast처럼 사용자가 직접 fast를 지정한 경우에는
    # 좌표 기반 재정렬을 적용하지 않습니다.
    if (
        selected_strategy == "hi_res"
        and path.name in _two_column_files()
    ):
        elements = _reorder_two_column_document(
            elements
        )

    return elements


def drop_header_footer(
    elements: list,
) -> list:
    """실제 반복 머리말·꼬리말을 제거하고 Header 오분류를 보정합니다.

    규칙:
    1. Header/Footer라고 해서 무조건 삭제하지 않습니다.
    2. 같은 텍스트가 여러 페이지에서 반복되고
       Header/Footer로 분류된 경우만 제거합니다.
    3. 반복되지 않는 번호형 Header는 실제 소제목으로 보고
       Title로 보정합니다.
    """

    from unstructured.documents.elements import Title

    pages_by_text: dict[
        str,
        set[int],
    ] = defaultdict(set)

    for element in elements:
        text = _normalize_text(
            element.text
        )

        page = (
            element.metadata.page_number
        )

        if (
            text
            and page is not None
        ):
            pages_by_text[text].add(
                page
            )

    result = []

    for element in elements:
        text = _normalize_text(
            element.text
        )

        repeated_on_multiple_pages = (
            len(
                pages_by_text.get(
                    text,
                    set(),
                )
            )
            >= 2
        )

        if (
            element.category
            in {"Header", "Footer"}
            and repeated_on_multiple_pages
        ):
            continue

        if (
            element.category == "Header"
            and _NUMBERED_HEADING.match(
                text
            )
        ):
            element = Title(
                text=element.text,
                metadata=element.metadata,
            )

        result.append(
            element
        )

    return result