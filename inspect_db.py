# inspect_db.py
import sqlite3
import pandas as pd
import time

DB_PATH = "mottu.db"

def main():
    conn = sqlite3.connect(DB_PATH)

    # Total de leituras salvas
    total = conn.execute("SELECT COUNT(*) FROM scans").fetchone()[0]
    print(f"📀 Total de leituras no banco: {total}")

    # Últimas 10 leituras
    df_last = pd.read_sql_query(
        """
        SELECT ts_ms, gateway_id, moto_id, rssi, rough_m
        FROM scans
        ORDER BY ts_ms DESC
        LIMIT 10
        """, conn
    )
    if not df_last.empty:
        df_last["ts_iso"] = pd.to_datetime(df_last["ts_ms"], unit="ms")
    print("\n🔎 Últimas 10 leituras:")
    print(df_last)

    # Leituras por moto (quantidade total)
    df_motos = pd.read_sql_query(
        """
        SELECT moto_id, COUNT(*) as qtd
        FROM scans
        GROUP BY moto_id
        ORDER BY qtd DESC
        """, conn
    )
    print("\n🏍 Leituras acumuladas por moto:")
    print(df_motos)

    # Leituras nos últimos 5 minutos
    now_ms = int(time.time() * 1000)
    cutoff = now_ms - 5 * 60 * 1000  # 5 minutos atrás
    df_recent = pd.read_sql_query(
        """
        SELECT moto_id, gateway_id, COUNT(*) as qtd, MIN(ts_ms) as primeiro, MAX(ts_ms) as ultimo
        FROM scans
        WHERE ts_ms >= ?
        GROUP BY moto_id, gateway_id
        ORDER BY moto_id, gateway_id
        """, conn, params=(cutoff,)
    )
    if not df_recent.empty:
        df_recent["primeiro"] = pd.to_datetime(df_recent["primeiro"], unit="ms")
        df_recent["ultimo"] = pd.to_datetime(df_recent["ultimo"], unit="ms")

    print("\n🕒 Leituras por moto/gateway nos últimos 5 minutos:")
    print(df_recent)

    conn.close()

if __name__ == "__main__":
    main()