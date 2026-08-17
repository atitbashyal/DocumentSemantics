from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rdflib import Graph, Literal, Namespace

from documents.models import DocumentGraph
from documents.services import build_graph_for_document, run_document_builtin_query


EX = Namespace("http://example.org/test/")


class DocumentBuildServiceTests(TestCase):
    def test_build_flow_stores_graph_uri_and_optional_artifacts(self):
        with TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root, FUSEKI_DATASET="documents"):
                document = DocumentGraph.objects.create(
                    source_file=SimpleUploadedFile("paper.pdf", b"%PDF-1.4 test", content_type="application/pdf")
                )
                graph = Graph()
                graph.add((EX["subject"], EX["label"], Literal("stored")))
                artifacts = Mock(
                    graph=graph,
                    title="Test Paper",
                    triple_count=1,
                    paragraph_count=2,
                    section_count=1,
                    document_id="test-paper",
                )
                artifacts.write_turtle.side_effect = lambda path: _write_file(path, "graph turtle")
                artifacts.write_summary_json.side_effect = lambda path: _write_file(path, '{"title": "Test Paper"}')

                with patch("documents.services.build_document_graph", return_value=artifacts), patch(
                    "documents.services.get_fuseki_repository"
                ) as get_repository:
                    repository = Mock()
                    get_repository.return_value = repository

                    build_graph_for_document(document, max_topics=5, min_paragraph_chars=40)

                document.refresh_from_db()
                repository.replace_document_graph.assert_called_once_with(f"urn:doc:{document.pk}", graph)
                self.assertEqual(document.graph_uri, f"urn:doc:{document.pk}")
                self.assertEqual(document.storage_backend, DocumentGraph.StorageBackend.FUSEKI)
                self.assertEqual(document.fuseki_dataset, "documents")
                self.assertTrue(document.graph_file.name.endswith(".ttl"))
                self.assertTrue(document.summary_file.name.endswith(".json"))


class GuidedQueryServiceTests(TestCase):
    def test_guided_query_uses_document_named_graph(self):
        document = DocumentGraph.objects.create(
            source_file=SimpleUploadedFile("paper.pdf", b"%PDF-1.4 test", content_type="application/pdf"),
            graph_uri="urn:doc:42",
            storage_backend=DocumentGraph.StorageBackend.FUSEKI,
            fuseki_dataset="documents",
        )

        repository = Mock()
        repository.run_select.return_value = [
            {
                "pageNumber": "1",
                "sectionTitle": "Intro",
                "paragraphLabel": "Page 1 Paragraph 1",
                "text": "Graph databases are useful.",
            }
        ]

        with patch("documents.services.get_fuseki_repository", return_value=repository):
            payload = run_document_builtin_query(document, "topic-page", "graph")

        self.assertEqual(payload["rows"][0]["pageNumber"], "1")
        self.assertEqual(repository.run_select.call_args.kwargs["graph_uri"], "urn:doc:42")


def _write_file(path: str | Path, content: str) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path
