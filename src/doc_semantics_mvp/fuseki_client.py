from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urljoin
from urllib.request import Request, urlopen

from rdflib import Graph


class FusekiError(RuntimeError):
    pass


@dataclass(slots=True)
class FusekiConfig:
    base_url: str
    dataset: str
    query_endpoint: str
    update_endpoint: str
    gsp_endpoint: str
    timeout_seconds: float = 10.0

    @property
    def ping_url(self) -> str:
        return urljoin(f"{self.base_url.rstrip('/')}/", "$/ping")


class FusekiClient:
    def __init__(self, config: FusekiConfig):
        self.config = config

    def health_check(self) -> bool:
        try:
            request = Request(self.config.ping_url, method="GET")
            with urlopen(request, timeout=self.config.timeout_seconds) as response:
                return 200 <= response.status < 300
        except (HTTPError, URLError):
            return False

    def replace_named_graph(self, graph_uri: str, graph: Graph) -> None:
        turtle_data = graph.serialize(format="turtle")
        if isinstance(turtle_data, str):
            body = turtle_data.encode("utf-8")
        else:
            body = turtle_data
        self._request(
            self._gsp_graph_url(graph_uri),
            method="PUT",
            data=body,
            headers={"Content-Type": "text/turtle; charset=utf-8"},
        )

    def upload_named_graph(self, graph_uri: str, graph: Graph) -> None:
        turtle_data = graph.serialize(format="turtle")
        if isinstance(turtle_data, str):
            body = turtle_data.encode("utf-8")
        else:
            body = turtle_data
        self._request(
            self._gsp_graph_url(graph_uri),
            method="POST",
            data=body,
            headers={"Content-Type": "text/turtle; charset=utf-8"},
        )

    def delete_named_graph(self, graph_uri: str) -> None:
        self._request(self._gsp_graph_url(graph_uri), method="DELETE")

    def select(self, query: str, *, default_graph_uri: str | None = None) -> list[dict[str, str]]:
        payload = self._query(
            query,
            accept="application/sparql-results+json",
            default_graph_uri=default_graph_uri,
        )
        return self._parse_select_results(payload)

    def ask(self, query: str, *, default_graph_uri: str | None = None) -> bool:
        payload = self._query(
            query,
            accept="application/sparql-results+json",
            default_graph_uri=default_graph_uri,
        )
        data = json.loads(payload.decode("utf-8"))
        return bool(data.get("boolean"))

    def construct(self, query: str, *, default_graph_uri: str | None = None) -> Graph:
        payload = self._query(query, accept="text/turtle", default_graph_uri=default_graph_uri)
        graph = Graph()
        graph.parse(data=payload.decode("utf-8"), format="turtle")
        return graph

    def update(self, query: str) -> None:
        body = urlencode({"update": query}).encode("utf-8")
        self._request(
            self.config.update_endpoint,
            method="POST",
            data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded; charset=utf-8"},
        )

    def list_graphs(self) -> list[str]:
        query = """
SELECT DISTINCT ?graph
WHERE {
  GRAPH ?graph { ?s ?p ?o }
}
ORDER BY ?graph
""".strip()
        rows = self.select(query)
        return [row["graph"] for row in rows if "graph" in row]

    def _query(self, query: str, *, accept: str, default_graph_uri: str | None = None) -> bytes:
        params: dict[str, str] = {"query": query}
        if default_graph_uri:
            params["default-graph-uri"] = default_graph_uri
        body = urlencode(params).encode("utf-8")
        return self._request(
            self.config.query_endpoint,
            method="POST",
            data=body,
            headers={
                "Accept": accept,
                "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
            },
        )

    def _gsp_graph_url(self, graph_uri: str) -> str:
        separator = "&" if "?" in self.config.gsp_endpoint else "?"
        return f"{self.config.gsp_endpoint}{separator}graph={quote(graph_uri, safe='')}"

    def _request(self, url: str, *, method: str, data: bytes | None = None, headers: dict[str, str] | None = None) -> bytes:
        request = Request(url, data=data, headers=headers or {}, method=method)
        try:
            with urlopen(request, timeout=self.config.timeout_seconds) as response:
                return response.read()
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise FusekiError(f"Fuseki request failed [{exc.code}] {method} {url}: {body}") from exc
        except URLError as exc:
            raise FusekiError(f"Fuseki request failed {method} {url}: {exc.reason}") from exc

    @staticmethod
    def _parse_select_results(payload: bytes) -> list[dict[str, str]]:
        data: dict[str, Any] = json.loads(payload.decode("utf-8"))
        bindings = data.get("results", {}).get("bindings", [])
        rows: list[dict[str, str]] = []
        for binding in bindings:
            row = {}
            for key, value in binding.items():
                row[key] = value.get("value", "")
            rows.append(row)
        return rows
