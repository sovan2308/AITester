# Writing a LangGraph teaching chapter against a live version

## Problem (one line)
Build chapter 18 (ten runnable LangGraph scripts) so every lesson demonstrates what it claims on the installed version (langgraph 1.2.12), not on whatever version the docs or my memory describe.

## Approach (plain steps)
1. **Verify imports before writing.** Exec'd every import the chapter would use (`StateGraph`, `InMemorySaver`, `interrupt`, `Command`, `ToolNode`, `tools_condition`) against the fresh venv first. Writing ten files against an API that moved would have meant ten rewrites.
2. **Offline first.** Scripts 001-007 cover every core concept (nodes, forks, loops, fan-out/reducers, checkpointer, interrupt) with no model, so a learner without a key still gets the whole mental model and the lessons are deterministic.
3. **Run each script and read the output as the learner would**, not just check the exit code. 005 exited with an error either way, but it was the *wrong* error.
4. **Anchor the capstone to a known oracle.** 010 rebuilds the chapter 5 analyzer and must print the same `FLAKY TEST COUNT: 1`; it also runs against the chapter 5 fixtures (two_way = 2, stable = 0 and skips the approval pause).
5. **Test every factual claim in the README too.** The "default recursion limit is 25" line came from memory. A 6-line probe showed 10007 on 1.2.12.
6. **Clean-install check** from `requirements.txt` in a throwaway venv, so the pins are proven, not just copied from `pip freeze`.

## Judgment calls (what was NOT done, why)
- **Kept the LLM out of the count in 010.** The model only adds notes after a human approves. A number a CI gate reads must not depend on sampling.
- **Did not copy chapter 17's `.env` into chapter 18.** Loaded it into the shell for the test runs only; the chapter ships a `.env.sample`. Duplicating secret files multiplies places to leak them.
- **Scripted the retry outcomes in 004** instead of `random`. A teaching demo that shows "flaky" only sometimes teaches nothing.
- **Did not commit.** The branch also carries unrelated uncommitted chapter 5 work; mixing them is the user's call.

## Reusable rule
When teaching a fast-moving library, treat every sentence in the docs you write as a test case: run a probe for each factual claim (defaults, error messages, limits) on the pinned version, because remembered defaults are the claims most likely to be silently wrong. LangGraph specifics worth remembering: a node's type hint is read as its input schema, parallel writers to one key need a reducer, and the recursion default is now 10007, so cap loops yourself.
