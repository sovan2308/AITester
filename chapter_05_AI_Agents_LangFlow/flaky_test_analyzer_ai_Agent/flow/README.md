# Flaky Test Analyzer (LangFlow flow)

Give it a folder holding two Playwright `results.json` runs. It tells you how many
tests are flaky, which ones, and which failures are real bugs instead.

```
Chat Input ──> Flaky Test Analyzer ──> Chat Output
 (folder path)   (deterministic Python)   (report)
```

No LLM, no API key, no token spend. The verdict is computed, not guessed, so the
same input always produces the same number.

## What counts as flaky

A test is flaky when it does **not** agree with itself:

1. **Verdict changed between the two runs**, in either direction.
   `passed -> failed` counts exactly as much as `failed -> passed`.
2. **Playwright already caught it on retry** inside a single run (failed, then
   passed on a retry attempt).

A test that failed in both runs is a **consistent failure**: a real bug, not flake.
A test present in only one run is reported under `NOT_COMPARABLE` and never counted
as flaky, since there is nothing to compare it against.

Retries are collapsed per test before comparing, so a test is one verdict per run.

## Files

| File | What it is |
|---|---|
| `Flaky_Test_Analyzer.json` | The flow. Import this into LangFlow. |
| `flaky_analyzer_component.py` | The custom component's source, readable on its own. |
| `test_flow.py` | End-to-end test: imports the flow, runs 8 cases, deletes it. |
| `tests/` | Fixture folders with known-correct answers. |

## Import and run

1. Start LangFlow: `../../langflow-up.sh`
2. In the UI: **Projects -> upload icon -> pick `Flaky_Test_Analyzer.json`**
3. Open the flow, hit **Playground**, paste a folder path, send.

The folder must be visible **inside the container**. `langflow-up.sh` mounts
`chapter_05_AI_Agents_LangFlow` read-only at `/test-results`, so:

- `/test-results/flaky_test_analyzer_ai_Agent` works
- the matching host path works too, the component remaps it
- anything outside that mount will not be found, by design

To analyze results living somewhere else, add another `-v <host dir>:/test-results/<name>:ro`
line to `langflow-up.sh` and recreate the container.

## Run it from code

```bash
curl -s -X POST "http://localhost:7860/api/v1/run/<FLOW_ID>?stream=false" \
  -H "Content-Type: application/json" \
  -H "x-api-key: $LANGFLOW_API_KEY" \
  -d '{"output_type":"chat","input_type":"chat",
       "input_value":"/test-results/flaky_test_analyzer_ai_Agent"}'
```

Since LangFlow 1.5 the `/run` endpoint needs an API key even when auto-login is on.
Mint one under **Settings -> API Keys**, or via `POST /api/v1/api_key/`.

## Test it

```bash
python3 test_flow.py
```

Imports the JSON fresh, exercises it, and cleans up after itself, so it verifies the
file you are about to ship rather than whatever happens to be loaded in the UI.

Covered: the real sample data, host-path remapping, flakiness in both directions,
a fully stable suite, Playwright's own retry flakiness, tests missing from one run,
and two error paths (missing folder, folder with no reports).

## Result on the bundled sample

```
FLAKY TEST COUNT: 1
FLAKY_TESTS (1)
  [failed -> passed] loginTests/auth.spec.ts > @P0 Login > redirects to dashboard after successful login
CONSISTENT_FAILURES (2)
  dashboardTests/dashboard.spec.ts > @P0 Dashboard > renders revenue chart with correct totals
  loginTests/auth.spec.ts > @P0 Login > rejects login with expired session token
```

Run 1 had 3 failures, run 2 had 2. The two runs share the same two failures, and
exactly one test recovered, so the flaky count is 1, not 3 and not 2.

## Note on the LLM agent in this folder

The parent folder holds an older agent-based version that uploads both files and
asks a model to reason over them. That one is great for narrative explanation and
costs tokens; this flow is for the number you can put in a CI gate.
