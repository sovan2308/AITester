"""009 - Build the agent loop yourself: model -> tools -> model -> ... -> answer.

This is what create_agent (chapter 17) does under the hood. The loop is just
two nodes and a conditional edge:
    agent --(asked for a tool?)--> tools --> agent
    agent --(no tool call)-------> END
tools_condition is the prebuilt router; ToolNode runs whatever tools were asked for.
"""
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from llm import get_llm

HISTORY = {
    "login_redirect": ["passed", "failed", "passed", "passed", "failed", "passed"],
    "checkout_pay": ["failed", "failed", "failed", "failed", "failed", "failed"],
    "cart_total": ["passed"] * 6,
}
LAST_ERROR = {
    "login_redirect": "TimeoutError: waiting for URL /dashboard (5000ms). Passed on retry.",
    "checkout_pay": "AssertionError: order total expected $120.00, got $0.00",
    "cart_total": "none",
}


@tool
def get_test_history(test_name: str) -> str:
    """Return the last 6 CI results (oldest first) for a test by name."""
    runs = HISTORY.get(test_name)
    return ", ".join(runs) if runs else f"no history for {test_name}"


@tool
def get_last_error(test_name: str) -> str:
    """Return the most recent error message for a test by name."""
    return LAST_ERROR.get(test_name, f"no error recorded for {test_name}")


TOOLS = [get_test_history, get_last_error]
model = get_llm().bind_tools(TOOLS)

SYSTEM = SystemMessage(
    "You are a QA assistant. Use the tools to look up facts; never guess results. "
    "A test is flaky if it both passes and fails across runs with no code change. "
    "Answer in 2-3 sentences."
)


def agent(state: MessagesState) -> dict:
    return {"messages": [model.invoke([SYSTEM] + state["messages"])]}


builder = StateGraph(MessagesState)
builder.add_node("agent", agent)
builder.add_node("tools", ToolNode(TOOLS))
builder.add_edge(START, "agent")
builder.add_conditional_edges("agent", tools_condition, ["tools", END])
builder.add_edge("tools", "agent")          # the loop back
app = builder.compile()

if __name__ == "__main__":
    question = "Is login_redirect flaky or genuinely broken? Compare it with checkout_pay."
    print("Q:", question, "\n")
    # Cap the loop explicitly: the 1.2.12 default is 10007 steps.
    config = {"recursion_limit": 12}
    for step in app.stream({"messages": [HumanMessage(question)]}, config, stream_mode="updates"):
        for node, update in step.items():
            msg = update["messages"][-1]
            if node == "agent" and msg.tool_calls:
                for c in msg.tool_calls:
                    print(f"[agent] calls {c['name']}({c['args']})")
            elif node == "tools":
                for m in update["messages"]:
                    print(f"[tools] {m.name} -> {m.content}")
            else:
                print(f"\n[agent] answer: {msg.content}")
