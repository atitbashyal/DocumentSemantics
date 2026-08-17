from django.contrib import admin

from .models import DocumentGraph


@admin.register(DocumentGraph)
class DocumentGraphAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "status", "triple_count", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("title", "source_file")
