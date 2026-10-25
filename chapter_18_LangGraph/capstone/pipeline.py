"""Capstone: Jira requirement -> analysis -> test plan + cases -> review -> run on TTACart
-> failure triage -> HTML report. One LangGraph, seven nodes.

    python pipeline.py VWO-105           # fetch, plan, run, report
    python pipeline.py VWO-105 --send    # ...and email the report
"""
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field, field_validator

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "chapters"))
from llm import get_llm  # noqa: E402  chapter 18's Groq helper, reads chapter_18_LangGraph/.env

import executor, jira, report  # noqa: E402

RUNS = Path(__file__).parent / "reports"
# Low reasoning effort: measured 3/3 valid plans vs 0/3 at the default, which broke the tool-call JSON.
llm = get_llm(reasoning_effort="low", max_tokens=8192)
MAX_REVIEWS = 2  # plan -> review -> (one rewrite) -> review -> run anyway


class Step(BaseModel):
    do: Literal["goto", "fill", "click", "select", "see", "not see", "count", "url"]
    target: str = Field("", description="a data-test id; empty for goto and url")
    value: str | int | float = ""  # models send count values as numbers; Groq rejects that for a str field

    @field_validator("value")
    @classmethod
    def as_text(cls, v):
        return str(v)


class Case(BaseModel):
    id: str = Field(description="TC-01, TC-02, ...")
    title: str
    priority: Literal["P0", "P1", "P2"]
    steps: list[Step]


class Plan(BaseModel):
    scope: str = Field(description="2-3 sentences: what is tested and what is not")
    risks: list[str]
    cases: list[Case]


class Review(BaseModel):
    approved: bool
    feedback: str = Field(description="what to add or fix; empty when approved")


class Verdict(BaseModel):
    id: str
    category: Literal["product_bug", "test_bug", "environment", "flaky"]
    reason: str = Field(description="one sentence")


class Triage(BaseModel):
    verdicts: list[Verdict]


class State(TypedDict, total=False):
    key: str
    send: bool
    ticket: dict
    analysis: str
    plan: dict
    feedback: str
    reviews: int
    out: str
    results: list
    triage: list
    report: str


PAGE_MAP = "\n".join(f"  '{page}': {ids}" for page, ids in executor.PAGES.items())
APP = f"""TTACart, a demo shop at {executor.BASE_URL}
Pages and the data-test ids on each ('' is the login page, <id> is a product id):
{PAGE_MAP}
  every page after login: {executor.AFTER_LOGIN}
  shopping-cart-badge only exists while the cart has items: check an empty cart with not see shopping-cart-badge
Users: standard_user, locked_out_user, problem_user, performance_glitch_user, error_user, visual_user. Password: tta_secret
Products (id: name, price): {json.dumps(executor.PRODUCTS)}
Texts: page titles 'Products', 'Your Cart', 'Checkout: Your Information', 'Checkout: Overview', 'Checkout: Complete'.
Overview labels look like 'Item total: $65.98', 'Tax: $5.28' (8%), 'Total: $71.26'. Order header 'Thank you for your order!'.
Errors: 'Epic sadface: Sorry, this user has been locked out.', 'Error: First Name is required' (Last Name, Postal Code alike).
Step actions: goto(value=page) fill(target,value) click(target) select(target,value: az|za|lohi|hilo)
see(target,value=text it contains, or '' for visible) not see(target, value='' or text) count(target,value=number)
url(value=part of the url, never empty).
To prove you are still on the login page, see login-button. url checks need a page name such as inventory.html."""


def ask(schema, prompt):
    """Structured LLM call. json_schema makes Groq decode straight into the schema, so the model
    can't skip the format or break the JSON; 3 tries cover rate limits and hiccups."""
    structured = llm.with_structured_output(schema, method="json_schema")
    return structured.with_retry(stop_after_attempt=3).invoke(prompt)


def fetch(s):
    return {"ticket": jira.fetch(s["key"]), "reviews": 0}


def analyse(s):
    t = s["ticket"]
    msg = llm.invoke("You are a senior QA engineer. From this requirement, list the testable "
                     "features, acceptance criteria and risks as short bullets.\n\n"
                     f"{t['summary']}\n\n{t['description']}")
    return {"analysis": msg.content}


def plan(s):
    prompt = ("Write a test plan with 5 to 8 automated UI test cases for the app below. Cover the "
              "acceptance criteria first (P0), then personas and form validation. Each case tests one "
              "thing in at most 12 steps, starting with goto '' and a login. Use only the ids listed "
              "for the page you are on. These actions can't resize the window, compare screenshots or "
              "time things: put those checks under risks as manual, don't write cases for them."
              f"\n\nANALYSIS:\n{s['analysis']}\n\nAPP:\n{APP}")
    if s.get("feedback"):
        prompt += f"\n\nA reviewer rejected your last plan. Fix this:\n{s['feedback']}"
    return {"plan": ask(Plan, prompt).model_dump()}


def review(s):
    """Rules check every step against the real app map; then an LLM, like a senior QA, looks for
    steps that contradict the app and acceptance criteria nobody tests."""
    bad = [f"{c['id']}: {p}" for c in s["plan"]["cases"] for p in executor.problems(c)]
    cases = "\n".join(f"{c['id']} [{c['priority']}] {c['title']}: "
                      + "; ".join(f"{st['do']} {st['target']} {st['value']}".strip() for st in c["steps"])
                      for c in s["plan"]["cases"])
    r = ask(Review,
        "You review automated UI test cases like a senior QA. Reject if a step contradicts the app "
        "facts (for example expecting something the app never shows) or if an acceptance criterion "
        "that UI steps can check has no test; name the case and step to fix. Visual, responsive and "
        "timing checks are manual, so don't ask for them. The plan must stay at 8 cases or fewer."
        f"\n\nAPP FACTS:\n{APP}\n\nANALYSIS:\n{s['analysis']}\n\nCASES:\n{cases}")
    feedback = "\n".join(([] if r.approved else [r.feedback]) + bad)
    return {"feedback": feedback, "reviews": s["reviews"] + 1}


def after_review(s) -> Literal["plan", "execute"]:
    return "plan" if s["feedback"] and s["reviews"] < MAX_REVIEWS else "execute"


def execute(s):
    out = RUNS / f"{s['key']}-{datetime.now():%Y%m%d-%H%M%S}"
    out.mkdir(parents=True)
    (out / "plan.json").write_text(json.dumps(s["plan"], indent=2))
    cases = s["plan"]["cases"]
    runnable = [c for c in cases if not executor.problems(c)]
    skipped = [{**c, "status": "skipped", "error": "; ".join(executor.problems(c))}
               for c in cases if executor.problems(c)]
    return {"out": str(out), "results": executor.run(runnable, out) + skipped}


def after_execute(s) -> Literal["triage", "write_report"]:
    return "triage" if any(r["status"] == "failed" for r in s["results"]) else "write_report"


def story(r):
    """A failed case as the triage model sees it: which steps passed, which one failed, and why."""
    mark = lambda n: "ok  " if n < r["step"] else "FAIL" if n == r["step"] else "--  "
    steps = "\n".join(f"  {mark(n)} {st['do']} {st['target']} {st['value']}" for n, st in enumerate(r["steps"], 1))
    return f"{r['id']} {r['title']}\n{steps}\n  error: {r['error']}"


def triage(s):
    failed = "\n\n".join(story(r) for r in s["results"] if r["status"] == "failed")
    t = ask(Triage,
        "Classify each failed UI test. Check the step that failed against the app facts first: if the "
        "test expected something the app never does, it is a test_bug, not a product_bug. TTACart also "
        "has deliberate persona bugs: problem_user ignores sorting and breaks checkout, error_user "
        "randomly ignores clicks, performance_glitch_user logs in 4s late.\n\n"
        f"APP FACTS:\n{APP}\n\nFAILED TESTS:\n{failed}")
    return {"triage": [v.model_dump() for v in t.verdicts]}


def write_report(s):
    path = report.write(s)
    if s.get("send") and os.getenv("SMTP_HOST"):
        failed = sum(r["status"] == "failed" for r in s["results"])
        report.email(path, f"[QA] {s['key']}: {len(s['results']) - failed} passed, {failed} failed")
    elif s.get("send"):
        print("email skipped: set SMTP_HOST and friends in .env (see README)")
    return {"report": str(path)}


g = StateGraph(State)
for name, fn in [("fetch", fetch), ("analyse", analyse), ("plan", plan), ("review", review),
                 ("execute", execute), ("triage", triage), ("write_report", write_report)]:
    g.add_node(name, fn)
g.add_edge(START, "fetch")
g.add_edge("fetch", "analyse")
g.add_edge("analyse", "plan")
g.add_edge("plan", "review")
g.add_conditional_edges("review", after_review, ["plan", "execute"])
g.add_conditional_edges("execute", after_execute, ["triage", "write_report"])
g.add_edge("triage", "write_report")
g.add_edge("write_report", END)
app = g.compile()


if __name__ == "__main__":
    key = next((a for a in sys.argv[1:] if not a.startswith("--")), "VWO-105")
    final = app.invoke({"key": key, "send": "--send" in sys.argv}, {"recursion_limit": 20})
    for r in final["results"]:
        print(f"{r['status']:>8}  {r['id']}  {r['title']}")
    print(f"\nreport: {final['report']}")
