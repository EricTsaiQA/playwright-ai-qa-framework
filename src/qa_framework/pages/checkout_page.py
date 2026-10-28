"""
Sample E-Commerce Checkout Page Object demonstrating Self-Healing POM in action.
"""
from __future__ import annotations
from typing import Optional
from .base_page import BasePage
from ..self_healing_locator import HealingEvent, SemanticLocatorHint


class CheckoutPage(BasePage):
    LEGACY_COUPON_INPUT = "#legacy-promo-code-input"
    LEGACY_SUBMIT_BTN = "#legacy-pay-now-btn"

    def locate_coupon_input(self, html_dom: str, case_id: str = "TC-CHECKOUT-01") -> tuple[str, Optional[HealingEvent]]:
        sel, ev, _ = self.resolve_resilient_selector(
            html_dom=html_dom,
            case_id=case_id,
            step_id="step-coupon-input",
            primary_selector=self.LEGACY_COUPON_INPUT,
            hint=SemanticLocatorHint(
                intent="Enter discount or promo coupon code",
                expected_role="textbox",
                expected_placeholder="Enter promo or discount code",
                tag_hint="input",
            ),
        )
        return sel, ev

    def locate_submit_order_button(self, html_dom: str, case_id: str = "TC-CHECKOUT-01") -> tuple[str, Optional[HealingEvent]]:
        sel, ev, _ = self.resolve_resilient_selector(
            html_dom=html_dom,
            case_id=case_id,
            step_id="step-submit-order",
            primary_selector=self.LEGACY_SUBMIT_BTN,
            hint=SemanticLocatorHint(
                intent="Complete purchase and submit order",
                expected_role="button",
                expected_name="Complete Purchase",
                expected_type="submit",
                tag_hint="button",
            ),
        )
        return sel, ev
