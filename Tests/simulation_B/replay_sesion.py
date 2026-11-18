"""
replay_sesion.py — replay en tiempo real de una grabación AURA_RAW en el dashboard (MIRAI 2026) · VERSIÓN B

Hace pasar una sesión grabada por todo el flujo en vivo, igual que con la diadema: publica el CSV de Aura.exe por LSL
a 250 Hz desde la primera muestra (source_id AuraLSL-…, así el pipeline aplica CAR e invierte Fp1 como con Aura.exe),
lanza su propio dashboard (sesion_aura_web.py, puerto 8010, base Go/NoGo data/replay.db: no toca data/mirai.db ni una
sesión real en el 8000), enciende el semáforo de electrodos y deja la sesión lista con el plan de la grabación.
Los bloques se controlan a mano como en una sesión real: Continue en Current block (el primero lanza el pipeline).
Con --auto los pulsa el script con los tiempos de la sesión original.

Go/NoGo: el 12 nov no existía la tarea; un teléfono simulado recibe la orden de cada bloque gonogo_*, espera lo que
dura el bloque y manda los ensayos de una vez (como gonogo.html) con respuestas SINTÉTICAS (TR ~390 ms, 2 % omisiones,
~30 % comisiones). Solo sirve para ver la tarjeta y los resultados en el dashboard, no son datos de la participante.

Uso (desde una terminal: el último Continue detiene el pipeline con Ctrl+Break, que necesita consola):
  python replay_sesion.py                 # 12 nov 16:38 (98.9 % válidas en vivo), bloques a mano
  python replay_sesion.py --auto          # bloques solos, alineados con la sesión original
  python replay_sesion.py --csv <AURA_RAW…csv> --baseline-raw <s> --original runs/<run en vivo> --codigo <código>
  (--plan "<s> bloque:<nombre> …" --dur <s> solo si el plan no fue 2+3+30+3 min, p. ej. el 10 nov 13:50)
Abrir http://localhost:8010. Ctrl+C cierra todo.
"""
import argparse
import json
import os
import random
import subprocess
import sys
import threading
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
os.environ.setdefault("LSLAPICFG", os.path.join(HERE, "lsl_api.cfg"))
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pylsl  # noqa: E402  (después de LSLAPICFG)

FS = 250.0
REC = os.path.join(HERE, "..", "Recordings", "2026-11-12___16;38;51", "AURA_RAW___2026-11-12___16;38;51.csv")
# Sesión original (run 20261112_163914): baseline 2 → Go/NoGo pre 3 → scroll 30 → Go/NoGo post 3 min, sin pausas;
# el baseline empezó en el segundo 25.75 del RAW (RAW t = LSL ts − 21415.5 s).
PLAN, DUR, BASE_RAW = "0 bloque:baseline 120 bloque:gonogo_pre 300 bloque:scroll 2100 bloque:gonogo_post", "2280", 25.75
ORIGINAL = os.path.join(HERE, "runs", "20261112_163914_AuraLSL-20261112-15;59;04", "ventanas.csv")
URL = ""


def api(path, body=None):
    req = urllib.request.Request(URL + path, None if body is None else json.dumps(body).encode(),
                                 {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.load(r)


def mmss(s):
    return f"{int(s // 60):02d}:{s % 60:04.1f}"


# ---------- EEG: el CSV de Aura.exe como stream LSL en tiempo real ----------
class Stream(threading.Thread):
    def __init__(self, x, name, sid):
        super().__init__(daemon=True)
        self.x, self.i = x, 0
        self.out = pylsl.StreamOutlet(pylsl.StreamInfo(name, "EEG", 8, FS, pylsl.cf_float32, sid))

    def raw_t(self):
        return self.i / FS

    def run(self):
        t0 = time.perf_counter()
        while self.i < len(self.x):  # bloques de ~20 ms, como el emulador
            n = min(int((time.perf_counter() - t0) * FS), len(self.x)) - self.i
            if n > 0:
                self.out.push_chunk(self.x[self.i:self.i + n].tolist())
                self.i += n
            time.sleep(0.02)
        print(f"[replay] fin de la grabación (RAW {mmss(self.raw_t())}): el stream ya no manda muestras")


# ---------- teléfono Go/NoGo simulado ----------
def tel_ms():
    return time.perf_counter() * 1000


def sync():
    """Como gonogo.html: 10 idas y vueltas a /api/gng/sync, se queda con la más corta."""
    best = None
    for _ in range(10):
        a = tel_ms()
        t = api("/api/gng/sync", {})["t"]
        b = tel_ms()
        if best is None or b - a < best["ida_vuelta_ms"]:
            best = {"ida_vuelta_ms": b - a, "tel": (a + b) / 2, "desfase": t - (a + b) / 2000}
    return best


def tel_bloque(o):
    rng = random.Random(o["bloque"])
    t0 = tel_ms()
    api("/api/gng/bloque/sync", {"bloque": o["bloque"], "fase": "inicio", **sync(), "cuadro_ms": 16.7})
    ensayos = []
    for n, d in enumerate(o["secuencia"]):
        if int(d) == o["nogo"]:
            rt = rng.gauss(330, 50) if rng.random() < 0.3 else None  # comisión
        else:
            rt = None if rng.random() < 0.02 else max(150.0, rng.gauss(390, 70))  # omisión / acierto
        ensayos.append({"n": n, "t_on": t0 + o["prep_ms"] + n * o["soa_ms"], "rt": rt})
    time.sleep(max(0.0, (ensayos[-1]["t_on"] + o["soa_ms"] - tel_ms()) / 1000))  # lo que dura el bloque en el teléfono
    api("/api/gng/ensayos", {"bloque": o["bloque"], "ensayos": ensayos})  # un solo envío al final, como la app
    api("/api/gng/bloque/sync", {"bloque": o["bloque"], "fase": "fin", **sync()})


def telefono():
    """Escucha /api/gng/eventos (SSE) como la página /gng; cada 'inicio' corre un bloque en su propio hilo."""
    while True:
        try:
            with urllib.request.urlopen(URL + "/api/gng/eventos", timeout=60) as r:
                ev = None
                for line in r:
                    line = line.decode().rstrip("\n")
                    if line.startswith("event: "):
                        ev = line[7:]
                    elif line.startswith("data: ") and ev == "inicio":
                        o = json.loads(line[6:])
                        print(f"[teléfono simulado] bloque {o['tipo']} ({len(o['secuencia'])} ensayos, sintéticos)")
                        threading.Thread(target=tel_bloque, args=(o,), daemon=True).start()
        except OSError:
            time.sleep(1)  # servidor reiniciándose / timeout: reconecta como la página


# ---------- control de bloques ----------
def originales(plan, dur, base):
    """[(nombre, inicio RAW, fin RAW)] de la sesión original."""
    tok = plan.split()
    ts = [(float(t), m.split(":", 1)[1]) for t, m in zip(tok[::2], tok[1::2])]
    return [(n, base + t, base + (ts[i + 1][0] if i + 1 < len(ts) else float(dur))) for i, (t, n) in enumerate(ts)]


def control(st, blq, auto, lead):
    """Cada segundo: avisa en la consola qué bloque corría en la sesión original a este tiempo del RAW y, con --auto,
    pulsa Continue (el baseline `lead` s antes, lo que tarda el pipeline en conectar)."""
    ultimo, t_pipe = None, None
    while True:
        time.sleep(1)
        s, raw = api("/api/estado"), st.raw_t()
        orig = next((n for n, a, b in blq if a <= raw < b), "—")
        if orig != ultimo:
            print(f"[replay] RAW {mmss(raw)} · en la sesión original empieza: {orig}")
            ultimo = orig
        if s["elapsed"] is not None and t_pipe is None:
            t_pipe = raw - s["elapsed"]
            print(f"[replay] baseline en RAW {mmss(t_pipe)} (original {mmss(blq[0][1])}, "
                  f"diferencia {t_pipe - blq[0][1]:+.1f} s)")
        elif s["elapsed"] is None:
            t_pipe = None
        if auto and s["btn"]["next"] and (s["blk"]["i"] != 0 or raw >= blq[0][1] - lead):
            api("/api/bloque/siguiente", {})
            print(f"[replay] Continue (auto) en RAW {mmss(raw)}")


def validas(run_dir):
    v = pd.read_csv(os.path.join(run_dir, "ventanas.csv"))["valida"]
    return f"{100 * v.mean():.1f} % ({int(v.sum())}/{len(v)} ventanas)"


def main():
    global URL
    p = argparse.ArgumentParser(description="Replay en tiempo real de un AURA_RAW en el dashboard")
    p.add_argument("--csv", default=REC)
    p.add_argument("--plan", default=PLAN)
    p.add_argument("--dur", default=DUR)
    p.add_argument("--baseline-raw", type=float, default=BASE_RAW, help="s del RAW en que empezó el baseline original")
    p.add_argument("--original", default=os.path.dirname(ORIGINAL),
                   help="carpeta runs/ de la sesión en vivo, para comparar las ventanas válidas al final")
    p.add_argument("--codigo", default="REPLAY1638")
    p.add_argument("--port", type=int, default=8010)
    p.add_argument("--db", default=os.path.join(HERE, "data", "replay.db"))
    p.add_argument("--auto", action="store_true", help="Continue automático con los tiempos originales")
    p.add_argument("--sin-telefono", action="store_true",
                   help="sin teléfono simulado: la tarea la hace un teléfono (o navegador) real abierto en /gng")
    # Medido el 18 nov: de Continue a la línea "Pipeline" pasan ~13 s (conducta 1.5 s + búsqueda del stream + arranque).
    p.add_argument("--lead", type=float, default=13.0, help="--auto: s antes del baseline original en que se pulsa")
    a = p.parse_args()
    URL = f"http://127.0.0.1:{a.port}"

    print(f"[replay] leyendo {os.path.basename(a.csv)}…")
    x = pd.read_csv(a.csv, skiprows=[1], usecols=range(1, 9)).dropna().to_numpy(np.float32)  # última línea truncada
    blq = originales(a.plan, a.dur, a.baseline_raw)
    print(f"[replay] {len(x) / FS / 60:.1f} min · bloques originales (RAW): "
          + " → ".join(f"{n} {mmss(s)}" for n, s, _ in blq) + f" → fin {mmss(blq[-1][2])}")

    # La salida del servidor (una línea por petición) va a un archivo: en la consola quedan solo las líneas [replay];
    # lo que hacen el pipeline y el semáforo se ve en el Log del dashboard.
    log = open(os.path.join(os.path.dirname(a.db), "replay_servidor.log"), "w", encoding="utf-8")
    srv = subprocess.Popen([sys.executable, "-u", "sesion_aura_web.py", "--port", str(a.port), "--db", a.db], cwd=HERE,
                           stdout=log, stderr=subprocess.STDOUT, env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    for _ in range(60):
        try:
            api("/api/estado")
            break
        except OSError:
            time.sleep(0.5)
    else:
        sys.exit("[replay] el dashboard no arrancó")

    name, sid = "AURA_REPLAY", f"AuraLSL-replay-{time.strftime('%H%M%S')}"
    st = Stream(x, name, sid)
    st.start()  # RAW 0: desde aquí corre en tiempo real
    if not a.sin_telefono:
        threading.Thread(target=telefono, daemon=True).start()
    api("/api/semaforo/iniciar", {"name": name, "sid": sid})
    time.sleep(1)  # el teléfono simulado ya conectado (Start session lo pide para los bloques Go/NoGo)
    err = api("/api/sesion/iniciar", {"name": name, "sid": sid, "iaf": "10", "per": "420", "dur": a.dur,
                                      "plan": a.plan, "codigo": a.codigo})["error"]
    if err:
        sys.exit(f"[replay] {err}")
    print(f"[replay] dashboard: {URL.replace('127.0.0.1', 'localhost')} · sesión {a.codigo} lista · "
          + ("Continue automático" if a.auto else f"pulsa Continue para el baseline (original en RAW {mmss(blq[0][1])})"))
    threading.Thread(target=control, args=(st, blq, a.auto, a.lead), daemon=True).start()

    hecho = None
    try:
        while srv.poll() is None:
            time.sleep(2)
            s = api("/api/estado")
            if s["run_dir"] and "pipeline" not in s["running"] and s["btn"]["start"] and s["run_dir"] != hecho:
                hecho = s["run_dir"]
                orig = validas(a.original) if os.path.exists(os.path.join(a.original, "ventanas.csv")) else "—"
                print(f"[replay] pipeline terminado · ventanas válidas: replay {validas(hecho)} · "
                      f"original en vivo {orig}\n[replay] {hecho} · Ctrl+C para cerrar")
    except KeyboardInterrupt:
        pass
    finally:
        for ruta in ("/api/abortar", "/api/semaforo/detener"):  # que no queden el pipeline ni el semáforo huérfanos
            try:
                api(ruta, {})
            except OSError:
                pass
        srv.terminate()


if __name__ == "__main__":
    main()
