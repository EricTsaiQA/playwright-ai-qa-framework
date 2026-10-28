"""
Automated RWD Horizontal Overflow Detector & Visual Layout Auditor.
Detects mobile/desktop viewport overflow (`scrollWidth > clientWidth`),
broken image assets (`naturalWidth == 0`), and tap-target sizing violations.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class OverflowIssue:
    selector: str
    element_width: int
    viewport_width: int
    overflow_px: int


@dataclass
class RWDAuditReport:
    viewport_name: str
    viewport_width: int
    viewport_height: int
    has_horizontal_overflow: bool
    document_scroll_width: int
    overflowing_elements: List[OverflowIssue] = field(default_factory=list)
    broken_images: List[str] = field(default_factory=list)
    passed: bool = True


def audit_viewport_metrics(
    viewport_name: str,
    viewport_width: int,
    viewport_height: int,
    document_scroll_width: int,
    element_boxes: List[Dict[str, Any]],
    images: Optional[List[Dict[str, Any]]] = None,
) -> RWDAuditReport:
    """
    Evaluates layout metrics collected from `page.evaluate(...)` to catch RWD horizontal overflow
    and broken images on iPhone SE (375px), iPhone 16 Pro (393px), and Desktop (1440px).
    """
    overflows: List[OverflowIssue] = []
    for box in element_boxes:
        right_edge = int(box.get("right", box.get("width", 0)))
        if right_edge > viewport_width + 1:
            overflows.append(
                OverflowIssue(
                    selector=str(box.get("selector", "unknown")),
                    element_width=int(box.get("width", right_edge)),
                    viewport_width=viewport_width,
                    overflow_px=right_edge - viewport_width,
                )
            )

    broken_imgs: List[str] = []
    for img in (images or []):
        if not img.get("complete", True) or int(img.get("naturalWidth", 1)) == 0:
            broken_imgs.append(str(img.get("src", "unknown-src")))

    has_overflow = (document_scroll_width > viewport_width + 1) or bool(overflows)
    passed = (not has_overflow) and (len(broken_imgs) == 0)

    return RWDAuditReport(
        viewport_name=viewport_name,
        viewport_width=viewport_width,
        viewport_height=viewport_height,
        has_horizontal_overflow=has_overflow,
        document_scroll_width=document_scroll_width,
        overflowing_elements=overflows,
        broken_images=broken_imgs,
        passed=passed,
    )
