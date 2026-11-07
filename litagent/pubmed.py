"""PubMed via NCBI E-utilities (public, no key required; a key raises rate limits)."""
import os
import xml.etree.ElementTree as ET
import requests
from .models import Doc

BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


def _params(extra: dict) -> dict:
    p = {"tool": "litagent", **extra}
    if os.getenv("NCBI_API_KEY"):
        p["api_key"] = os.environ["NCBI_API_KEY"]
    if os.getenv("NCBI_EMAIL"):
        p["email"] = os.environ["NCBI_EMAIL"]
    return p


def search_ids(query: str, retmax: int = 10, session=requests) -> list:
    r = session.get(f"{BASE}/esearch.fcgi",
                    params=_params({"db": "pubmed", "term": query, "retmax": retmax,
                                    "retmode": "json", "sort": "relevance"}),
                    timeout=20)
    r.raise_for_status()
    return r.json()["esearchresult"].get("idlist", [])


def parse_articles(xml_text: str) -> list:
    root = ET.fromstring(xml_text)
    docs = []
    for art in root.findall(".//PubmedArticle"):
        pmid = art.findtext(".//MedlineCitation/PMID")
        if not pmid:
            continue
        title = "".join(art.find(".//ArticleTitle").itertext()) if art.find(".//ArticleTitle") is not None else ""
        parts = []
        for ab in art.findall(".//Abstract/AbstractText"):
            label = ab.get("Label")
            body = "".join(ab.itertext())
            parts.append(f"{label}: {body}" if label else body)
        year = art.findtext(".//JournalIssue/PubDate/Year") or ""
        if not year:
            medline = art.findtext(".//JournalIssue/PubDate/MedlineDate") or ""
            year = medline[:4]
        journal = art.findtext(".//Journal/Title") or ""
        docs.append(Doc(id=f"PMID:{pmid}", title=title, text=" ".join(parts),
                        source="pubmed", year=year, journal=journal))
    return docs


def fetch(ids: list, session=requests) -> list:
    if not ids:
        return []
    r = session.get(f"{BASE}/efetch.fcgi",
                    params=_params({"db": "pubmed", "id": ",".join(ids), "retmode": "xml"}),
                    timeout=30)
    r.raise_for_status()
    return parse_articles(r.text)


def search(query: str, retmax: int = 10, session=requests) -> list:
    return fetch(search_ids(query, retmax, session), session)
