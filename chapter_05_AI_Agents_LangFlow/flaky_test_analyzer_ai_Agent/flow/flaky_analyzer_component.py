import json
from pathlib import Path

from langflow.custom import Component
from langflow.io import MessageTextInput, Output
from langflow.schema.message import Message

# The container only sees mounted paths. Accept host paths and remap them.
HOST_TO_CONTAINER = {
    "/Users/promode/Documents/AITesterBlueprint3x/chapter_05_AI_Agents_LangFlow": "/test-results",
}

PASSED, FAILED, SKIPPED, FLAKY_IN_RUN = "passed", "failed", "skipped", "flaky-in-run"


class FlakyTestAnalyzer(Component):
    display_name = "Flaky Test Analyzer"
    description = "Read two Playwright results.json files from a folder and report flaky tests."
    icon = "activity"
    name = "FlakyTestAnalyzer"

    inputs = [
        MessageTextInput(
            name="folder",
            display_name="Results Folder",
            info="Folder holding result1.json and result2.json (host or container path).",
            value="/test-results/flaky_test_analyzer_ai_Agent",
        ),
    ]

    outputs = [Output(display_name="Report", name="report", method="analyze")]

    # ---------- path handling ----------

    def _resolve(self, raw: str) -> Path:
        text = (raw or "").strip().strip('"').strip("'")
        if not text:
            text = "/test-results/flaky_test_analyzer_ai_Agent"
        for host, container in HOST_TO_CONTAINER.items():
            if text == host:
                text = container
            elif text.startswith(host + "/"):
                text = container + text[len(host):]
        return Path(text)

    def _find_pair(self, folder: Path):
        if not folder.exists():
            raise ValueError(f"Folder not found inside the Langflow container: {folder}")
        if not folder.is_dir():
            raise ValueError(f"Not a folder: {folder}")

        first = folder / "result1.json"
        second = folder / "result2.json"
        if first.exists() and second.exists():
            return first, second

        candidates = sorted(p for p in folder.glob("*.json") if p.is_file())
        if len(candidates) < 2:
            raise ValueError(
                f"Need two Playwright JSON reports in {folder}, found {len(candidates)}."
            )
        return candidates[0], candidates[1]

    # ---------- playwright parsing ----------

    def _walk(self, node, trail, out):
        for suite in node.get("suites") or []:
            self._walk(suite, trail + [suite.get("title", "")], out)
        for spec in node.get("specs") or []:
            parts = [p for p in trail if p]
            key = f"{spec.get('file', '')} > {' > '.join(parts)} > {spec.get('title', '')}"
            statuses = []
            for test in spec.get("tests") or []:
                for result in test.get("results") or []:
                    statuses.append(result.get("status"))
            out[key] = statuses

    def _verdict(self, statuses):
        """Collapse Playwright retries into one verdict per test."""
        if not statuses:
            return SKIPPED
        bad = {"failed", "timedOut", "interrupted"}
        had_pass = any(s == "passed" for s in statuses)
        had_fail = any(s in bad for s in statuses)
        if had_pass and had_fail:
            return FLAKY_IN_RUN  # Playwright's own retry already proved instability
        if had_pass:
            return PASSED
        if had_fail:
            return FAILED
        return SKIPPED

    def _parse(self, path: Path):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path.name} is not valid JSON: {exc}") from exc
        if "suites" not in data:
            raise ValueError(f"{path.name} does not look like a Playwright JSON report.")
        raw = {}
        for suite in data.get("suites") or []:
            self._walk(suite, [suite.get("title", "")], raw)
        return {k: self._verdict(v) for k, v in raw.items()}, data.get("stats", {})

    # ---------- main ----------

    def analyze(self) -> Message:
        folder = self._resolve(self.folder)
        file_a, file_b = self._find_pair(folder)

        run_a, stats_a = self._parse(file_a)
        run_b, stats_b = self._parse(file_b)

        shared = set(run_a) & set(run_b)
        only_a = sorted(set(run_a) - set(run_b))
        only_b = sorted(set(run_b) - set(run_a))

        # Flaky = same test, different verdict across the two runs,
        # plus anything Playwright already flagged flaky via retries.
        flipped = sorted(t for t in shared if run_a[t] != run_b[t])
        retry_flaky = sorted(
            t for t in shared
            if FLAKY_IN_RUN in (run_a[t], run_b[t]) and t not in flipped
        )
        flaky = flipped + retry_flaky

        consistent_fail = sorted(
            t for t in shared if run_a[t] == FAILED and run_b[t] == FAILED
        )

        lines = []
        lines.append(f"FLAKY TEST COUNT: {len(flaky)}")
        lines.append("")
        lines.append(f"Run A: {file_a.name}  ({len(run_a)} tests)")
        lines.append(f"Run B: {file_b.name}  ({len(run_b)} tests)")
        lines.append(f"Compared: {len(shared)} tests present in both runs")
        lines.append("")

        lines.append(f"## FLAKY_TESTS ({len(flaky)})")
        if flaky:
            for t in flipped:
                lines.append(f"- [{run_a[t]} -> {run_b[t]}] {t}")
            for t in retry_flaky:
                lines.append(f"- [flaky on retry within a run] {t}")
        else:
            lines.append("- none")
        lines.append("")

        lines.append(f"## CONSISTENT_FAILURES ({len(consistent_fail)})")
        if consistent_fail:
            for t in consistent_fail:
                lines.append(f"- {t}")
        else:
            lines.append("- none")
        lines.append("")

        if only_a or only_b:
            lines.append(f"## NOT_COMPARABLE ({len(only_a) + len(only_b)})")
            for t in only_a:
                lines.append(f"- only in {file_a.name}: {t}")
            for t in only_b:
                lines.append(f"- only in {file_b.name}: {t}")
            lines.append("")

        lines.append("## RERUN_RECOMMENDATION")
        if flaky:
            lines.append(
                f"Quarantine and rerun the {len(flaky)} flaky test(s) above; "
                "they changed verdict between identical runs, so they are unreliable signals."
            )
        else:
            lines.append("No verdict changed between runs. Nothing to quarantine.")
        if consistent_fail:
            lines.append(
                f"The {len(consistent_fail)} consistent failure(s) are real bugs, not flakiness. Fix them."
            )

        lines.append("")
        lines.append("## RAW_STATS")
        lines.append(f"- {file_a.name}: {json.dumps(stats_a)}")
        lines.append(f"- {file_b.name}: {json.dumps(stats_b)}")

        report = "\n".join(lines)
        self.status = f"{len(flaky)} flaky, {len(consistent_fail)} consistent failures"
        return Message(text=report)
