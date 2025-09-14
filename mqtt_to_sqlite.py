# mqtt_to_sqlite.py
import json, time, sqlite3, os
from paho.mqtt import client as mqtt

# === CONFIG ===
MQTT_HOST = "broker.emqx.io"   # use o MESMO broker do simulador
MQTT_PORT = 1883
TOPIC_SUB = "mottu/scan/#"
DB_PATH   = "mottu.db"
# ==============

def get_conn():
    first = not os.path.exists(DB_PATH)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    if first:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS scans (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          ts_ms INTEGER NOT NULL,
          gateway_id TEXT NOT NULL,
          gw_x REAL, gw_y REAL,
          moto_id TEXT NOT NULL,
          mac TEXT,
          rssi INTEGER,
          rough_m REAL
        );
        CREATE INDEX IF NOT EXISTS idx_scans_ts ON scans(ts_ms);
        CREATE INDEX IF NOT EXISTS idx_scans_moto ON scans(moto_id);
        CREATE INDEX IF NOT EXISTS idx_scans_gw ON scans(gateway_id);
        """)
        conn.commit()
    return conn

CONN = get_conn()

def on_connect(client, userdata, flags, reason_code, properties):
    print("MQTT:", reason_code, "(0=OK)")
    if reason_code == 0:
        client.subscribe(TOPIC_SUB)

def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode("utf-8"))
        gw_id = str(data.get("gateway_id"))
        gx = float(data.get("gw_x", 0.0))
        gy = float(data.get("gw_y", 0.0))
        ts = int(data.get("ts_ms", time.time()*1000))
        readings = data.get("readings", [])
        if not readings: return
        rows = []
        for r in readings:
            ssid = str(r.get("ssid",""))
            if not ssid.startswith("MOTTU_"): continue
            mac  = r.get("mac")
            rssi = int(r.get("rssi",-100))
            rough= float(r.get("rough_m", 0.0))
            rows.append((ts, gw_id, gx, gy, ssid, mac, rssi, rough))
        if rows:
            CONN.executemany("""
              INSERT INTO scans(ts_ms,gateway_id,gw_x,gw_y,moto_id,mac,rssi,rough_m)
              VALUES (?,?,?,?,?,?,?,?)
            """, rows)
            CONN.commit()
            print(f"+{len(rows)} leituras salvas (gw={gw_id})")
    except Exception as e:
        print("on_message err:", e)

def main():
    c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="ingestor_sqlite")
    c.on_connect = on_connect
    c.on_message = on_message
    print(f"Conectando em {MQTT_HOST}:{MQTT_PORT}…")
    c.connect(MQTT_HOST, MQTT_PORT, 60)
    c.loop_forever()

if __name__ == "__main__":
    main()