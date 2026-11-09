"""Deterministic citation checks. No LLM is involved, so these are testable."""
import re

CITE = re.compile(r"\[[^\[\]]*?(?:PMID|NCT):[^\[\]]*\]")  # a bracket group holding one or more IDs
ID = re.compile(r"((?:PMID|NCT):[A-Za-z0-9]+)")
# Sentences that are refusals / statements of missing evidence don't need a citation.
REFUSAL = re.compile(r"(insufficient evidence|not enough evidence|could not find|no (relevant )?(studies|evidence))", re.I)


def extract(answer: str) -> list:
    return [i for grp in CITE.findall(answer) for i in ID.findall(grp)]


def split_sentences(text: str) -> list:
    parts = re.split(r"(?<=[.!?])\s+|\n+", text)
    return [p.strip() for p in parts if p.strip()]


def check(answer: str, retrieved_ids: set) -> dict:
    cited = extract(answer)
    unique = set(cited)
    invalid = sorted(unique - set(retrieved_ids))
    uncited = [s for s in split_sentences(answer)
               if len(s.split()) >= 6 and not CITE.search(s) and not REFUSAL.search(s)]
    return {
        "cited": sorted(unique),
        "invalid": invalid,                 # cited but never retrieved = fabricated
        "uncited_sentences": uncited,       # factual-looking sentences with no citation
        "citation_valid": bool(unique) and not invalid,
        "is_refusal": bool(REFUSAL.search(answer)) and not unique,
    }
