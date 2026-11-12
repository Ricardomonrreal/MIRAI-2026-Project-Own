"""
semaforo_canales.py — semáforo de electrodos para la sesión AURA (MIRAI 2026) · VERSIÓN B

Reemplaza la verificación del stream (Paso 1 de la sesión, check_lsl_stream.py; 11 nov): el indicador de Aura.exe no
es confiable, así que cada electrodo se juzga con el mismo filtro y el mismo umbral que usa el pipeline. Corre hasta
que se detiene (antes y, si se quiere, durante la sesión: es un inlet LSL aparte). Cada segundo, sobre los últimos
VENTANA_S s, imprime `SEMAFORO {"Fp1": [color, σ µV, % segmentos > 150 µV], ...}` (color g / y / r):
  rojo      en el riel (desconectado), plano (σ < PLANO_UV), σ > ROJO_UV o ≥ RUIDO_FRAC de segmentos de 2 s > PTP_UV
            (por sí solo invalidaría casi todas las ventanas); también los 8 si no llegan muestras en SIN_DATOS_S s
  amarillo  σ > VERDE_UV o algún segmento > PTP_UV
  verde     lo demás
σ = 1.4826 · MAD de la señal filtrada (1–40 Hz + notch de CausalFilter; referencia promedio con la AURA real, como el
pipeline, sin Fp1 ni canales en el riel/planos). La MAD casi no la mueven los parpadeos, así que Fp1 se juzga por σ;
su % de segmentos se muestra pero no cuenta (sus parpadeos superan 150 µV aun con buen contacto, ver AVISO RUIDO).

Uso:
  python semaforo_canales.py --name AURA --source-id AuraLSL-     # Aura.exe (emulador: --source-id mirai-sim-)
  python semaforo_canales.py --selftest                            # chequeo de las reglas sin LSL
"""
import argparse
import json
import sys
import time

import numpy as np
from scipy import signal

from check_lsl_stream import find_stream  # fija LSLAPICFG antes de importar pylsl
from mock_lsl_streamer import AURA_CHANNELS
from realtime_pipeline import PTP_UV, RUIDO_FRAC, SEG_S, CausalFilter
import pylsl

VENTANA_S = 10.0
# ponytail: umbrales fijos; ajustar con las sesiones reales. ROJO_UV ≈ PTP_UV / 6: el rango de 500 muestras gaussianas
# (2 s a 250 Hz) es ~6 σ, así que con σ > 25 µV casi todo segmento pasa de 150 µV. Buen contacto con CAR: 6–10 µV (10 nov).
VERDE_UV, ROJO_UV, PLANO_UV = 15.0, 25.0, 0.5
RIEL_UV = 350_000.0  # la AURA deja los canales desconectados en −375 000 µV (crudo)
SIN_DATOS_S = 3.0


def semaforo(raw, y, fs, car):
    """raw / y: (muestras, 8) crudo y filtrado de los últimos VENTANA_S s → {canal: [color, σ, % segmentos]}."""
    mad = lambda v: 1.4826 * np.median(np.abs(v - np.median(v, 0)), 0)
    muerto = (np.abs(raw) >= RIEL_UV).any(0) | (mad(y) < PLANO_UV)  # antes del CAR: después un canal muerto copia la ref.
    if car:
        ref = [i for i, c in enumerate(AURA_CHANNELS) if c != "Fp1" and not muerto[i]]
        if ref:
            y = y - y[:, ref].mean(1, keepdims=True)
    sd, seg = mad(y), int(SEG_S * fs)
    frac = np.mean([np.ptp(y[s:s + seg], 0) > PTP_UV for s in range(0, len(y) - seg + 1, int(fs))], 0)
    out = {}
    for i, c in enumerate(AURA_CHANNELS):
        f = 0.0 if c == "Fp1" else frac[i]
        col = ("r" if muerto[i] or sd[i] > ROJO_UV or f >= RUIDO_FRAC else
               "y" if sd[i] > VERDE_UV or f > 0 else "g")
        out[c] = [col, round(float(sd[i]), 1), round(100 * float(frac[i]))]
    return out


def selftest():
    fs, n, rng = 250.0, 2500, np.random.default_rng(0)
    y = rng.normal(0, 8, (n, 8))  # 8 µV: todos verdes
    y[:, 1] *= 2.5   # F3 20 µV → amarillo
    y[:, 2] *= 5     # Fz 40 µV → rojo
    y[:, 6] = 0      # O1 plano → rojo
    y[::125, 0] += 300  # Fp1 con parpadeos: sigue verde
    raw = y - 100_000
    raw[:, 7] = -375_000  # O2 en el riel → rojo
    r = semaforo(raw, y, fs, car=False)
    assert [r[c][0] for c in AURA_CHANNELS] == ["g", "y", "r", "g", "g", "g", "r", "r"], r
    assert r["Fp1"][2] == 100 and r["Fz"][2] > 50, r
    print("selftest OK")


def main():
    ap = argparse.ArgumentParser(description="Semáforo de electrodos (sesión AURA)")
    ap.add_argument("--name", default="AURA")
    ap.add_argument("--source-id", default=None, help="'AuraLSL-' (Aura.exe) o 'mirai-sim-' (emulador)")
    ap.add_argument("--timeout", type=float, default=15.0)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()

    inlet = pylsl.StreamInlet(find_stream(a.name, a.source_id, a.timeout), max_buflen=30)
    info = inlet.info()
    fs, nch = info.nominal_srate(), info.channel_count()
    if fs <= 0 or nch != len(AURA_CHANNELS):
        sys.exit(f"Se esperaba EEG regular de {len(AURA_CHANNELS)} canales; llegó {nch} ch a {fs} Hz")
    line = float(info.desc().child_value("line_freq") or 60.0)  # Aura.exe no publica la red: México
    filt = CausalFilter(fs, line, nch)
    car = info.source_id().startswith("AuraLSL-")
    n, raw, y = int(VENTANA_S * fs), None, None
    print(f"Semáforo: {info.name()} ({info.source_id()}) | {fs:.0f} Hz | {'ref. promedio | ' if car else ''}"
          f"verde σ ≤ {VERDE_UV:.0f} µV · rojo σ > {ROJO_UV:.0f} µV o ≥ {RUIDO_FRAC:.0%} de segmentos > {PTP_UV:.0f} µV")
    last = nxt = pylsl.local_clock()
    while True:
        x, ts = inlet.pull_chunk(timeout=0.0, max_samples=int(fs))
        now = pylsl.local_clock()
        if ts:
            x = np.asarray(x, dtype=np.float64)
            if raw is None:  # arranque en régimen con la primera muestra: sin el transitorio del offset de ~−100 000 µV
                filt.zi = signal.sosfilt_zi(filt.sos)[:, :, None] * x[0]
                raw, y = x[:0], x[:0]
            raw, y, last = np.vstack([raw, x])[-n:], np.vstack([y, filt(x)])[-n:], now
        else:
            time.sleep(0.01)
        if now >= nxt:
            nxt += 1.0
            if now - last > SIN_DATOS_S:
                print("SEMAFORO " + json.dumps({c: ["r", None, None] for c in AURA_CHANNELS}), flush=True)
            elif raw is not None and len(raw) >= SEG_S * fs:
                print("SEMAFORO " + json.dumps(semaforo(raw, y, fs, car)), flush=True)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
