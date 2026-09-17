from dataclasses import dataclass, field
from typing import Literal


@dataclass
class Region:
    id: str
    page: int
    bbox: tuple[float, float, float, float]
    text: str
    source: Literal["native_annotation", "hand_drawn"]
    subtype: str
    color: tuple[float, float, float] | None
    merged_from: list[str] = field(default_factory=list)


@dataclass
class TextSpan:
    page: int
    bbox: tuple[float, float, float, float]
    text: str
    order_key: tuple[int, float, float]


@dataclass
class Finding:
    rule_id: str
    confidence: Literal["confirmed", "needs_review"]
    page: int
    bbox: tuple[float, float, float, float] | None
    snippet: str
    explanation: str
    region_id: str | None = None


@dataclass
class ComplianceReport:
    document: str
    status: Literal["PASS", "FAIL", "NEEDS_REVIEW"]
    rules_checked: int
    rules_violated: int
    needs_review_count: int
    findings: list[Finding]
