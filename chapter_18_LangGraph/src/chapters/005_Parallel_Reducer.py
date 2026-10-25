"""005 - Parallel branches and reducers.

Three check suites fan out from START and run in the same step. They all write
to `results`. Without a reducer, LangGraph refuses: two writers, one key, which
one wins? Annotated[list, operator.add] says "append, don't overwrite".
"""
import operator
from typing import Annotated, TypedDict

from langgraph.errors import InvalidUpdateError
from langgraph.graph import END, START, StateGraph


class State(TypedDict):
    results: Annotated[list[str], operator.add]   # reducer: concatenate
    summary: str


def api_checks(state):  return {"results": ["api: 42/42 passed"]}
def ui_checks(state):   return {"results": ["ui: 118/120 passed"]}
def perf_checks(state): return {"results": ["perf: p95 380ms (budget 500ms)"]}


def summarize(state) -> dict:   # untyped: LangGraph reads node hints as input schemas
    return {"summary": f"{len(state['results'])} suites reported"}


def build(state_cls):
    b = StateGraph(state_cls)
    for name, fn in [("api", api_checks), ("ui", ui_checks), ("perf", perf_checks)]:
        b.add_node(name, fn)
        b.add_edge(START, name)          # fan-out: three edges from START
        b.add_edge(name, "summarize")    # fan-in: summarize waits for all three
    b.add_node("summarize", summarize)
    b.add_edge("summarize", END)
    return b.compile()


class StateNoReducer(TypedDict):
    results: list[str]                    # no reducer on purpose
    summary: str


if __name__ == "__main__":
    out = build(State).invoke({"results": [], "summary": ""})
    for line in out["results"]:
        print(" ", line)
    print(" ", out["summary"])

    print("\nSame graph WITHOUT the reducer:")
    try:
        build(StateNoReducer).invoke({"results": [], "summary": ""})
    except InvalidUpdateError as e:
        print("  InvalidUpdateError:", str(e).splitlines()[0])
