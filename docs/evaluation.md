# Evaluating the agent

Run: `python -m evaluation.run_eval` (offline baseline) or `--generator azure` (model deployed in Microsoft Foundry; set `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_DEPLOYMENT`).

## What is measured

| Metric | Meaning | Gate |
|---|---|---|
| Retrieval hit rate | The right article was retrieved | report only |
| Citation accuracy | The answer cites the expected article | >= 0.8 |
| Refusal accuracy | Answers what it should, refuses what it should (out of scope, restricted) | 1.0 |
| Keyword coverage | Key facts present in the answer | >= 0.6 |
| Permission leaks | Restricted content retrieved or cited for a user without access | 0 |
| Latency p50 / p95 | Response time | p95 <= 4 s |
| Cost | Token cost per run from `config.json` rates | report only |

The script exits with code 1 when a gate fails, so CI blocks the change.

## What the evaluation caught (v1 → v2)

The first run **failed the refusal gate (0.8)**. Two out-of-scope questions, about travel per diem and a gaming laptop,
were answered from unrelated articles. They shared single words ("field", "laptop") with the VPN and printer articles,
which was enough for a keyword score.

**Fix:** retrieval now also requires the article to cover at least 40% of the question's meaning (IDF-weighted terms),
not just to share one word. Out-of-scope questions scored 0.24 and the weakest valid question 0.51, so the 0.4 threshold separates them.
A regression test (`test_out_of_scope_questions_are_not_answered_from_weak_matches`) keeps it fixed.
Result: refusal accuracy 1.0, citation accuracy 1.0, 0 permission leaks.

The same loop applies to the live agent: every unanswered or wrong answer from the pilot becomes a new test case.
