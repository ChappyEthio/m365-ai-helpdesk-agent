"""Permission-aware retrieval over the knowledge base.

Mirrors how the Copilot Studio agent grounds on SharePoint: a user only ever
sees content their groups allow (security trimming). Filtering happens BEFORE
ranking, so restricted text can never reach the model prompt.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from pathlib import Path

WORD = re.compile(r"[a-z0-9]+")
STOP = {"a", "an", "the", "and", "or", "to", "of", "in", "on", "for", "is", "are", "be", "with", "your", "you", "if", "it", "this", "that", "by", "from", "at", "as", "not", "do", "i", "my", "me", "can", "how", "what"}


def tokens(text: str) -> list[str]:
    return [t for t in WORD.findall(text.lower()) if t not in STOP and len(t) > 1]


@dataclass
class Article:
    id: str
    title: str
    audience: str
    body: str
    terms: list[str] = field(default_factory=list)

    def allowed_for(self, groups: set[str]) -> bool:
        return self.audience == "all" or self.audience in groups


def load_articles(folder: str | Path) -> list[Article]:
    articles = []
    for path in sorted(Path(folder).glob("*.md")):
        raw = path.read_text(encoding="utf-8")
        meta, body = {}, raw
        if raw.startswith("---"):
            _, header, body = raw.split("---", 2)
            for line in header.strip().splitlines():
                key, _, value = line.partition(":")
                meta[key.strip()] = value.strip()
        art = Article(meta.get("id", path.stem), meta.get("title", path.stem), meta.get("audience", "all"), body.strip())
        art.terms = tokens(art.title + " " + art.title + " " + art.body)  # title counts double
        articles.append(art)
    return articles


class Retriever:
    """Small BM25 retriever. In production this is Azure AI Search with security filters."""

    def __init__(self, articles: list[Article], k1: float = 1.5, b: float = 0.75):
        self.articles = articles
        self.k1, self.b = k1, b
        self.avgdl = sum(len(a.terms) for a in articles) / max(len(articles), 1)
        n = len(articles)
        df: dict[str, int] = {}
        for a in articles:
            for t in set(a.terms):
                df[t] = df.get(t, 0) + 1
        self.idf = {t: math.log(1 + (n - d + 0.5) / (d + 0.5)) for t, d in df.items()}

    def _score(self, query: list[str], art: Article) -> float:
        score = 0.0
        dl = len(art.terms)
        for q in set(query):
            tf = art.terms.count(q)
            if tf:
                score += self.idf.get(q, 0) * tf * (self.k1 + 1) / (tf + self.k1 * (1 - self.b + self.b * dl / self.avgdl))
        return score

    def coverage(self, query: list[str], art: Article) -> float:
        """Share of the question's meaning (IDF-weighted terms) that the article covers.

        A single shared word ("laptop", "field") gives a BM25 score but low coverage,
        which is how out-of-scope questions get confidently wrong answers.
        """
        q = set(query)
        total = sum(self.idf.get(t, 1.0) for t in q)
        if not total:
            return 0.0
        present = set(art.terms)
        return sum(self.idf.get(t, 1.0) for t in q if t in present) / total

    def search(self, question: str, user_groups: set[str], top_k: int = 3,
               min_score: float = 1.5, min_coverage: float = 0.4):
        query = tokens(question)
        visible = [a for a in self.articles if a.allowed_for(user_groups)]  # security trimming first
        scored = [(self._score(query, a), a) for a in visible]
        scored = [(s, a) for s, a in scored if s >= min_score and self.coverage(query, a) >= min_coverage]
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[:top_k]
