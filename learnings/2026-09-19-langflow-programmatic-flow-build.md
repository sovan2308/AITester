# Building and testing a LangFlow flow programmatically

## Problem (one line)
Ship a *tested* LangFlow flow that reads two Playwright `results.json` files from a folder and reports how many tests are flaky, when the container cannot see the host folder, the flow JSON format is undocumented, and "tested" has to mean the exported file actually works.

## Approach (plain steps)
1. **Establish ground truth outside the tool first.** Wrote a throwaway Python script over the real `result1/result2.json` before touching LangFlow: 50 tests, 1 verdict flip, 2 failures in both runs. Everything afterwards was checked against that number, so a plausible-but-wrong flow could not pass.
2. **Fix the container's blindness.** The flow runs inside Docker; `/Users/promode/...` does not exist there. Added a read-only bind mount to `langflow-up.sh` and taught the component to remap host paths to container paths, so pasting either one works.
3. **Let LangFlow compile the component.** `POST /api/v1/custom_component` with the Python source returns the full node template (inputs, outputs, base classes). Hand-writing that blob is guesswork; this validates the code and hands back the exact schema.
4. **Steal the edge format from a working flow.** Read a starter flow's row straight out of `langflow.db` with sqlite3. Edges encode handles as JSON with `"` replaced by `œ` (`œ`), twice: spaced form in `sourceHandle`/`targetHandle`, compact form inside the edge `id`. Copying beat inventing.
5. **Test the artifact, not the session.** `test_flow.py` imports `Flaky_Test_Analyzer.json` as a brand-new flow, runs 8 cases, and deletes it. Fixtures cover both flip directions, a stable suite, Playwright's own retry flakiness, a test missing from one run, and two error paths.

## Judgment calls (what was NOT done, why)
- **No LLM in the flow.** The existing agent version asks a model to reason over two 68KB JSONs. For a number that might gate CI, a wrong answer is worse than no answer, and an LLM cannot be regression-tested to an exact integer. Kept the agent version alongside for narrative use.
- **Did not mount at `/app/data`.** First attempt did, and the container crash-looped: `HOME=/app/data` in the langflow image, so a read-only mount broke mem0's startup `makedirs`. Moved to `/test-results`. Verify `HOME` before mounting anywhere under a container's app dir.
- **Did not count a test seen in only one run as flaky.** It has no second verdict to disagree with. Reported separately under `NOT_COMPARABLE` so the count stays honest.
- **Did not trust the user's example arithmetic.** The brief said "2 flaky"; the actual files contain 1. Reported the computed answer and showed the working, rather than tuning the rule to hit an expected number.
- **Did not commit the API key.** Minted at test time, kept in scratchpad; `test_flow.py` mints its own.

## Reusable rule
Before automating a tool you cannot fully see, compute the expected answer by hand once and keep it as the oracle; then build the automation to *reproduce* that number, and test the exported artifact by re-importing it clean rather than testing the live session you happened to build in.
