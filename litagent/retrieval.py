"""Small in-memory TF-IDF index. Re-ranks what the live APIs returned."""
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class Index:
    def __init__(self):
        self.docs = {}

    def add(self, docs):
        for d in docs:
            self.docs[d.id] = d

    def top_k(self, query: str, k: int = 5) -> list:
        docs = list(self.docs.values())
        if not docs:
            return []
        corpus = [f"{d.title} {d.text}" for d in docs]
        vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
        try:
            m = vec.fit_transform(corpus + [query])
        except ValueError:  # empty vocabulary
            return docs[:k]
        sims = cosine_similarity(m[-1], m[:-1]).ravel()
        order = sims.argsort()[::-1][:k]
        return [docs[i] for i in order]
