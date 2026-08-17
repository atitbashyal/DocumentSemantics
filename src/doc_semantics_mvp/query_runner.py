from __future__ import annotations

import re
from typing import Any

from .graph_repository import FusekiGraphRepository
from .queries import QUERY_BUILDERS, load_graph_from_path


BUILTIN_QUERY_MODES = tuple(sorted(QUERY_BUILDERS.keys()))


def run_builtin_query(graph_path: str, mode: str, value: str) -> dict[str, Any]:
    if mode not in QUERY_BUILDERS:
        raise ValueError(f"Unsupported query mode: {mode}")

    graph = load_graph_from_path(graph_path)
    query = QUERY_BUILDERS[mode](value)
    result = graph.query(query)
    vars_ = [str(v) for v in result.vars]
    rows = list(result)

    if mode == "summarize-topic":
        return {
            "mode": mode,
            "value": value,
            "summary": summarize_topic_rows(value, rows),
            "rows": _rows_to_dicts(vars_, rows),
        }

    return {
        "mode": mode,
        "value": value,
        "summary": None,
        "rows": _rows_to_dicts(vars_, rows),
    }


def run_raw_sparql(graph_path: str, query_text: str) -> list[dict[str, str]]:
    graph = load_graph_from_path(graph_path)
    result = graph.query(query_text)
    vars_ = [str(v) for v in result.vars]
    rows = list(result)
    return _rows_to_dicts(vars_, rows)


def run_builtin_query_via_repository(repository: FusekiGraphRepository, graph_uri: str, mode: str, value: str) -> dict[str, Any]:
    if mode not in QUERY_BUILDERS:
        raise ValueError(f"Unsupported query mode: {mode}")

    rows = repository.run_select(QUERY_BUILDERS[mode](value), graph_uri=graph_uri)
    if mode == "summarize-topic":
        return {
            "mode": mode,
            "value": value,
            "summary": summarize_topic_rows(value, _rows_to_sequence(rows)),
            "rows": rows,
        }

    return {
        "mode": mode,
        "value": value,
        "summary": None,
        "rows": rows,
    }


def run_raw_sparql_via_repository(repository: FusekiGraphRepository, graph_uri: str, query_text: str) -> list[dict[str, str]]:
    effective_graph_uri = None if raw_query_explicitly_targets_graph(query_text) else graph_uri
    return repository.run_select(query_text, graph_uri=effective_graph_uri)


def summarize_topic_rows(topic: str, results: list[Any]) -> str:
    if not results:
        return f'No passages found for topic: "{topic}"'

    lines: list[str] = [f'Summary for topic: "{topic}"', ""]
    seen_pages: set[str] = set()

    for row in results[:5]:
        page_number = str(row[0])
        section_title = str(row[1])
        text = str(row[3])
        if page_number not in seen_pages:
            lines.append(f"- Page {page_number}, section: {section_title}")
            seen_pages.add(page_number)
        snippet = text[:350].strip()
        if len(text) > 350:
            snippet += "..."
        lines.append(f"  {snippet}")

    lines.append("")
    lines.append("This is extractive, not generative: it surfaces the most relevant supporting passages with page citations.")
    return "\n".join(lines)


def _rows_to_dicts(vars_: list[str], rows: list[Any]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for row in rows:
        row_dict = {var: row[idx] for idx, var in enumerate(vars_)}
        out.append({k: str(v) for k, v in row_dict.items()})
    return out


def _rows_to_sequence(rows: list[dict[str, str]]) -> list[tuple[str, str, str, str]]:
    sequence: list[tuple[str, str, str, str]] = []
    for row in rows:
        sequence.append(
            (
                row.get("pageNumber", ""),
                row.get("sectionTitle", ""),
                row.get("paragraphLabel", ""),
                row.get("text", ""),
            )
        )
    return sequence


def raw_query_explicitly_targets_graph(query_text: str) -> bool:
    return bool(re.search(r"\b(?:GRAPH|FROM|FROM\s+NAMED)\b", query_text, flags=re.IGNORECASE))
