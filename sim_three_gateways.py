# sim_three_gateways.py
# Simula 3 gateways (sensores) publicando leituras no MQTT em paralelo.
# Tópico: mottu/scan/<gateway_id>
# Formato do payload compatível com o backend proposto.

import json, time, math, random, threading
from typing import Dict, Tuple, List
from paho.mqtt import client as mqtt

# ===================== CONFIG =====================
MQTT_HOST = "broker.emqx.io"
MQTT_PORT = 1883

# Coordenadas (em metros) dos 3 sensores no pátio (ajuste conforme sua planta)
GATEWAYS = [
    {"id": "gw_A", "x": 0.0,  "y": 0.0},
    {"id": "gw_B", "x": 20.0, "y": 0.0},
    {"id": "gw_C", "x": 10.0, "y": 15.0},
]

# Posições iniciais das motos (em metros)
MOTOS: Dict[str, Tuple[float, float]] = {
    "MOTTU_123": (10.0, 10.0),
    "MOTTU_456": (16.0, 4.0),
}

# Opções de cenário
ENABLE_MOVEMENT = True          # Faz as motos “passearem” levemente
DISAPPEAR_AFTER_S = 0           # Ex.: 30 -> após 30s, a MOTTU_456 some (não será publicada)
RANDOM_SEED = 42                # Para reprodutibilidade do ruído

# Parâmetros de RSSI
RSSI_AT_1M = -50.0              # RSSI esperado a 1m (calibrável)
PATH_LOSS_N = 2.2               # Expoente de perda (calibrável)
RSSI_NOISE_STD = 2.0            # ruído gaussiano [dB]

PUBLISH_EVERY_S = 1.0           # frequência de publicação

# ==================================================

random.seed(RANDOM_SEED)

def dist(ax, ay, bx, by) -> float:
    return math.hypot(ax - bx, ay - by)

def rssi_from_distance(d: float, rssi1m=RSSI_AT_1M, n=PATH_LOSS_N) -> float:
    """RSSI = RSSI(1m) - 10 * n * log10(d)."""
    d = max(d, 0.01)
    return rssi1m - 10.0 * n * math.log10(d)

def movement_thread(motos: Dict[str, Tuple[float, float]], bounds=(0, 20, 0, 15)):
    """Movimento leve aleatório dentro de um retângulo (minX, maxX, minY, maxY)."""
    minx, maxx, miny, maxy = bounds
    vx = {k: random.uniform(-0.3, 0.3) for k in motos}
    vy = {k: random.uniform(-0.3, 0.3) for k in motos}
    start = time.time()
    while True:
        time.sleep(1.0)
        t = time.time() - start

        # ‘Desaparecer’ MOTTU_456 após N segundos, se configurado
        if DISAPPEAR_AFTER_S and t > DISAPPEAR_AFTER_S and "MOTTU_456" in motos:
            # Use None para indicar “fora do ar” (gateways irão pular)
            motos["MOTTU_456"] = None  # type: ignore

        if not ENABLE_MOVEMENT:
            continue

        for moto, pos in list(motos.items()):
            if pos is None:  # desaparecida
                continue
            x, y = pos
            # Drift pequeno (random walk)
            x += vx[moto] + random.uniform(-0.1, 0.1)
            y += vy[moto] + random.uniform(-0.1, 0.1)

            # Rebater nas bordas
            if x < minx or x > maxx:
                vx[moto] *= -1
                x = max(minx, min(x, maxx))
            if y < miny or y > maxy:
                vy[moto] *= -1
                y = max(miny, min(y, maxy))

            motos[moto] = (x, y)

def gateway_publisher(gw_id: str, gx: float, gy: float, motos_ref: Dict[str, Tuple[float, float]]):
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"sim_{gw_id}")
    client.connect(MQTT_HOST, MQTT_PORT, 60)
    client.loop_start()
    print(f"[{gw_id}] conectado ao MQTT {MQTT_HOST}:{MQTT_PORT}")

    while True:
        ts_ms = int(time.time() * 1000)
        readings: List[dict] = []
        for moto, pos in list(motos_ref.items()):
            if pos is None:
                # Moto “desaparecida”: não publica
                continue
            x, y = pos
            d = dist(gx, gy, x, y)
            rssi = rssi_from_distance(d) + random.gauss(0, RSSI_NOISE_STD)
            readings.append({
                "ssid": moto,
                "mac": "AA:BB:CC:DD:EE:FF",
                "rssi": int(round(rssi)),
                "rough_m": round(d, 2),
                "bucket": "sim"
            })

        payload = {
            "gateway_id": gw_id,
            "gw_x": gx,
            "gw_y": gy,
            "ts_ms": ts_ms,
            "readings": readings
        }
        topic = f"mottu/scan/{gw_id}"
        client.publish(topic, json.dumps(payload))
        print(f"[{gw_id}] pub {topic}: {len(readings)} leituras")
        time.sleep(PUBLISH_EVERY_S)

def main():
    # cópia mutável das posições
    motos = dict(MOTOS)

    # thread opcional de movimento/desaparecimento
    t_move = threading.Thread(target=movement_thread, args=(motos,), daemon=True)
    t_move.start()

    # 3 threads de gateways
    threads = []
    for gw in GATEWAYS:
        t = threading.Thread(
            target=gateway_publisher,
            args=(gw["id"], gw["x"], gw["y"], motos),
            daemon=True
        )
        t.start()
        threads.append(t)

    # Segura a main
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nEncerrando simulação.")

if __name__ == "__main__":
    main()