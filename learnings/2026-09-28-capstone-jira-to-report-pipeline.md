# Capstone: Jira ticket -> LLM test plan -> Playwright run -> triaged HTML report

## Problem (one line)
Build a small, explainable LangGraph that takes a Jira requirement, writes and reviews test cases, runs them on TTACart, explains each failure, reports in HTML and runs 24x7 on a JQL query, and make the LLM parts reliable enough to leave unattended.

## Approach (plain steps)
1. **Map the app before prompting.** Read TTACart's own `ttacart.js` (public GETs) for every page's `data-test` ids, product ids, prices, the 8% tax and the exact error texts. The model writes steps only from that map; a vague "test the cart" prompt produced ids from the wrong page.
2. **Treat LLM steps as untrusted input.** `executor.problems()` allowlists pages and ids and keeps `goto` inside the app. It is both a safety rail (prompt injection via the ticket) and the cheapest reviewer: it caught invented ids like `back-home` and `terms-footer-link` before any browser opened.
3. **Measure structured-output reliability, don't assume it.** Three tries per setting on the real prompt: function-calling at default reasoning 0/3 (malformed tool JSON), low reasoning 3/3, and `method="json_schema"` needed for `gpt-oss-20b`, which otherwise answers in markdown and skips the tool. Kept json_schema + low reasoning + 3 retries.
4. **Give triage evidence, not a one-liner.** First triage called three test bugs "product bugs". Fixed by passing the steps with ok/FAIL markers, the app facts, and Playwright's "Actual value" line translated from `None` to "no matching element on the page". After that it classified correctly.
5. **Let the model's mistakes shape the vocabulary.** It kept inventing a `not see` action; adding it (one line) removed a whole class of failures that a `count 0` workaround never fixed.
6. **Verify every path you can't run live.** Jira token expired (401 on `/myself`, 404 on the issue because Jira hides from anonymous callers), so the API path is checked by shape and the fixture came via MCP. The worker was verified by stubbing only `search`/`mark_done`: one failing ticket stays isolated, and a ticket is labelled done only after a finished run.

## Judgment calls (what was NOT done, why)
- **No MCP client inside the code.** The 24x7 worker can't do an OAuth browser login; an API token over stdlib `urllib` needs no new dependency. MCP stays the human path (and fetched the fixture).
- **Did not log into the live TTACart myself.** My rules allow entering even public demo passwords only on localhost, so the pipeline ran against TTACart's own HTML/JS served on 127.0.0.1; the live run is one command for the user.
- **Did not let the review loop spin.** One rewrite, then run anyway and print leftover review notes in the report; unbounded loops also burn a free-tier token budget (hit Groq's 200k/day cap during testing, about 16k tokens per ticket).
- **Did not commit a GitHub Actions workflow.** It would start firing on push without secrets; the README carries the YAML instead.
- **Did not add a markdown renderer for the report.** The analysis sits in a collapsed `<pre>`; results come first.

## Reusable rule
When an LLM writes steps a program will execute, ground it in a machine-read map of the target, validate its output against that map before running, and hand the triage model the same map plus the failing step's actual value; measure the structured-output setting with a few real runs, because "usually valid JSON" is 0/3 until proven otherwise.
