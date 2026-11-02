"""Chequeo offline de los Pasos 2–6 (sin LSL) · VERSIÓN B (parpadeos supraumbral, sin veto EMG, ajuste 2–30 Hz)"""
import os
import time
import warnings

import numpy as np
from scipy import signal

import calibration as cal
from jitai import CONFIG, Jitai, chi_flat
from mock_lsl_streamer import AURA_CHANNELS, add_blink, inject, load_aura_csv, synthetic
from realtime_pipeline import (ALPHA_ROI, BLINK_PERIOD_S, SEG_S, SEG_STEP_S, THETA_ROI, VALID_MIN, WIN_S, BlinkCounter,
                               CausalFilter, Rejector, Windower, blink_blocks, blink_gain, blink_match, blink_report)
from spectral_features import Features, band_per, fit_roi, h1, window_psd

warnings.filterwarnings("ignore")  # avisos de specparam/MNE al importar el módulo offline

rng = np.random.default_rng(0)
SEEDS_P5 = (11, 12, 13, 14, 15, 16)
AURA_CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "AURA", "data", "eeg_data_20260122_123839.csv")


def run_step5(data, fs, events, line=60.0, bads0=(), jitai=None):
    """Cadena del Paso 5 como en realtime_pipeline: chequeo de calidad en los primeros QC_S s, luego Paso 3–4 con
    los canales malos excluidos y calibración congelada. Devuelve (Calibration, [(t, Z)], canales malos, motivo de
    parada); como en vivo, la sesión se detiene si una ROI se queda sin canales válidos. Con `jitai`, cada ventana
    pasa también por el motor del Paso 6 (con la regla de calidad de χ)."""
    win, hop = int(WIN_S * fs), int(fs)
    st = {"bads": list(bads0), "rej": None, "cal": None, "feat": Features(fs, 10.0), "z": [], "stop": ""}
    markers = sorted((s0 / fs, lab) for s0, lab in events)

    def on(v, tt):
        if st["stop"]:
            return
        if st["rej"] is None:
            if tt < cal.QC_S:
                return
            st["bads"] = sorted(set(st["bads"]) | set(cal.bad_channels(v, AURA_CHANNELS)))
            if not [c for c in THETA_ROI if c not in st["bads"]] or not [c for c in ALPHA_ROI if c not in st["bads"]]:
                st["stop"] = "sin canales válidos en una ROI"
                return
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
        if jitai is not None:
            pc = st["cal"].params
            block = bool(z is not None and o and chi_flat(o["alpha_exp"], pc["chi_post"]["mu"], pc["chi_post"]["sd"],
                                                          rr["emg_db"], st["rej"].emg_lim, CONFIG["calidad_chi_sigmas"]))
            jitai.window(tt, z, {n: bool(o.get(f"{n}_ok")) for n in ("theta", "alpha")}, block)
    f, w = CausalFilter(fs, line, 8), Windower(win, hop, 8, on)
    x, t = data.T.astype(float), np.arange(data.shape[1]) / fs
    for i in range(0, len(x), 5):
        w.push(f(x[i:i + 5]), t[i:i + 5])
    return st["cal"], st["z"], st["bads"], st["stop"]


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

    # 3b) Contador de parpadeos (2 nov): 14 min sintéticos (+ DC del equipo). En el 2.º período de 7 min ("scroll")
    #     quedan 1 de cada 3 parpadeos y al 40 % de amplitud (como al mirar el teléfono): el conteo definitivo, con el
    #     umbral de cada período, debe verlos todos y la comparación por bloques, la caída de la tasa.
    data, ev = synthetic(840, fs, 60.0, 10.0, 7)
    ich = {c: i for i, c in enumerate(AURA_CHANNELS)}
    truth = []
    for k, (s, lab) in enumerate(e for e in ev if e[1].startswith("blink:")):
        amp = float(lab.split(":")[1])
        if s / fs >= BLINK_PERIOD_S:
            add_blink(data, s, fs, -amp if k % 3 else -0.6 * amp, ich)
        if s / fs < BLINK_PERIOD_S or not k % 3:
            truth.append(s / fs)
    truth = np.array(truth)
    bc = BlinkCounter(fs)
    x, t = data[ich["Fp1"]].astype(float) + 3000.0, np.arange(data.shape[1]) / fs
    for i in range(0, len(x), 5):
        bc.push(x[i:i + 5], t[i:i + 5])
    bc.finish()
    det = np.array([b_[0] for b_ in bc.blinks])
    rec = [blink_match(det[(det >= a_) & (det < a_ + BLINK_PERIOD_S)], truth[(truth >= a_) & (truth < a_ + BLINK_PERIOD_S)])
           for a_ in (0.0, BLINK_PERIOD_S)]
    bl = blink_blocks(bc.blinks, [(0.0, "reposo"), (BLINK_PERIOD_S, "scroll")], bc.t0, bc.periods[-1]["fin"])
    print(f"fs={fs:.0f} Hz: parpadeos definitivos recall/precisión reposo {rec[0][0]:.1%}/{rec[0][1]:.1%}, scroll "
          f"{rec[1][0]:.1%}/{rec[1][1]:.1%} | umbral {bc.periods[0]['umbral_uv']:.0f} → {bc.periods[1]['umbral_uv']:.0f} µV | "
          f"tasa {bl['reposo']['tasa_min']:.1f} → {bl['scroll']['tasa_min']:.1f}/min (×{bl['scroll']['razon']:.2f}, "
          f"Mann-Whitney p = {bl['scroll']['p_mann_whitney']:.4f})")
    assert all(r_ >= 0.95 and p_ >= 0.95 for r_, p_ in rec), rec
    assert len(bc.periods) == 2 and bc.periods[1]["umbral_uv"] < 0.6 * bc.periods[0]["umbral_uv"]  # el umbral se movió
    assert 0.2 < bl["scroll"]["razon"] < 0.5 and bl["scroll"]["p_mann_whitney"] < 0.01

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
    assert h1.FIT_RANGE == [2, 40]  # Features ya no reescribe la global del offline
    h1.FIT_RANGE = feat.fit_range  # solo para la referencia h1.periodic(), que la lee
    spec, fq = rows[-1][1]["post_psd"], rows[-1][1]["f"]
    flat, exp, r2 = fit_roi(spec, fq, feat.fit_range)
    ref = h1.periodic(spec, fq, 8.0, 12.0)
    h1.FIT_RANGE = [2, 40]
    assert np.allclose((band_per(flat, fq, 8.0, 12.0), exp, r2), ref), (band_per(flat, fq, 8.0, 12.0), exp, r2, ref)

    # 6) Paso 5: 20 min sintéticos sin inyecciones (IAF 10 Hz), sin marcadores → primeros 90 s. El error de μ es un
    #    sorteo por sesión, así que RMS(Z) se evalúa combinando varias sesiones (semillas), no con una sola.
    zall = {"theta": [], "alpha": []}
    spur = []
    for seed in SEEDS_P5:
        data, ev = synthetic(1200, fs, 60.0, 10.0, seed)
        jt = Jitai()
        c, zs, bads, stop = run_step5(data, fs, [], jitai=jt)
        spur.append({lvl: sum(1 for e in jt.log if e[1] == lvl and e[2] == "on") for lvl in (1, 3)})
        assert c.state == "congelada" and not stop, (c.msg, stop)
        frozen = repr(c.params)
        p = c.params
        line = f"fs={fs:.0f} Hz semilla {seed}: IAF {p['iaf']:g} Hz, ventanas válidas {p['theta']['ventanas_validas']}"
        for n in ("theta", "alpha"):
            z = np.array([z_[n] for _, z_ in zs])
            zall[n].append(z)
            line += f" | {n} RMS {np.sqrt(np.mean(z ** 2)):.2f} (media {z.mean():+.2f}, DE {z.std():.2f})"
        print(line)
        assert abs(p["iaf"] - 10.0) <= 0.5 and not bads
        assert repr(c.params) == frozen  # μ, σ e IAF no cambian después de la calibración
    for n in ("theta", "alpha"):
        rms = float(np.sqrt(np.mean(np.concatenate(zall[n]) ** 2)))
        print(f"fs={fs:.0f} Hz: Paso 5 · RMS(Z_{n}) combinado de {len(SEEDS_P5)} sesiones = {rms:.2f} (criterio 0.7–1.4)")
        assert 0.7 <= rms <= 1.4, rms
    tot = [d[1] + d[3] for d in spur]
    print(f"fs={fs:.0f} Hz: Paso 6 · disparos espurios en 20 min sin inyecciones (criterio ≤ 1): "
          + ", ".join(f"semilla {sd}: N1={d[1]} N3={d[3]}" for sd, d in zip(SEEDS_P5, spur))
          + ("" if max(tot) <= 1 else "   [FALLA]"))

    # 10) Paso 6 con EEG: alfa inyectado (300–420 s) y theta sostenido (330–480 s), 15 µV. El Nivel 1 debe dispararse
    #     una vez y no antes de 5 s de persistencia; el Nivel 3, una vez, desplazando al Nivel 1.
    data, ev = synthetic(600, fs, 60.0, 10.0, 31)
    inject(data, ev, [("alpha", 300, 120, 15), ("theta", 330, 150, 15)], fs, 10.0)
    jt = Jitai()
    c, zs, bads, stop = run_step5(data, fs, [], jitai=jt)
    on1 = [e for e in jt.log if e[1] == 1 and e[2] == "on" and 300 <= e[0] <= 420]
    on3 = [e for e in jt.log if e[1] == 3 and e[2] == "on" and 330 <= e[0] <= 480 + 6]
    disp = [e for e in jt.log if e[1] == 1 and e[2] == "off" and "desplazado por nivel 3" in e[3]]
    print(f"fs={fs:.0f} Hz: Paso 6 con inyecciones · eventos: " + "; ".join(f"{e[0]:.0f} s N{e[1]} {e[2]} ({e[3]})" for e in jt.log))
    # Con los valores del protocolo (decisión del 30 oct: se ajustan en el Paso 7) se reporta en lugar de detener el test.
    ok1 = len(on1) == 1 and on1[0][0] - 300 >= CONFIG["niveles"][1]["persistencia_s"]
    print(f"     N1 durante el alfa: {len(on1)} activación(es) " + (f"(primera a los {on1[0][0] - 300:.0f} s)" if on1 else "")
          + ("" if ok1 else "   [FALLA] criterio: una vez, tras la persistencia"))
    print(f"     N3 durante el theta: {len(on3)} activación(es) " + (f"(a los {on3[0][0] - 330:.0f} s)" if on3 else "")
          + f" | desplaza a N1: {'sí' if disp else 'no (N1 no estaba activo)' if on3 else 'no'}"
          + ("" if len(on3) == 1 else "   [FALLA] criterio: una vez"))

    # 7) Paso 5 con fases AURA: fondo con IAF 10 Hz y alfa a 9 Hz solo en ojos cerrados → la IAF debe salir de ojos
    #    cerrados (9 Hz), μ y σ de ojos abiertos, y el Berger ≥ 3 dB.
    data, ev = synthetic(260, fs, 60.0, 10.0, 21)
    inject(data, ev, [("alpha", 102.5, 90, 15)], fs, 9.0)
    ph = [(0.0, "setup"), (12.5, cal.EYES_OPEN), (102.5, cal.EYES_CLOSED), (192.5, "baseline_completed")]
    c, zs, bads, stop = run_step5(data, fs, [(int(t_ * fs), f"file:{n_}") for t_, n_ in ph])
    p = c.params or {}
    print(f"fs={fs:.0f} Hz: Paso 5 con fases · estado {c.state} {c.msg} · {p.get('fuente')} · IAF {p.get('iaf')} Hz "
          f"({p.get('iaf_de')}) · Berger {p.get('berger_db', float('nan')):+.1f} dB · ventanas de ojos abiertos θ "
          f"{p.get('theta', {}).get('ventanas_validas')} / α {p.get('alpha', {}).get('ventanas_validas')}")
    assert c.state == "congelada" and p["fuente"] == "fases AURA" and p["iaf_de"] == cal.EYES_CLOSED
    assert abs(p["iaf"] - 9.0) <= 0.5 and p["berger_ok"]

    # 8) Chequeo de calidad: O1 muerto y Fz 10× más ruidoso → ambos excluidos de sus ROI y la calibración sigue;
    #    Fz y Cz muertos → la ROI frontal queda vacía y la sesión se detiene.
    data, ev = synthetic(150, fs, 60.0, 10.0, 22)
    data[AURA_CHANNELS.index("O1")] = 0
    data[AURA_CHANNELS.index("Fz")] *= 10
    c, zs, bads, stop = run_step5(data, fs, [])
    print(f"fs={fs:.0f} Hz: chequeo de calidad · malos {bads} · estado {c.state} {stop}")
    assert {"O1", "Fz"} <= set(bads) and c.state == "congelada" and not stop
    data, ev = synthetic(60, fs, 60.0, 10.0, 23)
    data[AURA_CHANNELS.index("Fz")] = 0
    data[AURA_CHANNELS.index("Cz")] = 0
    c, zs, bads, stop = run_step5(data, fs, [])
    print(f"fs={fs:.0f} Hz: chequeo de calidad · malos {bads} · {stop}")
    assert c is None and stop

# 11) Paso 6, lógica del motor con secuencias de Z controladas (sin EEG).
def feed(jt, seq, t0=0.0, ok=True, f="alpha"):
    """seq: valores de Z para la feature f, uno por segundo; la otra feature queda en 0."""
    for k, v in enumerate(seq):
        jt.window(t0 + k, {"alpha": v if f == "alpha" else 0.0, "theta": v if f == "theta" else 0.0},
                  {"alpha": ok, "theta": ok})
    return t0 + len(seq)


jt = Jitai()  # histéresis: activa con ≥ 1.5 sostenido, oscila 1.0–1.5 sin apagarse, se apaga una vez con < 1.0
t = feed(jt, [1.6] * 10)
t = feed(jt, [1.1, 1.4] * 50, t)
feed(jt, [0.5] * 5, t)
ev1 = [(e[1], e[2]) for e in jt.log]
assert ev1 == [(1, "on"), (1, "off")] and jt.log[0][0] == 4, jt.log  # on en la 5.ª ventana (t = 4)
jt = Jitai()  # sin llegar a 1.5 nunca se activa, aunque se quede entre 1.0 y 1.5
feed(jt, [1.4, 1.2, 1.45, 1.05] * 60)
assert not jt.log, jt.log
jt = Jitai()  # el contador se mantiene entre 1.0 y 1.5 y suma solo con ≥ 1.5
feed(jt, [1.6, 1.6, 1.3, 1.3, 1.6, 1.6, 1.2, 1.6])
assert [e[2] for e in jt.log] == ["on"] and jt.log[0][0] == 7, jt.log
jt = Jitai()  # > 5 s sin ventanas válidas reinician el contador
t = feed(jt, [1.6] * 3)
t = feed(jt, [1.6] * 6, t, ok=False)
feed(jt, [1.6] * 3, t)
assert not jt.log, jt.log
jt = Jitai()  # prioridad: N3 desplaza a N1; N1 no vuelve mientras N3 está en refractario
for k in range(200):
    jt.window(k, {"alpha": 2.0, "theta": 2.0 if k >= 20 else 0.0}, {"alpha": True, "theta": True})
ev = [(e[0], e[1], e[2]) for e in jt.log]
assert ev[:3] == [(4, 1, "on"), (49, 1, "off"), (49, 3, "on")], ev
assert not [e for e in jt.log if e[1] == 1 and e[2] == "on" and e[0] > 49], jt.log
jt = Jitai()  # N2: 2 eventos en 60 s lo activan y desplazan a N1; sale tras 60 s sin eventos; refractario de N1
feed(jt, [2.0] * 10)
jt.behavior(10.0, "nogo:error")
jt.behavior(30.0, "nogo:slow")
t = feed(jt, [2.0] * 100, 10.0)
ev = [(e[0], e[1], e[2]) for e in jt.log]
assert ev[:3] == [(4, 1, "on"), (30.0, 1, "off"), (30.0, 2, "on")] and (90.0, 2, "off") in ev, ev
assert not [e for e in jt.log if e[1] == 1 and e[2] == "on" and 30 < e[0] < 150], jt.log  # refractario de N2 (120 s)
cfg = {**CONFIG, "niveles": {**CONFIG["niveles"], 2: {**CONFIG["niveles"][2], "activo": False}}}
jt = Jitai(cfg)  # N2 desactivado (escenario H1 ✅ H2 ❌)
jt.behavior(0.0, "nogo:error")
jt.behavior(1.0, "nogo:error")
assert not jt.log
assert chi_flat(0.8, 1.6, 0.1, -10.0, -18.0, 3.0) and not chi_flat(0.8, 1.6, 0.1, -20.0, -18.0, 3.0)
assert not chi_flat(0.8, 1.6, 0.1, None, None, 3.0)  # sin EMG (50 Hz) la regla no aplica
print("Paso 6 · lógica del motor (histéresis, persistencia, pérdida de señal, prioridad, nivel 2, calidad χ): OK")

# 9) Paso 5 con el CSV real de la AURA (enero 2026, 50 Hz, con fases): informativo, no es criterio.
if os.path.exists(AURA_CSV):
    data, ev, bads0, fs = load_aura_csv(AURA_CSV, 0, None, None)
    c, zs, bads, stop = run_step5(data, fs, ev, line=60.0, bads0=bads0)  # como en vivo: malos de la fuente + chequeo propio
    p = c.params or {}
    print(f"CSV AURA ({fs:.0f} Hz): estado {c.state} {c.msg} · malos (emulador {bads0}, chequeo propio → {bads})")
    if p:
        print(f"     {p['fuente']} · IAF {p['iaf']:g} Hz ({p['iaf_de']}) · Berger {p.get('berger_db', float('nan')):+.1f} dB "
              f"({'OK' if p.get('berger_ok') else 'bajo 3 dB'}) · ventanas válidas θ {p['theta']['ventanas_validas']} / "
              f"α {p['alpha']['ventanas_validas']}")
