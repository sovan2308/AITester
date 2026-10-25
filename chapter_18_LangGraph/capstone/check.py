"""The runnable check: executor, safety rules, report and Jira parsing, fully offline.

    python check.py

Serves a two-page fake TTACart on localhost (same data-test ids as the real app),
so no LLM, Jira or internet is needed. Every assert is one thing the capstone promises.
"""
import http.server
import tempfile
import threading
from functools import partial
from pathlib import Path

import executor
import jira
import report

FAKE = {
    "index.html": """<input data-test="username"><input data-test="password" type="password">
<button data-test="login-button">Login</button><div data-test="error"></div>
<script>document.querySelector('[data-test=login-button]').onclick = () => {
  if (document.querySelector('[data-test=username]').value === 'locked_out_user')
    document.querySelector('[data-test=error]').textContent = 'Epic sadface: Sorry, this user has been locked out.';
  else location.href = 'inventory.html'; };</script>""",
    "inventory.html": """<span data-test="title">Products</span><span data-test="shopping-cart-badge"></span>
<button data-test="add-to-cart-tta-bike-light">Add to cart</button>
<script>let n = 0; document.querySelector('[data-test=add-to-cart-tta-bike-light]').onclick =
  () => document.querySelector('[data-test=shopping-cart-badge]').textContent = ++n;</script>""",
}


def step(do, target="", value=""):
    return {"do": do, "target": target, "value": value}


LOGIN = [step("goto"), step("fill", "username", "standard_user"),
         step("fill", "password", "fixture-pass"), step("click", "login-button")]
CASES = [
    {"id": "TC-01", "title": "add one item", "priority": "P0",
     "steps": LOGIN + [step("url", value="inventory.html"), step("see", "title", "Products"),
                       step("not see", "shopping-cart-badge", "1"),
                       step("click", "add-to-cart-tta-bike-light"), step("see", "shopping-cart-badge", "1")]},
    {"id": "TC-02", "title": "badge shows 2 (wrong on purpose)", "priority": "P1",
     "steps": LOGIN + [step("click", "add-to-cart-tta-bike-light"), step("see", "shopping-cart-badge", "2")]},
    {"id": "TC-03", "title": "locked out user", "priority": "P0",
     "steps": [step("goto"), step("fill", "username", "locked_out_user"), step("click", "login-button"),
               step("see", "error", "locked out")]},
]


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def serve(folder, port=0):
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), partial(Quiet, directory=folder))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


if __name__ == "__main__":
    tmp = Path(tempfile.mkdtemp())
    for name, body in FAKE.items():
        (tmp / name).write_text(body)
    server = serve(str(tmp))
    base = f"http://127.0.0.1:{server.server_port}/"

    # 1. safety rules: an LLM-written step that leaves the app or invents an element is refused
    assert executor.problems(CASES[0]) == []
    assert executor.problems({"steps": [step("goto", value="https://evil.example")]})
    assert executor.problems({"steps": [step("click", "buy-now")]})
    assert executor.problems({"steps": [step("count", "inventory-item-name", "six")]})

    # 2. executor: a pass, a real failure with step number + screenshot, and a negative test that passes
    results = executor.run(CASES, tmp, base_url=base)
    status = {r["id"]: r["status"] for r in results}
    assert status == {"TC-01": "passed", "TC-02": "failed", "TC-03": "passed"}, status
    failed = results[1]
    assert failed["step"] == 6 and Path(failed["screenshot"]).stat().st_size > 1000, failed

    # 3. report: one self-contained HTML file with counts, steps and the inlined screenshot
    html = report.write({"ticket": {"key": "VWO-105", "summary": "check"}, "analysis": "-",
                         "plan": {"scope": "-", "risks": []}, "results": results, "out": tmp,
                         "triage": [{"id": "TC-02", "category": "test_bug", "reason": "wrong count"}]}).read_text()
    assert "2 passed" in html and "1 failed" in html and "data:image/png;base64," in html and "test_bug" in html

    # 4. jira: ADF (Jira's rich-text JSON) becomes plain text; fixture works with no token
    adf = {"type": "doc", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Log in"}]}]}
    assert jira._text(adf) == "Log in\n"
    assert jira.fetch("VWO-105")["summary"].startswith("Product Requirements Document")

    server.shutdown()
    print("all checks passed:", status)
