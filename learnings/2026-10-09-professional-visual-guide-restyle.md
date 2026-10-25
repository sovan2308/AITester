# Turning the LangGraph picture book into a professional visual guide

## Problem (one line)
The chapter 18 learning book was a children's picture book (kid analogies, kid characters, handwriting font); the user wanted professional pictures and real-world examples instead, then the book reopened.

## Approach (plain steps)
1. **Swap the content model first, pictures second.** In `learning/build.py` each lesson's `kid`/`kid_say` became `pic`/`example`, and every analogy became a real QA scenario that maps one to one onto the graph: CI build ID (state), Playwright setup/execute/teardown (pipeline), CI result router (conditional edge), Playwright retries (loop with a cap), API/UI/perf suites into one report (reducer), nightly vs smoke histories (thread_id), QA lead approval (interrupt), AI triage (LLM node), agent and tools (ReAct), two CI runs compared (flaky analyzer), ticket to report (capstone). Titles, labels and colour key went professional too.
2. **Render illustrations one at a time, style-locked.** First Codex render approved, then `--ref` to it for the other ten. Each brief allows only a few uppercase labels (RUN 1, TICKET, PLAN...), so QA is a short character-by-character check. All eleven passed on the first render.
3. **Keep the graphs hand-drawn, fix only their text.** Mermaid `look: handDrawn` stays (the user asked for it earlier); the handwriting font went. Re-render all 13 `.mmd` files and look at one before trusting the batch.
4. **Rebuild, then sweep before looking:** grep the output for old words (kid, sticker, picture book...), em dashes, and missing local image paths. Then look at index and lessons at 1280 and 390 wide.
5. **Republish to the same artifact URL** (pass `url`, since the file name changed), delete the old kid JPEGs and old book file, update the README, reopen the way it was opened last time (`open learning/index.html`).

## Gotchas that cost time
- **Codex: "gpt-6.1-sol is not supported with a ChatGPT account".** The user's Codex default model had changed. Pass `--model gpt-5.5` (found in `~/.codex/sessions` logs of the last good renders) instead of editing their config.
- **Mermaid silently drops a `fontFamily` containing a hyphen** (`sans-serif`, `system-ui`), so labels fall back to serif. Use `"Helvetica Neue, Helvetica, Arial"`.
- **Scratchpad scripts vanish after days.** `render.sh` and `approve.sh` were gone; the renders failed loudly only because the script checks its files.
- **A pill badge turned into a big circle** in the featured card: the grid's last row was `1fr` and the badge's default `align-self: stretch` filled it. Fix: `align-self: start`. It only appeared once shorter text left spare height.
- **Verification traps, not bugs:** the in-app browser shows `file://` pages outside the project as static `data:` snapshots (relative images look broken, so serve over http); lazy images report `complete=false` offscreen (check with `fetch` status); a `#hash` navigation does not reload after a rebuild (add `?v=2`); the content-only artifact file reports 980px wide under mobile emulation because the host adds the viewport meta (measure it in a 390px iframe).

## Judgment calls (what was NOT done, why)
- **Did not touch `~/.codex/config`.** It is the user's setup; a per-call `--model` fixes this job without side effects.
- **Did not redraw graphs with Codex.** Node names must be exact; generated text drifts.
- **Did not add a dark mode.** The live version is light-only by design (white illustrations, multiply-blended graphs), and the request was about the pictures.
- **Did not leave the kid assets beside the new ones.** The user asked to replace them; dead files invite the old book back.

## Reusable rule
When restyling a teaching asset, change the example model before the pictures so every image has a real scenario to show, keep exact-text pictures code-rendered, and when a check fails, first ask whether the check (cache, lazy load, file snapshot, missing host wrapper) is lying before you fix the page.
