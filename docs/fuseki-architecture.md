# Fuseki Architecture Note

## Why Fuseki was introduced

The original MVP stored each RDF graph only as a local Turtle file and queried it by loading that file into RDFLib at request time. That was simple, but it mixed artifact storage with query storage and made it harder to grow toward a real graph-backed application.

Fuseki is now the main graph database because it gives the MVP:

- a local-first SPARQL endpoint that is easy to run in Docker
- persistent storage through a TDB2-backed dataset
- a clean separation between generated artifacts and queryable graph storage
- a straightforward path toward background jobs and larger datasets later

Local Turtle export remains in place as an optional artifact for debugging, download, and backward-compatible developer workflows.

For local development, the Docker setup now runs Fuseki in a single explicit dataset mode:

- one persistent dataset lives at `/documents`
- storage is backed by a TDB2 directory under `./fuseki/databases`
- startup does not rely on Fuseki scanning `/fuseki/configuration` for service registration
- local development uses a permissive `shiro.ini` so Django can write/query without separate credentials

That keeps local startup more predictable and avoids duplicate service-registration issues in the container runtime.

## Named graph strategy

Each uploaded document is stored as its own named graph:

```text
urn:doc:{document_id}
```

This keeps the current UI model intact:

- one Django `DocumentGraph` row maps to one named graph in Fuseki
- guided queries can always be scoped to the current document
- raw SPARQL can default to the current document without rewriting existing templates
- future cross-document querying can still be added at the dataset level

The Django model stores:

- `graph_uri`
- `storage_backend`
- `fuseki_dataset`

## Request flow

### Upload to graph storage

1. User uploads a PDF in Django.
2. The extraction/enrichment pipeline parses the document and builds an RDFLib graph in memory.
3. Django serializes that graph to local Turtle for artifact/debug use.
4. The Fuseki repository replaces the document's named graph in the configured dataset.
5. Django saves document status, counts, graph URI, dataset, and artifact paths.

### Query flow

1. User opens a document detail page.
2. Guided query mode builds a SPARQL query from the existing query builder.
3. The Fuseki repository runs that query against the document's named graph via the query endpoint.
4. Raw SPARQL uses the same repository and defaults to the current named graph unless the query explicitly selects another graph.
5. Django renders results using the existing page structure.
