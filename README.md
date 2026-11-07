# litagent — citation-checked medical literature agent

A small agent that answers literature questions using **PubMed** (NCBI E-utilities) and
**ClinicalTrials.gov** (API v2) as tools, re-ranks results with TF-IDF retrieval, and then
**verifies in code** that every citation in the answer was actually retrieved.

Public data only. No patient data. Not medical advice.

## How it works
1. The model (Gemini by default) emits one JSON action per turn: `search_pubmed`, `search_trials`, or `answer`.
2. Results go into an in-memory TF-IDF index; the top-k records are shown back to the model.
3. The final answer must cite `[PMID:...]` / `[NCT:...]`. `citations.py` then flags:
   - **invalid** citations (ID never retrieved = fabricated),
   - **uncited** factual-looking sentences,
   - refusals ("Insufficient evidence retrieved") are allowed and recognised.
4. `evaluate.py` runs a question set and reports pass rates and fabricated-citation count.

## Status — read before you rely on it
- Offline unit tests pass (parsers, retrieval, citation checks, agent loop with a scripted fake model, eval scoring).
- **Not yet verified:** live PubMed / ClinicalTrials.gov calls and live Gemini calls (they could not be run in the build sandbox).
  Run the quick start below and fix whatever breaks (response shapes, model name, rate limits).
- No evaluation results exist yet. `eval/questions.jsonl` has placeholders; write 15–30 questions
  on topics you have actually read, with hand-checked gold IDs in `must_cite_any`, then record the numbers.
- Citation validity checks that an ID was retrieved, **not** that the claim is supported by that abstract.
  Say this limit in any write-up; a manual spot-check of ~20 answers is the honest complement.
- Abstract-level evidence only; no full text.

## Quick start (local)
```bash
pip install -r requirements.txt
export GEMINI_API_KEY=...          # from Google AI Studio
export NCBI_EMAIL=you@example.com  # optional, polite to NCBI
python -m unittest discover -s tests -v      # offline tests
python -m litagent.cli "What does the evidence say about anti-TNF response in ulcerative colitis?"
python -m litagent.evaluate eval/questions.jsonl
```

## Deploy to Google Cloud Run
```bash
gcloud config set project YOUR_PROJECT
gcloud services enable run.googleapis.com secretmanager.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com
printf '%s' "$GEMINI_API_KEY" | gcloud secrets create gemini-api-key --data-file=-
gcloud run deploy litagent --source . --region asia-east1 \
  --set-secrets GEMINI_API_KEY=gemini-api-key:latest --no-allow-unauthenticated
# the Compute service account needs roles/secretmanager.secretAccessor on the secret
curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  -H 'Content-Type: application/json' -d '{"question":"..."}' https://SERVICE_URL/ask
```
Keep `--no-allow-unauthenticated` so strangers cannot spend your API quota. Delete the service when done.

## Resume wording (only after you have actually done each step)
- After eval is run: "Built and evaluated a citation-checked literature agent (PubMed, ClinicalTrials.gov); N questions, X% valid-citation rate, Y fabricated citations."
- After Cloud Run deploy: "Containerised (Docker) and deployed on Google Cloud Run with Secret Manager."
Until then, do not list them.
