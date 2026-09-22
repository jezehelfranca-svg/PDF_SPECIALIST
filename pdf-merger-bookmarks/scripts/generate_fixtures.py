#!/usr/bin/env python3
"""Generate deterministic PDFs used by the manual merge/bookmark QA flow."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from reportlab.lib.colors import HexColor, white
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = PROJECT_ROOT / "tests" / "fixtures"
ALPHA_PDF = FIXTURE_DIR / "Alpha_packet.pdf"
BETA_PDF = FIXTURE_DIR / "계약서_Beta.pdf"


def _render_pages(packet_label: str, page_count: int, accent: str) -> bytes:
    """Render clearly distinguishable source pages into an in-memory PDF."""
    buffer = BytesIO()
    width, height = A4
    document = canvas.Canvas(buffer, pagesize=A4, invariant=1)
    document.setTitle(f"{packet_label} QA fixture")
    document.setAuthor("PDF Merger with Bookmarks QA")

    for page_number in range(1, page_count + 1):
        document.setFillColor(HexColor(accent))
        document.rect(0, height - 118, width, 118, stroke=0, fill=1)

        document.setFillColor(white)
        document.setFont("Helvetica-Bold", 26)
        document.drawString(48, height - 72, f"{packet_label} PACKET")

        document.setFillColor(HexColor("#172033"))
        document.setFont("Helvetica-Bold", 32)
        document.drawCentredString(
            width / 2,
            height / 2 + 24,
            f"SOURCE PAGE {page_number} OF {page_count}",
        )

        document.setFont("Helvetica", 15)
        document.drawCentredString(
            width / 2,
            height / 2 - 20,
            f"Visible label: {packet_label} page {page_number}",
        )

        if packet_label == "BETA":
            document.setFont("Helvetica", 12)
            document.setFillColor(HexColor("#44506A"))
            document.drawCentredString(
                width / 2,
                height / 2 - 54,
                f"Existing outline destination: Beta page {page_number}",
            )

        document.setStrokeColor(HexColor(accent))
        document.setLineWidth(2)
        document.line(48, 66, width - 48, 66)
        document.setFillColor(HexColor("#44506A"))
        document.setFont("Helvetica", 10)
        document.drawString(48, 48, "PDF merger bookmark QA fixture")
        document.drawRightString(width - 48, 48, f"Page {page_number}")
        document.showPage()

    document.save()
    return buffer.getvalue()


def _writer_for(rendered_pdf: bytes, title: str) -> PdfWriter:
    reader = PdfReader(BytesIO(rendered_pdf))
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    writer.add_metadata({"/Title": title, "/Author": "PDF Merger with Bookmarks QA"})
    return writer


def generate_fixtures() -> None:
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)

    alpha_writer = _writer_for(
        _render_pages("ALPHA", page_count=1, accent="#2855D9"),
        "Alpha packet QA fixture",
    )
    with ALPHA_PDF.open("wb") as output:
        alpha_writer.write(output)

    beta_writer = _writer_for(
        _render_pages("BETA", page_count=2, accent="#8B3FD1"),
        "Unicode Beta contract QA fixture",
    )
    source_outline = beta_writer.add_outline_item("Beta source outline", 0)
    beta_writer.add_outline_item("Beta page 1", 0, parent=source_outline)
    beta_writer.add_outline_item("Beta page 2", 1, parent=source_outline)
    with BETA_PDF.open("wb") as output:
        beta_writer.write(output)

    print(
        "Created PDF QA fixtures: Alpha_packet.pdf (1 page), "
        "Unicode Beta PDF (2 pages with nested outline)."
    )


if __name__ == "__main__":
    generate_fixtures()
