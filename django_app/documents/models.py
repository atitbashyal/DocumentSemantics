from __future__ import annotations

from django.db import models


class DocumentGraph(models.Model):
    class StorageBackend(models.TextChoices):
        FUSEKI = "FUSEKI", "Fuseki"
        FILE = "FILE", "File"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        READY = "READY", "Ready"
        FAILED = "FAILED", "Failed"

    title = models.CharField(max_length=500, blank=True)
    source_file = models.FileField(upload_to="uploads/")
    graph_file = models.FileField(upload_to="graphs/", blank=True)
    summary_file = models.FileField(upload_to="summaries/", blank=True)
    graph_uri = models.CharField(max_length=500, blank=True)
    storage_backend = models.CharField(max_length=20, choices=StorageBackend.choices, default=StorageBackend.FUSEKI)
    fuseki_dataset = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    triple_count = models.PositiveIntegerField(default=0)
    paragraph_count = models.PositiveIntegerField(default=0)
    section_count = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.title or self.source_file.name

    def default_graph_uri(self) -> str:
        return f"urn:doc:{self.pk}"
