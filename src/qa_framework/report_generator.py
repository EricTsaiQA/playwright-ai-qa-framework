"""
Generates Markdown & HTML QA Acceptance Reports for Client Release Sign-Off.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import List
from .self_healing_locator import HealingEvent


@dataclass
class QATestCaseResult:
    case_id: str
    module: str
    expected: str
    actual: str
    duration_ms: float
    passed: bool


def generate_markdown_acceptance_report(
    project_name: str,
    cases: List[QATestCaseResult],
    healing_events: List[HealingEvent],
    output_path: Path | None = None,
) -> str:
    passed_count = sum(1 for c in cases if c.passed)
    total_count = len(cases)
    pass_rate = round((passed_count / total_count) * 100.0, 1) if total_count else 100.0

    lines = [
        f"# 《QA 測試與交付驗收報告》 (QA Verification & Handover Report)",
        "",
        f"- **Project / 專案名稱**: `{project_name}`",
        f"- **Lead QA Architect / 驗收簽核**: Eric Tsai (`EricTsaiQA`) — e3t4fun Half-Human, Half-AI Studio",
        f"- **Pass Rate / 測試通過率**: `{pass_rate}% ({passed_count}/{total_count} Passed)`",
        "",
        "## 1. Functional & E2E Test Matrix (核心功能與自動化測試結果)",
        "",
        "| Case ID | Module / Scenario | Expected Outcome | Actual Result | Latency | Status |",
        "| :--- | :--- | :--- | :--- | :--- | :--- |",
    ]
    for c in cases:
        badge = "✅ PASS" if c.passed else "❌ FAIL"
        lines.append(
            f"| **{c.case_id}** | {c.module} | {c.expected} | {c.actual} | `{c.duration_ms:.1f} ms` | {badge} |"
        )

    if healing_events:
        lines.extend(
            [
                "",
                "## 2. Self-Healing Selector Telemetry (自我修復定位器紀錄)",
                "",
                "| Case / Step | Broken Selector | Healed Selector | Confidence | Latency | DOM Token Reduction |",
                "| :--- | :--- | :--- | :--- | :--- | :--- |",
            ]
        )
        for ev in healing_events:
            lines.append(
                f"| `{ev.case_id}/{ev.step_id}` | `{ev.broken_selector}` | `{ev.healed_selector}` | "
                f"`{ev.confidence_score:.2f}` | `{ev.healing_latency_ms:.2f} ms` | `-{ev.token_reduction_pct:.2f}%` |"
            )

    md = "\n".join(lines) + "\n"
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(md, encoding="utf-8")
    return md


def generate_html_acceptance_report(project_name: str, cases: List[QATestCaseResult]) -> str:
    rows = "".join(
        f"<tr><td>{c.case_id}</td><td>{c.module}</td><td>{c.actual}</td>"
        f"<td>{'PASS' if c.passed else 'FAIL'}</td></tr>"
        for c in cases
    )
    return (
        f"<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'><title>{project_name} QA Report</title></head>"
        f"<body><h1>{project_name} — QA Verification Report</h1>"
        f"<table border='1'><thead><tr><th>ID</th><th>Module</th><th>Actual</th><th>Status</th></tr></thead>"
        f"<tbody>{rows}</tbody></table></body></html>"
    )
