"""Jira over REST with an API token: fetch a ticket, search with JQL, label it done.

People can pull the same ticket through the Atlassian MCP (see README); code that
runs unattended 24x7 uses the API because a token needs no browser login.
"""
import base64
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"


def _call(path, body=None, method="GET"):
    auth = base64.b64encode(f"{os.environ['JIRA_EMAIL']}:{os.environ['JIRA_API_TOKEN']}".encode()).decode()
    req = urllib.request.Request(
        os.environ["JIRA_URL"].rstrip("/") + path, method=method,
        data=json.dumps(body).encode() if body else None,
        headers={"Authorization": f"Basic {auth}", "Accept": "application/json",
                 "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read() or "{}")
    except urllib.error.HTTPError as exc:  # Jira answers an expired token with 401, or 404 for anything it hides
        raise RuntimeError(f"Jira said {exc.code} for {path}. 401 or 404 on a real ticket usually means the "
                           "API token expired: make a new one at id.atlassian.com > Security > API tokens") from None


def _text(adf):
    """Jira v3 descriptions are ADF (nested JSON), not text."""
    if isinstance(adf, list):
        return "".join(_text(n) for n in adf)
    if not isinstance(adf, dict):
        return adf or ""
    if adf.get("type") == "text":
        return adf.get("text", "")
    inner = _text(adf.get("content", []))
    return inner + "\n" if adf.get("type") in ("paragraph", "heading", "listItem") else inner


def fetch(key):
    """One ticket as {key, summary, description}. No token? Use fixtures/<key>.json (class demo)."""
    if not os.getenv("JIRA_API_TOKEN"):
        return json.loads((FIXTURES / f"{key}.json").read_text())
    fields = _call(f"/rest/api/3/issue/{key}?fields=summary,description")["fields"]
    return {"key": key, "summary": fields["summary"], "description": _text(fields["description"]).strip()}


def search(jql):
    """Ticket keys matching a JQL query: the 24x7 worker's inbox."""
    query = urllib.parse.urlencode({"jql": jql, "fields": "summary", "maxResults": 20})
    return [issue["key"] for issue in _call(f"/rest/api/3/search/jql?{query}")["issues"]]


def mark_done(key, label="qa-auto-done"):
    """Add a label so the worker's JQL skips this ticket from now on."""
    _call(f"/rest/api/3/issue/{key}", {"update": {"labels": [{"add": label}]}}, method="PUT")
