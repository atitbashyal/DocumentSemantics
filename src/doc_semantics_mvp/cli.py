from __future__ import annotations

import argparse
import json
from pathlib import Path

from .pipeline import build_document_graph
from .query_runner import run_builtin_query, run_raw_sparql


def build_command(args: argparse.Namespace) -> int:
    artifacts = build_document_graph(
        pdf_path=args.pdf,
        output_dir=args.out,
        max_topics=args.max_topics,
        min_paragraph_chars=args.min_paragraph_chars,
    )
    output_dir = Path(args.out)
    ttl_path = artifacts.write_turtle(output_dir / "graph.ttl")
    json_path = artifacts.write_summary_json(output_dir / "document_summary.json")

    print(f"Built graph: {ttl_path}")
    print(f"Wrote summary: {json_path}")
    print(f"Triples: {artifacts.triple_count}")
    print(f"Paragraphs: {artifacts.paragraph_count}")
    print(f"Sections: {artifacts.section_count}")
    return 0


def query_command(args: argparse.Namespace) -> int:
    payload = run_builtin_query(args.graph, args.mode, args.value)
    if payload["summary"]:
        print(payload["summary"])
        return 0
    rows = payload["rows"]
    if not rows:
        print("No results.")
        return 0
    for row in rows:
        print(json.dumps(row, ensure_ascii=False, indent=2))
    return 0


def sparql_command(args: argparse.Namespace) -> int:
    query_text = Path(args.query_file).read_text(encoding="utf-8")
    rows = run_raw_sparql(args.graph, query_text)
    if not rows:
        print("No results.")
        return 0
    for row in rows:
        print(json.dumps(row, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Document semantics MVP")
    subparsers = parser.add_subparsers(dest="command", required=True)

    build = subparsers.add_parser("build", help="Extract structure + semantics and build RDF graph")
    build.add_argument("--pdf", required=True, help="Path to a local PDF file")
    build.add_argument("--out", required=True, help="Output directory")
    build.add_argument("--max-topics", type=int, default=5, help="Max topics stored per paragraph")
    build.add_argument("--min-paragraph-chars", type=int, default=40, help="Ignore shorter paragraph-like blocks")
    build.set_defaults(func=build_command)

    query = subparsers.add_parser("query", help="Run a built-in SPARQL-backed query")
    query.add_argument("--graph", required=True, help="Path to graph.ttl")
    query.add_argument(
        "--mode",
        required=True,
        choices=["claim-support", "concept-sections", "entity-paragraphs", "summarize-topic", "topic-page"],
        help="Built-in query mode",
    )
    query.add_argument("--value", required=True, help="Query value")
    query.set_defaults(func=query_command)

    sparql = subparsers.add_parser("sparql", help="Run an arbitrary SPARQL file")
    sparql.add_argument("--graph", required=True, help="Path to graph.ttl")
    sparql.add_argument("--query-file", required=True, help="Path to a .rq SPARQL query file")
    sparql.set_defaults(func=sparql_command)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)
