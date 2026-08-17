from __future__ import annotations

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from .forms import BuiltinQueryForm, DocumentUploadForm, RawSPARQLForm
from .models import DocumentGraph
from .services import build_graph_for_document, run_document_builtin_query, run_document_raw_query


def document_list(request):
    documents = DocumentGraph.objects.all()
    form = DocumentUploadForm()
    return render(request, "documents/document_list.html", {"documents": documents, "upload_form": form})


def upload_document(request):
    if request.method != "POST":
        return redirect("documents:list")

    form = DocumentUploadForm(request.POST, request.FILES)
    if not form.is_valid():
        documents = DocumentGraph.objects.all()
        return render(request, "documents/document_list.html", {"documents": documents, "upload_form": form}, status=400)

    document = DocumentGraph.objects.create(source_file=form.cleaned_data["pdf"])

    try:
        build_graph_for_document(
            document,
            max_topics=form.cleaned_data["max_topics"],
            min_paragraph_chars=form.cleaned_data["min_paragraph_chars"],
        )
        messages.success(request, "Document uploaded and knowledge graph created.")
    except Exception as exc:
        document.status = DocumentGraph.Status.FAILED
        document.error_message = str(exc)
        document.save(update_fields=["status", "error_message", "updated_at"])
        messages.error(request, f"Upload succeeded but graph creation failed: {exc}")
        return redirect("documents:detail", pk=document.pk)

    return redirect("documents:detail", pk=document.pk)


def document_detail(request, pk: int):
    document = get_object_or_404(DocumentGraph, pk=pk)
    context = {
        "document": document,
        "builtin_form": BuiltinQueryForm(initial={"mode": "topic-page"}),
        "sparql_form": RawSPARQLForm(),
        "builtin_results": request.session.pop("builtin_results", None),
        "builtin_summary": request.session.pop("builtin_summary", None),
        "builtin_error": request.session.pop("builtin_error", None),
        "sparql_results": request.session.pop("sparql_results", None),
        "sparql_error": request.session.pop("sparql_error", None),
    }
    return render(request, "documents/document_detail.html", context)


def run_builtin_query_view(request, pk: int):
    document = get_object_or_404(DocumentGraph, pk=pk)
    if request.method != "POST":
        return redirect("documents:detail", pk=pk)

    form = BuiltinQueryForm(request.POST)
    if not form.is_valid():
        request.session["builtin_error"] = "Please correct the built-in query form."
        return redirect("documents:detail", pk=pk)

    try:
        payload = run_document_builtin_query(document, form.cleaned_data["mode"], form.cleaned_data["value"])
        request.session["builtin_results"] = payload["rows"]
        request.session["builtin_summary"] = payload.get("summary")
        request.session["builtin_error"] = None
    except Exception as exc:
        request.session["builtin_error"] = str(exc)

    return redirect("documents:detail", pk=pk)


def run_raw_sparql_view(request, pk: int):
    document = get_object_or_404(DocumentGraph, pk=pk)
    if request.method != "POST":
        return redirect("documents:detail", pk=pk)

    form = RawSPARQLForm(request.POST)
    if not form.is_valid():
        request.session["sparql_error"] = "Please correct the SPARQL form."
        return redirect("documents:detail", pk=pk)

    try:
        rows = run_document_raw_query(document, form.cleaned_data["query_text"])
        request.session["sparql_results"] = rows
        request.session["sparql_error"] = None
    except Exception as exc:
        request.session["sparql_error"] = str(exc)

    return redirect("documents:detail", pk=pk)
