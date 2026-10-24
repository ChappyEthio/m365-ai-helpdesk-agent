"""Run the agent evaluation.

Usage:
    python -m evaluation.run_eval                    # offline stub baseline
    python -m evaluation.run_eval --generator azure  # real model in Microsoft Foundry

Measures what the job description asks for: answer quality, grounding,
handling of unreliable answers (refusals), permission safety, latency and cost.
Exits with code 1 if a quality gate fails, so it can block a deployment in CI.
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from datetime import UTC, datetime
from pathlib import Path

from .generators import REFUSAL, AzureOpenAIGenerator, StubGenerator
from .kb import Retriever, load_articles

ROOT = Path(__file__).resolve().parent.parent
CITE = re.compile(r"\[(KB-\d+)\]")


def is_refusal(answer: str) -> bool:
    return answer.strip().startswith(REFUSAL[:40])


def p95(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, round(0.95 * (len(ordered) - 1)))]


def evaluate(generator, dataset_path: Path, kb_path: Path, config: dict) -> dict:
    articles = load_articles(kb_path)
    by_id = {a.id: a for a in articles}
    retriever = Retriever(articles)
    price = config["pricing_usd_per_1k_tokens"]
    rows = []
    for line in dataset_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        case = json.loads(line)
        groups = set(case["groups"])
        hits = retriever.search(case["question"], groups)
        res = generator.answer(case["question"], hits)
        cited = set(CITE.findall(res.answer))
        retrieved = {a.id for _, a in hits}
        leaked = sorted(s for s in cited | retrieved if s in by_id and not by_id[s].allowed_for(groups))
        refused = is_refusal(res.answer)
        expected = case["expected_source"]
        must = case.get("must_include", [])
        coverage = (sum(k.lower() in res.answer.lower() for k in must) / len(must)) if must else None
        rows.append({
            "id": case["id"],
            "question": case["question"],
            "groups": sorted(groups),
            "answerable": expected is not None,
            "retrieval_hit": (expected in retrieved) if expected else None,
            "citation_correct": (expected in cited) if expected else None,
            "refusal_correct": (not refused) if expected else refused,
            "keyword_coverage": coverage,
            "permission_leaks": leaked,
            "latency_ms": round(res.latency_ms, 1),
            "cost_usd": round(res.prompt_tokens / 1000 * price["prompt"] + res.completion_tokens / 1000 * price["completion"], 6),
            "answer": res.answer,
        })

    answerable = [r for r in rows if r["answerable"]]
    covs = [r["keyword_coverage"] for r in rows if r["keyword_coverage"] is not None]
    lat = [r["latency_ms"] for r in rows]
    summary = {
        "generator": generator.name,
        "cases": len(rows),
        "retrieval_hit_rate": round(sum(r["retrieval_hit"] for r in answerable) / len(answerable), 3),
        "citation_accuracy": round(sum(r["citation_correct"] for r in answerable) / len(answerable), 3),
        "refusal_accuracy": round(sum(r["refusal_correct"] for r in rows) / len(rows), 3),
        "keyword_coverage": round(statistics.mean(covs), 3) if covs else None,
        "permission_leaks": sum(len(r["permission_leaks"]) for r in rows),
        "latency_p50_ms": round(statistics.median(lat), 1),
        "latency_p95_ms": round(p95(lat), 1),
        "total_cost_usd": round(sum(r["cost_usd"] for r in rows), 6),
    }
    g = config["gates"]
    summary["gates"] = {
        "citation_accuracy": summary["citation_accuracy"] >= g["min_citation_accuracy"],
        "refusal_accuracy": summary["refusal_accuracy"] >= g["min_refusal_accuracy"],
        "permission_leaks": summary["permission_leaks"] <= g["max_permission_leaks"],
        "keyword_coverage": (summary["keyword_coverage"] or 0) >= g["min_keyword_coverage"],
        "latency_p95": summary["latency_p95_ms"] <= g["max_p95_latency_ms"],
    }
    summary["passed"] = all(summary["gates"].values())
    return {"summary": summary, "cases": rows}


def to_markdown(result: dict) -> str:
    s = result["summary"]
    out = [f"# Evaluation report ({s['generator']})", "",
           f"Run: {datetime.now(UTC):%Y-%m-%d %H:%M} UTC  ·  Cases: {s['cases']}  ·  **{'PASSED' if s['passed'] else 'FAILED'}**", "",
           "| Metric | Value | Gate |", "|---|---|---|"]
    gate_of = {"citation_accuracy": "citation_accuracy", "refusal_accuracy": "refusal_accuracy",
               "permission_leaks": "permission_leaks", "keyword_coverage": "keyword_coverage", "latency_p95_ms": "latency_p95"}
    for key in ["retrieval_hit_rate", "citation_accuracy", "refusal_accuracy", "keyword_coverage",
                "permission_leaks", "latency_p50_ms", "latency_p95_ms", "total_cost_usd"]:
        gate = gate_of.get(key)
        mark = ("pass" if s["gates"][gate] else "FAIL") if gate else "-"
        out.append(f"| {key} | {s[key]} | {mark} |")
    out += ["", "| Case | Groups | Expected behaviour | Result | Answer |", "|---|---|---|---|---|"]
    for r in result["cases"]:
        exp = "answer with citation" if r["answerable"] else "refuse"
        ok = r["refusal_correct"] and (r["citation_correct"] in (None, True)) and not r["permission_leaks"]
        ans = r["answer"].replace("|", "/")[:140]
        out.append(f"| {r['id']} | {', '.join(r['groups'])} | {exp} | {'pass' if ok else 'FAIL'} | {ans} |")
    return "\n".join(out) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--generator", choices=["stub", "azure"], default="stub")
    ap.add_argument("--dataset", default=str(ROOT / "evaluation" / "dataset.jsonl"))
    ap.add_argument("--kb", default=str(ROOT / "knowledge"))
    ap.add_argument("--out", default=str(ROOT / "evaluation" / "reports"))
    args = ap.parse_args(argv)
    config = json.loads((ROOT / "evaluation" / "config.json").read_text())
    generator = StubGenerator() if args.generator == "stub" else AzureOpenAIGenerator()
    result = evaluate(generator, Path(args.dataset), Path(args.kb), config)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / f"latest-{generator.name}.json").write_text(json.dumps(result, indent=2))
    (out / f"latest-{generator.name}.md").write_text(to_markdown(result))
    print(json.dumps(result["summary"], indent=2))
    return 0 if result["summary"]["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
