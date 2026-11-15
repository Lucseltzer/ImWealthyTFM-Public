"""Public, read-only research dashboard for I'm Wealthy TFM."""

from dataclasses import replace

import pandas as pd
import streamlit as st

from forecast import read_forecast
from live_chart import chart_html, chart_payload
from market import SYMBOL, closed_candles, latest_quote
from simulator import Settings, replay


st.set_page_config(page_title="I'm Wealthy TFM | Research", page_icon=":material/candlestick_chart:",
                   layout="wide", initial_sidebar_state="collapsed")


@st.cache_data(ttl=120, max_entries=1, show_spinner=False)
def candles():
    return closed_candles(600)


@st.cache_data(ttl=10, max_entries=1, show_spinner=False)
def quote():
    return latest_quote()


COPY = {
    "es": {
        "caption": "Observatorio experimental de BTC/USDT spot · velas 4h UTC",
        "market": "Mercado y pronóstico", "sim": "Simulador", "about": "Método y límites",
        "model": "Modelo de pronóstico", "model_help": "TimesFM 2.5 es el único modelo integrado actualmente.",
        "live": "Cotización actual", "closed": "Último cierre 4h", "origin": "Última vela cerrada",
        "data_error": "No se pudieron validar los datos públicos de Binance spot. Comprueba la conexión y vuelve a intentar.",
        "quote_error": "Cotización temporalmente no disponible; el gráfico conserva las velas cerradas.",
        "forecast_ok": "Pronóstico TimesFM de 24 velas · origen {origin} · diagnóstico, sin garantía de cobertura.",
        "forecast_missing": "No hay un pronóstico vigente para la última vela cerrada. El gráfico muestra datos observados.",
        "price_source": "Binance spot público · lectura {time} UTC · actualización automática aproximada cada 15 s.",
        "closed_source": "Las velas y las EMA se calculan sobre cierres de 4h. El gráfico se revisa cada 2 minutos; la cotización superior, cada 15 segundos.",
        "sim_intro": "Prueba educativa de políticas técnicas sobre el mismo histórico de BTC/USDT. No incluye el filtro TimesFM ni reproduce el worker o los fills de Binance.",
        "policy": "Política habilitada", "nominal": "Nominal por compra (USDT)",
        "stop": "Stop fijo (%)", "trailing": "Trailing (%)", "range": "Ancho mínimo del canal (%)",
        "run": "Comparar con configuración base", "sim_error": "No se pudo completar la simulación.",
        "selected": "Configuración elegida", "baseline": "Base técnica", "return": "Retorno neto simulado",
        "drawdown": "Drawdown máximo", "buys": "Compras", "equity": "Equity simulado (USDT)",
        "no_trades": "Este tramo no produjo entradas para la configuración elegida.",
        "sim_note": "Se decide al cierre y se ejecuta en la siguiente apertura. Se aplican 0,10% de comisión y 0,05% de deslizamiento por lado. Stops con huecos se ejecutan al peor precio de apertura. El resultado histórico no predice rentabilidad futura.",
        "about_text": "**Qué muestra:** precio spot público, EMA 9/21, volumen y, si existe un archivo válido para el último cierre, 24 puntos futuros de TimesFM 2.5 con cuantiles de diagnóstico. **Qué no hace:** enviar órdenes, gestionar una cartera, entrenar el modelo ni probar que una estrategia sea rentable.",
        "limits": "Las bandas 10–90% y 25–75% no tienen cobertura futura validada. El simulador simplifica las políticas y no utiliza TimesFM; sus controles no modifican ningún bot. Las cotizaciones pueden fallar o retrasarse. No es asesoramiento financiero y es posible perder dinero.",
    },
    "en": {
        "caption": "Experimental BTC/USDT spot research view · 4h UTC candles",
        "market": "Market and forecast", "sim": "Simulator", "about": "Method and limits",
        "model": "Forecast model", "model_help": "TimesFM 2.5 is the only integrated model today.",
        "live": "Latest quote", "closed": "Latest 4h close", "origin": "Latest closed candle",
        "data_error": "Public Binance spot data could not be validated. Check connectivity and try again.",
        "quote_error": "Quote temporarily unavailable; the chart still shows closed candles.",
        "forecast_ok": "24-candle TimesFM forecast · origin {origin} · diagnostic, coverage not guaranteed.",
        "forecast_missing": "No current forecast matches the latest closed candle. The chart shows observed data.",
        "price_source": "Public Binance spot · fetched {time} UTC · approximate automatic refresh every 15 s.",
        "closed_source": "Candles and EMAs use closed 4h bars. The chart refreshes every 2 minutes; the quote above, every 15 seconds.",
        "sim_intro": "Educational technical-policy replay on the same BTC/USDT history. It omits the TimesFM filter and does not reproduce the worker or Binance fills.",
        "policy": "Enabled policy", "nominal": "Order notional (USDT)",
        "stop": "Fixed stop (%)", "trailing": "Trailing stop (%)", "range": "Minimum channel width (%)",
        "run": "Compare with technical baseline", "sim_error": "The simulation could not be completed.",
        "selected": "Selected settings", "baseline": "Technical baseline", "return": "Simulated net return",
        "drawdown": "Maximum drawdown", "buys": "Buys", "equity": "Simulated equity (USDT)",
        "no_trades": "The selected settings produced no entries in this sample.",
        "sim_note": "Decisions use a candle's close and fill at the next open. Fees of 0.10% and slippage of 0.05% apply on each side. Gap stops fill at the worse opening price. Historical results do not predict future returns.",
        "about_text": "**Shown:** public spot price, EMA 9/21, volume and, when a valid file matches the latest close, 24 future TimesFM 2.5 points with diagnostic quantiles. **Not provided:** orders, portfolio management, model training or evidence of a profitable strategy.",
        "limits": "The 10–90% and 25–75% bands have no validated future coverage. The simulator simplifies the policies and does not use TimesFM; its controls cannot change any bot. Quotes can fail or be delayed. This is not financial advice and money can be lost.",
    },
}

st.title("I'm Wealthy TFM")
language = st.segmented_control("Idioma / Language", ["Español", "English"], default="Español")
t = COPY["en" if language == "English" else "es"]
st.caption(t["caption"])
st.badge("Research", icon=":material/science:", color="blue")
st.badge("Read only", icon=":material/visibility:", color="green")

selected_tab = st.segmented_control("Sección / Section", [t["market"], t["sim"], t["about"]],
                                    default=t["market"])

if selected_tab == t["market"]:
    st.selectbox(t["model"], ["TimesFM 2.5"], disabled=True, help=t["model_help"])

    @st.fragment(run_every="15s")
    def live_quote_view():
        try:
            live = quote()
        except Exception:
            st.warning(t["quote_error"])
            return
        st.metric(t["live"], f"${live['price']:,.2f}", border=True)
        st.caption(t["price_source"].format(time=pd.Timestamp(live["trade_time"]).strftime("%Y-%m-%d %H:%M:%S")))

    live_quote_view()

    @st.fragment(run_every="120s")
    def market_chart_view():
        try:
            frame = candles()
        except Exception:
            st.error(t["data_error"])
            return
        try:
            live = quote()
        except Exception:
            live = None
        last = frame.iloc[-1]
        a, b = st.columns(2)
        a.metric(t["closed"], f"${last['Close']:,.2f}", border=True)
        b.metric(t["origin"], frame.index[-1].strftime("%Y-%m-%d %H:%M UTC"), border=True)
        report = read_forecast(frame)
        payload = chart_payload(frame.tail(128), [], report, live_quote=live)
        st.iframe(chart_html(payload, SYMBOL, show_ledger=False,
                             language="en" if language == "English" else "es"),
                  height=612, alt="BTC/USDT candles, EMA, volume and optional TimesFM forecast")
        if report is None:
            st.caption(t["forecast_missing"])
        else:
            st.info(t["forecast_ok"].format(origin=report["origin"]))
        st.caption(t["closed_source"])

    market_chart_view()

elif selected_tab == t["sim"]:
    st.info(t["sim_intro"])
    with st.form("simulation"):
        policy = st.selectbox(t["policy"], ["Mixta", "Tendencia", "Rango"])
        a, b = st.columns(2)
        with a:
            nominal = st.slider(t["nominal"], 25, 500, 100, 25)
            stop = st.slider(t["stop"], 0.5, 5.0, 2.0, 0.1)
        with b:
            trailing = st.slider(t["trailing"], 1.0, 8.0, 3.5, 0.1)
            range_width = st.slider(t["range"], 1.0, 5.0, 2.0, 0.1)
        submitted = st.form_submit_button(t["run"], type="primary")
    if submitted:
        try:
            history = candles()
            baseline = replay(history, Settings())
            selected = replay(history, replace(Settings(), policy=policy, nominal=nominal,
                                               stop_loss=stop / 100, trailing=trailing / 100,
                                               minimum_range_width=range_width / 100))
        except Exception:
            st.error(t["sim_error"])
        else:
            st.caption(f"{history.index[0]:%Y-%m-%d} — {history.index[-1]:%Y-%m-%d} UTC · {len(history)} candles")
            cols = st.columns(2)
            for column, label, result in zip(cols, (t["selected"], t["baseline"]),
                                             (selected, baseline), strict=True):
                with column:
                    st.subheader(label)
                    st.metric(t["return"], f"{result['return_pct']:+.2f}%")
                    st.metric(t["drawdown"], f"{result['max_drawdown_pct']:.2f}%")
                    st.metric(t["buys"], result["buy_count"])
            curves = pd.concat([selected["curve"].rename(t["selected"]),
                                baseline["curve"].rename(t["baseline"])], axis=1)
            st.line_chart(curves, y_label=t["equity"], alt=t["equity"])
            if not selected["buy_count"]:
                st.warning(t["no_trades"])
            st.caption(t["sim_note"])

else:
    st.markdown(t["about_text"])
    st.warning(t["limits"])
    st.caption("Charts by [TradingView](https://www.tradingview.com/) · TimesFM by Google Research")
