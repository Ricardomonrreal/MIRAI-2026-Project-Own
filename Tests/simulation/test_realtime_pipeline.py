"""Chequeo offline de los Pasos 2, 3 y 4 (sin LSL): python test_realtime_pipeline.py"""
import time
import warnings

import numpy as np
from scipy import signal

from mock_lsl_streamer import AURA_CHANNELS, inject, synthetic
from realtime_pipeline import (ALPHA_ROI, SEG_S, SEG_STEP_S, THETA_ROI, VALID_MIN, WIN_S, CausalFilter, Rejector,
                               Windower, blink_report)
from spectral_features import Features, window_psd

warnings.filterwarnings("ignore")  # avisos de specparam/MNE al importar el módulo offline

rng = np.random.default_rng(0)

for fs in (250.0, 50.0):
    x = rng.standard_normal((int(60 * fs), 8)) * 20  # 60 s, 8 canales, µV
    # Bloques de tamaño variable, como llegan por LSL.
    cuts = np.cumsum(rng.integers(1, int(0.05 * fs) + 2, size=len(x)))
    cuts = cuts[cuts < len(x)]

    # 1) Filtrar por bloques con estado == filtrar el registro entero de una vez.
    f = CausalFilter(fs, 60.0, 8)
    y_blocks = np.concatenate([f(b) for b in np.split(x, cuts)])
    y_whole = signal.sosfilt(f.sos, x, axis=0)
    err = np.abs(y_blocks - y_whole).max()
    assert err < 1e-6, err
    assert f.notch == (fs == 250.0) and f.band[1] == (40.0 if fs == 250 else 20.0)

    # 2) Cada ventana son exactamente las últimas 4 s al cumplirse cada 1 s, sea cual sea el troceo.
    win, hop = int(WIN_S * fs), int(fs)
    ts = np.arange(len(x)) / fs
    got = []
    w = Windower(win, hop, 8, lambda v, t: got.append((v.copy(), t)))
    for b, t in zip(np.split(x, cuts), np.split(ts, cuts)):
        w.push(b, t)
    ends = range(win, len(x) + 1, hop)
    assert len(got) == len(ends), (len(got), len(ends))
    for (v, t), n in zip(got, ends):
        assert np.array_equal(v, x[n - win:n]) and t == ts[n - 1]
    print(f"fs={fs:.0f} Hz: filtro por bloques err={err:.1e} µV, {len(got)} ventanas exactas — OK")

    # 3) Paso 3: 10 min sintéticos (~15 parpadeos/min) + tren de 30 s a 1 Hz, con verdad de campo.
    data, ev = synthetic(600, fs, 60.0, 10.0, 7)
    inject(data, ev, [("blink", 300, 30, 200)], fs, 10.0)
    f, rej, wins = CausalFilter(fs, 60.0, 8), Rejector(fs), []
    w = Windower(win, hop, 8, lambda v, t: wins.append((t, rej(v))))
    x, t = data.T.astype(float), np.arange(data.shape[1]) / fs
    for i in range(0, len(x), 5):
        w.push(f(x[i:i + 5]), t[i:i + 5])
    r = blink_report(wins, [(s / fs, lab) for s, lab in ev])
    print(f"fs={fs:.0f} Hz: parpadeos={r['parpadeos']}  rechazo con parpadeo={r['rechazo_con_parpadeo']:.1%}  "
          f"sin parpadeo={r['rechazo_sin_parpadeo']:.1%}  válidas fuera del tren={r['validas_fuera_de_trenes']:.1%}  "
          f"señal perdida={r['ventanas_senal_perdida']}")
    assert r["rechazo_con_parpadeo"] >= 0.95 and r["rechazo_sin_parpadeo"] < 0.05
    assert r["ventanas_senal_perdida"] > 0  # el tren de 30 s debe marcar señal perdida
    if r["validas_fuera_de_trenes"] < VALID_MIN:
        print(f"  [FALLA] ventanas válidas < {VALID_MIN:.0%} (criterio del protocolo)")

    # 4) Paso 4: 180 s sintéticos (alfa en IAF 10 Hz, theta en 6 Hz) con alfa inyectado (ojos cerrados) en 90–120 s.
    data, ev = synthetic(180, fs, 60.0, 10.0, 3)
    inject(data, ev, [("alpha", 90, 30, 15)], fs, 10.0)
    f, rej, feat, rows = CausalFilter(fs, 60.0, 8), Rejector(fs), Features(fs, 10.0), []
    front, post = [AURA_CHANNELS.index(c) for c in THETA_ROI], [AURA_CHANNELS.index(c) for c in ALPHA_ROI]

    def on(v, tt):
        rr = rej(v)
        if rr["valida"]:
            t0 = time.perf_counter()
            fq, psd = window_psd(v, rr["clean"], fs, int(SEG_S * fs), int(SEG_STEP_S * fs))
            rows.append((tt, feat(fq, psd, front, post), (time.perf_counter() - t0) * 1000))
    w = Windower(win, hop, 8, on)
    x, t = data.T.astype(float), np.arange(data.shape[1]) / fs
    for i in range(0, len(x), 5):
        w.push(f(x[i:i + 5]), t[i:i + 5])
    base = np.mean([o["alpha_per"] for tt, o, _ in rows if 20 <= tt < 85 and o["alpha_ok"]])
    eyes = np.mean([o["alpha_per"] for tt, o, _ in rows if 97 <= tt <= 120 and o["alpha_ok"]])
    ok = np.mean([o["theta_ok"] and o["alpha_ok"] for _, o, _ in rows])
    ms = max(m for _, _, m in rows)
    print(f"fs={fs:.0f} Hz: α_per base {base:.2f} dB → con alfa inyectado {eyes:.2f} dB (+{eyes - base:.2f}) | "
          f"R² ≥ 0.75 en {ok:.1%} | Welch + specparam máx. {ms:.1f} ms")
    assert eyes > base + 1 and ok > 0.9 and ms <= 250  # máx. ≤ 250 ms (criterio del 29 oct)
