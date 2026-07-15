#!/usr/bin/env python3
"""Verify the merged PDF produced by the bookmark-preservation QA flow."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import sys
from typing import Iterable, TextIO

from pypdf import PdfReader


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PDF = PROJECT_ROOT / "output" / "pdf" / "qa_merged_bookmarks.pdf"
EXPECTED_TOP_LEVEL = ("계약서_Beta", "Alpha_packet")


@dataclass
class Bookmark:
    title: str
    page_index: int
    children: list["Bookmark"] = field(default_factory=list)


def _safe_line(message: str, *, stream: TextIO = sys.stdout) -> None:
    """Write diagnostics without failing on legacy Windows console encodings."""
    encoding = stream.encoding or "utf-8"
    safe_message = message.encode(encoding, errors="backslashreplace").decode(encoding)
    print(safe_message, file=stream)


def _title_of(item: object) -> str:
    title = getattr(item, "title", None)
    if title is None and hasattr(item, "get"):
        title = item.get("/Title")  # type: ignore[attr-defined]
    if title is None:
        raise AssertionError("Encountered an outline item without a title.")
    return str(title)


def _parse_level(reader: PdfReader, items: Iterable[object]) -> list[Bookmark]:
    nodes: list[Bookmark] = []
    last_node: Bookmark | None = None

    for item in items:
        if isinstance(item, list):
            if last_node is None:
                raise AssertionError("Malformed outline: child list has no parent item.")
            last_node.children.extend(_parse_level(reader, item))
            continue

        try:
            page_index = reader.get_destination_page_number(item)  # type: ignore[arg-type]
        except Exception as exc:
            raise AssertionError(
                f"Bookmark {_title_of(item)!r} has an unreadable destination."
            ) from exc

        if page_index < 0:
            raise AssertionError(
                f"Bookmark {_title_of(item)!r} does not resolve to a page."
            )

        last_node = Bookmark(title=_title_of(item), page_index=page_index)
        nodes.append(last_node)

    return nodes


def _descendants(node: Bookmark) -> Iterable[Bookmark]:
    for child in node.children:
        yield child
        yield from _descendants(child)


def _require_unique(nodes: Iterable[Bookmark], title: str) -> Bookmark:
    matches = [node for node in nodes if node.title == title]
    if len(matches) != 1:
        raise AssertionError(
            f"Expected exactly one nested bookmark {title!r}; found {len(matches)}."
        )
    return matches[0]


def verify_output() -> None:
    if not OUTPUT_PDF.is_file():
        raise AssertionError(f"Merged QA output is missing: {OUTPUT_PDF}")

    reader = PdfReader(str(OUTPUT_PDF), strict=False)
    if len(reader.pages) != 3:
        raise AssertionError(f"Expected 3 merged pages; found {len(reader.pages)}.")

    roots = _parse_level(reader, reader.outline)
    top_level_titles = tuple(node.title for node in roots)
    if top_level_titles != EXPECTED_TOP_LEVEL:
        raise AssertionError(
            "Top-level bookmarks are incorrect: "
            f"expected {list(EXPECTED_TOP_LEVEL)!r}, found {list(top_level_titles)!r}."
        )

    beta_root, alpha_root = roots
    if beta_root.page_index != 0:
        raise AssertionError(
            f"{beta_root.title!r} should open merged page 1; got page {beta_root.page_index + 1}."
        )
    if alpha_root.page_index != 2:
        raise AssertionError(
            f"{alpha_root.title!r} should open merged page 3; got page {alpha_root.page_index + 1}."
        )

    beta_descendants = list(_descendants(beta_root))
    source_outline = _require_unique(beta_descendants, "Beta source outline")
    if source_outline.page_index != 0:
        raise AssertionError("'Beta source outline' should open merged page 1.")

    preserved_destinations = list(_descendants(source_outline))
    beta_page_1 = _require_unique(preserved_destinations, "Beta page 1")
    beta_page_2 = _require_unique(preserved_destinations, "Beta page 2")
    if beta_page_1.page_index != 0 or beta_page_2.page_index != 1:
        raise AssertionError(
            "Preserved Beta destinations are incorrect: "
            f"Beta page 1 -> {beta_page_1.page_index + 1}, "
            f"Beta page 2 -> {beta_page_2.page_index + 1}."
        )

    _safe_line(
        "PASS: qa_merged_bookmarks.pdf has 3 pages; "
        "top-level order is Unicode Beta, Alpha; "
        "nested Beta destinations resolve to pages 1 and 2."
    )


def main() -> int:
    try:
        verify_output()
    except Exception as exc:
        _safe_line(f"FAIL: {exc}", stream=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
