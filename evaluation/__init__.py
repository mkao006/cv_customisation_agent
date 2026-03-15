"""
Evaluation module for Job Research Agent V2.

Contains models and evaluators for CV quality assessment.
"""

from .models import ATSEvaluation, JudgeAudit, FaithfulnessAudit
from .evaluator import CVAnalyzer, FaithfulnessEvaluator
from .utils import (
    clean_text,
    is_exact_match,
    check_yoe_hallucination,
    check_metric_hallucination
)

__all__ = [
    "ATSEvaluation",
    "JudgeAudit",
    "FaithfulnessAudit",
    "CVAnalyzer",
    "FaithfulnessEvaluator",
    "clean_text",
    "is_exact_match",
    "check_yoe_hallucination",
    "check_metric_hallucination",
]