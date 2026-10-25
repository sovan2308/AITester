r"""Project - a retry loop around REAL Playwright tests.

Lesson 004 scripted its outcomes so the demo was repeatable. This runs the real
thing: pytest drives Chromium against TTACart, writes a JUnit report, and the
graph reads that report to decide what to do next.

    run_tests -> read_report -> should_retry? --(failures left)--> run_tests
                                             \--(done)----------> summarise

Only the failed tests are re-run on a retry, which is what you would do by hand.
A test that passes on attempt 2 is FLAKY. One that fails every attempt is a REAL
FAILURE. That distinction is the whole point of the loop.

    .venv/bin/python3.13 src/Project_PW_FlakyFinder.py
"""
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph

MAX_ATTEMPTS = 2                       # 1 run + 1 retry. Raise this for more.
HEADED = True                          # watch the browser. False is faster in CI.
SLOW_MO_MS = 600                       # slow each action down so it is followable.
HERE = Path(__file__).parent
TESTS = HERE / "tests" / "test_login.py"
REPORT = HERE / "report.xml"
PYTHON = HERE.parent / ".venv" / "bin" / "python3.13"   # 3.12 in this venv has no pytest


class State(TypedDict):
    attempts: int
    failed: list[str]          # test ids still red after the last attempt
    history: list[dict]        # one entry per attempt
    verdict: str


# ---------------------------------------------------------------- nodes
def run_tests(state: State) -> dict:
    """Run pytest. On a retry, run ONLY the tests that failed last time."""
    attempt = state["attempts"] + 1
    targets = state["failed"] or [str(TESTS)]
    print(f"\n-- attempt {attempt}: pytest {' '.join(Path(t).name for t in targets)}")
    watch = ["--headed", f"--slowmo={SLOW_MO_MS}"] if HEADED else []
    subprocess.run(
        [str(PYTHON), "-m", "pytest", *targets, *watch, f"--junitxml={REPORT}", "-q"],
        cwd=HERE.parent, capture_output=True, text=True,
    )                                   # exit code ignored: the report is the truth
    return {"attempts": attempt}


def read_report(state: State) -> dict:
    """Parse the JUnit XML pytest just wrote. This is the agent's only evidence."""
    passed, failed = [], []
    for tc in ET.parse(REPORT).getroot().iter("testcase"):
        test_id = f"{TESTS}::{tc.get('name')}"
        broke = any(c.tag in ("failure", "error") for c in tc)
        (failed if broke else passed).append(test_id)
    for t in passed:
        print(f"   PASS  {t.split('::')[-1]}")
    for t in failed:
        print(f"   FAIL  {t.split('::')[-1]}")
    entry = {"attempt": state["attempts"], "passed": passed, "failed": failed}
    return {"failed": failed, "history": state["history"] + [entry]}


def should_retry(state: State) -> Literal["run_tests", "summarise"]:
    """The conditional edge. Pointing back at run_tests is what makes it a loop."""
    if not state["failed"]:
        return "summarise"
    if state["attempts"] < MAX_ATTEMPTS:
        return "run_tests"
    return "summarise"


def summarise(state: State) -> dict:
    """Compare every attempt to tell a flaky test from a broken one."""
    ever_failed = {t for h in state["history"] for t in h["failed"]}
    still_failing = set(state["failed"])
    lines = []
    for test in sorted({t for h in state["history"] for t in h["passed"] + h["failed"]}):
        name = test.split("::")[-1]
        if test in still_failing:
            lines.append(f"REAL FAILURE  {name}  (red in all {state['attempts']} attempt(s))")
        elif test in ever_failed:
            lines.append(f"FLAKY         {name}  (failed, then passed on retry)")
        else:
            lines.append(f"STABLE PASS   {name}")
    return {"verdict": "\n".join(lines)}


# ---------------------------------------------------------------- graph
builder = StateGraph(State)
builder.add_node("run_tests", run_tests)
builder.add_node("read_report", read_report)
builder.add_node("summarise", summarise)

builder.add_edge(START, "run_tests")
builder.add_edge("run_tests", "read_report")
builder.add_conditional_edges("read_report", should_retry)   # <- the loop lives here
builder.add_edge("summarise", END)

app = builder.compile()

if __name__ == "__main__":
    result = app.invoke({"attempts": 0, "failed": [], "history": [], "verdict": ""})

    print(f"\n{'=' * 60}\nVERDICT after {result['attempts']} attempt(s)\n{'=' * 60}")
    print(result["verdict"])

    print("\nThe graph as Mermaid (paste into mermaid.live):")
    print(app.get_graph().draw_mermaid())
