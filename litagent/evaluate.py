"""Evaluation harness. Reads a .jsonl question file, runs the agent, writes results.json + results.csv.

Each line: {"id": str, "question": str, "expect": "answer"|"refuse"|"either" (optional),
            "must_cite_any": ["PMID:..."] (optional, hand-checked gold IDs)}
  answer : must cite >=1 retrieved record, no invalid citations, no uncited factual sentences
  refuse : the agent should decline (no evidence / out of scope)
  either : a valid cited answer OR an honest refusal both pass (ids starting with "edge" default to this)
These are AUTOMATIC checks only. They do not show that a cited paper really supports the sentence
or that limitations were mentioned: use the blank human_* columns in results.csv for that.
"""
import csv
import json
import os
import sys
import time
from .agent import Agent


def score_one(item: dict, result, expect: str = None) -> dict:
    c = result.check
    expect = expect or item.get("expect", "answer")
    row = {"id": item.get("id", ""), "question": item["question"], "expect": expect,
           "answer": result.answer, "cited": c["cited"], "n_retrieved": len(result.retrieved_ids),
           "invalid_citations": c["invalid"], "n_uncited": len(c["uncited_sentences"]),
           "is_refusal": c["is_refusal"], "error": ""}
    valid = c["citation_valid"] and not c["uncited_sentences"]
    if expect == "refuse":
        row["pass"] = c["is_refusal"] or not c["cited"]
    elif expect == "either":
        row["pass"] = valid or (c["is_refusal"] and not c["invalid"])
    else:
        ok = valid
        gold = item.get("must_cite_any")
        if gold:
            row["gold_hit"] = bool(set(gold) & set(c["cited"]))
            ok = ok and row["gold_hit"]
        row["pass"] = ok
    return row


def summarize(rows: list) -> dict:
    n = len(rows)
    done = [r for r in rows if not r.get("error")]
    by = lambda e: [r for r in done if r["expect"] == e]
    rate = lambda xs: (sum(r["pass"] for r in xs) / len(xs)) if xs else None
    return {
        "n": n,
        "n_errors": n - len(done),
        "pass_rate": sum(r["pass"] for r in rows) / n if n else 0.0,
        "answer_pass_rate": rate(by("answer")),
        "refusal_pass_rate": rate(by("refuse")),
        "either_pass_rate": rate(by("either")),
        "n_refusals": sum(r["is_refusal"] for r in done),
        "fabricated_citation_count": sum(len(r["invalid_citations"]) for r in done),
    }


def run(path: str, agent: Agent, pause: float = None) -> dict:
    pause = float(os.getenv("EVAL_PAUSE", "2")) if pause is None else pause
    rows = []
    with open(path, encoding="utf-8") as f:
        items = [json.loads(line) for line in f if line.strip()]
    for i, item in enumerate(items, 1):
        item.setdefault("question", item.get("query", ""))
        expect = item.get("expect") or ("either" if str(item.get("id", "")).startswith("edge") else "answer")
        try:
            rows.append(score_one(item, agent.run(item["question"]), expect))
        except Exception as e:  # one failed question must not kill the whole run
            rows.append({"id": item.get("id", ""), "question": item["question"], "expect": expect,
                         "answer": "", "cited": [], "n_retrieved": 0, "invalid_citations": [],
                         "n_uncited": 0, "is_refusal": False, "pass": False, "error": str(e)[:300]})
        print(f"[{i}/{len(items)}] {item.get('id','')}: {'PASS' if rows[-1]['pass'] else 'FAIL'}"
              + (f"  ERROR: {rows[-1]['error']}" if rows[-1]["error"] else ""), flush=True)
        time.sleep(pause)
    return {"model": os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest"),
            "summary": summarize(rows), "rows": rows}


def save(out: dict, json_path="eval/results.json", csv_path="eval/results.csv"):
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    cols = ["id", "expect", "pass", "error", "n_retrieved", "cited", "invalid_citations", "n_uncited",
            "is_refusal", "question", "answer"]
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:  # utf-8-sig so Excel opens Chinese/English fine
        w = csv.writer(f)
        w.writerow(cols + ["human_claims_supported(Y/N/partial)", "human_limitations_mentioned(Y/N)", "human_notes"])
        for r in out["rows"]:
            w.writerow([", ".join(r[c]) if isinstance(r[c], list) else r[c] for c in cols] + ["", "", ""])


if __name__ == "__main__":
    from .llm import Gemini
    path = sys.argv[1] if len(sys.argv) > 1 else "eval/questions.jsonl"
    out = run(path, Agent(Gemini()))
    save(out)
    print(json.dumps(out["summary"], indent=2))
