# Turning a code chapter into an ELI5 picture book with rendered diagrams

## Problem (one line)
Build a `learning/` folder for chapter 18 where every lesson is an ELI5 page (big pictures, few words) whose 21 pictures come from the `/diagram` skill (Mermaid -> SVG + PNG + editable Excalidraw), readable on desktop and phone.

## Approach (plain steps)
1. **Two pictures per lesson, same colours everywhere.** A kid analogy ("like this") next to the real graph ("in LangGraph"). Colour carries meaning across all 21: yellow = a job, pink = a decision, green = memory, orange = a human, purple = the AI. The index shows the key once.
2. **Render three, look, then batch.** Rendered one overview plus one lesson pair first and read the PNGs before writing the other 18. The style problems below showed up on 3 files instead of 21.
3. **Guard the render loop against stale state.** The render page keeps its last result in `window.__svg`; a failed render would silently write the previous diagram. Reset it before each call and fail on anything that isn't `SVG OK`.
4. **Measure readability instead of eyeballing.** Read each SVG's viewBox and computed the font size it gets at the page's 960px width. That flagged every too-wide and too-tall diagram in one pass.
5. **Generate pages from one list.** `build.py` holds the words for all ten lessons and emits every page plus a self-contained whole-book file (SVGs as data URIs) for publishing. Eleven hand-written pages would drift apart.
6. **Verify with measurements, not a screenshot loop.** One look at the index and one at a lesson, then a JS check on all 12 pages at 390px and 1280px: sideways scroll, broken images, card overflow.

## Judgment calls (what was NOT done, why)
- **Reused chapter 17's design tokens** (IBM Plex, navy ink on #F7F9FC) instead of a fresh "picture book" identity; the existing system wins, and students see one course.
- **Did not upgrade gstack mid-task** (1.61 -> 1.91 was offered): it would have swapped the render bundle halfway through 21 renders. The user chose to snooze it.
- **Did not accept gstack's CLAUDE.md routing commit** on the chapter branch: an unrelated tooling change doesn't belong there. The user declined it.
- **Kept model output out of the "Try it" blocks** where wording varies, marking it with "..." and a note instead of pasting one run's prose as if it were fixed.
- **Did not revert `.gitignore`**: the browse daemon added `.gstack/` itself when it started; reverting would expose its logs to `git add`.

## Reusable rule
Mermaid-to-SVG gotchas worth checking on the first render: edge labels sit on a 50%-opacity rect (fix with `themeCSS: ".edgeLabel rect { opacity: 1 !important; }"` in the init line); edge labels over about 22 characters wrap mid-word; a subgraph's `direction` is ignored once any of its nodes links outside it (link the subgraphs, `CH5 ~~~ CH18`, instead); and in a CSS grid, give children `min-width: 0` or one wide picture widens the whole page on phones.
