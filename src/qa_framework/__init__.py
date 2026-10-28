"""
playwright-ai-qa-framework
Enterprise E2E QA Automation Framework with Accessibility-Tree Compression,
Sub-20ms Semantic Self-Healing Locators, RWD Overflow Auditing, and BYOK Token Circuit Breakers.
Author: Eric Tsai (EricTsaiQA) — e3t4fun Studio
"""
from .ax_compressor import PrunedAXSnapshot, SemanticAXNode, compress_html_to_ax_snapshot
from .self_healing_locator import (
    HealingEvent,
    SemanticLocatorHint,
    SelfHealingLocatorResolver,
    TokenBudgetCircuitBreaker,
)
from .rwd_visual_auditor import OverflowIssue, RWDAuditReport, audit_viewport_metrics
from .report_generator import QATestCaseResult, generate_markdown_acceptance_report, generate_html_acceptance_report

__all__ = [
    "PrunedAXSnapshot",
    "SemanticAXNode",
    "compress_html_to_ax_snapshot",
    "HealingEvent",
    "SemanticLocatorHint",
    "SelfHealingLocatorResolver",
    "TokenBudgetCircuitBreaker",
    "OverflowIssue",
    "RWDAuditReport",
    "audit_viewport_metrics",
    "QATestCaseResult",
    "generate_markdown_acceptance_report",
    "generate_html_acceptance_report",
]
