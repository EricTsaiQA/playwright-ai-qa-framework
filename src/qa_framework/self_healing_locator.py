"""
Deterministic + Semantic Self-Healing Selector Resolver with BYOK Token Circuit Breaker.
Heals broken CSS/ID selectors via ARIA role, accessible name, placeholder, and test-id similarity
in <20ms without burning paid LLM API tokens on every CI run.
"""
from __future__ import annotations
from collections import defaultdict, deque
from dataclasses import dataclass
import difflib
import time
from typing import Deque, Dict, List, Optional, Tuple

from .ax_compressor import PrunedAXSnapshot, SemanticAXNode


@dataclass
class SemanticLocatorHint:
    intent: str
    expected_role: str
    expected_name: str = ""
    expected_placeholder: str = ""
    expected_type: str = ""
    tag_hint: str = ""


@dataclass
class HealingEvent:
    case_id: str
    step_id: str
    intent: str
    broken_selector: str
    healed_selector: str
    healed_playwright_locator: str
    matched_ref: str
    confidence_score: float
    healing_latency_ms: float
    raw_dom_tokens: int
    pruned_ax_tokens: int
    token_reduction_pct: float


class TokenBudgetCircuitBreaker:
    """Prevents runaway API token usage during automated QA self-healing or agent exploration."""

    def __init__(
        self,
        max_rpm_per_runner: int = 20,
        max_tokens_per_case: int = 4000,
        max_daily_tokens: int = 150000,
    ) -> None:
        self.max_rpm_per_runner = max_rpm_per_runner
        self.max_tokens_per_case = max_tokens_per_case
        self.max_daily_tokens = max_daily_tokens
        self._runner_hits: Dict[str, Deque[float]] = defaultdict(deque)
        self._case_tokens: Dict[str, int] = defaultdict(int)
        self.daily_tokens_used: int = 0

    def check_and_record(self, runner_id: str, case_id: str, estimated_tokens: int) -> Tuple[bool, str]:
        now = time.time()
        window = self._runner_hits[runner_id]
        while window and now - window[0] > 60.0:
            window.popleft()

        if len(window) >= self.max_rpm_per_runner:
            return False, f"CIRCUIT_OPEN: Runner '{runner_id}' exceeded {self.max_rpm_per_runner} RPM"
        if self._case_tokens[case_id] + estimated_tokens > self.max_tokens_per_case:
            return False, f"CIRCUIT_OPEN: Case '{case_id}' exceeded {self.max_tokens_per_case} token cap"
        if self.daily_tokens_used + estimated_tokens > self.max_daily_tokens:
            return False, f"CIRCUIT_OPEN: Daily token ceiling ({self.max_daily_tokens}) reached"

        window.append(now)
        self._case_tokens[case_id] += max(0, estimated_tokens)
        self.daily_tokens_used += max(0, estimated_tokens)
        return True, "ALLOWED"


class SelfHealingLocatorResolver:
    """Resolves broken selectors against a PrunedAXSnapshot using semantic similarity scoring."""

    def __init__(self, breaker: Optional[TokenBudgetCircuitBreaker] = None, runner_id: str = "ci-runner-01") -> None:
        self.breaker = breaker or TokenBudgetCircuitBreaker()
        self.runner_id = runner_id
        self.events: List[HealingEvent] = []

    @staticmethod
    def score_node(node: SemanticAXNode, hint: SemanticLocatorHint) -> float:
        score = 0.0
        if hint.expected_role and node.role.lower() == hint.expected_role.lower():
            score += 0.35
        elif hint.tag_hint and node.tag.lower() == hint.tag_hint.lower():
            score += 0.25

        if hint.expected_placeholder and node.placeholder:
            ratio = difflib.SequenceMatcher(None, hint.expected_placeholder.lower(), node.placeholder.lower()).ratio()
            score += 0.35 * ratio

        if hint.expected_name and node.name:
            nl, el = node.name.lower(), hint.expected_name.lower()
            if el in nl or nl in el:
                score += 0.35
            else:
                score += 0.35 * difflib.SequenceMatcher(None, el, nl).ratio()

        if hint.expected_type and node.input_type.lower() == hint.expected_type.lower():
            score += 0.20
        elif hint.tag_hint and node.tag.lower() == hint.tag_hint.lower():
            score += 0.15

        intent_words = {w for w in hint.intent.lower().replace("-", " ").split() if len(w) > 2}
        blob = f"{node.name} {node.placeholder} {node.id_attr} {node.test_id} {node.class_hint}".lower()
        overlap = sum(1 for w in intent_words if w in blob)
        if overlap:
            score += min(0.15, overlap * 0.05)

        return round(min(0.99, score), 3)

    def heal(
        self,
        snapshot: PrunedAXSnapshot,
        case_id: str,
        step_id: str,
        broken_selector: str,
        hint: SemanticLocatorHint,
    ) -> Tuple[str, HealingEvent]:
        t0 = time.perf_counter()
        ok, reason = self.breaker.check_and_record(
            runner_id=self.runner_id,
            case_id=case_id,
            estimated_tokens=snapshot.pruned_estimated_tokens,
        )
        if not ok:
            raise RuntimeError(reason)

        best_node: Optional[SemanticAXNode] = None
        best_score = -1.0
        for node in snapshot.nodes:
            s = self.score_node(node, hint)
            if s > best_score:
                best_score = s
                best_node = node

        if not best_node or best_score < 0.35:
            raise LookupError(f"Unable to self-heal broken selector '{broken_selector}' (max_score={best_score})")

        if best_node.test_id:
            healed = f'[data-testid="{best_node.test_id}"]'
        elif best_node.id_attr:
            healed = f"#{best_node.id_attr}"
        elif best_node.placeholder:
            healed = f'{best_node.tag}[placeholder="{best_node.placeholder}"]'
        else:
            healed = best_node.css_selector

        latency_ms = round((time.perf_counter() - t0) * 1000.0, 3)
        ev = HealingEvent(
            case_id=case_id,
            step_id=step_id,
            intent=hint.intent,
            broken_selector=broken_selector,
            healed_selector=healed,
            healed_playwright_locator=best_node.playwright_locator,
            matched_ref=best_node.ref,
            confidence_score=best_score,
            healing_latency_ms=latency_ms,
            raw_dom_tokens=snapshot.raw_estimated_tokens,
            pruned_ax_tokens=snapshot.pruned_estimated_tokens,
            token_reduction_pct=snapshot.token_reduction_pct,
        )
        self.events.append(ev)
        return healed, ev
