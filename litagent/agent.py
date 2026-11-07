"""Tool-using agent loop with a deterministic citation check on the final answer.

Protocol (model-agnostic): the model replies with ONE JSON object per turn:
  {"action": "search_pubmed", "query": "..."}
  {"action": "search_trials", "query": "..."}
  {"action": "answer", "text": "... [PMID:123] ..."}
"""
import json
import re
from dataclasses import dataclass, field
from . import pubmed, trials, citations
from .retrieval import Index

SYSTEM = """You are a medical literature assistant for analysts. You do not give medical advice.
Use tools to gather evidence, then answer.
Reply with exactly one JSON object per turn, nothing else:
  {"action":"search_pubmed","query":"<PubMed query>"}
  {"action":"search_trials","query":"<ClinicalTrials.gov query>"}
  {"action":"answer","text":"<answer>"}
Rules for the answer:
- Every factual sentence must end with a citation like [PMID:12345678] or [NCT:NCT01234567].
- Cite ONLY records returned by your tool calls. Never invent identifiers.
- Report what the records say, including limits (small samples, abstracts only). Do not extrapolate.
- If the evidence retrieved does not answer the question, say "Insufficient evidence retrieved" and explain what is missing."""


@dataclass
class Result:
    answer: str
    check: dict
    steps: list = field(default_factory=list)
    retrieved_ids: list = field(default_factory=list)


def _parse_action(text: str) -> dict:
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError("no JSON object in model reply")
    return json.loads(m.group(0))


class Agent:
    def __init__(self, llm, pubmed_search=pubmed.search, trials_search=trials.search,
                 max_steps: int = 5, top_k: int = 6):
        self.llm, self.pubmed_search, self.trials_search = llm, pubmed_search, trials_search
        self.max_steps, self.top_k = max_steps, top_k

    def _observe(self, docs, index, query):
        index.add(docs)
        top = index.top_k(query, self.top_k)
        if not top:
            return "No records found."
        return "\n".join(f"[{d.id}] ({d.year}) {d.title}\n  {d.snippet()}" for d in top)

    def run(self, question: str) -> Result:
        index, steps = Index(), []
        messages = [{"role": "user", "text": question}]
        for _ in range(self.max_steps):
            raw = self.llm.complete(SYSTEM, messages)
            messages.append({"role": "model", "text": raw})
            try:
                act = _parse_action(raw)
            except (ValueError, json.JSONDecodeError) as e:
                messages.append({"role": "user", "text": f"Invalid reply ({e}). Send one JSON object."})
                steps.append({"error": str(e)})
                continue
            kind = act.get("action")
            steps.append({k: v for k, v in act.items() if k != "text"})
            if kind == "answer":
                return self._finish(act.get("text", ""), index, steps)
            q = act.get("query", "")
            try:
                if kind == "search_pubmed":
                    obs = self._observe(self.pubmed_search(q), index, question)
                elif kind == "search_trials":
                    obs = self._observe(self.trials_search(q), index, question)
                else:
                    obs = f"Unknown action {kind!r}."
            except Exception as e:  # network/API failure must not crash the loop
                obs = f"Tool error: {e}"
            messages.append({"role": "user", "text": f"Tool result:\n{obs}"})
        # Out of steps: force an answer from what we have.
        messages.append({"role": "user", "text": 'Step limit reached. Reply now with {"action":"answer",...}.'})
        raw = self.llm.complete(SYSTEM, messages)
        try:
            text = _parse_action(raw).get("text", "")
        except (ValueError, json.JSONDecodeError):
            text = "Insufficient evidence retrieved: the agent did not produce a valid answer."
        return self._finish(text, index, steps)

    def _finish(self, text, index, steps):
        ids = set(index.docs)
        return Result(answer=text, check=citations.check(text, ids), steps=steps, retrieved_ids=sorted(ids))
