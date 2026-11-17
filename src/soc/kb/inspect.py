"""📘 PDF 파싱 결과를 직접 확인하는 도구.

예:
    python -m soc.kb.inspect
    python -m soc.kb.inspect --file 03 --show 10

전략을 직접 비교할 때만:
    python -m soc.kb.inspect --strategy fast --file 05 --show 20
    python -m soc.kb.inspect --strategy hi_res --file 05 --show 20

--strategy를 생략하면 실제 ingest와 동일하게
문서별 자동 전략을 사용합니다.
"""
from __future__ import annotations

import argparse
from collections import Counter

from .parse import iter_pdfs, parse_pdf


def main() -> None:
    ap = argparse.ArgumentParser()

    ap.add_argument(
        "--strategy",
        default=None,
        choices=[
            "fast",
            "hi_res",
            "ocr_only",
            "auto",
        ],
        help=(
            "강제로 사용할 파싱 전략. "
            "생략하면 문서별 설정을 사용합니다."
        ),
    )

    ap.add_argument(
        "--file",
        help="파일 이름 앞부분 (예: 03)",
    )

    ap.add_argument(
        "--show",
        type=int,
        default=0,
        help="요소를 몇 개 출력할지",
    )

    a = ap.parse_args()

    print(
        f"{'파일':45s} "
        f"{'요소 수':>6s}  "
        "요소 종류"
    )

    for pdf in iter_pdfs():
        if (
            a.file
            and not pdf.name.startswith(a.file)
        ):
            continue

        elements = parse_pdf(
            pdf,
            a.strategy,
        )

        kinds = Counter(
            e.category
            for e in elements
        ).most_common()

        print(
            f"{pdf.name:45s} "
            f"{len(elements):6d}  "
            + ", ".join(
                f"{kind} {count}"
                for kind, count in kinds
            )
        )

        for element in elements[: a.show]:
            page = (
                element.metadata.page_number
            )

            text = (
                element.text or ""
            )[:80]

            print(
                f"    "
                f"[{element.category}] "
                f"p.{page}: "
                f"{text!r}"
            )


if __name__ == "__main__":
    main()