"""Answer generators.

- StubGenerator: deterministic, offline. Lets the evaluation and CI run without
  a model or a tenant, and gives a reproducible baseline.
- AzureOpenAIGenerator: calls a model deployed in Microsoft Foundry (Azure OpenAI
  endpoint). Configure with environment variables, never in code.
"""

from __future__ import annotations

import json
import os
import re
import time
import urllib.request
from dataclasses import dataclass

from .kb import Article, tokens

REFUSAL = "I don't have approved guidance on that. I can raise a ticket so the IT helpdesk can help you."

SYSTEM_PROMPT = (
    "You are the IT helpdesk assistant. Answer ONLY from the provided knowledge articles. "
    "Cite every article you use as [KB-xxx]. If the articles do not answer the question, reply exactly: "
    f"\"{REFUSAL}\" Never invent steps, links or policies. Keep answers under 120 words."
)


@dataclass
class Result:
    answer: str
    latency_ms: float
    prompt_tokens: int
    completion_tokens: int


def approx_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def build_context(hits: list[tuple[float, Article]]) -> str:
    return "\n\n".join(f"[{a.id}] {a.title}\n{a.body}" for _, a in hits)


class StubGenerator:
    name = "stub"

    def answer(self, question: str, hits: list[tuple[float, Article]]) -> Result:
        start = time.perf_counter()
        if not hits:
            text = REFUSAL
        else:
            top = hits[0][1]
            q = set(tokens(question))
            sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", top.body) if s.strip()]
            ranked = sorted(sentences, key=lambda s: len(q & set(tokens(s))), reverse=True)[:2]
            ordered = [s for s in sentences if s in ranked]
            text = " ".join(ordered) + f" [{top.id}]"
        prompt = SYSTEM_PROMPT + build_context(hits) + question
        return Result(text, (time.perf_counter() - start) * 1000, approx_tokens(prompt), approx_tokens(text))


class AzureOpenAIGenerator:
    name = "azure-openai"

    def __init__(self) -> None:
        self.endpoint = os.environ["AZURE_OPENAI_ENDPOINT"].rstrip("/")
        self.key = os.environ["AZURE_OPENAI_API_KEY"]
        self.deployment = os.environ["AZURE_OPENAI_DEPLOYMENT"]
        self.api_version = os.environ.get("AZURE_OPENAI_API_VERSION", "2024-10-21")

    def answer(self, question: str, hits: list[tuple[float, Article]]) -> Result:
        if not hits:  # no grounding -> refuse without spending tokens
            return Result(REFUSAL, 0.0, 0, 0)
        body = {
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Knowledge articles:\n{build_context(hits)}\n\nQuestion: {question}"},
            ],
            "temperature": 0,
            "max_tokens": 300,
        }
        url = f"{self.endpoint}/openai/deployments/{self.deployment}/chat/completions?api-version={self.api_version}"
        req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "api-key": self.key})
        start = time.perf_counter()
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.load(resp)
        latency = (time.perf_counter() - start) * 1000
        usage = data.get("usage", {})
        return Result(data["choices"][0]["message"]["content"].strip(), latency,
                      usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0))
