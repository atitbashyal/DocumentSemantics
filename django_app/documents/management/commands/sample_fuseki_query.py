from __future__ import annotations

import json

from django.core.management.base import BaseCommand, CommandError

from documents.models import DocumentGraph
from documents.services import run_sample_graph_query


class Command(BaseCommand):
    help = "Run a small sample query against a document's named graph in Fuseki."

    def add_arguments(self, parser):
        parser.add_argument("document_id", type=int, help="Primary key of the DocumentGraph row")

    def handle(self, *args, **options):
        try:
            document = DocumentGraph.objects.get(pk=options["document_id"])
        except DocumentGraph.DoesNotExist as exc:
            raise CommandError("Document not found.") from exc

        rows = run_sample_graph_query(document)
        if not rows:
            self.stdout.write("No rows returned.")
            return
        for row in rows:
            self.stdout.write(json.dumps(row, ensure_ascii=False))
