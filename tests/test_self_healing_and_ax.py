"""
Unit & Integration Tests for playwright-ai-qa-framework.
Verifies:
1. ~98% DOM-to-Accessibility-Tree token compression
2. Sub-20ms semantic self-healing selector recovery via CheckoutPage POM
3. TokenBudgetCircuitBreaker enforcement
4. Automated RWD horizontal overflow detection
5. Markdown & HTML QA Acceptance Report generation
"""
from __future__ import annotations
from pathlib import Path
import pytest

from qa_framework import (
    QATestCaseResult,
    SelfHealingLocatorResolver,
    TokenBudgetCircuitBreaker,
    audit_viewport_metrics,
    compress_html_to_ax_snapshot,
    generate_html_acceptance_report,
    generate_markdown_acceptance_report,
)
from qa_framework.pages import CheckoutPage


def _build_noisy_checkout_html() -> str:
    noisy_scripts = "<script>" + ("const bundleChunk = '0123456789abcdef';\n" * 950) + "</script>"
    noisy_styles = "<style>" + (".unused-utility-class { display: flex; margin: 0; }\n" * 650) + "</style>"
    return f"""<!DOCTYPE html>
    <html>
    <head><title>Enterprise Checkout Portal</title>{noisy_scripts}{noisy_styles}</head>
    <body>
      <header><h1>Secure Checkout</h1></header>
      <main>
        <input type="text" data-testid="promo-code-field" placeholder="Enter promo or discount code" />
        <button type="submit" id="btn-complete-order" aria-label="Complete Purchase">Complete Purchase</button>
      </main>
    </body>
    </html>"""


def test_ax_snapshot_achieves_98_percent_token_compression() -> None:
    html = _build_noisy_checkout_html()
    snapshot = compress_html_to_ax_snapshot(html, url="https://shop.example.com/checkout")
    assert snapshot.raw_estimated_tokens > 10000
    assert snapshot.pruned_estimated_tokens < 250
    assert snapshot.token_reduction_pct >= 97.5
    assert len(snapshot.nodes) == 3


def test_checkout_page_self_heals_broken_selectors_under_20ms(tmp_path: Path) -> None:
    html = _build_noisy_checkout_html()
    page_obj = CheckoutPage(base_url="https://shop.example.com")

    healed_coupon_sel, ev1 = page_obj.locate_coupon_input(html)
    assert healed_coupon_sel == '[data-testid="promo-code-field"]'
    assert ev1 is not None
    assert ev1.confidence_score >= 0.70
    assert ev1.healing_latency_ms < 20.0

    healed_submit_sel, ev2 = page_obj.locate_submit_order_button(html)
    assert healed_submit_sel == "#btn-complete-order"
    assert ev2 is not None
    assert ev2.confidence_score >= 0.80
    assert ev2.healing_latency_ms < 20.0

    report_path = tmp_path / "SAMPLE_QA_ACCEPTANCE_REPORT.md"
    cases = [
        QATestCaseResult(
            case_id="TC-01",
            module="Checkout Promo Input (Self-Healed)",
            expected="Locates promo code field after frontend ID change",
            actual=f"Healed to {healed_coupon_sel} in {ev1.healing_latency_ms:.2f}ms",
            duration_ms=ev1.healing_latency_ms,
            passed=True,
        ),
        QATestCaseResult(
            case_id="TC-02",
            module="Checkout Submit CTA (Self-Healed)",
            expected="Locates submit button via ARIA role + accessible name",
            actual=f"Healed to {healed_submit_sel} in {ev2.healing_latency_ms:.2f}ms",
            duration_ms=ev2.healing_latency_ms,
            passed=True,
        ),
    ]
    md = generate_markdown_acceptance_report("Enterprise Checkout Portal", cases, [ev1, ev2], report_path)
    html_rep = generate_html_acceptance_report("Enterprise Checkout Portal", cases)
    assert "✅ PASS" in md
    assert "Self-Healing Selector Telemetry" in md
    assert "Enterprise Checkout Portal" in html_rep


def test_token_circuit_breaker_trips_on_excessive_calls() -> None:
    breaker = TokenBudgetCircuitBreaker(max_rpm_per_runner=2, max_tokens_per_case=500, max_daily_tokens=1000)
    resolver = SelfHealingLocatorResolver(breaker=breaker, runner_id="runner-test")
    snapshot = compress_html_to_ax_snapshot(_build_noisy_checkout_html())

    page_obj = CheckoutPage(base_url="https://shop.example.com", resolver=resolver)
    page_obj.locate_coupon_input(_build_noisy_checkout_html(), case_id="TC-LIMIT")
    page_obj.locate_submit_order_button(_build_noisy_checkout_html(), case_id="TC-LIMIT")

    with pytest.raises(RuntimeError, match="CIRCUIT_OPEN"):
        page_obj.locate_coupon_input(_build_noisy_checkout_html(), case_id="TC-LIMIT")


def test_rwd_visual_auditor_detects_mobile_horizontal_overflow() -> None:
    clean_mobile = audit_viewport_metrics(
        viewport_name="iPhone 16 Pro",
        viewport_width=393,
        viewport_height=852,
        document_scroll_width=393,
        element_boxes=[{"selector": "header.nav", "right": 393, "width": 393}],
        images=[{"src": "/hero.webp", "complete": True, "naturalWidth": 800}],
    )
    assert clean_mobile.passed is True
    assert not clean_mobile.has_horizontal_overflow

    broken_mobile = audit_viewport_metrics(
        viewport_name="iPhone SE",
        viewport_width=375,
        viewport_height=667,
        document_scroll_width=520,
        element_boxes=[{"selector": "div.pricing-table-wide", "right": 520, "width": 520}],
        images=[{"src": "/missing-banner.png", "complete": True, "naturalWidth": 0}],
    )
    assert broken_mobile.passed is False
    assert broken_mobile.has_horizontal_overflow is True
    assert len(broken_mobile.overflowing_elements) == 1
    assert broken_mobile.overflowing_elements[0].overflow_px == 145
    assert broken_mobile.broken_images == ["/missing-banner.png"]
