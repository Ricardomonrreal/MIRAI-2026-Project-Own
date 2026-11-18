"""
grabar_lsl.py — grabación del EEG de la sesión desde LSL (MIRAI 2026) · VERSIÓN B

El dashboard (sesion_aura_web.py) lo lanza con Start session y lo detiene cuando termina el pipeline (o al abortar).
Graba el mismo stream que recibe el pipeline, con el reloj LSL de esta PC: el mismo de los marcadores de bloque, de
ventanas.csv / eventos.csv y de la tarea Go/NoGo (inicio_lsl en la base). Así no hay desfase entre la grabación y la
sesión, como el que hay entre el botón de grabar de Aura.exe y el cronómetro del dashboard. El CSV de Aura.exe puede
seguir grabándose como respaldo.

Salida en runs/<fecha>_<hora>_grabacion_<código>/:
  eeg.csv         ts_lsl, Fp1…O2 (µV crudos, como llegan) y bloque: el último marcador bloque:<nombre> con ts ≤ el
                  de la muestra ("previo" antes del baseline, "pausa" entre bloques). Todo se graba; la columna
                  bloque separa lo que se usa para las hipótesis (dentro de los bloques).
  marcadores.csv  ts_lsl, marcador: los marcadores que el dashboard manda a MIRAI_Behavior (le llegan por la entrada
                  estándar y se fechan con el reloj LSL al llegar).
  info.json       stream, source_id, fs y la hora de inicio (reloj LSL y reloj de pared).
Marcas de tiempo: solo proc_clocksync (sin dejitter, que el pipeline sí usa): quedan visibles las muestras perdidas por
Bluetooth; el dejitter se puede aplicar después. Cada minuto imprime GRABACION con muestras y tasa del último minuto.

Uso: python grabar_lsl.py --name AURA --source-id AuraLSL- --codigo P01      (chequeo sin LSL: --check)
"""
import argparse
import csv
import json
import os
import queue
import signal
import sys
import threading
import time

import numpy as np

from check_lsl_stream import find_stream  # fija LSLAPICFG antes de importar pylsl
from mock_lsl_streamer import AURA_CHANNELS
import pylsl

HERE = os.path.dirname(os.path.abspath(__file__))


def etiquetas(ts, mk):
    """Bloque de cada muestra: el último marcador bloque:<nombre> con ts ≤ el de la muestra ('previo' si no hay)."""
    if not mk:
        return ["previo"] * len(ts)
    t = np.array([m[0] for m in mk])
    i = np.searchsorted(t, ts, side="right") - 1
    return ["previo" if k < 0 else mk[k][1] for k in i]


def main():
    ap = argparse.ArgumentParser(description="Grabación del EEG de la sesión desde LSL")
    ap.add_argument("--name", default="AURA")
    ap.add_argument("--source-id", default=None)
    ap.add_argument("--codigo", default="SIN_CODIGO")
    ap.add_argument("--timeout", type=float, default=15.0)
    ap.add_argument("--check", action="store_true", help="chequeo de la columna bloque, sin LSL")
    a = ap.parse_args()
    if a.check:
        t = np.array([1.0, 2.0, 3.0, 4.0])
        assert etiquetas(t, []) == ["previo"] * 4
        assert etiquetas(t, [(2.0, "baseline"), (3.5, "pausa")]) == ["previo", "baseline", "baseline", "pausa"]
        return print("check OK")
    if hasattr(signal, "SIGBREAK"):  # Ctrl+Break del dashboard = cierre limpio, como en el pipeline
        signal.signal(signal.SIGBREAK, signal.default_int_handler)

    inlet = pylsl.StreamInlet(find_stream(a.name, a.source_id, a.timeout), max_buflen=60,
                              processing_flags=pylsl.proc_clocksync)
    info = inlet.info()
    fs = info.nominal_srate()
    d = os.path.join(HERE, "runs", time.strftime("%Y%m%d_%H%M%S") + f"_grabacion_{a.codigo}")
    os.makedirs(d)
    with open(os.path.join(d, "info.json"), "w", encoding="utf-8") as f:
        json.dump({"stream": info.name(), "source_id": info.source_id(), "host": info.hostname(), "fs": fs,
                   "canales": AURA_CHANNELS, "codigo": a.codigo, "inicio_lsl": pylsl.local_clock(),
                   "inicio": time.strftime("%Y-%m-%d %H:%M:%S"), "marcas": "proc_clocksync, sin dejitter"},
                  f, indent=2, ensure_ascii=False)
    fe = open(os.path.join(d, "eeg.csv"), "w", newline="", encoding="utf-8")
    fm = open(os.path.join(d, "marcadores.csv"), "w", newline="", encoding="utf-8")
    we, wm = csv.writer(fe), csv.writer(fm)
    we.writerow(["ts_lsl", *AURA_CHANNELS, "bloque"])
    wm.writerow(["ts_lsl", "marcador"])
    print(f"Grabación: {d}", flush=True)

    # Marcadores: el dashboard escribe en la entrada estándar los mismos que manda a MIRAI_Behavior y aquí se fechan
    # con el reloj LSL al llegar (como push_sample en behavior_markers.py). Sin buscar el stream: el de conducta nace
    # con el primer Continue y otro viejo de una sesión abierta se llama igual (18 nov: la búsqueda tomaba ese).
    cola = queue.Queue()
    threading.Thread(target=lambda: [cola.put((pylsl.local_clock(), l.strip())) for l in sys.stdin if l.strip()],
                     daemon=True).start()
    mk, n, n_min, nxt_min = [], 0, 0, time.monotonic()
    try:
        while True:
            now = time.monotonic()
            while not cola.empty():
                mts, m = cola.get()
                wm.writerow([f"{mts:.6f}", m])
                if m.startswith("bloque:"):
                    mk.append((mts, m.split(":", 1)[1]))
                fm.flush()
            x, ts = inlet.pull_chunk(timeout=0.0, max_samples=int(fs))
            if ts:
                for t, row, b in zip(ts, x, etiquetas(ts, mk)):
                    we.writerow([f"{t:.6f}", *(f"{v:.3f}" for v in row), b])
                fe.flush()  # si el proceso se mata, lo escrito ya está en disco
                n, n_min = n + len(ts), n_min + len(ts)
            else:
                time.sleep(0.02)
            if now >= nxt_min + 60:
                nxt_min += 60
                print(f"GRABACION {n} muestras · {n / fs / 60:.1f} min · último minuto {n_min / 60:.1f} Hz · "
                      f"bloque {mk[-1][1] if mk else 'previo'}", flush=True)
                n_min = 0
    except KeyboardInterrupt:
        pass
    fe.close()
    fm.close()
    print(f"Grabación cerrada: {n} muestras ({n / fs / 60:.1f} min) en {d}", flush=True)


if __name__ == "__main__":
    main()
