from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass(slots=True)
class ParagraphRecord:
    paragraph_id: str
    page_number: int
    order_in_page: int
    section_id: str
    section_title: str
    text: str
    bbox: tuple[float, float, float, float] | None = None
    topics: list[str] = field(default_factory=list)
    entities: list[str] = field(default_factory=list)
    claims: list[str] = field(default_factory=list)


@dataclass(slots=True)
class SectionRecord:
    section_id: str
    title: str
    start_page: int
    order: int


@dataclass(slots=True)
class PageRecord:
    page_id: str
    page_number: int
    width: float
    height: float


@dataclass(slots=True)
class DocumentRecord:
    document_id: str
    title: str
    source_path: str
    pages: list[PageRecord] = field(default_factory=list)
    sections: list[SectionRecord] = field(default_factory=list)
    paragraphs: list[ParagraphRecord] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "title": self.title,
            "source_path": self.source_path,
            "pages": [asdict(p) for p in self.pages],
            "sections": [asdict(s) for s in self.sections],
            "paragraphs": [asdict(p) for p in self.paragraphs],
        }
