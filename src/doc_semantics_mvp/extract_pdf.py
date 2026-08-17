from __future__ import annotations

import re
from collections import Counter
from pathlib import Path
from statistics import median

import fitz

from .models import DocumentRecord, PageRecord, ParagraphRecord, SectionRecord


COMMON_SECTION_TITLES = {
    "abstract",
    "introduction",
    "background",
    "related work",
    "method",
    "methods",
    "methodology",
    "approach",
    "materials and methods",
    "experiments",
    "evaluation",
    "results",
    "discussion",
    "conclusion",
    "conclusions",
    "limitations",
    "future work",
    "references",
    "appendix",
}

HEADING_NUMBER_RE = re.compile(r"^(\d+(?:\.\d+)*)\s+.+")
MULTISPACE_RE = re.compile(r"\s+")


class PDFExtractionError(RuntimeError):
    pass


class PDFStructureExtractor:
    def __init__(self, min_paragraph_chars: int = 40) -> None:
        self.min_paragraph_chars = min_paragraph_chars

    def extract(self, pdf_path: str | Path) -> DocumentRecord:
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        try:
            doc = fitz.open(pdf_path)
        except Exception as exc:  # pragma: no cover
            raise PDFExtractionError(f"Could not open PDF: {pdf_path}") from exc

        title = self._derive_title(doc, pdf_path)
        document_id = self._slugify(pdf_path.stem)
        record = DocumentRecord(document_id=document_id, title=title, source_path=str(pdf_path))

        current_section = SectionRecord(
            section_id=f"{document_id}-section-0",
            title="Front Matter",
            start_page=1,
            order=0,
        )
        record.sections.append(current_section)

        section_counter = 1
        for page_index in range(len(doc)):
            page = doc.load_page(page_index)
            page_number = page_index + 1
            record.pages.append(
                PageRecord(
                    page_id=f"{document_id}-page-{page_number}",
                    page_number=page_number,
                    width=float(page.rect.width),
                    height=float(page.rect.height),
                )
            )

            blocks = self._extract_blocks(page)
            if not blocks:
                continue

            page_median_font = median([b["avg_font_size"] for b in blocks if b["avg_font_size"] > 0] or [10.0])

            paragraph_order = 0
            for block in blocks:
                text = block["text"]
                if not text:
                    continue

                if self._is_heading(text, block["avg_font_size"], page_median_font):
                    title_text = self._normalize_heading(text)
                    if title_text.lower() == "references":
                        # stop before references for the MVP to reduce noise
                        break
                    current_section = SectionRecord(
                        section_id=f"{document_id}-section-{section_counter}",
                        title=title_text,
                        start_page=page_number,
                        order=section_counter,
                    )
                    record.sections.append(current_section)
                    section_counter += 1
                    continue

                cleaned = self._normalize_text(text)
                if len(cleaned) < self.min_paragraph_chars:
                    continue

                paragraph_order += 1
                record.paragraphs.append(
                    ParagraphRecord(
                        paragraph_id=f"{document_id}-p{page_number}-{paragraph_order}",
                        page_number=page_number,
                        order_in_page=paragraph_order,
                        section_id=current_section.section_id,
                        section_title=current_section.title,
                        text=cleaned,
                        bbox=tuple(block["bbox"]),
                    )
                )

        doc.close()
        return record

    def _derive_title(self, doc: fitz.Document, pdf_path: Path) -> str:
        metadata_title = (doc.metadata or {}).get("title")
        if metadata_title and metadata_title.strip():
            return metadata_title.strip()
        return pdf_path.stem.replace("_", " ").replace("-", " ").strip().title()

    def _extract_blocks(self, page: fitz.Page) -> list[dict]:
        page_dict = page.get_text("dict", sort=True)
        blocks: list[dict] = []
        for block in page_dict.get("blocks", []):
            if block.get("type") != 0:
                continue
            lines = block.get("lines", [])
            line_texts: list[str] = []
            font_sizes: list[float] = []
            for line in lines:
                spans = line.get("spans", [])
                span_text = "".join(span.get("text", "") for span in spans).strip()
                if span_text:
                    line_texts.append(span_text)
                font_sizes.extend(float(span.get("size", 0.0)) for span in spans if span.get("size"))
            text = "\n".join(line_texts).strip()
            if not text:
                continue
            blocks.append(
                {
                    "text": text,
                    "bbox": block.get("bbox"),
                    "avg_font_size": sum(font_sizes) / len(font_sizes) if font_sizes else 0.0,
                    "line_count": len(line_texts),
                }
            )
        return blocks

    def _is_heading(self, text: str, avg_font_size: float, page_median_font: float) -> bool:
        one_line = " " not in text.strip("\n") or text.count("\n") <= 1
        cleaned = self._normalize_text(text)
        lower = cleaned.lower()

        if lower in COMMON_SECTION_TITLES:
            return True
        if HEADING_NUMBER_RE.match(cleaned):
            return True
        if avg_font_size >= page_median_font * 1.18 and len(cleaned) <= 120 and one_line:
            return True
        if one_line and len(cleaned) <= 80 and cleaned == cleaned.title() and cleaned[-1:] not in {".", ":", ";"}:
            return True
        return False

    def _normalize_heading(self, text: str) -> str:
        cleaned = self._normalize_text(text)
        return cleaned.rstrip(":")

    def _normalize_text(self, text: str) -> str:
        text = text.replace("-\n", "")
        text = text.replace("\n", " ")
        text = MULTISPACE_RE.sub(" ", text)
        return text.strip()

    def _slugify(self, value: str) -> str:
        value = value.lower()
        value = re.sub(r"[^a-z0-9]+", "-", value)
        value = re.sub(r"-+", "-", value).strip("-")
        return value or "document"
