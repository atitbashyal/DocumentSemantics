from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from documents.services import check_fuseki_connection


class Command(BaseCommand):
    help = "Check whether the configured Fuseki service is reachable."

    def handle(self, *args, **options):
        if check_fuseki_connection():
            self.stdout.write(self.style.SUCCESS("Fuseki is reachable."))
            return
        raise CommandError("Fuseki is not reachable with the current Django settings.")

