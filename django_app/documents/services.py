from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.core.files import File

from doc_semantics_mvp.fuseki_client import FusekiClient, FusekiConfig
from doc_semantics_mvp.graph_repository import FusekiGraphRepository
from doc_semantics_mvp.pipeline import build_document_graph
from doc_semantics_mvp.query_runner import run_builtin_query_via_repository, run_raw_sparql_via_repository

from .models import DocumentGraph


def get_fuseki_repository() -> FusekiGraphRepository:
    config = FusekiConfig(
        base_url=settings.FUSEKI_BASE_URL,
        dataset=settings.FUSEKI_DATASET,
        query_endpoint=settings.FUSEKI_QUERY_ENDPOINT,
        update_endpoint=settings.FUSEKI_UPDATE_ENDPOINT,
        gsp_endpoint=settings.FUSEKI_GSP_ENDPOINT,
        timeout_seconds=settings.FUSEKI_TIMEOUT_SECONDS,
    )
    return FusekiGraphRepository(FusekiClient(config))


def build_graph_for_document(document: DocumentGraph, *, max_topics: int, min_paragraph_chars: int) -> DocumentGraph:
    workspace = Path(settings.MEDIA_ROOT) / "generated" / str(document.pk)
    workspace.mkdir(parents=True, exist_ok=True)

    artifacts = build_document_graph(
        pdf_path=document.source_file.path,
        output_dir=workspace,
        max_topics=max_topics,
        min_paragraph_chars=min_paragraph_chars,
    )

    graph_uri = document.graph_uri or document.default_graph_uri()
    repository = get_fuseki_repository()

    # The upload still happens in-request for the MVP. This is the seam to move to async jobs later.
    repository.replace_document_graph(graph_uri, artifacts.graph)

    ttl_path = artifacts.write_turtle(workspace / "graph.ttl")
    json_path = artifacts.write_summary_json(workspace / "document_summary.json")

    document.title = artifacts.title
    document.triple_count = artifacts.triple_count
    document.paragraph_count = artifacts.paragraph_count
    document.section_count = artifacts.section_count
    document.graph_uri = graph_uri
    document.storage_backend = DocumentGraph.StorageBackend.FUSEKI
    document.fuseki_dataset = settings.FUSEKI_DATASET
    document.status = DocumentGraph.Status.READY
    document.error_message = ""

    with ttl_path.open("rb") as graph_handle:
        document.graph_file.save(f"{artifacts.document_id}.ttl", File(graph_handle), save=False)
    with json_path.open("rb") as summary_handle:
        document.summary_file.save(f"{artifacts.document_id}.json", File(summary_handle), save=False)

    document.save()
    return document


def run_document_builtin_query(document: DocumentGraph, mode: str, value: str) -> dict:
    repository = get_fuseki_repository()
    return run_builtin_query_via_repository(repository, _require_graph_uri(document), mode, value)


def run_document_raw_query(document: DocumentGraph, query_text: str) -> list[dict[str, str]]:
    repository = get_fuseki_repository()
    return run_raw_sparql_via_repository(repository, _require_graph_uri(document), query_text)


def check_fuseki_connection() -> bool:
    return get_fuseki_repository().ping()


def list_document_graphs() -> list[str]:
    return get_fuseki_repository().list_graphs()


def delete_document_graph(document: DocumentGraph) -> None:
    repository = get_fuseki_repository()
    repository.delete_document_graph(_require_graph_uri(document))


def run_sample_graph_query(document: DocumentGraph) -> list[dict[str, str]]:
    query = """
PREFIX doc: <http://example.org/doc#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?pageNumber ?paragraphLabel
WHERE {
  ?paragraph a doc:Paragraph ;
             doc:pageNumber ?pageNumber ;
             rdfs:label ?paragraphLabel .
}
ORDER BY ?pageNumber ?paragraphLabel
LIMIT 5
""".strip()
    repository = get_fuseki_repository()
    return repository.run_select(query, graph_uri=_require_graph_uri(document))


def _require_graph_uri(document: DocumentGraph) -> str:
    if not document.graph_uri:
        raise ValueError("Graph URI is not available for this document.")
    return document.graph_uri
