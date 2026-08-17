from __future__ import annotations

from django.core.management.base import BaseCommand

from documents.services import list_document_graphs


class Command(BaseCommand):
    help = "List named graphs currently stored in Fuseki."

    def handle(self, *args, **options):
        graphs = list_document_graphs()
        if not graphs:
            self.stdout.write("No named graphs found.")
            return
        for graph_uri in graphs:
            self.stdout.write(graph_uri)

