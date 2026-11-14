# Portions of this file were generated with AI assistance (Claude Code, Anthropic) and reviewed by the author.
"""G3v shared: slope bins, 'provides' rule and metre-scale slope-condition coverage."""
import numpy as np

BINS = [(0, 5), (5, 10), (10, 15), (15, 20), (20, 30), (30, 90)]
PROVIDE_FRAC = 0.05


def bin_counts(slope: np.ndarray) -> np.ndarray:
    s = slope[np.isfinite(slope)]
    out = []
    for i, (lo, hi) in enumerate(BINS):
        out.append(np.sum((s >= lo) & ((s <= hi) if i == len(BINS) - 1 else (s < hi))))
    return np.array(out, dtype=np.int64)


def provides(counts: np.ndarray) -> np.ndarray:
    tot = counts.sum()
    return (counts / tot >= PROVIDE_FRAC) if tot > 0 else np.zeros(len(BINS), bool)


def coverage(target_counts: list, site_counts: list) -> float:
    """Share of pooled target valid area whose bin is provided by >= 1 site; 0 if no site."""
    if not site_counts:
        return 0.0
    prov = np.any([provides(c) for c in site_counts], axis=0)
    T = np.sum(target_counts, axis=0)
    return float(T[prov].sum() / T.sum()) if T.sum() > 0 else float("nan")
