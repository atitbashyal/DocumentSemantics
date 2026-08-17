from __future__ import annotations

import uuid
import unittest

from django.conf import settings
from django.test import SimpleTestCase
from rdflib import Graph, Literal, Namespace

from doc_semantics_mvp.fuseki_client import FusekiClient, FusekiConfig


EX = Namespace("http://example.org/test/")


class FusekiClientIntegrationTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.client = FusekiClient(
            FusekiConfig(
                base_url=settings.FUSEKI_BASE_URL,
                dataset=settings.FUSEKI_DATASET,
                query_endpoint=settings.FUSEKI_QUERY_ENDPOINT,
                update_endpoint=settings.FUSEKI_UPDATE_ENDPOINT,
                gsp_endpoint=settings.FUSEKI_GSP_ENDPOINT,
                timeout_seconds=settings.FUSEKI_TIMEOUT_SECONDS,
            )
        )
        if not cls.client.health_check():
            raise unittest.SkipTest("Fuseki is not available locally; skipping integration test.")

    def test_upload_and_select_roundtrip(self):
        graph_uri = f"urn:test:{uuid.uuid4()}"
        graph = Graph()
        subject = EX["subject"]
        graph.add((subject, EX["label"], Literal("hello")))

        self.client.replace_named_graph(graph_uri, graph)
        try:
            rows = self.client.select(
                """
SELECT ?s ?label
WHERE {
  ?s <http://example.org/test/label> ?label .
}
""".strip(),
                default_graph_uri=graph_uri,
            )
        finally:
            self.client.delete_named_graph(graph_uri)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["label"], "hello")
