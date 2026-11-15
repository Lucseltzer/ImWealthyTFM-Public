import json

import numpy as np
import pandas as pd
import pytest

import market
from forecast import HORIZON, MODEL, context_identity, read_forecast
from simulator import Settings, replay


def sample_candles(length=320):
    index = pd.date_range("2026-01-01", periods=length, freq="4h", tz="UTC")
    close = 100 + np.arange(length, dtype=float) * 0.14
    volume = np.full(length, 100.0)
    volume[::7] = 300.0
    return pd.DataFrame({"Open": close, "High": close * 1.002,
                         "Low": close * 0.998, "Close": close,
                         "Volume": volume}, index=index)


def test_replay_is_causal_and_charges_costs():
    candles = sample_candles()
    config = Settings(policy="Tendencia")
    result = replay(candles, config)
    assert result["buy_count"] > 0
    first_buy = next(trade for trade in result["trades"] if trade["side"] == "BUY")
    assert first_buy["price"] == pytest.approx(candles.loc[first_buy["time"], "Open"] * 1.0005)
    expensive = replay(candles, Settings(policy="Tendencia", fees=0.01, slippage=0.01))
    assert expensive["final_equity"] < result["final_equity"]
    changed_future = candles.copy()
    changed_future.loc[changed_future.index[-5:], ["Open", "High", "Low", "Close"]] *= 1.1
    altered = replay(changed_future, config)
    pd.testing.assert_series_equal(result["curve"].iloc[:-5], altered["curve"].iloc[:-5])


def test_forecast_only_matches_exact_closed_context(tmp_path):
    candles = sample_candles()
    origin, digest = context_identity(candles)
    rows = [{"time": int((candles.index[-1] + pd.Timedelta(hours=4 * i)).timestamp()),
             "point": 100.0, "q10": 90.0, "q25": 95.0, "q75": 105.0, "q90": 110.0}
            for i in range(1, HORIZON + 1)]
    path = tmp_path / "forecast.json"
    path.write_text(json.dumps({"schema": 1, "model": MODEL, "origin": origin,
                                "context_sha256": digest, "horizon": HORIZON,
                                "rows": rows}), encoding="utf-8")
    assert read_forecast(candles, path) is not None
    changed = candles.copy()
    changed.iloc[-1, changed.columns.get_loc("Close")] *= 1.01
    assert read_forecast(changed, path) is None


def test_market_rejects_four_hour_gap(monkeypatch):
    candles = sample_candles(250)
    candles = candles.drop(candles.index[100])

    class FakeExchange:
        def fetch_ohlcv(self, *_args, **_kwargs):
            return [[int(index.timestamp() * 1000), *map(float, row)]
                    for index, row in candles.iterrows()]

        def close(self):
            pass

    monkeypatch.setattr(market, "_exchange", FakeExchange)
    with pytest.raises(ValueError, match="incomplete"):
        market.closed_candles(250)
