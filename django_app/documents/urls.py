from __future__ import annotations

from django.urls import path

from . import views

app_name = "documents"

urlpatterns = [
    path("", views.document_list, name="list"),
    path("upload/", views.upload_document, name="upload"),
    path("documents/<int:pk>/", views.document_detail, name="detail"),
    path("documents/<int:pk>/query/", views.run_builtin_query_view, name="run_builtin_query"),
    path("documents/<int:pk>/sparql/", views.run_raw_sparql_view, name="run_raw_sparql"),
]
