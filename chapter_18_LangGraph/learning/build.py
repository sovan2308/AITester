#!/usr/bin/env python3
"""Build the chapter 18 LangGraph Visual Guide.

    cd chapter_18_LangGraph/learning && python3 build.py

Writes index.html and one page per lesson (pictures linked from diagrams/),
plus langgraph-visual-guide.html: the whole guide in one self-contained file
with every picture inlined, for sharing.

Words live in LESSONS below. Two kinds of pictures:
  diagrams/<slug>.mmd        the real graphs, rendered hand-drawn by the /diagram skill
                             (Mermaid look=handDrawn) into .png, .svg and an editable .excalidraw
  illustrations/<slug>.jpg   the real-world examples, drawn by Codex through the /codex-imagegen skill
"""
import base64
import html
import re
import struct
from pathlib import Path
from string import Template

HERE = Path(__file__).resolve().parent
DIAGRAMS = HERE / "diagrams"
ILLUSTRATIONS = HERE / "illustrations"
TOTAL = 11

LESSONS = [
    dict(n=1, slug="01-hello-graph", script="001_Hello_Graph.py", key="none",
         title="Your first graph",
         idea='A graph is a set of nodes joined by edges. Every node reads the shared state and returns only what it changed.',
         pic='01-state-node', example='A CI step receives a test-run record and adds one field, such as a build ID, before passing it on.',
         graph="01-graph-hello", graph_say="greet is a node. It reads the state and hands back one new key: greeting.",
         remember=["State is a plain dict shared by every node",
                   "A node returns only what it changed",
                   "Build it, compile() it, invoke() it"],
         run="python 001_Hello_Graph.py",
         out="Hello Pramod, your first graph ran."),
    dict(n=2, slug="02-linear-pipeline", script="002_Linear_Pipeline.py", key="none",
         title="A sequential pipeline",
         idea='Edges run nodes in order. Each step adds its result to the state, and nothing is lost on the way.',
         pic='02-test-lifecycle', example='Every Playwright test has a lifecycle: set up the browser, run the test, clean up. Each stage records what it did.',
         graph="02-graph-linear-pipeline", graph_say="setup, execute and teardown each add one key. stream() lets you watch every step.",
         remember=["Edges run the steps in order",
                   "Keys you don't return stay as they were",
                   "stream(stream_mode=\"updates\") shows each step"],
         run="python 002_Linear_Pipeline.py",
         out="setup     changed -> {'browser': 'chromium'}\n"
             "execute   changed -> {'status': 'passed'}\n"
             "teardown  changed -> {'cleaned_up': True}"),
    dict(n=3, slug="03-conditional-edge", script="003_Conditional_Edge.py", key="none",
         title="Conditional routing",
         idea='A router function reads the state and returns the name of the next node. Decisions live in that one function.',
         pic='03-result-router', example='A CI result router: passed tests go to the dashboard, failures become Jira bugs, flaky tests move to quarantine.',
         graph="03-graph-conditional-edge", graph_say="route_by_status() reads the status and returns the name of the next node.",
         remember=["The router returns a node's name",
                   "The diamond is a decision, not a node",
                   "This is where an agent makes choices"],
         run="python 003_Conditional_Edge.py",
         out="cart_total      passed  -> logged as green\n"
             "checkout_pay    failed  -> Jira bug filed for checkout_pay\n"
             "login_redirect  flaky   -> login_redirect moved to quarantine, rerun nightly"),
    dict(n=4, slug="04-loop-retry", script="004_Loop_Retry.py", key="none",
         title="Retries with a limit",
         idea='An edge can point back to an earlier node. That makes a loop, and every loop needs a cap.',
         pic='04-retry-limit', example="Like Playwright's retries: rerun a failing test up to three times. A pass after a failure marks the test as flaky.",
         graph="04-graph-loop-retry", graph_say="should_retry() sends a failed test back to run_test, three times at most.",
         remember=["A loop is an edge that points back",
                   "Keep the counter in the state",
                   "Set recursion_limit as a backstop"],
         run="python 004_Loop_Retry.py",
         out="login_redirect (flaky)\n"
             "   attempt 1: failed\n"
             "   attempt 2: failed\n"
             "   attempt 3: passed\n"
             "   => FLAKY: passed on attempt 3 after 2 failure(s)"),
    dict(n=5, slug="05-parallel-reducer", script="005_Parallel_Reducer.py", key="none",
         title="Parallel branches and reducers",
         idea='Independent nodes run at the same time. A reducer defines how their results merge into one key.',
         pic='05-parallel-suites', example='API, UI and performance suites run in parallel, and their results merge into one release report.',
         graph="05-graph-parallel-reducer", graph_say="api, ui and perf run together. operator.add joins their results into one list.",
         remember=["Many edges from START run in parallel",
                   "Many writers, one key? Add a reducer",
                   "No reducer means InvalidUpdateError"],
         run="python 005_Parallel_Reducer.py",
         out="  api: 42/42 passed\n"
             "  perf: p95 380ms (budget 500ms)\n"
             "  ui: 118/120 passed\n"
             "  3 suites reported\n\n"
             "Same graph WITHOUT the reducer:\n"
             "  InvalidUpdateError: At key 'results': Can receive only one value per step. "
             "Use an Annotated key to handle multiple values."),
    dict(n=6, slug="06-checkpointer-memory", script="006_Checkpointer_Memory.py", key="none",
         title="Checkpoints and memory",
         idea='A checkpointer saves the state after every step. Each thread_id keeps its own history.',
         pic='06-checkpoints', example='The nightly regression and the smoke run keep separate histories, like two CI pipelines that never overwrite each other.',
         graph="06-graph-checkpointer", graph_say="One graph, two thread_ids, two separate memories.",
         remember=["compile(checkpointer=InMemorySaver())",
                   "Pass a thread_id in the config",
                   "Use a SQLite or Postgres saver to survive restarts"],
         run="python 006_Checkpointer_Memory.py",
         out="nightly-regression remembers: ['run #1', 'run #2', 'run #3']\n"
             "smoke is separate:            ['run #1']"),
    dict(n=7, slug="07-human-in-the-loop", script="007_Human_In_The_Loop.py", key="none",
         title="Human approval gates",
         idea='interrupt() pauses the graph and waits for a person. Command(resume=...) continues it with their answer.',
         pic='07-approval-gate', example='Before quarantining tests, the pipeline waits for a QA lead to approve, like a manual gate before a production deploy.',
         graph="07-graph-interrupt", graph_say="ask_approval pauses the graph. Command(resume=...) on the same thread_id carries your answer back in.",
         remember=["interrupt() needs a checkpointer",
                   "Resume with Command(resume=answer)",
                   "Same thread_id, or it starts over"],
         run="python 007_Human_In_The_Loop.py yes",
         out="Graph paused. It is asking:\n"
             "  Quarantine these tests? (yes/no)\n"
             "   - login_redirect\n"
             "   - search_autocomplete\n"
             "Paused before node: ('ask_approval',)\n\n"
             "Resumed with 'yes' -> quarantined 2 tests"),
    dict(n=8, slug="08-llm-node", script="008_LLM_Node.py", key="required",
         title="An LLM inside a node",
         idea='A node can call an LLM. Its structured answer decides which edge the graph takes next.',
         pic='08-ai-triage', example='AI-assisted triage: read a failure log, classify it as a product bug, test bug, environment issue or flake, and route it to the right team.',
         graph="08-graph-llm-node", graph_say="classify asks the LLM for one of four labels. route() sends the test on its way.",
         remember=["with_structured_output gives a fixed answer shape",
                   "The model picks. The router routes.",
                   "Needs GROQ_API_KEY in .env"],
         run="python 008_LLM_Node.py",
         out="checkout_pay    -> product_bug  | file a Jira bug for the dev team\n"
             "login_button    -> test_bug     | fix the test code (locator / assertion)\n"
             "search_results  -> environment  | ping DevOps, rerun when the env is healthy",
         note="The model also prints a one-line reason for each. Its wording changes run to run."),
    dict(n=9, slug="09-react-agent", script="009_ReAct_Agent_Tools.py", key="required",
         title="The ReAct agent loop",
         idea='The model reasons, calls a tool, reads the result, and repeats until it can answer.',
         pic='09-agent-loop', example='A QA assistant answers "Is login_redirect flaky?" by checking the test history and the last error before it replies.',
         graph="09-graph-react-agent", graph_say="The agent asks for a tool. ToolNode runs it. tools_condition says: again, or done.",
         remember=["This is what create_agent builds for you",
                   "Two nodes and one loop",
                   "Cap it with recursion_limit"],
         run="python 009_ReAct_Agent_Tools.py",
         out="[agent] calls get_test_history({'test_name': 'login_redirect'})\n"
             "[tools] get_test_history -> passed, failed, passed, passed, failed, passed\n"
             "[agent] calls get_test_history({'test_name': 'checkout_pay'})\n"
             "[tools] get_test_history -> failed, failed, failed, failed, failed, failed\n\n"
             "[agent] answer: ...",
         note="The tool calls are the lesson. The final answer's wording changes run to run."),
    dict(n=10, slug="10-flaky-analyzer", script="010_Flaky_Analyzer_Graph.py", key="optional",
         title="Flaky test analyzer",
         idea="Chapter 5's flaky test finder, rebuilt with a decision, an approval pause and an optional LLM explanation.",
         pic='10-run-compare', example='Compare two CI runs of the same suite: a test that passed in one run and failed in the other is flaky.',
         extra=("10-story-ch5-vs-ch18", "Then and now",
                "Same answer as chapter 5. Now it can choose a path, wait for you, and explain."),
         graph="10-graph-capstone", graph_say="Clean runs go straight to the report. Flaky runs ask you first.",
         remember=["The count is plain Python, never the AI",
                   "Pause before changing anything",
                   "Uses every idea from lessons 1 to 9"],
         run="python 010_Flaky_Analyzer_Graph.py --yes",
         out="Quarantine these flaky tests? (yes/no)\n"
             "  - loginTests/auth.spec.ts > @P0 Login > redirects to dashboard after successful login\n\n"
             "FLAKY TEST COUNT: 1\n"
             "Compared 50 tests present in both runs",
         note="Same count as the chapter 5 LangFlow flow. With a GROQ key it also adds LLM notes."),
    dict(n=11, slug="11-capstone", script="capstone/pipeline.py", path="../capstone/README.md", key="required",
         title="From Jira ticket to test report",
         idea='Give it a Jira ticket. It plans the tests, runs them in a browser, and explains what failed and why.',
         pic='11-qa-pipeline', example='An end-to-end QA pipeline: the ticket becomes a reviewed test plan, the plan runs in Playwright, and every failure is triaged in one report.',
         graph="11-graph-capstone-qa", graph_say="Seven nodes. The review can send the plan back once. Failures go to triage before the report.",
         remember=["Steps written by an LLM are untrusted: check them against the app",
                   "Triage says why: test bug, product bug, environment or flaky",
                   "A Jira label is the 24x7 worker's memory"],
         run="python pipeline.py VWO-105",
         out='  passed  TC-01  Login success for standard_user redirects to inventory\n  passed  TC-03  Add then remove a product updates cart badge correctly\n  passed  TC-04  Sorting options display correct product order\n  failed  TC-05  Product detail page add/remove syncs with cart badge\n  passed  TC-06  Checkout information validation errors\n  failed  TC-07  Reset App State clears cart and remove buttons\n skipped  TC-02  Locked out user sees error and stays on login page\n skipped  TC-08  Logout clears session and returns to login page\n\nreport: reports/VWO-105-20260928-184544/report.html',
         note="One real run on gpt-oss-120b against VWO-105, the TTACart requirement pulled via the MCP. The model writes a new plan every run, so your cases will differ. Skipped cases had a step the safety rules refused."),
]

KEY_BADGE = {
    "none": ("No API key needed", "k-none"),
    "required": ("Needs GROQ_API_KEY", "k-req"),
    "optional": ("API key optional", "k-opt"),
}

COLOR_KEY = [
    ("job", "Node", "a step"),
    ("fork", "Conditional edge", "a decision"),
    ("memory", "State", "data and checkpoints"),
    ("human", "Interrupt", "a person approves"),
    ("ai", "LLM call", "a model decides"),
]

FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">'
         '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
         '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500'
         '&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap">')

CSS = """
:root{
  --bg:#F7F9FC; --surface:#FFFFFF; --ink:#13294B; --body:#2A3A56; --muted:#5F7090; --line:#D9E1EC;
  --paper:#FFFFFF;  /* the illustrations are drawn on pure white, so they sit seamlessly on the plates */
  --blue:#2A66D6; --blue-soft:#E7EFFC; --green:#1E8A5A; --green-soft:#E4F4EB; --amber:#B8741A; --amber-soft:#FFF5E1;
  --code-bg:#13294B; --code-fg:#E6EDF7; --code-dim:#8FA3C4; --prompt:#8DE0B9;
  --job:#FFF4CC; --job-edge:#C9A227; --fork:#FFE0E6; --fork-edge:#D9486B;
  --memory:#D8F3DC; --memory-edge:#2D8A4E; --human:#FFD6A5; --human-edge:#E07A1F;
  --ai:#E0E7FF; --ai-edge:#4F46E5;
  --radius:10px;
  color-scheme: light;
}
*{box-sizing:border-box}
html{background:var(--bg)}
body{margin:0;background:var(--bg);color:var(--body);
  font:400 17px/1.6 "IBM Plex Sans",system-ui,-apple-system,"Segoe UI",sans-serif;
  padding-inline:20px}
code,pre,.mono{font-family:"IBM Plex Mono",ui-monospace,SFMono-Regular,Menlo,monospace}
a{color:var(--blue);text-underline-offset:3px}
a:focus-visible{outline:3px solid var(--blue);outline-offset:3px;border-radius:4px}
.wrap{max-width:980px;margin:0 auto;padding-block:24px 72px;display:grid;gap:40px}
.wrap>*,.pics>*,.plate>*,.try>*,.book-lesson>*{min-width:0}
.top{display:flex;justify-content:space-between;align-items:center;gap:16px;flex-wrap:wrap;
  padding-block:6px 14px;border-bottom:1px solid var(--line)}
.brand{font-weight:700;color:var(--ink);text-decoration:none;letter-spacing:.2px}
.where{font-size:14px;color:var(--muted);font-variant-numeric:tabular-nums}
.hero{display:grid;gap:14px}
.eyebrow{margin:0;display:flex;flex-wrap:wrap;gap:8px 14px;align-items:center;
  font-size:13px;letter-spacing:.8px;text-transform:uppercase;color:var(--muted);font-weight:600}
.eyebrow code{text-transform:none;letter-spacing:0;font-size:13px;color:var(--ink);font-weight:500}
h1{margin:0;color:var(--ink);font-weight:700;font-size:clamp(34px,5.2vw,54px);line-height:1.08;
  letter-spacing:-.5px;text-wrap:balance}
.idea{margin:0;max-width:46ch;font-size:clamp(19px,2.3vw,23px);line-height:1.45;font-weight:500;
  color:var(--body);text-wrap:pretty}
.badge{display:inline-block;padding:3px 10px;border-radius:999px;font-size:12px;letter-spacing:.4px;
  text-transform:none;font-weight:600;border:1px solid transparent}
.k-none{background:var(--green-soft);color:var(--green);border-color:#BFE3CF}
.k-req{background:var(--amber-soft);color:var(--amber);border-color:#F2D7A6}
.k-opt{background:var(--blue-soft);color:var(--blue);border-color:#C6D8F7}
.plate{margin:0;background:var(--paper);border:1px solid var(--line);border-radius:var(--radius);
  padding:18px 22px 20px;display:grid;gap:14px}
.label{margin:0;font-size:13px;font-weight:700;letter-spacing:1px;text-transform:uppercase;color:var(--muted)}
.art{overflow-x:auto;display:flex;justify-content:center}
.art img{display:block;width:100%;height:auto}
.art img.graph{mix-blend-mode:multiply}  /* the rendered graphs have a white ground; multiply drops it onto the paper */
.plate figcaption{font-size:clamp(17px,1.9vw,19px);line-height:1.5;color:var(--body);max-width:62ch}
.pics{display:grid;gap:22px}
h2{margin:0 0 14px;color:var(--ink);font-size:14px;font-weight:700;letter-spacing:1px;text-transform:uppercase}
.remember ul{list-style:none;margin:0;padding:0;display:grid;gap:12px;grid-template-columns:repeat(3,minmax(0,1fr))}
.remember li{background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);
  padding:14px 16px;color:var(--ink);font-weight:500;line-height:1.4;display:flex;gap:10px;align-items:flex-start}
.remember li b{flex:none;width:24px;height:24px;border-radius:50%;display:grid;place-items:center;
  background:var(--blue-soft);color:var(--blue);font-size:13px;font-variant-numeric:tabular-nums}
.term{margin:0;background:var(--code-bg);color:var(--code-fg);border-radius:var(--radius);padding:18px 20px;
  overflow-x:auto;font-size:14px;line-height:1.6;white-space:pre}
.term .cmd{color:var(--prompt)}
.term .out{color:var(--code-fg)}
.fine{margin:10px 0 0;font-size:14px;color:var(--muted)}
.turn{display:grid;grid-template-columns:1fr 1fr;gap:14px;border-top:1px solid var(--line);padding-top:22px}
.turn a{display:grid;gap:2px;padding:14px 16px;border:1px solid var(--line);border-radius:var(--radius);
  background:var(--surface);text-decoration:none;color:var(--ink);font-weight:600}
.turn a small{font-weight:500;color:var(--muted);font-size:13px}
.turn .next{text-align:right;grid-column:2}
.turn a:hover{border-color:var(--blue)}
.keys{list-style:none;margin:0;padding:0;display:flex;flex-wrap:wrap;gap:10px}
.keys li{display:flex;align-items:center;gap:10px;padding:8px 14px 8px 8px;background:var(--surface);
  border:1px solid var(--line);border-radius:999px;color:var(--ink);font-weight:600;font-size:15px}
.keys li span{font-weight:400;color:var(--muted)}
.sw{width:22px;height:22px;border-radius:6px;border:2px solid}
.sw.job{background:var(--job);border-color:var(--job-edge)} .sw.fork{background:var(--fork);border-color:var(--fork-edge)}
.sw.memory{background:var(--memory);border-color:var(--memory-edge)} .sw.human{background:var(--human);border-color:var(--human-edge)}
.sw.ai{background:var(--ai);border-color:var(--ai-edge)}
.lessons{list-style:none;margin:0;padding:0;display:grid;gap:16px;grid-template-columns:repeat(2,minmax(0,1fr))}
.card{height:100%;display:grid;grid-template-rows:auto auto 1fr auto;gap:10px;padding:18px 18px 16px;
  background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);text-decoration:none;color:var(--body)}
.card:hover{border-color:var(--blue)}
.card .num{font-size:13px;font-weight:700;color:var(--blue);letter-spacing:.8px;font-variant-numeric:tabular-nums}
.card .t{font-size:20px;font-weight:700;color:var(--ink);line-height:1.2}
.card .thumb{display:block;border-radius:8px;overflow:hidden;background:var(--bg)}
.card .thumb img{display:block;width:100%;height:auto;aspect-ratio:16/9;object-fit:cover}
.card .i{margin:0;font-size:15px;line-height:1.45}
.card .badge{justify-self:start;align-self:start}
.book-lesson{display:grid;gap:40px;padding-top:40px;border-top:2px solid var(--line)}
.lessons li.featured{grid-column:1/-1}
.lessons li.featured .card{grid-template-columns:minmax(0,1fr) minmax(0,1fr);grid-template-rows:auto auto auto 1fr;column-gap:22px}
.lessons li.featured .thumb{grid-column:1;grid-row:1/span 4}
.lessons li.featured .card>:not(.thumb){grid-column:2}
@media (max-width:760px){
  .remember ul{grid-template-columns:1fr}
  .lessons{grid-template-columns:1fr}
  .lessons li.featured .card{grid-template-columns:1fr;grid-template-rows:none}
  .lessons li.featured .thumb,.lessons li.featured .card>:not(.thumb){grid-column:auto;grid-row:auto}
}
@media (max-width:640px){
  body{font-size:16px;padding-inline:16px}
  .plate{padding:14px 14px 16px}
  .art{justify-content:flex-start}
  .art img{min-width:var(--minw)}
  .turn{grid-template-columns:1fr}
  .turn .next{grid-column:1}
}
@media (prefers-reduced-motion:no-preference){ .card,.turn a{transition:border-color .15s ease} }
"""


def esc(s):
    return html.escape(s, quote=True)


def svg_size(slug):
    head = (DIAGRAMS / f"{slug}.svg").read_text()[:4000]
    m = re.search(r'viewBox="[\d.\-]+ [\d.\-]+ ([\d.]+) ([\d.]+)"', head)
    return float(m.group(1)), float(m.group(2))


def jpeg_size(path):
    """Width and height from a JPEG's SOF marker (stdlib only)."""
    data = path.read_bytes()
    i = 2
    while i < len(data):
        marker, length = data[i + 1], struct.unpack(">H", data[i + 2:i + 4])[0]
        if marker in (0xC0, 0xC1, 0xC2):
            h, w = struct.unpack(">HH", data[i + 5:i + 9])
            return w, h
        i += 2 + length
    raise ValueError(f"no size in {path}")


def src_of(path, inline):
    if not inline:
        return path.relative_to(HERE).as_posix()
    mime = "image/jpeg" if path.suffix == ".jpg" else "image/png"
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode()}"


def img(slug, alt, inline, thumb=False):
    """A hand-drawn graph from diagrams/ (PNG, sized from its SVG twin)."""
    w, h = svg_size(slug)
    maxw = round(w * (1.0 if h > w else 1.3))
    minw = round(min(w, 560))                          # phones scroll wide pictures instead of shrinking them
    size = "" if thumb else f' style="max-width:{maxw}px;--minw:{minw}px"'
    return (f'<img class="graph" src="{src_of(DIAGRAMS / f"{slug}.png", inline)}" alt="{esc(alt)}" '
            f'width="{round(w)}" height="{round(h)}"{size} loading="lazy">')


def illustration(slug, alt, inline):
    """A professional Codex illustration from illustrations/ (JPEG)."""
    path = ILLUSTRATIONS / f"{slug}.jpg"
    w, h = jpeg_size(path)
    return f'<img src="{src_of(path, inline)}" alt="{esc(alt)}" width="{w}" height="{h}" loading="lazy">'


def badge(key):
    text, cls = KEY_BADGE[key]
    return f'<span class="badge {cls}">{esc(text)}</span>'


def lesson_body(L, inline, prev, nxt, href):
    pic_label = "Real-world example"
    remember = "".join(f"<li><b>{i}</b>{esc(t)}</li>" for i, t in enumerate(L["remember"], 1))
    note = f'<p class="fine">{esc(L["note"])}</p>' if L.get("note") else ""
    link = L.get("path", f"../src/chapters/{L['script']}")
    script = (f'<code>{esc(L["script"])}</code>' if inline
              else f'<a href="{esc(link)}"><code>{esc(L["script"])}</code></a>')
    extra = ""
    if L.get("extra"):
        slug, label, say = L["extra"]
        extra = (f'<figure class="plate"><p class="label">{esc(label)}</p>'
                 f'<div class="art">{img(slug, label + ": " + say, inline)}</div><figcaption>{esc(say)}</figcaption></figure>')
    turn = ['<nav class="turn" aria-label="Lessons">']
    if prev:
        turn.append(f'<a class="prev" href="{href(prev)}"><small>Previous</small>{esc(prev["title"])}</a>')
    if nxt:
        turn.append(f'<a class="next" href="{href(nxt)}"><small>Next</small>{esc(nxt["title"])}</a>')
    else:
        turn.append(f'<a class="next" href="{href(None)}"><small>Done</small>Back to all lessons</a>')
    turn.append("</nav>")
    return f"""
<section class="hero">
  <p class="eyebrow">Lesson {L['n']:02d} {script} {badge(L['key'])}</p>
  <h1>{esc(L['title'])}</h1>
  <p class="idea">{esc(L['idea'])}</p>
</section>
<div class="pics">
  <figure class="plate">
    <p class="label">{esc(pic_label)}</p>
    <div class="art">{illustration(L['pic'], pic_label + ': ' + L['example'], inline)}</div>
    <figcaption>{esc(L['example'])}</figcaption>
  </figure>
  <figure class="plate">
    <p class="label">In LangGraph</p>
    <div class="art">{img(L['graph'], 'In LangGraph: ' + L['graph_say'], inline)}</div>
    <figcaption>{esc(L['graph_say'])}</figcaption>
  </figure>
  {extra}
</div>
<section class="remember"><h2>Key points</h2><ul>{remember}</ul></section>
<section class="try">
  <h2>Try it</h2>
  <pre class="term"><span class="cmd">$ {esc(L['run'])}</span>
<span class="out">{esc(L['out'])}</span></pre>
  {note}
</section>
{''.join(turn)}"""


def index_body(inline, href):
    # The one-file book skips card thumbnails: each lesson's picture sits right below, and
    # inlining every illustration twice would double the file.
    keys = "".join(f'<li><i class="sw {c}" aria-hidden="true"></i>{esc(a)} <span>{esc(b)}</span></li>'
                   for c, a, b in COLOR_KEY)
    cards = "".join(f"""<li{' class="featured"' if L['n'] == TOTAL else ''}><a class="card" href="{href(L)}">
  <span class="num">LESSON {L['n']:02d}{' &middot; FINAL PROJECT' if L['n'] == TOTAL else ''}</span>
  <span class="t">{esc(L['title'])}</span>
  {'' if inline else f'<span class="thumb">{illustration(L["pic"], L["example"], inline)}</span>'}
  <p class="i">{esc(L['idea'])}</p>
  {badge(L['key'])}
</a></li>""" for L in LESSONS)
    return f"""
<section class="hero">
  <p class="eyebrow">Chapter 18 <span>AI Tester Blueprint</span></p>
  <h1>LangGraph Visual Guide</h1>
  <p class="idea">Eleven lessons, from a first graph to a production QA pipeline. Each pairs a real-world example with the exact graph and the code you can run.</p>
</section>
<figure class="plate">
  <p class="label">LangGraph at a glance</p>
  <div class="art">{img('00-overview', 'LangGraph at a glance: nodes, a conditional edge with a loop back, an interrupt for human approval, the shared state and the checkpointer', inline)}</div>
  <figcaption>Nodes do the work, edges set the order, conditional edges decide, and the state carries data through the graph.</figcaption>
</figure>
<section><h2>Colour key for every graph</h2><ul class="keys">{keys}</ul></section>
<section><h2>The eleven lessons</h2><ol class="lessons">{cards}</ol></section>
<section class="try">
  <h2>Run the scripts</h2>
  <pre class="term"><span class="cmd">$ cd chapter_18_LangGraph
$ python3 -m venv .venv &amp;&amp; .venv/bin/pip install -r requirements.txt
$ source .venv/bin/activate &amp;&amp; cd src/chapters
$ python 001_Hello_Graph.py
$ cd ../../capstone && python pipeline.py VWO-105</span></pre>
  <p class="fine">Lessons 1 to 7 need no API key. For 8, 9 and the capstone, copy <code>.env.sample</code> to <code>.env</code> and add a free Groq key. The capstone also needs <code>pip install -r capstone/requirements.txt</code> and <code>playwright install chromium</code>.</p>
</section>"""


PAGE = Template("""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>$title</title>
$fonts
<style>$css</style>
</head>
<body>
<main class="wrap">
<header class="top"><a class="brand" href="index.html">LangGraph Visual Guide</a><span class="where">$where</span></header>
$body
</main>
</body>
</html>
""")

# Published as an Artifact: the host adds doctype/html/head/body, so this is content only.
BOOK = Template("""<title>LangGraph Visual Guide</title>
$fonts
<style>$css</style>
<main class="wrap" id="top">
<header class="top"><a class="brand" href="#top">LangGraph Visual Guide</a><span class="where">Chapter 18</span></header>
$body
</main>
""")


def build():
    page_href = lambda L: "index.html" if L is None else f"{L['slug']}.html"
    (HERE / "index.html").write_text(PAGE.substitute(
        title="LangGraph Visual Guide", fonts=FONTS, css=CSS, where="Chapter 18",
        body=index_body(False, page_href)))
    for i, L in enumerate(LESSONS):
        prev = LESSONS[i - 1] if i else None
        nxt = LESSONS[i + 1] if i + 1 < len(LESSONS) else None
        (HERE / f"{L['slug']}.html").write_text(PAGE.substitute(
            title=f"{L['title']} | LangGraph Visual Guide", fonts=FONTS, css=CSS,
            where=f"Lesson {L['n']} of {TOTAL}", body=lesson_body(L, False, prev, nxt, page_href)))

    book_href = lambda L: "#top" if L is None else f"#lesson-{L['n']}"
    parts = [index_body(True, book_href)]
    for i, L in enumerate(LESSONS):
        prev = LESSONS[i - 1] if i else None
        nxt = LESSONS[i + 1] if i + 1 < len(LESSONS) else None
        parts.append(f'<article class="book-lesson" id="lesson-{L["n"]}">'
                     f'{lesson_body(L, True, prev, nxt, book_href)}</article>')
    (HERE / "langgraph-visual-guide.html").write_text(BOOK.substitute(
        fonts=FONTS, css=CSS, body="\n".join(parts)))
    print(f"built index.html, {len(LESSONS)} lesson pages, langgraph-visual-guide.html")


if __name__ == "__main__":
    build()
