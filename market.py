"""Public BTC/USDT market data, independent of the paper-trading exchange."""

from __future__ import annotations

import math

import ccxt
import numpy as np
import pandas as pd

SYMBOL = "BTC/USDT"
BAR = pd.Timedelta(hours=4)


def _exchange():
    return ccxt.binance({"enableRateLimit": True, "timeout": 12000,
                         "options": {"defaultType": "spot"}})


def closed_candles(limit: int = 600) -> pd.DataFrame:
    """Return continuous, complete 4h candles from the public spot API."""
    if not 220 <= limit <= 1000:
        raise ValueError("limit must be between 220 and 1000")
    exchange = _exchange()
    try:
        rows = exchange.fetch_ohlcv(SYMBOL, "4h", limit=limit)
    finally:
        exchange.close()
    frame = pd.DataFrame(rows, columns=["time", "Open", "High", "Low", "Close", "Volume"])
    if frame.empty:
        raise ValueError("The exchange returned no candles")
    frame.index = pd.to_datetime(frame.pop("time"), unit="ms", utc=True)
    frame = frame.loc[frame.index + BAR <= pd.Timestamp.now(tz="UTC")]
    numbers = frame[["Open", "High", "Low", "Close", "Volume"]].to_numpy(dtype=float)
    if (len(frame) < 220 or frame.index.has_duplicates or
            not frame.index.to_series().diff().dropna().eq(BAR).all() or
            not np.isfinite(numbers).all() or
            (frame[["Open", "High", "Low", "Close"]] <= 0).any().any() or
            (frame["Volume"] < 0).any() or
            (frame["High"] < frame[["Open", "Close", "Low"]].max(axis=1)).any() or
            (frame["Low"] > frame[["Open", "Close", "High"]].min(axis=1)).any()):
        raise ValueError("The 4h candle series is incomplete or invalid")
    return frame


def latest_quote() -> dict:
    exchange = _exchange()
    try:
        ticker = exchange.fetch_ticker(SYMBOL)
    finally:
        exchange.close()
    price = float(ticker.get("last") or 0)
    timestamp = ticker.get("timestamp")
    if not math.isfinite(price) or price <= 0 or timestamp is None:
        raise ValueError("Missing public spot quote")
    quoted_at = pd.to_datetime(timestamp, unit="ms", utc=True)
    age = (pd.Timestamp.now(tz="UTC") - quoted_at).total_seconds()
    if not -10 <= age <= 90:
        raise ValueError("Public spot quote is stale")
    return {"price": price, "trade_time": quoted_at.isoformat()}
