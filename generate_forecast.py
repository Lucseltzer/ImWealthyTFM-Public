"""Optional scheduled producer; the public web process never loads TimesFM."""

import argparse
import json
import os
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

from forecast import FORECAST_PATH, HORIZON, MODEL, context_identity
from market import closed_candles


def generate(candles):
    import timesfm
    import torch

    use_cuda = torch.cuda.is_available()
    model = timesfm.TimesFM_2p5_200M_torch.from_pretrained(MODEL, torch_compile=False)
    device = torch.device("cuda" if use_cuda else "cpu")
    model.model.to(device)
    model.model.device = device
    model.model.device_count = max(1, torch.cuda.device_count()) if use_cuda else 1
    model.compile(timesfm.ForecastConfig(
        max_context=128, max_horizon=HORIZON, normalize_inputs=True,
        use_continuous_quantile_head=True, fix_quantile_crossing=True,
        per_core_batch_size=1,
    ))
    closes = candles["Close"].tail(128).to_numpy(dtype=np.float64)
    points, quantiles = model.forecast(horizon=HORIZON, inputs=[closes])
    points, quantiles = np.asarray(points), np.asarray(quantiles)
    if points.shape != (1, HORIZON) or quantiles.shape != (1, HORIZON, 10):
        raise ValueError("Unexpected TimesFM forecast shape")
    origin, digest = context_identity(candles)
    stamp = pd.Timestamp(origin)
    rows = []
    for i in range(HORIZON):
        row = {"time": int((stamp + pd.Timedelta(hours=4 * (i + 1))).timestamp()),
               "point": float(points[0, i]), "q10": float(quantiles[0, i, 1]),
               "q25": float((quantiles[0, i, 2] + quantiles[0, i, 3]) / 2),
               "q75": float((quantiles[0, i, 7] + quantiles[0, i, 8]) / 2),
               "q90": float(quantiles[0, i, 9])}
        values = [row[key] for key in ("q10", "q25", "q75", "q90")]
        if (not np.isfinite(list(row.values())).all() or min(values + [row["point"]]) <= 0 or
                values != sorted(values)):
            raise ValueError("Invalid forecast quantiles")
        rows.append(row)
    return {"schema": 1, "model": MODEL, "origin": origin,
            "context_sha256": digest, "horizon": HORIZON, "rows": rows}


def publish(report, path=FORECAST_PATH):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent,
                                         prefix=".forecast-", suffix=".tmp", delete=False) as handle:
            temporary = handle.name
            json.dump(report, handle, allow_nan=False)
        os.replace(temporary, path)
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Publish a 24-candle TimesFM spot forecast")
    parser.add_argument("--output", default=str(FORECAST_PATH))
    args = parser.parse_args()
    candles = closed_candles(600)
    report = generate(candles)
    publish(report, Path(args.output))
    print(f"Published forecast for {report['origin']}")
