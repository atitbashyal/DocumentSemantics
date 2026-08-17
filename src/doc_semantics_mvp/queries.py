from __future__ import annotations

from textwrap import dedent

from rdflib import Graph


PREFIXES = dedent(
    """
    PREFIX doc: <http://example.org/doc#>
    PREFIX dom: <http://example.org/domain#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX prov: <http://www.w3.org/ns/prov#>
    """
).strip()


def load_graph_from_path(graph_path: str) -> Graph:
    graph = Graph()
    graph.parse(graph_path, format="turtle")
    return graph


def topic_page_query(value: str) -> str:
    escaped = value.lower().replace('"', '\\"')
    return f"""
{PREFIXES}
SELECT DISTINCT ?pageNumber ?sectionTitle ?paragraphLabel ?text
WHERE {{
  ?paragraph a doc:Paragraph ;
             doc:pageNumber ?pageNumber ;
             rdfs:label ?paragraphLabel ;
             doc:text ?text ;
             doc:inSection ?section .
  ?section rdfs:label ?sectionTitle .
  OPTIONAL {{
    ?paragraph dom:hasTopic ?topic .
    ?topic rdfs:label ?topicLabel .
  }}
  FILTER(
    CONTAINS(LCASE(STR(?text)), "{escaped}") ||
    CONTAINS(LCASE(STR(?sectionTitle)), "{escaped}") ||
    (BOUND(?topicLabel) && CONTAINS(LCASE(STR(?topicLabel)), "{escaped}"))
  )
}}
ORDER BY ?pageNumber ?paragraphLabel
""".strip()


def entity_paragraphs_query(value: str) -> str:
    escaped = value.lower().replace('"', '\\"')
    return f"""
{PREFIXES}
SELECT DISTINCT ?pageNumber ?sectionTitle ?paragraphLabel ?text ?entityLabel
WHERE {{
  ?paragraph a doc:Paragraph ;
             doc:pageNumber ?pageNumber ;
             rdfs:label ?paragraphLabel ;
             doc:text ?text ;
             doc:inSection ?section ;
             dom:mentionsEntity ?entity .
  ?section rdfs:label ?sectionTitle .
  ?entity rdfs:label ?entityLabel .
  FILTER(CONTAINS(LCASE(STR(?entityLabel)), "{escaped}"))
}}
ORDER BY ?pageNumber ?paragraphLabel
""".strip()


def concept_sections_query(value: str) -> str:
    escaped = value.lower().replace('"', '\\"')
    return f"""
{PREFIXES}
SELECT DISTINCT ?sectionTitle ?pageNumber
WHERE {{
  ?paragraph a doc:Paragraph ;
             doc:pageNumber ?pageNumber ;
             doc:text ?text ;
             doc:inSection ?section .
  ?section rdfs:label ?sectionTitle .
  OPTIONAL {{
    ?paragraph dom:hasTopic ?topic .
    ?topic rdfs:label ?topicLabel .
  }}
  FILTER(
    CONTAINS(LCASE(STR(?text)), "{escaped}") ||
    CONTAINS(LCASE(STR(?sectionTitle)), "{escaped}") ||
    (BOUND(?topicLabel) && CONTAINS(LCASE(STR(?topicLabel)), "{escaped}"))
  )
}}
ORDER BY ?pageNumber ?sectionTitle
""".strip()


def claim_support_query(value: str) -> str:
    escaped = value.replace('"', '\\"')
    return f"""
{PREFIXES}
SELECT DISTINCT ?claimType ?pageNumber ?sectionTitle ?paragraphLabel ?text
WHERE {{
  ?claim a dom:Claim ;
         dom:claimType ?claimType ;
         prov:wasDerivedFrom ?paragraph .
  ?paragraph a doc:Paragraph ;
             doc:pageNumber ?pageNumber ;
             rdfs:label ?paragraphLabel ;
             doc:text ?text ;
             doc:inSection ?section .
  ?section rdfs:label ?sectionTitle .
  FILTER(LCASE(STR(?claimType)) = LCASE("{escaped}"))
}}
ORDER BY ?pageNumber ?paragraphLabel
""".strip()


def summarize_topic_query(value: str) -> str:
    # Reuse topic-page query; summarization is handled after query execution.
    return topic_page_query(value)


QUERY_BUILDERS = {
    "topic-page": topic_page_query,
    "entity-paragraphs": entity_paragraphs_query,
    "concept-sections": concept_sections_query,
    "claim-support": claim_support_query,
    "summarize-topic": summarize_topic_query,
}
