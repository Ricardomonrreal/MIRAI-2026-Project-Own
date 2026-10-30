"""Chequeo offline de los Pasos 2–5 (sin LSL) · VERSIÓN B (parpadeos supraumbral, sin veto EMG, ajuste 2–30 Hz)"""
import os
import time
import warnings

import numpy as np
from scipy import signal

import calibration as cal
from mock_lsl_streamer import AURA_CHANNELS, inject, load_aura_csv, synthetic
from realtime_pipeline import (ALPHA_ROI, SEG_S, SEG_STEP_S, THETA_ROI, VALID_MIN, WIN_S, CausalFilter, Rejector,
                               Windower, blink_gain, blink_report)
from spectral_features import Features, band_per, fit_roi, h1, window_psd

warnings.filterwarnings("ignore")  # avisos de specparam/MNE al importar el módulo offline

rng = np.random.default_rng(0)
AURA_CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "AURA", "data", "eeg_data_20260122_123839.csv")


def run_step5(data, fs, events, line=60.0, bads0=()):
    """Cadena del Paso 5 como en realtime_pipeline: chequeo de calidad en los primeros QC_S s, luego Paso 3–4 con
    los canales malos excluidos y calibración congelada. Devuelve (Calibration, [(t, Z)], canales malos)."""
    win, hop = int(WIN_S * fs), int(fs)
    st = {"bads": list(bads0), "rej": None, "cal": None, "feat": Features(fs, 10.0), "z": []}
    markers = sorted((s0 / fs, lab) for s0, lab in events)

    def on(v, tt):
        if st["rej"] is None:
            if tt < cal.QC_S:
                return
            st["bads"] = sorted(set(st["bads"]) | set(cal.bad_channels(v, AURA_CHANNELS)))
            st["rej"], st["cal"] = Rejector(fs, st["bads"]), cal.Calibration(tt, WIN_S)
            for m in markers:
                st["cal"].marker(*m)
        front = [AURA_CHANNELS.index(c) for c in THETA_ROI if c not in st["bads"]]
        post = [AURA_CHANNELS.index(c) for c in ALPHA_ROI if c not in st["bads"]]
        rr = st["rej"](v)
        o = {}
        if rr["valida"]:
            fq, psd = window_psd(v, rr["clean"], fs, int(SEG_S * fs), int(SEG_STEP_S * fs))
            o = st["feat"](fq, psd, front, post)
        z = st["cal"].update(tt, o)
        if z is not None:
            st["z"].append((tt, z))
    f, w = CausalFilter(fs, line, 8), Windower(win, hop, 8, on)
    x, t = data.T.astype(float), np.arange(data.shape[1]) / fs
    for i in range(0, len(x), 5):
        w.push(f(x[i:i + 5]), t[i:i + 5])
    return st["cal"], st["z"], st["bads"]


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
    r = blink_report(wins, [(s / fs, lab) for s, lab in ev], blink_gain(fs, 60.0))
    print(f"fs={fs:.0f} Hz: parpadeos={r['parpadeos']} (subumbral {r['parpadeos_subumbral']}, mín. detectable "
          f"{r['amplitud_minima_detectable_uv']:.0f} µV)  rechazo con pico supraumbral={r['rechazo_con_parpadeo']:.1%}  "
          f"parciales={r['rechazo_parcial']:.1%} (n={r['segmentos_parciales']})  "
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

    # 5) fit_roi() + band_per() == h1.periodic() (mismo ajuste que el offline) en la última ventana.
    h1.FIT_RANGE = feat.fit_range
    spec, fq = rows[-1][1]["post_psd"], rows[-1][1]["f"]
    flat, exp, r2 = fit_roi(spec, fq)
    ref = h1.periodic(spec, fq, 8.0, 12.0)
    assert np.allclose((band_per(flat, fq, 8.0, 12.0), exp, r2), ref), (band_per(flat, fq, 8.0, 12.0), exp, r2, ref)

    # 6) Paso 5: 20 min sintéticos sin inyecciones (IAF 10 Hz), sin marcadores de fase → primeros 90 s.
    data, ev = synthetic(1200, fs, 60.0, 10.0, 11)
    c, zs, bads = run_step5(data, fs, [e for e in ev if e[1].startswith("file:")])
    assert c.state == "congelada", c.msg
    frozen = repr(c.params)
    p = c.params
    zt, za = np.array([z["theta"] for _, z in zs]), np.array([z["alpha"] for _, z in zs])
    print(f"fs={fs:.0f} Hz: Paso 5 · malos {bads or 'ninguno'} · IAF {p['iaf']:g} Hz · ventanas válidas θ "
          f"{p['theta']['ventanas_validas']} / α {p['alpha']['ventanas_validas']} · μ θ {p['theta']['mu']:.2f} / α "
          f"{p['alpha']['mu']:.2f} dB · σ_suav θ {p['theta']['sigma_suav']:.3f} / α {p['alpha']['sigma_suav']:.3f}")
    for n, z in (("theta", zt), ("alpha", za)):
        frac, fac = np.mean(np.abs(z) >= 1.5), p[n]["factor_autocorrelacion"]
        print(f"     {n}: |Z| ≥ 1.5 en {frac:.1%} del tiempo (criterio < 15 %) | σ(Z) {z.std():.2f} | "
              f"factor de autocorrelación {fac:.2f} → con él |Z| ≥ 1.5 en {np.mean(np.abs(z) >= 1.5 * fac):.1%}"
              + ("" if frac < 0.15 else "   [FALLA]"))
    assert abs(p["iaf"] - 10.0) <= 0.5 and not bads
    assert repr(c.params) == frozen  # μ, σ e IAF no cambian después de la calibración

# 7) Paso 5 con el CSV real de la AURA (enero 2026, 50 Hz, con fases): informativo, no es criterio.
if os.path.exists(AURA_CSV):
    data, ev, bads0, fs = load_aura_csv(AURA_CSV, 0, None, None)
    c, zs, bads = run_step5(data, fs, ev, line=60.0)
    p = c.params or {}
    print(f"CSV AURA ({fs:.0f} Hz): estado {c.state} {c.msg} · malos (emulador {bads0}, chequeo propio → {bads})")
    if p:
        print(f"     {p['fuente']} · IAF {p['iaf']:g} Hz ({p['iaf_de']}) · Berger {p.get('berger_db', float('nan')):+.1f} dB "
              f"({'OK' if p.get('berger_ok') else 'bajo 3 dB'}) · ventanas válidas θ {p['theta']['ventanas_validas']} / "
              f"α {p['alpha']['ventanas_validas']}")
