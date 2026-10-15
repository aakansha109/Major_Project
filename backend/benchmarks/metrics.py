import numpy as np
from typing import List, Dict, Any, Tuple

def normalize_triplet(triplet: Dict[str, str]) -> Tuple[str, str, str]:
    sub = str(triplet.get("subject", "")).strip().lower()
    pred = str(triplet.get("predicate", "")).strip().lower()
    obj = str(triplet.get("object", "")).strip().lower()
    return (sub, pred, obj)

def calculate_set_precision_recall_f1(
    extracted: List[Dict[str, str]],
    expected: List[Dict[str, str]]
) -> Dict[str, float]:
    """
    Computes precision, recall, and F1 score for triplet extraction.
    """
    ext_set = set(normalize_triplet(t) for t in extracted)
    exp_set = set(normalize_triplet(t) for t in expected)
    
    if not exp_set and not ext_set:
        return {"precision": 1.0, "recall": 1.0, "f1": 1.0, "tp": 0, "fp": 0, "fn": 0}
        
    tp = len(ext_set.intersection(exp_set))
    fp = len(ext_set - exp_set)
    fn = len(exp_set - ext_set)
    
    prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * (prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0
    
    return {
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "f1": round(f1, 4),
        "tp": tp,
        "fp": fp,
        "fn": fn
    }

def check_stale_fact_errors(
    answer: str,
    target_temporal_state: str,
    expected_keywords: List[str],
    forbidden_keywords: List[str]
) -> Dict[str, Any]:
    """
    Evaluates query correctness and detects Stale-Fact Errors:
    e.g., answering a historical question with current facts or forbidden keywords.
    """
    ans_lower = answer.lower()
    stale_error = False
    reasons = []
    
    # Check forbidden keywords (e.g. current fact appearing in historical query)
    for kw in forbidden_keywords:
        if kw.lower() in ans_lower:
            stale_error = True
            reasons.append(f"Forbidden keyword '{kw}' found in {target_temporal_state} query response")
            
    # Check expected keywords
    matched_expected = 0
    missing_keywords = []
    for kw in expected_keywords:
        if kw.lower() in ans_lower:
            matched_expected += 1
        else:
            missing_keywords.append(kw)
            
    passed = (not stale_error) and (len(missing_keywords) == 0 if expected_keywords else True)
    
    return {
        "passed": passed,
        "stale_fact_error": stale_error,
        "matched_expected": matched_expected,
        "missing_keywords": missing_keywords,
        "reasons": reasons
    }

def compute_distribution_metrics(latencies_ms: List[float]) -> Dict[str, float]:
    if not latencies_ms:
        return {"mean_ms": 0.0, "median_ms": 0.0, "p95_ms": 0.0, "max_ms": 0.0}
    arr = np.array(latencies_ms)
    return {
        "mean_ms": round(float(np.mean(arr)), 2),
        "median_ms": round(float(np.median(arr)), 2),
        "p95_ms": round(float(np.percentile(arr, 95)), 2),
        "max_ms": round(float(np.max(arr)), 2)
    }
