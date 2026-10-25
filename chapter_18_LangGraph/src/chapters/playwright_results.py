"""Parse a Playwright JSON report into {test id: verdict}. Same rules as chapter 5."""
import json
from pathlib import Path

BAD = {"failed", "timedOut", "interrupted"}


def _walk(node, trail, out):
    for suite in node.get("suites") or []:
        _walk(suite, trail + [suite.get("title", "")], out)
    for spec in node.get("specs") or []:
        parts = " > ".join(p for p in trail if p)
        key = f"{parts} > {spec.get('title', '')}"
        out[key] = [r.get("status") for t in spec.get("tests") or []
                    for r in t.get("results") or []]


def verdict(statuses):
    if not statuses:
        return "skipped"
    passed = "passed" in statuses
    failed = any(s in BAD for s in statuses)
    if passed and failed:
        return "flaky-in-run"
    return "passed" if passed else ("failed" if failed else "skipped")


def load_report(path: Path) -> dict[str, str]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    raw = {}
    for suite in data.get("suites") or []:
        _walk(suite, [suite.get("title", "")], raw)
    return {k: verdict(v) for k, v in raw.items()}
