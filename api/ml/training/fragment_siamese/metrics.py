from __future__ import annotations
import numpy as np
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, average_precision_score

def binary_metrics(y_true, probabilities, threshold=0.5):
    y_true = np.asarray(y_true, dtype=np.int64)
    probabilities = np.asarray(probabilities, dtype=np.float64)
    pred = (probabilities >= threshold).astype(np.int64)
    result = {
        'accuracy': float(accuracy_score(y_true, pred)),
        'precision': float(precision_score(y_true, pred, zero_division=0)),
        'recall': float(recall_score(y_true, pred, zero_division=0)),
        'f1': float(f1_score(y_true, pred, zero_division=0)),
    }
    if len(np.unique(y_true)) == 2:
        result['roc_auc'] = float(roc_auc_score(y_true, probabilities))
        result['pr_auc'] = float(average_precision_score(y_true, probabilities))
    else:
        result['roc_auc'] = None
        result['pr_auc'] = None
    return result
