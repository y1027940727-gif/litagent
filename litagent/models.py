from dataclasses import dataclass


@dataclass(frozen=True)
class Doc:
    """One retrievable record. `id` is e.g. 'PMID:123456' or 'NCT:NCT01234567'."""
    id: str
    title: str
    text: str
    source: str  # "pubmed" | "clinicaltrials"
    year: str = ""
    journal: str = ""

    def snippet(self, n: int = 700) -> str:
        t = self.text.strip().replace("\n", " ")
        return t if len(t) <= n else t[:n] + "..."
