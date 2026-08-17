from __future__ import annotations

from dataclasses import dataclass

from rdflib import Graph

from .fuseki_client import FusekiClient


@dataclass(slots=True)
class FusekiGraphRepository:
    client: FusekiClient

    def replace_document_graph(self, graph_uri: str, graph: Graph) -> None:
        self.client.replace_named_graph(graph_uri, graph)

    def delete_document_graph(self, graph_uri: str) -> None:
        self.client.delete_named_graph(graph_uri)

    def run_select(self, query: str, *, graph_uri: str | None = None) -> list[dict[str, str]]:
        return self.client.select(query, default_graph_uri=graph_uri)

    def run_construct(self, query: str, *, graph_uri: str | None = None) -> Graph:
        return self.client.construct(query, default_graph_uri=graph_uri)

    def run_ask(self, query: str, *, graph_uri: str | None = None) -> bool:
        return self.client.ask(query, default_graph_uri=graph_uri)

    def run_update(self, query: str) -> None:
        self.client.update(query)

    def list_graphs(self) -> list[str]:
        return self.client.list_graphs()

    def ping(self) -> bool:
        return self.client.health_check()
