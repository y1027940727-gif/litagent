"""ClinicalTrials.gov API v2 (public)."""
import requests
from .models import Doc

URL = "https://clinicaltrials.gov/api/v2/studies"


def parse_studies(payload: dict) -> list:
    docs = []
    for s in payload.get("studies", []):
        p = s.get("protocolSection", {})
        ident = p.get("identificationModule", {})
        nct = ident.get("nctId")
        if not nct:
            continue
        status = p.get("statusModule", {}).get("overallStatus", "")
        desc = p.get("descriptionModule", {})
        design = p.get("designModule", {})
        conds = ", ".join(p.get("conditionsModule", {}).get("conditions", []))
        text = " ".join(x for x in [
            f"Status: {status}.", f"Phase: {', '.join(design.get('phases', []))}." if design.get("phases") else "",
            f"Conditions: {conds}." if conds else "",
            desc.get("briefSummary", ""),
        ] if x)
        year = p.get("statusModule", {}).get("startDateStruct", {}).get("date", "")[:4]
        docs.append(Doc(id=f"NCT:{nct}", title=ident.get("briefTitle", ""), text=text,
                        source="clinicaltrials", year=year))
    return docs


def search(query: str, page_size: int = 10, session=requests) -> list:
    r = session.get(URL, params={"query.term": query, "pageSize": page_size, "format": "json"}, timeout=20)
    r.raise_for_status()
    return parse_studies(r.json())
