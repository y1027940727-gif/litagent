---
title: LitAgent
emoji: 🧬
colorFrom: blue
colorTo: green
sdk: gradio
sdk_version: 5.0.0
app_file: app.py
pinned: false
license: mit
---

# LitAgent: citation-checked biomedical literature agent

A small tool-calling agent that searches PubMed and ClinicalTrials.gov, ranks the records with TF-IDF (scikit-learn),
asks Gemini to answer from those records only, and then checks the answer's citations in plain code.
It is a personal learning project, not a clinical tool, and gives no medical advice.

一個小型文獻檢索 Agent：搜尋 PubMed 與 ClinicalTrials.gov，用 TF-IDF 排序，讓 Gemini 只根據檢索到的紀錄作答，再用程式檢查引用。這是個人學習專案，不是臨床工具。

## What the checker does (and does not)

- Checks that every `[PMID:…]` / `[NCT:…]` in the answer was actually returned by a search in that run (cited but not retrieved = "invalid").
- Flags factual-looking sentences with no citation. Recognises "insufficient evidence" refusals.
- It does **not** check that a cited paper really supports the sentence. That needs human review (blank `human_*` columns in `eval/results.csv`).

## First evaluation (15 questions, Gemini `gemini-flash-lite-latest`)

| Metric | Result |
| :--- | :---: |
| Questions | 15 (IBD biologics, speech biomarkers in Alzheimer's, edge cases) |
| Invalid citations (cited but not retrieved) | 0 |
| Passed automated checks | 11 / 15 |
| Needs a full answer (10 questions) | 6 passed |
| Edge questions (answer or honest refusal, 5) | 5 passed |
| Human check of claim support | not done yet |

Caveats: small sample; the same 15 questions were used while debugging, so this is a development score, not a held-out one;
results vary between runs because the model is not deterministic. Raw output is in `eval/results.json` and `eval/results.csv`.

## Run it

```bash
pip install -r requirements.txt
export GEMINI_API_KEY=...        # never commit a key
python -m unittest discover -s tests   # offline tests, no network
python -m litagent.evaluate eval/questions.jsonl
```

`app.py` is a small Gradio interface. Hosting status of any public demo is not guaranteed.

## Layout

`litagent/` agent loop, PubMed/ClinicalTrials.gov parsers, TF-IDF retrieval, citation checker, Gemini client, evaluation harness · `tests/` offline unit tests with a scripted mock model · `eval/` questions and results.
