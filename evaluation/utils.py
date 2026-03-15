import re
from datetime import datetime


def clean_text(text):
    """Normalize text by lowercasing and removing extra whitespace."""
    return re.sub(r'\s+', ' ', str(text).lower()).strip()


def is_exact_match(keyword, master_text):
    """Check if a keyword appears as a whole word in the master text."""
    kw = clean_text(keyword)
    pattern = rf"\b{re.escape(kw)}\b"
    return re.search(pattern, master_text) is not None


def check_yoe_hallucination(cv_text, start_year=2010):
    """Check for Year of Experience hallucination in CV text.

    Args:
        cv_text: The CV text to check
        start_year: Ground truth start year (default 2010)

    Returns:
        Dictionary with status, message, and ground truth YoE
    """
    current_year = datetime.now().year
    ground_truth_yoe = current_year - start_year
    yoe_patterns = [
        r"(\d+)\+?\s*(?:years?|yrs)(?:\s+of)?\s+(?:experience|exp)",
        r"(?:with|over)\s+(\d+)\+?\s*(?:years?|yrs)"
    ]
    mentions = []
    for pattern in yoe_patterns:
        found = re.findall(pattern, cv_text, re.IGNORECASE)
        mentions.extend([int(m) for m in found])

    if not mentions:
        return {
            "status": "pass",
            "message": "No YoE mentions found.",
            "ground_truth": ground_truth_yoe
        }

    max_mentioned = max(mentions)
    if max_mentioned > ground_truth_yoe:
        return {
            "status": "fail",
            "message": f"YoE Hallucination: Claims {max_mentioned}, truth {ground_truth_yoe}.",
            "ground_truth": ground_truth_yoe,
            "claimed": max_mentioned
        }

    return {
        "status": "pass",
        "message": "YoE within bounds.",
        "ground_truth": ground_truth_yoe
    }


def check_metric_hallucination(cv_text, master_text):
    """Check for metric hallucination (%, $, time units) not in master text.

    Args:
        cv_text: The CV text to check
        master_text: The master CV text (source of truth)

    Returns:
        Dictionary with status and message
    """
    metric_pattern = r"(\d+(?:\.\d+)?%|\$\d+(?:\.\d+)?[MBKk]?|\d+\s*(?:hour|min|sec|day)s?)"
    cv_metrics = set(re.findall(metric_pattern, cv_text, re.IGNORECASE))
    master_metrics = set(re.findall(metric_pattern, master_text, re.IGNORECASE))
    hallucinated_metrics = [m for m in cv_metrics if m not in master_metrics]

    if hallucinated_metrics:
        return {
            "status": "fail",
            "message": f"Metric Hallucination: {hallucinated_metrics}"
        }
    return {
        "status": "pass",
        "message": "No invented metrics found."
    }