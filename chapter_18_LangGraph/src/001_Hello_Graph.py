from typing import TypedDict

from langgraph.graph import END, START, StateGraph

"""001 - The smallest possible graph: one node between START and END.
State is the backpack. A node is a plain function: it receives the backpack
and returns only the keys it wants to change. LangGraph merges them in.
"""

class State(TypedDict):
    tester: str
    greeting: str

def greet(state: State) -> dict:
    return {"greeting": f"Hello {state['tester']}, your first graph ran."}

builder = StateGraph(State)
builder.add_node("greet", greet)


builder.add_edge(START, "greet")
builder.add_edge("greet", END)

app = builder.compile()

if __name__ == "__main__":
    result = app.invoke({"tester": "Pramod"})
    print(result["greeting"])
    print("\nFinal state:", result)
    print("\nThe graph as Mermaid (paste into mermaid.live):")
    print(app.get_graph().draw_mermaid())