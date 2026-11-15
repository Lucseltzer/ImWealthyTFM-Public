"""Causal educational spot replay. It is intentionally separate from live trading."""

from dataclasses import dataclass

import numpy as np
import pandas as pd
import talib


@dataclass(frozen=True)
class Settings:
    policy: str = "Mixta"
    initial_cash: float = 1_000.0
    nominal: float = 100.0
    stop_loss: float = 0.02
    trailing: float = 0.035
    minimum_range_width: float = 0.02
    fees: float = 0.001
    slippage: float = 0.0005

    def __post_init__(self):
        if self.policy not in ("Mixta", "Tendencia", "Rango"):
            raise ValueError("Unknown policy")
        if not (self.initial_cash > 0 and 0 < self.nominal <= self.initial_cash and
                0 < self.stop_loss < 0.2 and 0 < self.trailing < 0.2 and
                0 < self.minimum_range_width < 0.2 and
                0 <= self.fees < 0.05 and 0 <= self.slippage < 0.05):
            raise ValueError("Invalid simulation settings")


def features(candles):
    """Each row uses only the information available at that candle's close."""
    frame = candles.copy()
    close = frame["Close"].to_numpy(dtype=float)
    frame["ema9"] = talib.EMA(close, timeperiod=9)
    frame["ema21"] = talib.EMA(close, timeperiod=21)
    frame["ema200"] = talib.EMA(close, timeperiod=200)
    frame["rsi"] = talib.RSI(close, timeperiod=14)
    frame["vol10"] = frame["Volume"].rolling(10).mean().shift(1)
    frame["channel_low"] = frame["Low"].rolling(20).min().shift(1)
    frame["channel_high"] = frame["High"].rolling(20).max().shift(1)
    frame["ema_slope"] = frame["ema200"] / frame["ema200"].shift(5) - 1
    volatility = frame["Close"].pct_change().rolling(10).std()
    frame["volatility"] = volatility
    frame["average_volatility"] = volatility.rolling(30).mean().shift(1)
    return frame


def _policy(row, config):
    required = ("ema9", "ema21", "ema200", "rsi", "vol10", "channel_low",
                "channel_high", "ema_slope", "volatility", "average_volatility")
    if not all(np.isfinite(row[key]) for key in required):
        return "Abstención", False, False
    if (row["Close"] < row["ema200"] or
            row["volatility"] > 1.5 * row["average_volatility"]):
        return "Abstención", False, False
    width = row["channel_high"] / row["channel_low"] - 1
    in_channel = row["channel_low"] <= row["Close"] <= row["channel_high"]
    range_ok = (row["Volume"] <= row["vol10"] and abs(row["ema_slope"]) <= 0.002 and
                40 <= row["rsi"] <= 60 and width >= config.minimum_range_width and in_channel)
    if range_ok and config.policy in ("Mixta", "Rango"):
        span = row["channel_high"] - row["channel_low"]
        entry = row["Close"] <= row["channel_low"] + 0.25 * span and row["rsi"] <= 50
        exit_now = row["Close"] >= row["channel_low"] + 0.75 * span or row["rsi"] >= 55
        return "Rango", entry, exit_now
    trend_ok = (row["Close"] > row["ema200"] and row["Volume"] > row["vol10"] and
                row["ema9"] > row["ema21"])
    if trend_ok and config.policy in ("Mixta", "Tendencia"):
        return "Tendencia", True, False
    return "Abstención", False, False


def replay(candles, config: Settings):
    """Decide at close, fill at next open; stop gaps fill at the worse opening price."""
    frame = features(candles)
    if len(frame) < 240:
        raise ValueError("At least 240 closed candles are required")
    cash, quantity, entry, peak = config.initial_cash, 0.0, 0.0, 0.0
    pending = None
    trades = []
    equity = []
    for time, row in frame.iterrows():
        open_price = float(row["Open"])
        if pending == "sell" and quantity:
            proceeds = quantity * open_price * (1 - config.slippage) * (1 - config.fees)
            trades.append({"time": time, "side": "SELL", "price": open_price,
                           "quantity": quantity, "reason": "policy"})
            cash += proceeds
            quantity, entry, peak = 0.0, 0.0, 0.0
        elif isinstance(pending, tuple) and pending[0] == "buy" and not quantity:
            amount = min(config.nominal * pending[1], cash / (1 + config.fees))
            if amount > 0:
                entry = open_price * (1 + config.slippage)
                quantity = amount / entry
                cash -= amount * (1 + config.fees)
                peak = open_price
                trades.append({"time": time, "side": "BUY", "price": entry,
                               "quantity": quantity, "reason": pending[2]})
        pending = None
        if quantity:
            stop = entry * (1 - config.stop_loss)
            if peak >= entry * 1.025:
                stop = max(stop, entry * 1.003)
            if peak >= entry * 1.05:
                stop = max(stop, peak * (1 - config.trailing))
            if peak >= entry * 1.12:
                stop = max(stop, peak * (1 - min(config.trailing, 0.025)))
            if row["Low"] <= stop:
                fill = min(open_price, stop) * (1 - config.slippage)
                cash += quantity * fill * (1 - config.fees)
                trades.append({"time": time, "side": "SELL", "price": fill,
                               "quantity": quantity, "reason": "stop"})
                quantity, entry, peak = 0.0, 0.0, 0.0
            else:
                peak = max(peak, float(row["High"]))
        policy, entry_allowed, range_exit = _policy(row, config)
        if quantity and policy == "Rango" and range_exit:
            pending = "sell"
        elif not quantity and entry_allowed:
            pending = ("buy", 0.5 if policy == "Rango" else 1.0, policy)
        equity.append(cash + quantity * float(row["Close"]))
    curve = pd.Series(equity, index=frame.index, name="Equity")
    drawdown = (curve / curve.cummax() - 1).min()
    return {"curve": curve, "trades": trades, "final_equity": float(curve.iloc[-1]),
            "return_pct": 100 * (float(curve.iloc[-1]) / config.initial_cash - 1),
            "max_drawdown_pct": 100 * float(drawdown),
            "buy_count": sum(t["side"] == "BUY" for t in trades),
            "open_position": bool(quantity)}
