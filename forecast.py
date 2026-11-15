"""Validate the read-only, published TimesFM forecast against public spot candles."""

import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

MODEL = "google/timesfm-2.5-200m-pytorch"
HORIZON = 24
FORECAST_PATH = Path(__file__).with_name("live_forecast_24.json")


def context_identity(candles):
    closes = candles["Close"].tail(128).to_numpy(dtype="<f8")
    if len(closes) != 128 or not np.isfinite(closes).all() or (closes <= 0).any():
        raise ValueError("128 valid closed candles are required")
    return candles.index[-1].isoformat(), hashlib.sha256(closes.tobytes()).hexdigest()


def read_forecast(candles, path=FORECAST_PATH):
    """Never display a forecast from another origin or revised history."""
    try:
        report = json.loads(Path(path).read_text(encoding="utf-8"))
        origin, digest = context_identity(candles)
        if (report.get("schema") != 1 or report.get("model") != MODEL or
                report.get("origin") != origin or report.get("context_sha256") != digest or
                report.get("horizon") != HORIZON or len(report.get("rows", [])) != HORIZON):
            return None
        stamp = pd.Timestamp(origin)
        for step, row in enumerate(report["rows"], 1):
            if row["time"] != int((stamp + pd.Timedelta(hours=4 * step)).timestamp()):
                return None
            values = [float(row[key]) for key in ("q10", "q25", "q75", "q90")]
            point = float(row["point"])
            if (not all(math.isfinite(v) and v > 0 for v in values + [point]) or
                    values != sorted(values)):
                return None
        return report
    except (OSError, ValueError, TypeError, KeyError, AttributeError, IndexError):
        return None
