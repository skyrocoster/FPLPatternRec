"""Retrieve Wikidata footballer birth-date statements for Premier League clubs."""

from __future__ import annotations

from urllib.parse import urlencode

from .common import RawCollector

WIKIDATA_QUERY = """PREFIX wd: <http://www.wikidata.org/entity/>
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX p: <http://www.wikidata.org/prop/>
PREFIX psv: <http://www.wikidata.org/prop/statement/value/>
PREFIX wikibase: <http://wikiba.se/ontology#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
SELECT DISTINCT ?player ?name ?dob ?precision ?team WHERE {
  ?player wdt:P106 wd:Q937857;
          wdt:P54 ?team;
          p:P569/psv:P569 ?birthDate;
          rdfs:label ?name.
  ?team wdt:P118 wd:Q9448.
  ?birthDate wikibase:timeValue ?dob;
             wikibase:timePrecision ?precision.
  FILTER(LANG(?name) = "en")
  FILTER(?dob >= "1970-01-01T00:00:00Z"^^xsd:dateTime)
}"""
ENDPOINTS = (
    "https://query.wikidata.org/sparql",
    "https://qlever.cs.uni-freiburg.de/api/wikidata",
)


def collect_wikidata_players(collector: RawCollector) -> None:
    """Save query results including date precision and club IDs for later review."""
    print("Collecting Wikidata Premier League club footballer birth dates", flush=True)
    for endpoint in ENDPOINTS:
        url = endpoint + "?" + urlencode({"query": WIKIDATA_QUERY, "format": "json"})
        response = collector.get_json(
            "wikidata_players",
            "premier_league_club_players_dob.json",
            url,
            {"Accept": "application/sparql-results+json"},
        )
        results = response.get("results") if isinstance(response, dict) else None
        if isinstance(results, dict) and isinstance(results.get("bindings"), list) and results["bindings"]:
            return
        print(f"  Wikidata query unavailable at {endpoint}; trying next endpoint", flush=True)
    raise RuntimeError("Wikidata player birth-date query did not return results")
