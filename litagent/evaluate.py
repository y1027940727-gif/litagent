"""Evaluation harness. Reads eval/questions.jsonl, runs the agent, reports deterministic metrics.

Each line: {"question": str, "expect": "answer"|"refuse", "must_cite_any": ["PMID:..."] (optional)}
  expect=answer : answer should cite >=1 retrieved record, no invalid citations, few uncited sentences
  expect=refuse : question has no good evidence (or is out of scope); agent should decline, not fabricate
  must_cite_any : (optional) hand-checked IDs; counts as a hit if the answer cites any of them
Only YOU can write good questions/gold IDs: they require reading the papers.
"""
import json
import sys
from .agent import Agent


def score_one(item: dict, result) -> dict:
    c = result.check
    expect = item.get("expect", "answer")
    row = {"question": item["question"], "expect": expect,
           "invalid_citations": c["invalid"], "n_uncited": len(c["uncited_sentences"])}
    if expect == "refuse":
        row["pass"] = c["is_refusal"] or (not c["cited"])
    else:
        ok = c["citation_valid"] and len(c["uncited_sentences"]) == 0
        gold = item.get("must_cite_any")
        if gold:
            row["gold_hit"] = bool(set(gold) & set(c["cited"]))
            ok = ok and row["gold_hit"]
        row["pass"] = ok
    return row


def summarize(rows: list) -> dict:
    n = len(rows)
    ans = [r for r in rows if r["expect"] == "answer"]
    ref = [r for r in rows if r["expect"] == "refuse"]
    return {
        "n": n,
        "pass_rate": sum(r["pass"] for r in rows) / n if n else 0.0,
        "answer_pass_rate": sum(r["pass"] for r in ans) / len(ans) if ans else None,
        "refusal_pass_rate": sum(r["pass"] for r in ref) / len(ref) if ref else None,
        "fabricated_citation_count": sum(len(r["invalid_citations"]) for r in rows),
    }


def run(path: str, agent: Agent) -> dict:
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                item = json.loads(line)
                rows.append(score_one(item, agent.run(item["question"])))
    return {"summary": summarize(rows), "rows": rows}


if __name__ == "__main__":
    from .llm import Gemini
    out = run(sys.argv[1] if len(sys.argv) > 1 else "eval/questions.jsonl", Agent(Gemini()))
    print(json.dumps(out, indent=2, ensure_ascii=False))
