from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from documents.models import DocumentGraph
from documents.services import delete_document_graph


class Command(BaseCommand):
    help = "Delete the Fuseki named graph for a stored document."

    def add_arguments(self, parser):
        parser.add_argument("document_id", type=int, help="Primary key of the DocumentGraph row")

    def handle(self, *args, **options):
        try:
            document = DocumentGraph.objects.get(pk=options["document_id"])
        except DocumentGraph.DoesNotExist as exc:
            raise CommandError("Document not found.") from exc
        delete_document_graph(document)
        self.stdout.write(self.style.SUCCESS(f"Deleted graph {document.graph_uri}"))

