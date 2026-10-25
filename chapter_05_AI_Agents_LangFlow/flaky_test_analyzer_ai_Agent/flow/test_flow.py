#!/usr/bin/env python3
"""
Test the Flaky Test Analyzer Langflow flow end to end.

Imports Flaky_Test_Analyzer.json into a running Langflow, runs it against
fixture folders with known answers, then deletes the imported copy.

    python3 test_flow.py                 # needs Langflow on :7860
    LANGFLOW_URL=... python3 test_flow.py
"""
import gzip
import json
import os
import re
import sys
import urllib.error
import urllib.request

BASE = os.environ.get("LANGFLOW_URL", "http://localhost:7860")
HERE = os.path.dirname(os.path.abspath(__file__))
FLOW_FILE = os.path.join(HERE, "Flaky_Test_Analyzer.json")
# Folder as seen from INSIDE the container (mounted by langflow-up.sh).
ROOT = "/test-results/flaky_test_analyzer_ai_Agent"


def _call(path, data=None, headers=None, method=None):
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(
        BASE + path, data=body, method=method or ("POST" if data is not None else "GET")
    )
    req.add_header("Content-Type", "application/json")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            raw = resp.read()
            if resp.headers.get("Content-Encoding") == "gzip":
                raw = gzip.decompress(raw)
            text = raw.decode()
            try:
                return resp.status, json.loads(text)
            except json.JSONDecodeError:
                return resp.status, text
    except urllib.error.HTTPError as e:
        raw = e.read()
        if e.headers.get("Content-Encoding") == "gzip":
            raw = gzip.decompress(raw)
        return e.code, raw.decode()[:2000]


def bootstrap():
    """Auto-login, then mint an API key (run endpoints require one since v1.5)."""
    st, out = _call("/api/v1/auto_login")
    if st != 200:
        sys.exit(f"Langflow not reachable at {BASE} (auto_login -> {st})")
    bearer = {"Authorization": "Bearer " + out["access_token"]}
    st, out = _call("/api/v1/api_key/", {"name": "flaky-flow-test"}, headers=bearer)
    if st not in (200, 201):
        sys.exit(f"could not create api key: {st} {out}")
    return bearer, (out.get("api_key") or out.get("key"))


def run_flow(flow_id, key, folder):
    st, out = _call(
        f"/api/v1/run/{flow_id}?stream=false",
        {"output_type": "chat", "input_type": "chat", "input_value": folder},
        headers={"x-api-key": key},
    )
    if st != 200:
        return st, str(out)
    try:
        return 200, out["outputs"][0]["outputs"][0]["results"]["message"]["text"]
    except (KeyError, IndexError, TypeError):
        return 200, json.dumps(out)


def num(pattern, text):
    m = re.search(pattern, text)
    return int(m.group(1)) if m else None


CASES = [
    # name,                            folder,                          flaky, consistent
    ("real data (result1 vs result2)",  ROOT,                                1, 2),
    ("host path is remapped",
     "/Users/promode/Documents/AITesterBlueprint3x/chapter_05_AI_Agents_LangFlow/"
     "flaky_test_analyzer_ai_Agent",                                         1, 2),
    ("flaky in both directions",        f"{ROOT}/flow/tests/two_way",        2, 2),
    ("fully stable suite",              f"{ROOT}/flow/tests/stable",         0, 0),
    ("retry flakiness inside one run",  f"{ROOT}/flow/tests/retry_flaky",    1, 0),
    ("test present in only one run",    f"{ROOT}/flow/tests/uneven",         0, 0),
]

ERROR_CASES = [
    ("missing folder",         "/test-results/does_not_exist"),
    ("folder with no reports", "/test-results"),
]


def main():
    bearer, key = bootstrap()

    flow = json.load(open(FLOW_FILE))
    flow.pop("id", None)
    flow["name"] = "ZZ_flaky_flow_undertest"
    st, created = _call("/api/v1/flows/", flow, headers=bearer)
    if st not in (200, 201):
        sys.exit(f"import of {os.path.basename(FLOW_FILE)} failed: {st} {created}")
    flow_id = created["id"]
    print(f"imported {os.path.basename(FLOW_FILE)} -> {flow_id}\n")

    passed = failed = 0
    try:
        for name, folder, want_f, want_c in CASES:
            st, text = run_flow(flow_id, key, folder)
            got_f = num(r"FLAKY TEST COUNT:\s*(\d+)", text) if st == 200 else None
            got_c = num(r"## CONSISTENT_FAILURES \((\d+)\)", text) if st == 200 else None
            ok = st == 200 and got_f == want_f and got_c == want_c
            print(f"[{'PASS' if ok else 'FAIL'}] {name}")
            print(f"       flaky {got_f}/{want_f}  consistent {got_c}/{want_c}")
            if not ok:
                print("       " + text[:300].replace("\n", "\n       "))
            passed += ok
            failed += not ok

        print()
        for name, folder in ERROR_CASES:
            st, text = run_flow(flow_id, key, folder)
            low = text.lower()
            ok = st != 200 or "not found" in low or "need two" in low or "error" in low
            print(f"[{'PASS' if ok else 'FAIL'}] {name} raises instead of answering wrongly")
            passed += ok
            failed += not ok
    finally:
        _call(f"/api/v1/flows/{flow_id}", headers=bearer, method="DELETE")
        print(f"\ncleaned up {flow_id}")

    print(f"\n{passed} passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
