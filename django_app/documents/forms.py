from __future__ import annotations

from django import forms

from doc_semantics_mvp.query_runner import BUILTIN_QUERY_MODES


QUERY_MODE_CHOICES = [(mode, mode) for mode in BUILTIN_QUERY_MODES]


class DocumentUploadForm(forms.Form):
    pdf = forms.FileField(help_text="Upload an English research-paper PDF.")
    max_topics = forms.IntegerField(min_value=1, max_value=10, initial=5)
    min_paragraph_chars = forms.IntegerField(min_value=20, max_value=300, initial=40)


class BuiltinQueryForm(forms.Form):
    mode = forms.ChoiceField(choices=QUERY_MODE_CHOICES)
    value = forms.CharField(max_length=300)


class RawSPARQLForm(forms.Form):
    query_text = forms.CharField(widget=forms.Textarea(attrs={"rows": 12, "placeholder": "SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 25"}))
