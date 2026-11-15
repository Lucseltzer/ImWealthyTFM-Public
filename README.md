# I'm Wealthy TFM — public research preview

An experimental, **read-only** BTC/USDT spot dashboard. It shows closed four-hour candles, EMA 9/21, volume, an automatically refreshed public quote and, when produced for the latest closed candle, a 24-candle TimesFM 2.5 forecast with diagnostic bands. The app has a separate technical-policy simulator; it does not contain the paper-trading worker, private ledger, credentials or order routes.

## License

The original code and documentation in this repository are copyright 2026 Lucas Seltzer and are provided under the [PolyForm Noncommercial License 1.0.0](./LICENSE). Keep the [required copyright notice](./NOTICE.md) with copies as specified by that license. The license permits use, modification, and redistribution for permitted noncommercial purposes, subject to its terms. Commercial use of this code requires separate permission from the copyright holder. This is **source-available software, not open-source software** under the Open Source Definition.

For commercial licensing inquiries, contact Lucas Seltzer at lucasseltzer98@gmail.com.

Bundled third-party chart assets retain their own licenses and notices; see [THIRD_PARTY_NOTICES.md](./THIRD_PARTY_NOTICES.md). Dependencies, including TimesFM and its separately downloaded model weights, retain their respective licenses. The project name and branding are not licensed by the software license.

## Run locally

Use Python 3.12 in a fresh virtual environment, then:

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

The web app uses the **public Binance spot** market endpoints through CCXT; no API keys are needed. It fetches 4h candles only after they close. The quote refreshes approximately every 15 seconds and the chart every 2 minutes while a browser session is open. If the exchange is unavailable, the app labels unavailable data; it does not invent prices.

The direct application dependencies are pinned to the versions used for this preview. To run the offline tests locally, install `requirements-dev.txt` and run `python -m pytest -q tests/test_public.py`.

## Optional forecast producer

The web process never loads PyTorch or TimesFM. On a machine with enough CPU/RAM or a compatible GPU, install the optional dependencies and run the producer shortly after each 4h UTC candle closes (00:00, 04:00, 08:00, 12:00, 16:00, 20:00):

```bash
python -m pip install -r requirements-forecast.txt
python generate_forecast.py
```

For example, schedule it at minute 5 after each close. It atomically writes `live_forecast_24.json`, which is excluded from Git. The app only displays a forecast if its source time and 128-price context match the latest closed candles. A missing or stale forecast is displayed as unavailable. The file contains forecasts from **public spot** prices; do not substitute a demo-exchange forecast. TimesFM model weights download separately and are not shipped with this source.

The outer and inner bands represent TimesFM quantiles, approximately 10–90% and 25–75%. Their actual coverage has **not** been calibrated or validated for future BTC prices. They must not be interpreted as guaranteed confidence intervals.

## Technical-policy simulator

The simulator uses historical 4h BTC/USDT candles and tests a simplified technical selector for trend, range and abstention. It decides from a closed candle and fills at the next opening price. It includes 0.10% fee and 0.05% slippage per side, emergency stops and trailing exits. It compares selected settings with the same technical baseline on the same sample.

It **does not use TimesFM** in its decisions, reproduce the private VPS strategy, model limit-order execution, or establish out-of-sample profitability. Repeatedly tuning sliders on the visible history can overfit that history. Simulated results are not investment recommendations or guarantees; money can be lost.

## Publication boundary

This directory is the intended public source. Do not copy the original trading project into it. Its `.gitignore` is an allowlist; only the listed source, docs, tests and chart assets are tracked. Before publishing or pushing any revision, inspect `git status --short`, run a secret scanner on **all changed files**, and review the final diff. Never include `.env`, SQLite files, caches, logs, screenshots of accounts, or forecast artifacts. Keep the operator dashboard and worker on a separate private host and repository.

The original code uses the PolyForm Noncommercial License 1.0.0. The chart bundles have their own licenses and required attribution in `THIRD_PARTY_NOTICES.md`.

GitHub Actions runs syntax and unit checks with Python 3.12 on Ubuntu. It does not run the heavy optional forecast model or contact Binance.

## Limitations

This is a research demonstration, not a trading service. Quotes may be delayed, public API access may be unavailable in some locations, and the forecast generator may miss a 4h close. The model selector displays only TimesFM 2.5; other models are a possible future extension, not a committed feature. The simulator and forecasts have not demonstrated profitable trading after real execution costs.
