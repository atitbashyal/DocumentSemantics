# Document Semantics MVP

A local MVP for turning an English PDF research paper into a document-specific RDF knowledge graph and interacting with it through either a CLI or a Django UI.

This version keeps local Turtle export as a useful artifact, but Apache Jena Fuseki is now the main graph database for storage and querying.

## What this version includes

- local PDF upload and storage
- document structure extraction (`Document`, `Page`, `Section`, `Paragraph`)
- lightweight semantics (`Topic`, `Entity`, `Claim`)
- RDF graph generation with RDFLib
- per-document named-graph storage in Fuseki
- local `graph.ttl` and `document_summary.json` artifacts for debugging/download
- Django UI for:
  - uploading a PDF and creating the knowledge graph
  - querying the created graph from a document detail page

## Core project layout

```text
src/doc_semantics_mvp/
  cli.py
  extract_pdf.py
  fuseki_client.py
  graph_builder.py
  graph_repository.py
  pipeline.py
  queries.py
  query_runner.py
  semantics.py

django_app/
  config/settings.py
  documents/
    management/commands/
    models.py
    forms.py
    services.py
    views.py
    templates/documents/

fuseki/
  databases/

docs/
  fuseki-architecture.md
```

## Python setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
python -m spacy download en_core_web_sm
cp .env.example .env
```

## Start Fuseki locally

From the repository root:

```bash
docker compose up -d fuseki
```

If you change the Docker or local Fuseki auth config, recreate the container:

```bash
docker compose down -v
docker compose up -d fuseki
```

The local development dataset is configured as:

- Dataset name: `documents`
- Query endpoint: `http://127.0.0.1:3030/documents/query`
- Update endpoint: `http://127.0.0.1:3030/documents/update`
- Graph Store Protocol endpoint: `http://127.0.0.1:3030/documents/data`
- Health check: `http://127.0.0.1:3030/$/ping`

Fuseki uses a persistent TDB2-backed dataset mounted under `./fuseki/databases`.
The container is started in a single explicit dataset mode rather than loading service definitions from `/fuseki/configuration`.
For local MVP development, the container mounts a permissive `fuseki/shiro.ini`, so local Fuseki access does not require authentication.

## How Django connects to Fuseki

Django reads the following environment variables from `.env`:

- `FUSEKI_BASE_URL`
- `FUSEKI_DATASET`
- `FUSEKI_QUERY_ENDPOINT`
- `FUSEKI_UPDATE_ENDPOINT`
- `FUSEKI_GSP_ENDPOINT`
- `FUSEKI_TIMEOUT_SECONDS`

Local defaults are already defined in [django_app/config/settings.py](/Users/atitbashyal/Desktop/document-semantics-mvp/django_app/config/settings.py).

The default local values are:

```env
FUSEKI_BASE_URL=http://127.0.0.1:3030
FUSEKI_DATASET=documents
FUSEKI_QUERY_ENDPOINT=http://127.0.0.1:3030/documents/query
FUSEKI_UPDATE_ENDPOINT=http://127.0.0.1:3030/documents/update
FUSEKI_GSP_ENDPOINT=http://127.0.0.1:3030/documents/data
FUSEKI_TIMEOUT_SECONDS=10
```

No Fuseki username/password is required in local development with the included Docker setup.

## Django UI setup

From the repository root:

```bash
docker compose up -d fuseki
cd django_app
python manage.py migrate
python manage.py check_fuseki
python manage.py runserver
```

Then open:

```text
http://127.0.0.1:8000/
```

## Django UI workflow

### 1. Upload document and create knowledge graph

- Upload an English PDF research paper.
- Django stores the uploaded PDF locally under `MEDIA_ROOT`.
- The graph-building pipeline runs synchronously for the MVP.
- The RDF graph is built in memory, written to Fuseki as a named graph, and also exported locally as `graph.ttl`.
- The generated `document_summary.json` remains available as a local artifact.

Each uploaded document is stored in Fuseki as its own named graph using:

```text
urn:doc:{document_id}
```

### 2. Query the created knowledge graph

Each uploaded document gets a detail page where you can:

- run built-in query modes:
  - `topic-page`
  - `entity-paragraphs`
  - `concept-sections`
  - `claim-support`
  - `summarize-topic`
- run raw SPARQL against Fuseki
- download the generated local Turtle and JSON artifacts

Guided queries are always scoped to the current document's named graph. Raw SPARQL queries default to that same graph unless your query explicitly uses `GRAPH` or `FROM`.

## CLI usage

Build a graph from a local PDF and keep local artifacts:

```bash
python -m doc_semantics_mvp build \
  --pdf /path/to/paper.pdf \
  --out ./output
```

Run a built-in query against a local Turtle file:

```bash
python -m doc_semantics_mvp query \
  --graph ./output/graph.ttl \
  --mode topic-page \
  --value "transformer"
```

## Developer helpers

Check Fuseki connectivity:

```bash
cd django_app
python manage.py check_fuseki
```

List named graphs:

```bash
python manage.py list_fuseki_graphs
```

Delete a document graph:

```bash
python manage.py delete_document_graph 1
```

Run a sample query against a document graph:

```bash
python manage.py sample_fuseki_query 1
```

## Sample curl commands

List named graphs:

```bash
curl -G http://127.0.0.1:3030/documents/query \
  --data-urlencode 'query=SELECT DISTINCT ?graph WHERE { GRAPH ?graph { ?s ?p ?o } } ORDER BY ?graph'
```

Delete one document graph:

```bash
curl -X DELETE 'http://127.0.0.1:3030/documents/data?graph=urn%3Adoc%3A1'
```

Run a sample query against one graph:

```bash
curl -G http://127.0.0.1:3030/documents/query \
  --data-urlencode 'default-graph-uri=urn:doc:1' \
  --data-urlencode 'query=PREFIX doc: <http://example.org/doc#> SELECT ?pageNumber WHERE { ?p a doc:Paragraph ; doc:pageNumber ?pageNumber } LIMIT 5'
```

## Tests

From `django_app/`:

```bash
python manage.py test
```

The Fuseki roundtrip test skips automatically when the local Fuseki service is not running.

## MVP notes

- This version still uses synchronous processing in the web request for simplicity.
- The natural next step is moving graph build + Fuseki upload into a background job.
- The current parser is aimed at published research-paper PDFs in English.
- The query interface remains document-specific rather than cross-document.
