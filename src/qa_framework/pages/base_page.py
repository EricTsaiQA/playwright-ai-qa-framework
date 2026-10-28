"""
Page Object Model (POM) Base Class with Integrated Self-Healing Selector Resolution.
"""
from __future__ import annotations
from typing import Dict, Optional
from ..ax_compressor import PrunedAXSnapshot, compress_html_to_ax_snapshot
from ..self_healing_locator import HealingEvent, SemanticLocatorHint, SelfHealingLocatorResolver


class BasePage:
    def __init__(self, base_url: str, resolver: Optional[SelfHealingLocatorResolver] = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.resolver = resolver or SelfHealingLocatorResolver()
        self._selector_cache: Dict[str, str] = {}

    def resolve_resilient_selector(
        self,
        html_dom: str,
        case_id: str,
        step_id: str,
        primary_selector: str,
        hint: SemanticLocatorHint,
    ) -> tuple[str, Optional[HealingEvent], PrunedAXSnapshot]:
        """
        Checks if the primary selector exists in the current DOM snapshot.
        If missing (simulating a frontend refactor that broke an ID/class), automatically triggers
        sub-20ms semantic self-healing and caches the repaired selector for zero-token CI replay.
        """
        snapshot = compress_html_to_ax_snapshot(html_dom, url=self.base_url)
        for node in snapshot.nodes:
            if primary_selector in (node.css_selector, f"#{node.id_attr}", f'[data-testid="{node.test_id}"]'):
                return primary_selector, None, snapshot

        healed_selector, event = self.resolver.heal(
            snapshot=snapshot,
            case_id=case_id,
            step_id=step_id,
            broken_selector=primary_selector,
            hint=hint,
        )
        self._selector_cache[primary_selector] = healed_selector
        return healed_selector, event, snapshot
