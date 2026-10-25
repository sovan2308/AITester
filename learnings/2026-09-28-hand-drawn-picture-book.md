# Making the picture book hand-drawn: Mermaid handDrawn graphs + Codex illustrations

## Problem (one line)
The ELI5 pages "looked very basic"; the user wanted a hand-drawn, proper-looking book, with generated images from Codex, without losing exact code names in the graphs.

## Approach (plain steps)
1. **Split the pictures by what they must get right.** Graphs must spell `route_by_status()` exactly, so they stay code-rendered by the /diagram skill. Kid analogies only need to feel right, so they became Codex illustrations with no text at all (nothing to misspell).
2. **Try the obvious hand-drawn route and look at it.** Re-exporting the diagram skill's `.excalidraw` scenes gave a sketch font but clipped `read_result`, stacked START/END letter by letter and dropped all colour: the converter sized boxes for Mermaid's font, not the handwriting one.
3. **Use Mermaid 11's own `look: handDrawn`.** Mermaid measures text in the font it renders, so boxes fit. One init line per `.mmd` (seed, Chalkboard SE font stack) keeps the skill's pipeline and source-of-truth rule intact.
4. **Find why the hatching was unreadable.** Mermaid turns a classDef into `.step path { stroke: ... !important }`, which repaints the hatch lines in the outline colour. Removing `stroke` from the classes lets outlines fall back to one marker colour while each class's fill colour becomes the hatching.
5. **Ship PNGs, not SVGs, for the handwriting font.** Chalkboard SE exists on Macs only; rasterising on the build machine makes every reader see the same thing.
6. **Codex: one reference character, tightly scoped.** Illustration 1 became `--ref` for the rest so the child stays the same. The first attempt at #2 copied #1's machine and dropped a station: the brief said "keep the child", not "copy only the child". Rewording to "use the reference ONLY for the child and style; don't copy props or layout" fixed it.

## Judgment calls (what was NOT done, why)
- **Did not let Codex draw the graphs.** Generated text drifts; exact node names are the whole point of those pictures.
- **Did not trust my render script's "OK".** After the browse daemon restarted from another folder it refused every `--out` into the repo, and the script swallowed that. It now writes via /private/tmp, copies, and fails if any file is missing or stale.
- **Did not spend a third render on a nit** (the child wearing the backpack while packing another): the lesson reads clearly, and the skill caps renders at three.
- **Deleted the old kid flowcharts** once the illustrations replaced them, instead of leaving dead files beside live ones.
- **Converted illustrations to 1400px JPEG with `sips`** (native): about 1.8MB PNG to about 220KB each, which keeps the self-contained book far under the 16MB artifact limit.

## Reusable rule
When a picture must be exact, keep it code-rendered and style it through the renderer's own mode; when it only must feel right, generate it with no text; and tell an image model precisely which parts of a reference to copy, or it will copy the scene.
