from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

from rdflib import Graph, Literal, Namespace, RDF, RDFS, URIRef
from rdflib.namespace import DCTERMS, PROV, XSD

from .models import DocumentRecord

EX = Namespace("http://example.org/resource/")
DOC = Namespace("http://example.org/doc#")
DOM = Namespace("http://example.org/domain#")


class GraphBuilder:
    def build(self, document: DocumentRecord) -> Graph:
        graph = Graph()
        self._bind_namespaces(graph)
        self._declare_schema(graph)

        document_uri = EX[document.document_id]
        graph.add((document_uri, RDF.type, DOC.Document))
        graph.add((document_uri, DCTERMS.title, Literal(document.title)))
        graph.add((document_uri, DOC.sourcePath, Literal(document.source_path)))

        page_uri_map: dict[int, URIRef] = {}
        for page in document.pages:
            page_uri = EX[page.page_id]
            page_uri_map[page.page_number] = page_uri
            graph.add((page_uri, RDF.type, DOC.Page))
            graph.add((page_uri, DOC.pageNumber, Literal(page.page_number, datatype=XSD.integer)))
            graph.add((page_uri, DOC.pageWidth, Literal(page.width, datatype=XSD.double)))
            graph.add((page_uri, DOC.pageHeight, Literal(page.height, datatype=XSD.double)))
            graph.add((document_uri, DOC.hasPage, page_uri))

        section_uri_map: dict[str, URIRef] = {}
        for section in document.sections:
            section_uri = EX[section.section_id]
            section_uri_map[section.section_id] = section_uri
            graph.add((section_uri, RDF.type, DOC.Section))
            graph.add((section_uri, RDFS.label, Literal(section.title)))
            graph.add((section_uri, DOC.sectionOrder, Literal(section.order, datatype=XSD.integer)))
            graph.add((section_uri, DOC.startPage, Literal(section.start_page, datatype=XSD.integer)))
            graph.add((document_uri, DOC.hasSection, section_uri))

        for paragraph in document.paragraphs:
            paragraph_uri = EX[paragraph.paragraph_id]
            page_uri = page_uri_map[paragraph.page_number]
            section_uri = section_uri_map[paragraph.section_id]

            graph.add((paragraph_uri, RDF.type, DOC.Paragraph))
            graph.add((paragraph_uri, DOC.text, Literal(paragraph.text)))
            graph.add((paragraph_uri, DOC.paragraphOrder, Literal(paragraph.order_in_page, datatype=XSD.integer)))
            graph.add((paragraph_uri, DOC.pageNumber, Literal(paragraph.page_number, datatype=XSD.integer)))
            graph.add((paragraph_uri, RDFS.label, Literal(f"Page {paragraph.page_number} Paragraph {paragraph.order_in_page}")))
            graph.add((page_uri, DOC.containsParagraph, paragraph_uri))
            graph.add((section_uri, DOC.containsParagraph, paragraph_uri))
            graph.add((paragraph_uri, DOC.inSection, section_uri))
            graph.add((paragraph_uri, PROV.wasDerivedFrom, page_uri))

            if paragraph.bbox:
                graph.add((paragraph_uri, DOC.bbox, Literal(",".join(str(v) for v in paragraph.bbox))))

            for topic in paragraph.topics:
                topic_uri = EX[f"topic/{quote(topic)}"]
                graph.add((topic_uri, RDF.type, DOM.Topic))
                graph.add((topic_uri, RDFS.label, Literal(topic)))
                graph.add((paragraph_uri, DOM.hasTopic, topic_uri))

            for entity in paragraph.entities:
                entity_uri = EX[f"entity/{quote(entity)}"]
                graph.add((entity_uri, RDF.type, DOM.Entity))
                graph.add((entity_uri, RDFS.label, Literal(entity)))
                graph.add((paragraph_uri, DOM.mentionsEntity, entity_uri))

            for claim in paragraph.claims:
                claim_uri = EX[f"{paragraph.paragraph_id}/claim/{quote(claim)}"]
                graph.add((claim_uri, RDF.type, DOM.Claim))
                graph.add((claim_uri, DOM.claimType, Literal(claim)))
                graph.add((claim_uri, PROV.wasDerivedFrom, paragraph_uri))
                graph.add((paragraph_uri, DOM.statesClaim, claim_uri))

        return graph

    def serialize(self, graph: Graph, path: str | Path) -> None:
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        graph.serialize(destination=str(output_path), format="turtle")

    def _bind_namespaces(self, graph: Graph) -> None:
        graph.bind("ex", EX)
        graph.bind("doc", DOC)
        graph.bind("dom", DOM)
        graph.bind("dct", DCTERMS)
        graph.bind("prov", PROV)
        graph.bind("rdfs", RDFS)

    def _declare_schema(self, graph: Graph) -> None:
        classes = [
            DOC.Document,
            DOC.Page,
            DOC.Section,
            DOC.Paragraph,
            DOM.Topic,
            DOM.Entity,
            DOM.Claim,
        ]
        for cls in classes:
            graph.add((cls, RDF.type, RDFS.Class))

        properties = [
            DOC.hasPage,
            DOC.hasSection,
            DOC.containsParagraph,
            DOC.inSection,
            DOC.text,
            DOC.pageNumber,
            DOC.paragraphOrder,
            DOC.sectionOrder,
            DOC.startPage,
            DOC.pageWidth,
            DOC.pageHeight,
            DOC.sourcePath,
            DOC.bbox,
            DOM.hasTopic,
            DOM.mentionsEntity,
            DOM.statesClaim,
            DOM.claimType,
        ]
        for prop in properties:
            graph.add((prop, RDF.type, RDF.Property))
