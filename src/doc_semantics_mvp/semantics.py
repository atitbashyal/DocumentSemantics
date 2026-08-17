from __future__ import annotations

import re
from collections import Counter, defaultdict
from typing import Iterable

from sklearn.feature_extraction.text import TfidfVectorizer

from .models import DocumentRecord

try:
    import spacy
    from spacy.language import Language
except ImportError:  # pragma: no cover
    spacy = None
    Language = object  # type: ignore[misc, assignment]


CLAIM_PATTERNS: dict[str, tuple[str, ...]] = {
    "ResearchObjective": (
        "we propose",
        "we present",
        "this paper presents",
        "this paper proposes",
        "we investigate",
        "we study",
        "the aim of this paper",
        "our objective",
    ),
    "Method": (
        "we use",
        "we employ",
        "our method",
        "our approach",
        "we train",
        "we fine-tune",
        "methodology",
        "experimental setup",
    ),
    "Result": (
        "results show",
        "we find",
        "we observe",
        "our results",
        "significantly outperforms",
        "improves",
        "achieves",
        "outperforms",
    ),
    "Conclusion": (
        "in conclusion",
        "to conclude",
        "we conclude",
        "this suggests",
        "future work",
    ),
    "Finding": (
        "this indicates",
        "this demonstrates",
        "we demonstrate",
        "we show",
    ),
}

SECTION_TO_CLAIM = {
    "abstract": ("ResearchObjective", "Method", "Result"),
    "introduction": ("ResearchObjective",),
    "method": ("Method",),
    "methods": ("Method",),
    "methodology": ("Method",),
    "approach": ("Method",),
    "experiments": ("Method", "Result"),
    "evaluation": ("Result",),
    "results": ("Result",),
    "discussion": ("Finding", "Conclusion"),
    "conclusion": ("Conclusion",),
    "conclusions": ("Conclusion",),
}

CAPITALIZED_PHRASE_RE = re.compile(r"\b(?:[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b")
ACRONYM_RE = re.compile(r"\b[A-Z][A-Z0-9\-]{1,}\b")


class SemanticEnricher:
    def __init__(self, max_topics_per_paragraph: int = 5) -> None:
        self.max_topics_per_paragraph = max_topics_per_paragraph
        self._nlp = self._load_spacy_model()

    def enrich(self, document: DocumentRecord) -> DocumentRecord:
        self._attach_topics(document)
        self._attach_entities(document)
        self._attach_claims(document)
        return document

    def _attach_topics(self, document: DocumentRecord) -> None:
        texts = [p.text for p in document.paragraphs]
        if not texts:
            return

        vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 3),
            lowercase=True,
            max_features=3000,
            token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z\-]{1,}\b",
        )
        matrix = vectorizer.fit_transform(texts)
        feature_names = vectorizer.get_feature_names_out()

        for idx, paragraph in enumerate(document.paragraphs):
            row = matrix[idx].toarray().ravel()
            if row.size == 0 or row.max() == 0:
                continue
            ranked = row.argsort()[::-1]
            topics: list[str] = []
            for feature_index in ranked:
                candidate = feature_names[feature_index].strip()
                if not candidate or candidate.isdigit():
                    continue
                if len(candidate) < 3:
                    continue
                if candidate not in topics:
                    topics.append(candidate)
                if len(topics) >= self.max_topics_per_paragraph:
                    break
            paragraph.topics = topics

    def _attach_entities(self, document: DocumentRecord) -> None:
        for paragraph in document.paragraphs:
            entities = self._extract_entities(paragraph.text)
            paragraph.entities = sorted(entities)

    def _attach_claims(self, document: DocumentRecord) -> None:
        for paragraph in document.paragraphs:
            labels: set[str] = set()
            text_lower = paragraph.text.lower()
            section_lower = paragraph.section_title.lower()

            for claim_label, patterns in CLAIM_PATTERNS.items():
                if any(pattern in text_lower for pattern in patterns):
                    labels.add(claim_label)

            for section_hint, claim_labels in SECTION_TO_CLAIM.items():
                if section_hint in section_lower:
                    if any(marker in text_lower for marker in CLAIM_PATTERNS.get(claim_labels[0], ())):
                        labels.update(claim_labels)
                    elif claim_labels == ("Method",) and any(k in text_lower for k in ("dataset", "model", "training", "baseline")):
                        labels.update(claim_labels)
                    elif claim_labels == ("Result",) and any(k in text_lower for k in ("accuracy", "f1", "improvement", "performance")):
                        labels.update(claim_labels)

            paragraph.claims = sorted(labels)

    def _extract_entities(self, text: str) -> set[str]:
        entities: set[str] = set()
        if self._nlp is not None:
            doc = self._nlp(text)
            for ent in doc.ents:
                value = ent.text.strip()
                if len(value) >= 2:
                    entities.add(value)

        for value in CAPITALIZED_PHRASE_RE.findall(text):
            entities.add(value.strip())
        for value in ACRONYM_RE.findall(text):
            if len(value) > 1:
                entities.add(value.strip())

        cleaned = {
            e
            for e in entities
            if not e.lower() in {"introduction", "abstract", "results", "conclusion", "methods"}
        }
        return cleaned

    def _load_spacy_model(self) -> Language | None:
        if spacy is None:
            return None
        try:
            return spacy.load("en_core_web_sm")
        except Exception:
            return None
