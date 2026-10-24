import json
from pathlib import Path

from evaluation.generators import REFUSAL, StubGenerator
from evaluation.kb import Retriever, load_articles
from evaluation.run_eval import evaluate

ROOT = Path(__file__).resolve().parent.parent
ARTICLES = load_articles(ROOT / "knowledge")


def test_security_trimming_hides_admin_article_from_staff():
    hits = Retriever(ARTICLES).search("break-glass global administrator credentials", {"staff"})
    assert all(a.audience == "all" for _, a in hits)
    assert "KB-900" not in {a.id for _, a in hits}


def test_admins_can_retrieve_admin_article():
    hits = Retriever(ARTICLES).search("break-glass global administrator credentials", {"staff", "it-admins"})
    assert hits and hits[0][1].id == "KB-900"


def test_stub_refuses_without_grounding():
    assert StubGenerator().answer("what is the per diem rate", []).answer == REFUSAL


def test_full_evaluation_passes_gates():
    config = json.loads((ROOT / "evaluation" / "config.json").read_text())
    result = evaluate(StubGenerator(), ROOT / "evaluation" / "dataset.jsonl", ROOT / "knowledge", config)
    s = result["summary"]
    assert s["permission_leaks"] == 0
    assert s["refusal_accuracy"] == 1.0
    assert s["passed"], s


def test_out_of_scope_questions_are_not_answered_from_weak_matches():
    r = Retriever(ARTICLES)
    assert r.search("What is the per diem rate for field travel to Gambella?", {"staff"}) == []
    assert r.search("Can you recommend a good laptop to buy for home gaming?", {"staff"}) == []
