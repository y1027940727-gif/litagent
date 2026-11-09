"""Offline tests: no network, no API key. Run: python -m unittest discover -s tests -v"""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from litagent import citations, pubmed, trials, evaluate  # noqa: E402
from litagent.agent import Agent  # noqa: E402
from litagent.llm import LLM  # noqa: E402
from litagent.models import Doc  # noqa: E402
from litagent.retrieval import Index  # noqa: E402

PUBMED_XML = """<PubmedArticleSet><PubmedArticle><MedlineCitation><PMID>111</PMID><Article>
<Journal><Title>J Test</Title><JournalIssue><PubDate><Year>2022</Year></PubDate></JournalIssue></Journal>
<ArticleTitle>Anti-TNF response in ulcerative colitis</ArticleTitle>
<Abstract><AbstractText Label="RESULTS">Response was 40% at week 8.</AbstractText></Abstract>
</Article></MedlineCitation></PubmedArticle></PubmedArticleSet>"""

CT_JSON = {"studies": [{"protocolSection": {
    "identificationModule": {"nctId": "NCT0000001", "briefTitle": "Trial A"},
    "statusModule": {"overallStatus": "COMPLETED", "startDateStruct": {"date": "2020-01"}},
    "designModule": {"phases": ["PHASE3"]}, "conditionsModule": {"conditions": ["UC"]},
    "descriptionModule": {"briefSummary": "Tests drug X."}}}]}


class Scripted(LLM):
    def __init__(self, replies):
        self.replies = list(replies)

    def complete(self, system, messages):
        return self.replies.pop(0)


def docs(*ids):
    return [Doc(id=i, title=f"t {i}", text="ulcerative colitis anti-TNF response", source="pubmed") for i in ids]


class TestParsers(unittest.TestCase):
    def test_pubmed(self):
        d = pubmed.parse_articles(PUBMED_XML)[0]
        self.assertEqual((d.id, d.year, d.journal), ("PMID:111", "2022", "J Test"))
        self.assertIn("RESULTS: Response was 40%", d.text)

    def test_trials(self):
        d = trials.parse_studies(CT_JSON)[0]
        self.assertEqual(d.id, "NCT:NCT0000001")
        self.assertIn("PHASE3", d.text)


class TestCitations(unittest.TestCase):
    def test_valid(self):
        c = citations.check("Response was 40% at week eight in this cohort [PMID:111].", {"PMID:111"})
        self.assertTrue(c["citation_valid"])
        self.assertEqual(c["uncited_sentences"], [])

    def test_grouped_citation(self):
        a = "Many patients lose response over time in practice [PMID:111, PMID:222]."
        c = citations.check(a, {"PMID:111", "PMID:222"})
        self.assertEqual(c["cited"], ["PMID:111", "PMID:222"])
        self.assertTrue(c["citation_valid"])
        self.assertEqual(c["uncited_sentences"], [])
        c2 = citations.check(a, {"PMID:111"})
        self.assertEqual(c2["invalid"], ["PMID:222"])

    def test_fabricated_id_flagged(self):
        c = citations.check("Response was 40% at week eight in this cohort [PMID:999].", {"PMID:111"})
        self.assertFalse(c["citation_valid"])
        self.assertEqual(c["invalid"], ["PMID:999"])

    def test_uncited_sentence_flagged(self):
        c = citations.check("This drug clearly works well for every patient in every setting.", {"PMID:111"})
        self.assertEqual(len(c["uncited_sentences"]), 1)

    def test_refusal(self):
        c = citations.check("Insufficient evidence retrieved to answer this.", set())
        self.assertTrue(c["is_refusal"])
        self.assertEqual(c["uncited_sentences"], [])


class TestRetrieval(unittest.TestCase):
    def test_ranking(self):
        idx = Index()
        idx.add([Doc("PMID:1", "cats", "feline grooming habits", "pubmed"),
                 Doc("PMID:2", "colitis", "ulcerative colitis anti-TNF response", "pubmed")])
        self.assertEqual(idx.top_k("anti-TNF in colitis", 1)[0].id, "PMID:2")

    def test_empty(self):
        self.assertEqual(Index().top_k("x"), [])


class TestAgent(unittest.TestCase):
    def test_search_then_cited_answer(self):
        llm = Scripted([
            json.dumps({"action": "search_pubmed", "query": "anti-TNF UC"}),
            json.dumps({"action": "answer", "text": "Response was 40% at week eight in this cohort [PMID:111]."}),
        ])
        a = Agent(llm, pubmed_search=lambda q: docs("PMID:111"), trials_search=lambda q: [])
        r = a.run("q")
        self.assertTrue(r.check["citation_valid"])
        self.assertEqual(r.retrieved_ids, ["PMID:111"])

    def test_hallucinated_citation_is_caught(self):
        llm = Scripted([
            json.dumps({"action": "search_pubmed", "query": "x"}),
            json.dumps({"action": "answer", "text": "Response was 40% at week eight in this cohort [PMID:777]."}),
        ])
        r = Agent(llm, pubmed_search=lambda q: docs("PMID:111")).run("q")
        self.assertEqual(r.check["invalid"], ["PMID:777"])

    def test_tool_error_does_not_crash(self):
        def boom(q):
            raise RuntimeError("network down")
        llm = Scripted([
            json.dumps({"action": "search_pubmed", "query": "x"}),
            json.dumps({"action": "answer", "text": "Insufficient evidence retrieved; the search failed."}),
        ])
        r = Agent(llm, pubmed_search=boom).run("q")
        self.assertTrue(r.check["is_refusal"])

    def test_bad_json_then_recover(self):
        llm = Scripted(["not json", json.dumps({"action": "answer", "text": "Insufficient evidence retrieved."})])
        r = Agent(llm).run("q")
        self.assertTrue(r.check["is_refusal"])

    def test_empty_answer_is_retried(self):
        llm = Scripted([
            json.dumps({"action": "answer", "text": ""}),
            json.dumps({"action": "answer", "text": "Insufficient evidence retrieved."}),
        ])
        r = Agent(llm).run("q")
        self.assertTrue(r.answer)
        self.assertTrue(r.check["is_refusal"])

    def test_answer_under_other_key_is_accepted(self):
        llm = Scripted([
            json.dumps({"action": "search_pubmed", "query": "x"}),
            json.dumps({"action": "answer", "answer": "Response was 40% at week eight in this cohort [PMID:111]."}),
        ])
        r = Agent(llm, pubmed_search=lambda q: docs("PMID:111")).run("q")
        self.assertTrue(r.check["citation_valid"])

    def test_step_limit_forces_answer(self):
        s = json.dumps({"action": "search_pubmed", "query": "x"})
        llm = Scripted([s, s, json.dumps({"action": "answer", "text": "Insufficient evidence retrieved."})])
        r = Agent(llm, pubmed_search=lambda q: [], max_steps=2).run("q")
        self.assertTrue(r.check["is_refusal"])


class TestEval(unittest.TestCase):
    def test_scoring(self):
        llm = Scripted([
            json.dumps({"action": "search_pubmed", "query": "x"}),
            json.dumps({"action": "answer", "text": "Response was 40% at week eight in this cohort [PMID:111]."}),
            json.dumps({"action": "answer", "text": "Insufficient evidence retrieved."}),
        ])
        a = Agent(llm, pubmed_search=lambda q: docs("PMID:111"))
        r1 = evaluate.score_one({"question": "a", "expect": "answer", "must_cite_any": ["PMID:111"]}, a.run("a"))
        r2 = evaluate.score_one({"question": "b", "expect": "refuse"}, a.run("b"))
        self.assertTrue(r1["pass"] and r2["pass"])
        s = evaluate.summarize([r1, r2])
        self.assertEqual((s["pass_rate"], s["fabricated_citation_count"]), (1.0, 0))


class TestEvalRun(unittest.TestCase):
    def test_run_survives_errors_and_saves(self):
        import tempfile
        d = tempfile.mkdtemp()
        q = os.path.join(d, "q.jsonl")
        with open(q, "w") as f:
            f.write(json.dumps({"id": "a1", "query": "x"}) + "\n")
            f.write(json.dumps({"id": "edge_1", "question": "y"}) + "\n")

        class Boom(LLM):
            n = 0

            def complete(self, system, messages):
                Boom.n += 1
                if Boom.n == 1:
                    raise RuntimeError("api down")
                return json.dumps({"action": "answer", "text": "Insufficient evidence retrieved."})

        out = evaluate.run(q, Agent(Boom()), pause=0)
        self.assertEqual(out["summary"]["n_errors"], 1)
        self.assertTrue(out["rows"][1]["pass"])  # edge_ -> "either" -> honest refusal passes
        evaluate.save(out, os.path.join(d, "r.json"), os.path.join(d, "r.csv"))
        self.assertTrue(os.path.exists(os.path.join(d, "r.csv")))


if __name__ == "__main__":
    unittest.main()
