"""Run 24x7: test every Jira ticket the JQL finds, then label it so it runs once.

    python worker.py            # one pass: what cron / GitHub Actions call on a schedule
    python worker.py --loop 15  # or stay up and check every 15 minutes
"""
import os
import sys
import time

import jira
from pipeline import app

JQL = os.getenv("JQL", "project = VWO AND labels = qa-auto AND labels != qa-auto-done ORDER BY created")


def once():
    for key in jira.search(JQL):
        print(f"[worker] testing {key}", flush=True)
        try:
            final = app.invoke({"key": key, "send": True}, {"recursion_limit": 20})
            jira.mark_done(key)  # only after a finished run, so a crash is retried next pass
            print(f"[worker] {key} done: {final['report']}", flush=True)
        except Exception as exc:  # one bad ticket must not stop the rest of the inbox
            print(f"[worker] {key} failed: {str(exc)[:300]}", flush=True)


if __name__ == "__main__":
    if "--loop" in sys.argv:
        minutes = int(sys.argv[sys.argv.index("--loop") + 1])
        while True:
            once()
            time.sleep(minutes * 60)
    once()
