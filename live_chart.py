"""Closed Binance candles and ledger fills for the live market chart."""

import json
from functools import lru_cache
from pathlib import Path

import pandas as pd
import talib


LIBRARY_PATH = Path(__file__).with_name("lightweight-charts.standalone.production.js")
PLUGIN_PATH = Path(__file__).with_name("lwc-plugin-hlc-area-series.standalone.js")


def chart_payload(velas, trades, forecast=None, *, live_quote=None):
    """Build UTC chart data without changing the worker or the ledger."""
    if velas.empty:
        raise ValueError("No hay velas cerradas para mostrar.")
    candles = velas.sort_index()
    times = pd.to_datetime(candles.index, utc=True)
    close = candles["Close"].astype(float).to_numpy()
    ema9 = talib.EMA(close, timeperiod=9)
    ema21 = talib.EMA(close, timeperiod=21)
    bars = []
    volume = []
    fast = []
    slow = []
    for index, timestamp in enumerate(times):
        epoch = int(timestamp.timestamp())
        bars.append({
            "time": epoch,
            "open": float(candles["Open"].iloc[index]),
            "high": float(candles["High"].iloc[index]),
            "low": float(candles["Low"].iloc[index]),
            "close": float(close[index]),
        })
        volume.append({
            "time": epoch,
            "value": float(candles["Volume"].iloc[index]),
            "color": "#183b3b" if close[index] >= candles["Open"].iloc[index] else "#493037",
        })
        if pd.notna(ema9[index]):
            fast.append({"time": epoch, "value": float(ema9[index])})
        if pd.notna(ema21[index]):
            slow.append({"time": epoch, "value": float(ema21[index])})

    first_time = bars[0]["time"]
    last_time = bars[-1]["time"]
    interval = 4 * 60 * 60
    markers = []
    future_times = set()
    for trade in trades:
        side = str(trade.get("side", "")).upper()
        if side not in {"BUY", "SELL"}:
            continue
        candle_time = pd.to_datetime(
            trade.get("candle_timestamp"),
            utc=True, errors="coerce", format="ISO8601",
        )
        if pd.isna(candle_time):
            continue
        execution = candle_time
        if trade.get("created_at"):
            actual_time = pd.to_datetime(
                trade["created_at"], utc=True, errors="coerce", format="ISO8601",
            )
            if pd.notna(actual_time) and (
                candle_time <= actual_time < candle_time + pd.Timedelta(seconds=interval)
                or int(candle_time.timestamp()) > last_time
            ):
                execution = actual_time
        execution_epoch = int(execution.timestamp())
        bucket = execution_epoch - execution_epoch % interval
        if bucket < first_time:
            continue
        if bucket > last_time:
            future_times.add(bucket)
        price = float(trade["execution_price"])
        markers.append({
            "time": bucket,
            "position": "belowBar" if side == "BUY" else "aboveBar",
            "color": "#19c79a" if side == "BUY" else "#f46b78",
            "shape": "arrowUp" if side == "BUY" else "arrowDown",
            "text": f"{side} ${price:,.2f}",
            "execution_time": execution.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "execution_price": price,
            "sort_time": execution.timestamp(),
        })
    for epoch in sorted(future_times):
        bars.append({"time": epoch})
    forecast_line = []
    outer_band = []
    inner_band = []
    if forecast is not None:
        if int(pd.Timestamp(forecast["origin"]).timestamp()) != last_time:
            raise ValueError("El pronóstico no corresponde a la última vela cerrada.")
        forecast_line.append({"time": last_time, "value": float(close[-1])})
        display_rows = forecast.get("display_rows") or forecast["rows"]
        for step, (row, band) in enumerate(zip(forecast["rows"], display_rows, strict=True), start=1):
            epoch = last_time + step * interval
            if row["time"] != epoch:
                raise ValueError("El pronóstico contiene tiempos desalineados.")
            forecast_line.append({"time": epoch, "value": row["point"]})
            outer_band.append({"time": epoch, "lower": band["q10"], "upper": band["q90"]})
            inner_band.append({"time": epoch, "lower": band["q25"], "upper": band["q75"]})
        future_times.add(last_time + len(forecast["rows"]) * interval)
    markers.sort(key=lambda marker: (marker["time"], marker["sort_time"]))
    visible_from = bars[max(0, len(bars) - 72)]["time"]
    if markers:
        visible_from = min(visible_from, markers[0]["time"])
    return {
        "candles": bars,
        "volume": volume,
        "ema9": fast,
        "ema21": slow,
        "markers": markers,
        "forecast": forecast_line,
        "outer_band": outer_band,
        "inner_band": inner_band,
        "calibrated": bool(forecast and forecast.get("calibration")),
        "live_price": float(live_quote["price"]) if live_quote else None,
        "live_time": live_quote["trade_time"] if live_quote else None,
        "visible_from": visible_from,
        "visible_to": max(last_time + interval, max(future_times, default=last_time) + interval),
    }


@lru_cache(maxsize=1)
def _library_source():
    return LIBRARY_PATH.read_text(encoding="utf-8")


@lru_cache(maxsize=1)
def _plugin_source():
    """Bind the pinned TradingView HLC area plugin to the standalone bundle."""
    source = PLUGIN_PATH.read_text(encoding="utf-8")
    module_import = 'import { customSeriesDefaultOptions as e } from "lightweight-charts";'
    module_export = 'export { x as HLCAreaSeries, S as createHLCAreaSeries, l as defaultOptions };'
    if source.count(module_import) != 1 or source.count(module_export) != 1:
        raise ValueError("La versión del plugin HLC no coincide con el adaptador local.")
    source = source.replace(module_import, "const e = LightweightCharts.customSeriesDefaultOptions;")
    source = source.replace(module_export, "return {createHLCAreaSeries: S};")
    return "globalThis.HLCAreaPlugin = (() => {\n" + source + "\n})();"


def chart_html(payload, symbol="BTC/USDT", *, show_ledger=True, language="es"):
    """Embed a pinned, local Lightweight Charts bundle in a Streamlit iframe."""
    if language not in {"es", "en"}:
        raise ValueError("Unsupported chart language")
    data = json.dumps(payload, allow_nan=False).replace("</", "<\\/")
    safe_symbol = symbol.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    template = HTML_TEMPLATE
    if not show_ledger:
        template = template.replace(" · BUY/SELL: precio de ejecución del ledger", "")
    if language == "en":
        translations = {
            '<html lang="es">': '<html lang="en">',
            "<span>Volumen</span>": "<span>Volume</span>",
            "Velas cerradas de Binance": "Closed Binance candles",
            "BUY/SELL: precio de ejecución del ledger": "BUY/SELL: ledger execution price",
            "Gráficos por": "Charts by",
            "locale:'es-ES'": "locale:'en-US'",
            "Bandas ajustadas con errores anteriores; cobertura futura no garantizada. Solo diagnóstico.":
                "Bands adjusted using past errors; future coverage is not guaranteed. Diagnostic only.",
            "Cuantiles TimesFM sin calibración de cobertura; q25/q75 interpolados. Solo diagnóstico.":
                "TimesFM quantiles have no coverage calibration; q25/q75 are interpolated. Diagnostic only.",
            "No se pudo dibujar el gráfico:": "Could not render the chart:",
        }
        for original, translated in translations.items():
            template = template.replace(original, translated)
    return (template.replace("__LIBRARY__", _library_source())
            .replace("__PLUGIN__", _plugin_source())
            .replace("__PAYLOAD__", data).replace("__SYMBOL__", safe_symbol))


HTML_TEMPLATE = """<!doctype html>
<html lang="es"><head><meta charset="utf-8"><style>
*{box-sizing:border-box}html,body{margin:0;background:#0c1421;color:#dce5ef;font:13px system-ui,sans-serif}
.shell{height:610px;border:1px solid #243448;border-radius:14px;overflow:hidden;background:#0c1421}
.head{height:54px;display:flex;align-items:center;gap:17px;padding:0 18px;border-bottom:1px solid #203044}
.symbol{font-size:18px;font-weight:700;color:#fff}.tag{font-size:11px;color:#94a8bd;border:1px solid #34465a;padding:3px 7px;border-radius:5px}
.legend{display:flex;gap:14px;margin-left:auto;color:#a9bacb}.blue{color:#4da3ff}.yellow{color:#ffd54f}.forecast-label{color:#87c6f9}
#chart{height:516px;width:100%}.foot{height:39px;padding:10px 18px;color:#8aa0b4;font-size:11px;border-top:1px solid #203044}
#error{display:none;padding:24px;color:#f46b78}
</style></head><body><div class="shell"><div class="head"><span class="symbol">__SYMBOL__</span><span class="tag">4H · UTC</span><div class="legend"><span class="blue">● EMA 9</span><span class="yellow">● EMA 21</span><span>Volumen</span><span class="forecast-label" id="forecast-label" hidden>╌ TimesFM 24 · 10–90% / 25–75%</span></div></div><div id="chart"></div><div id="error"></div><div class="foot">Velas cerradas de Binance · BUY/SELL: precio de ejecución del ledger · Gráficos por <a href="https://www.tradingview.com/" target="_blank" rel="noopener" style="color:#a9bacb">TradingView</a></div></div>
<script>__LIBRARY__</script><script>__PLUGIN__</script><script>
const data = __PAYLOAD__;
try {
 const api = LightweightCharts;
 const container = document.getElementById('chart');
 const chart = api.createChart(container, {
  width:container.clientWidth,height:container.clientHeight,
  layout:{background:{type:'solid',color:'#0c1421'},textColor:'#9cafc1',fontFamily:'system-ui, sans-serif',panes:{separatorColor:'#23364a',separatorHoverColor:'#4da3ff'}},
  grid:{vertLines:{color:'#172538'},horzLines:{color:'#172538'}},
  rightPriceScale:{borderColor:'#294056'},timeScale:{borderColor:'#294056',timeVisible:true,secondsVisible:false,rightOffset:3},
  crosshair:{mode:api.CrosshairMode.Normal},localization:{locale:'es-ES',timeFormatter:t=>new Date(t*1000).toISOString().slice(0,16).replace('T',' ')+' UTC'}
 });
 const candles=chart.addSeries(api.CandlestickSeries,{upColor:'#19c79a',downColor:'#f46b78',wickUpColor:'#19c79a',wickDownColor:'#f46b78',borderVisible:false,priceFormat:{type:'price',precision:2,minMove:0.01}});
 candles.setData(data.candles);
 if(data.live_price){candles.createPriceLine({price:data.live_price,color:'#f4b860',lineWidth:1,lineStyle:api.LineStyle.Dashed,axisLabelVisible:true,title:'SPOT'});}
 if(data.forecast?.length){
  const shade=(rows,alpha)=>{
   const area=HLCAreaPlugin.createHLCAreaSeries(chart,{
    highLineColor:'rgba(77,163,255,0.48)',lowLineColor:'rgba(77,163,255,0.48)',
    highAreaColor:`rgba(77,163,255,${alpha})`,lowAreaColor:`rgba(77,163,255,${alpha})`,
    closeLineVisible:false,priceLineVisible:false,lastValueVisible:false,hoverPointRadius:0,
    priceFormat:{type:'price',precision:2,minMove:0.01}});
   area.setData(rows.map(row=>({time:row.time,high:row.upper,low:row.lower,
    close:(row.upper+row.lower)/2})));
  };
  shade(data.outer_band,0.10);
  shade(data.inner_band,0.24);
  const line=chart.addSeries(api.LineSeries,{color:'#87c6f9',lineWidth:2,lineStyle:api.LineStyle.Dashed,
   priceLineVisible:false,lastValueVisible:false});line.setData(data.forecast);
  document.getElementById('forecast-label').hidden=false;
  document.querySelector('.foot').textContent += data.calibrated
   ? ' · Bandas ajustadas con errores anteriores; cobertura futura no garantizada. Solo diagnóstico.'
   : ' · Cuantiles TimesFM sin calibración de cobertura; q25/q75 interpolados. Solo diagnóstico.';
 }
 const ema9=chart.addSeries(api.LineSeries,{color:'#4da3ff',lineWidth:2,priceLineVisible:false,lastValueVisible:false});ema9.setData(data.ema9);
 const ema21=chart.addSeries(api.LineSeries,{color:'#ffd54f',lineWidth:2,priceLineVisible:false,lastValueVisible:false});ema21.setData(data.ema21);
 const vol=chart.addSeries(api.HistogramSeries,{priceFormat:{type:'volume'},priceScaleId:'',lastValueVisible:false},1);vol.setData(data.volume);
 chart.panes()[1].setHeight(125);
 api.createSeriesMarkers(candles,data.markers.map(({execution_time,execution_price,sort_time,...marker})=>marker));
 const rangeKey=data.forecast?.length?'im-wealthy-tfm-chart-range-forecast24':'im-wealthy-tfm-chart-range';
 let restoredRange=null;
 try {restoredRange=JSON.parse(sessionStorage.getItem(rangeKey));} catch (_) {}
 chart.timeScale().setVisibleRange(restoredRange?.from && restoredRange?.to ? restoredRange : {from:data.visible_from,to:data.visible_to});
 chart.timeScale().subscribeVisibleTimeRangeChange(range=>{
  if (range?.from && range?.to) {
   try {sessionStorage.setItem(rangeKey,JSON.stringify(range));} catch (_) {}
  }
 });
 new ResizeObserver(()=>chart.applyOptions({width:container.clientWidth,height:container.clientHeight})).observe(container);
} catch(error) {document.getElementById('chart').style.display='none';const box=document.getElementById('error');box.style.display='block';box.textContent='No se pudo dibujar el gráfico: '+error.message;}
</script></body></html>"""
