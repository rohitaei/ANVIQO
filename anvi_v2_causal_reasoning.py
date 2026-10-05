"""V2 evidence-backed causal reasoning boundary.

The adapter never upgrades temporal association into causation without explicit
validated evidence. It returns hypotheses for human review.
"""
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class CausalHypothesis:
    tenant: object
    hypothesis_id: str
    cause_node: str
    effect_node: str
    confidence: float
    evidence_ids: tuple[str, ...]
    human_review_required: bool = True
    causal_claimed: bool = False
    def validate(self) -> None:
        if not self.hypothesis_id or not self.cause_node or not self.effect_node:
            raise ValueError("hypothesis identity/endpoints are required")
        if not 0.0 <= self.confidence <= 1.0: raise ValueError("confidence must be 0..1")
        if not self.evidence_ids: raise ValueError("evidence is required")
        if not self.human_review_required or self.causal_claimed:
            raise ValueError("causal hypotheses require human review and cannot claim causation")

def build_hypothesis(tenant, hypothesis_id, cause_node, effect_node, confidence, evidence_ids):
    h = CausalHypothesis(tenant, hypothesis_id, cause_node, effect_node, confidence, tuple(evidence_ids))
    h.validate()
    return h
