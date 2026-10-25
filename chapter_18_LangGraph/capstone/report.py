"""One self-contained HTML report (screenshots inlined), optionally emailed."""
import base64
import html
import os
import smtplib
from email.message import EmailMessage
from pathlib import Path

CSS = """body{font:15px/1.55 -apple-system,'Segoe UI',Arial,sans-serif;color:#13294B;max-width:980px;margin:24px auto;padding:0 16px}
h1{font-size:24px;margin:0 0 8px} h2{font-size:14px;letter-spacing:1px;text-transform:uppercase;color:#5F7090;margin:30px 0 10px}
table{border-collapse:collapse;width:100%} th,td{border-bottom:1px solid #D9E1EC;padding:8px;text-align:left;vertical-align:top}
.pill{display:inline-block;padding:2px 10px;border-radius:99px;font-weight:600;font-size:13px}
.passed{background:#E4F4EB;color:#1E8A5A} .failed{background:#FDE8E8;color:#B42318} .skipped{background:#FFF5E1;color:#9A5B0B}
pre{white-space:pre-wrap;background:#F7F9FC;padding:12px;border-radius:8px} code{font-size:13px}
img{max-width:100%;border:1px solid #D9E1EC;border-radius:6px} details{margin:4px 0}"""


def write(s):
    """Write <run folder>/report.html and return its path."""
    e = html.escape
    res, t, plan = s["results"], s["ticket"], s["plan"]
    n = {k: sum(r["status"] == k for r in res) for k in ("passed", "failed", "skipped")}
    why = {v["id"]: v for v in s.get("triage", [])}

    rows = "".join(
        f"<tr><td>{e(r['id'])}</td><td><details><summary>{e(r['title'])}</summary><ol>"
        + "".join(f"<li><code>{e(st['do'])} {e(st['target'])} {e(st['value'])}</code></li>" for st in r["steps"])
        + f"</ol></details></td><td>{e(r['priority'])}</td><td><span class='pill {r['status']}'>{r['status']}</span></td>"
        f"<td>{e(r.get('error', ''))}</td></tr>" for r in res)

    fails = ""
    for r in (r for r in res if r["status"] == "failed"):
        v = why.get(r["id"], {})
        shot = base64.b64encode(Path(r["screenshot"]).read_bytes()).decode()
        fails += (f"<h3>{e(r['id'])}: {e(r['title'])}</h3>"
                  f"<p><b>{e(v.get('category', 'not triaged'))}</b>: {e(v.get('reason', ''))}<br>"
                  f"Failed at step {r['step']}: <code>{e(r['error'])}</code></p>"
                  f"<img alt='Screenshot when {e(r['id'])} failed' src='data:image/png;base64,{shot}'>")

    doc = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>{e(t['key'])} QA report</title><style>{CSS}</style></head><body>
<h1>{e(t['key'])}: {e(t['summary'])}</h1>
<p><span class="pill passed">{n['passed']} passed</span> <span class="pill failed">{n['failed']} failed</span>
<span class="pill skipped">{n['skipped']} skipped</span></p>
<h2>Test cases and results</h2>
<table><tr><th>ID</th><th>Test case (click for steps)</th><th>Priority</th><th>Status</th><th>Failure</th></tr>{rows}</table>
<h2>Failure analysis</h2>{fails or '<p>No failures.</p>'}
{f"<h2>Review notes not fixed before the run</h2><pre>{e(s['feedback'])}</pre>" if s.get("feedback") else ""}
<h2>Test plan</h2><p>{e(plan['scope'])}</p><ul>{''.join(f'<li>{e(x)}</li>' for x in plan['risks'])}</ul>
<h2>Requirement analysis</h2><details><summary>What the AI read in {e(t['key'])} (click to open)</summary><pre>{e(s['analysis'])}</pre></details>
</body></html>"""
    path = Path(s["out"]) / "report.html"
    path.write_text(doc)
    return path


def email(path, subject):
    """Send the report as the email body, plus attached (Gmail hides inline data: images)."""
    msg = EmailMessage()
    msg["Subject"], msg["From"], msg["To"] = subject, os.environ["SMTP_USER"], os.environ["REPORT_TO"]
    msg.set_content("This report is HTML. Open the attached report.html for screenshots.")
    msg.add_alternative(path.read_text(), subtype="html")
    msg.add_attachment(path.read_bytes(), maintype="text", subtype="html", filename=path.name)
    with smtplib.SMTP_SSL(os.environ["SMTP_HOST"], int(os.getenv("SMTP_PORT", "465"))) as smtp:
        smtp.login(os.environ["SMTP_USER"], os.environ["SMTP_PASSWORD"])
        smtp.send_message(msg)
