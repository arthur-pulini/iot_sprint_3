# dashboard_streamlit.py  — lê do SQLite e renderiza o dash
import time
from typing import Tuple, List
import sqlite3
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ===================== CONFIG =====================
DB_PATH = "mottu.db"              # mesmo DB usado pelo mqtt_to_sqlite.py
WINDOW_SEC = 10                   # janela para “leituras recentes”
MISSING_SEC = 60                  # acima disso a moto vira “desaparecida”
RSSI_AT_1M = -50.0                # calibração
PATH_LOSS_N = 2.2                 # calibração

# Coordenadas conhecidas dos gateways (use as mesmas do simulador/hardware)
GATEWAYS_POS = {
    "gw_A": (0.0, 0.0),
    "gw_B": (20.0, 0.0),
    "gw_C": (10.0, 15.0),
}
# ==================================================

st.set_page_config(page_title="Telemetria de Motos (SQLite)", layout="wide")
st.title("Dashboard — Telemetria de Motos (via SQLite)")

# ---------- Utils ----------
def open_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def rssi_to_meters(rssi: float, rssi1m=RSSI_AT_1M, n=PATH_LOSS_N) -> float:
    # d = 10^((RSSI1m - RSSI)/(10n))
    return float(10 ** ((rssi1m - rssi) / (10 * n)))

def trilaterate(gw_points: List[Tuple[float, float]], dists: List[float]) -> Tuple[float, float]:
    """Gauss-Newton simples para min || |Pi - x| - di ||^2"""
    P = np.array(gw_points, dtype=float)
    d = np.array(dists, dtype=float)
    x = P.mean(axis=0)  # chute inicial
    for _ in range(30):
        r = np.linalg.norm(P - x, axis=1) + 1e-9
        J = (x - P) / r[:, None]
        f = r - d
        dx, *_ = np.linalg.lstsq(J, f, rcond=None)
        x = x - dx
        if np.linalg.norm(dx) < 1e-3:
            break
    return float(x[0]), float(x[1])

@st.cache_data(ttl=2.0, show_spinner=False)
def load_recent_scans(now_ms: int, window_sec: int) -> pd.DataFrame:
    """Carrega leituras dos últimos N segundos."""
    since = now_ms - window_sec * 1000
    conn = open_db()
    try:
        df = pd.read_sql_query(
            """
            SELECT ts_ms, gateway_id, gw_x, gw_y, moto_id, mac, rssi, rough_m
            FROM scans
            WHERE ts_ms >= ?
            """,
            conn, params=(since,)
        )
    finally:
        conn.close()
    return df

def compute_status_and_positions(df: pd.DataFrame):
    """Gera (df_status, df_pos) a partir das leituras recentes."""
    now_s = time.time()
    if df.empty:
        return (
            pd.DataFrame(columns=["moto_id","gateways_vistos","ultima_leitura_s","status"]),
            pd.DataFrame(columns=["moto_id","x","y","n_gw","age_s"])
        )

    # pega última leitura por (moto, gateway)
    df_last = df.sort_values("ts_ms").groupby(["moto_id","gateway_id"], as_index=False).tail(1)

    rows, pos_rows = [], []
    for moto, gdf in df_last.groupby("moto_id"):
        last_ts_ms = int(gdf["ts_ms"].max())
        age = now_s - (last_ts_ms / 1000.0)
        status = "ok" if age <= MISSING_SEC else "desaparecida"

        # trilateração se >=3 gateways com posição conhecida
        pts, dists = [], []
        for _, row in gdf.iterrows():
            gw = row["gateway_id"]
            if gw in GATEWAYS_POS:
                pts.append(GATEWAYS_POS[gw])
                dists.append(rssi_to_meters(int(row["rssi"])))
        if len(pts) >= 3:
            try:
                x, y = trilaterate(pts, dists)
                pos_rows.append({"moto_id": moto, "x": x, "y": y, "n_gw": len(pts), "age_s": round(age, 1)})
            except Exception:
                pass

        rows.append({
            "moto_id": moto,
            "gateways_vistos": gdf["gateway_id"].nunique(),
            "ultima_leitura_s": round(age, 1),
            "status": status,
        })

    df_status = pd.DataFrame(rows).sort_values(["status","moto_id"]) if rows else pd.DataFrame(
        columns=["moto_id","gateways_vistos","ultima_leitura_s","status"]
    )
    df_pos = pd.DataFrame(pos_rows) if pos_rows else pd.DataFrame(
        columns=["moto_id","x","y","n_gw","age_s"]
    )
    return df_status, df_pos

# ---------- Sidebar ----------
st.sidebar.subheader("Fonte de dados")
st.sidebar.write(f"📀 SQLite: {DB_PATH}")
auto = st.sidebar.toggle("🔄 Atualizar automaticamente (2s)", value=True)
st.sidebar.caption("Os dados são gravados por mqtt_to_sqlite.py a partir de mottu/scan/#.")

# ---------- Load + Process ----------
now_ms = int(time.time() * 1000)
df_scans = load_recent_scans(now_ms, WINDOW_SEC)
df_status, df_pos = compute_status_and_positions(df_scans)

# ---------- KPIs ----------
st.subheader("📊 Estatísticas")
col1, col2, col3, col4 = st.columns(4)
total_motos = len(df_status)
ok_motos = int((df_status["status"] == "ok").sum()) if total_motos else 0
missing_motos = int((df_status["status"] == "desaparecida").sum()) if total_motos else 0
col1.metric("Total Motos", total_motos)
col2.metric("Motos OK", ok_motos)
col3.metric("Desaparecidas", missing_motos)
col4.metric("Gateways Ativos", len(GATEWAYS_POS))

# ---------- Tabela ----------
st.subheader("📋 Status por Moto")
if not df_status.empty:
    st.dataframe(df_status.reset_index(drop=True), use_container_width=True)
else:
    st.info("⏳ Sem leituras recentes no banco (aguardando ingestão).")

# ---------- Mapa ----------
st.subheader("🗺 Planta do Pátio (estimativa por trilateração)")
fig = go.Figure()

# Gateways
for gw_id, (x, y) in GATEWAYS_POS.items():
    fig.add_trace(go.Scatter(
        x=[x], y=[y],
        mode='markers+text',
        name=gw_id,
        text=gw_id,
        textposition="top center",
        marker=dict(size=15, symbol='square')
    ))

# Motos
if not df_pos.empty:
    fig.add_trace(go.Scatter(
        x=df_pos["x"], y=df_pos["y"],
        mode='markers+text',
        name='Motos',
        text=df_pos["moto_id"],
        textposition="bottom center",
        marker=dict(size=12)
    ))

fig.update_layout(
    height=500, xaxis_title="X (m)", yaxis_title="Y (m)",
    xaxis=dict(scaleanchor="y", scaleratio=1), margin=dict(l=10, r=10, t=40, b=10)
)
st.plotly_chart(fig, use_container_width=True)

# ---------- Debug ----------
with st.expander("🔍 Debug — últimas 50 leituras do DB"):
    if not df_scans.empty:
        df_dbg = df_scans.sort_values("ts_ms", ascending=False).head(50).copy()
        df_dbg["ts_iso"] = pd.to_datetime(df_dbg["ts_ms"], unit="ms")
        st.dataframe(df_dbg, use_container_width=True)
    else:
        st.info("Nada nos últimos segundos. Verifique o ingestor e o simulador.")

# ---------- Auto refresh ----------
if auto:
    time.sleep(2)
    st.rerun()