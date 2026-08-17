from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from rdflib import Graph

from .extract_pdf import PDFStructureExtractor
from .graph_builder import GraphBuilder
from .semantics import SemanticEnricher


@dataclass(slots=True)
class BuildArtifacts:
    graph: Graph
    document_payload: dict
    triple_count: int
    paragraph_count: int
    section_count: int
    title: str
    document_id: str

    def write_turtle(self, path: str | Path) -> Path:
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        self.graph.serialize(destination=str(output_path), format="turtle")
        return output_path

    def write_summary_json(self, path: str | Path) -> Path:
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(self.document_payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return output_path


def build_document_graph(
    pdf_path: str | Path,
    output_dir: str | Path,
    *,
    max_topics: int = 5,
    min_paragraph_chars: int = 40,
) -> BuildArtifacts:
    extractor = PDFStructureExtractor(min_paragraph_chars=min_paragraph_chars)
    document = extractor.extract(pdf_path)

    enricher = SemanticEnricher(max_topics_per_paragraph=max_topics)
    document = enricher.enrich(document)

    builder = GraphBuilder()
    graph = builder.build(document)

    return BuildArtifacts(
        graph=graph,
        document_payload=document.to_dict(),
        triple_count=len(graph),
        paragraph_count=len(document.paragraphs),
        section_count=len(document.sections),
        title=document.title,
        document_id=document.document_id,
    )
