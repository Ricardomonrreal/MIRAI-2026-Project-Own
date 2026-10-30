"""
realtime_pipeline.py — Pasos 2, 3 y 4 del Protocolo de Simulación (MIRAI 2026)

Recibe el EEG por LSL (emulador o AURA real), lo filtra en línea, entrega una ventana cada 1 s, marca qué
segmentos de 2 s están libres de artefactos (Fp1/ROI > 150 µV, EMG) y calcula theta_per / alfa_per con esos
segmentos (spectral_features.py). Los Pasos 5–6 se enganchan en `on_window()`.

  * Stream elegido por nombre + source_id con el entorno LSL cerrado a esta PC (lsl_api.cfg).
  * Todo en segundos: fs y red se leen del stream (250 Hz emulador, 250/50 Hz AURA).
  * Filtro causal con estado entre bloques: pasa-banda 1 Hz – min(40, 0.8·fs/2) + notch si cabe bajo Nyquist.
  * Las ventanas se cortan en múltiplos exactos del avance, aunque los bloques LSL lleguen de tamaños variables.
  * Registro por sesión en runs/<AAAAMMDD_HHMMSS>_<fuente>/: config.json, ventanas.csv, eventos.csv.

Uso:
  python realtime_pipeline.py --name AURA --source-id mirai-sim- --seconds 600   # emulador
  python realtime_pipeline.py --name AURA --source-id AuraLSL-                   # AURA real (Aura.exe de esta PC)
"""
import argparse
import csv
import json
import os
import sys
import time

import numpy as np
from scipy import signal

from check_lsl_stream import channel_meta, find_markers, find_stream  # fija LSLAPICFG antes de importar pylsl
from mock_lsl_streamer import AURA_CHANNELS
from spectral_features import Features, window_psd
import pylsl

WIN_S = 6.0  # ventana: con ~15 parpadeos/min, 4 s dejaban sin tramo limpio de 2 s al 14 % de las ventanas (6 s: 4 %)
HOP_S = 1.0  # una evaluación por segundo
SEG_S = 2.0  # segmentos de Welch y de rechazo (Paso 3): 0.5 Hz de resolución, como el offline
SEG_STEP_S = 0.5  # paso entre segmentos: 9 por ventana de 6 s (Welch con 75 % de solapamiento)
PTP_UV = 150.0  # mismo umbral pico a pico que el offline (h1_ds007537.PTP_UV)
THETA_ROI = ["Fz", "Cz"]  # offline: Fz/FCz (AURA no tiene FCz)
ALPHA_ROI = ["Pz", "O1", "O2"]  # offline: Pz/POz/O1/O2 (AURA no tiene POz)
EMG_BAND = (25.0, 40.0)
CAL_S = 90.0  # calibración (Paso 5); aquí fija la línea base EMG
LOST_S = 5.0  # más segundos seguidos sin ventanas válidas = señal perdida
VALID_MIN = 0.90  # criterio del Paso 3: fracción de ventanas válidas con ~15 parpadeos/min
HERE = os.path.dirname(os.path.abspath(__file__))


class CausalFilter:
    """Pasa-banda Butterworth (orden 4: 2 por flanco) + notch, con estado conservado entre bloques."""

    def __init__(self, fs, line_freq, nch):
        self.band = (1.0, min(40.0, 0.8 * fs / 2))
        sos = signal.butter(2, self.band, btype="band", fs=fs, output="sos")
        self.notch = line_freq < fs / 2  # a 50 Hz de muestreo, 60 Hz no cabe: depende del antialiasing del equipo
        if self.notch:
            sos = np.vstack([sos, signal.tf2sos(*signal.iirnotch(line_freq, 30.0, fs))])
        self.sos = sos
        self.zi = np.zeros((sos.shape[0], 2, nch))

    def __call__(self, x):
        """x: (muestras, canales) → mismo tamaño, continuando el estado del bloque anterior."""
        y, self.zi = signal.sosfilt(self.sos, x, axis=0, zi=self.zi)
        return y


class Windower:
    """Búfer circular: acumula muestras filtradas y llama a `emit(ventana, ts_última)` cada `hop` muestras."""

    def __init__(self, win, hop, nch, emit):
        self.buf = np.zeros((win, nch))
        self.win, self.hop, self.emit = win, hop, emit
        self.n = 0  # muestras totales recibidas

    def push(self, x, ts):
        i = 0
        while i < len(x):
            # Cortar el bloque en el siguiente múltiplo del avance para que la ventana termine justo ahí.
            k = min(len(x) - i, self.hop - self.n % self.hop)
            pos = (self.n + np.arange(k)) % self.win
            self.buf[pos] = x[i:i + k]
            self.n += k
            i += k
            if self.n % self.hop == 0 and self.n >= self.win:
                start = self.n % self.win
                self.emit(np.concatenate([self.buf[start:], self.buf[:start]]), ts[i - 1])


class Rejector:
    """Paso 3: decide qué segmentos de 2 s de la ventana (paso de 0.5 s → 9 por ventana de 6 s) están limpios.

    Un segmento se descarta si el pico a pico supera PTP_UV en el canal ocular (Fp1; F3/F4 si Fp1 está malo)
    o en cualquier canal válido de las ROI, o si la potencia EMG posterior (25–40 Hz, solo con fs ≥ 100)
    supera μ + 3σ de los primeros CAL_S s. La ventana es válida con ≥ 1 segmento limpio; las inválidas
    mantienen los contadores del Paso 6 y más de LOST_S seguidas marcan señal perdida (reinicio).
    """

    def __init__(self, fs, bads=(), ocular_uv=PTP_UV):
        self.ocular_uv = ocular_uv  # umbral del canal ocular; las ROI siempre usan PTP_UV
        idx = {c: i for i, c in enumerate(AURA_CHANNELS)}
        self.ocular_chs = ["Fp1"] if "Fp1" not in bads else [c for c in ("F3", "F4") if c not in bads]
        self.ocular = [idx[c] for c in self.ocular_chs]
        self.roi = [idx[c] for c in THETA_ROI + ALPHA_ROI if c not in bads]
        self.post = [idx[c] for c in ALPHA_ROI if c not in bads]
        self.fs, self.seg, self.step = fs, int(round(SEG_S * fs)), int(round(SEG_STEP_S * fs))
        self.emg = fs >= 100 and bool(self.post)  # a 50 Hz no hay banda de 25–40 Hz
        self.emg_cal, self.emg_lim = [], None
        self.n, self.invalid_run = 0, 0

    def __call__(self, w):
        # Todos los segmentos a la vez: (segmentos, canales, muestras). Con un Welch por segmento el EMG
        # costaba ~12 ms por ventana a 250 Hz; con un periodograma vectorizado, < 1 ms.
        segs = np.lib.stride_tricks.sliding_window_view(w, self.seg, axis=0)[::self.step]
        ptp = np.ptp(segs, axis=2)
        if self.emg:
            f, p = signal.periodogram(segs[:, self.post], self.fs, window="hann", axis=2)
            band = (f >= EMG_BAND[0]) & (f <= EMG_BAND[1])
            emg_all = 10 * np.log10(p[:, :, band].mean(axis=(1, 2)))
        clean, why, emg = [], [], []
        for i in range(len(segs)):
            r = [k for k, chs, lim in (("ocular", self.ocular, self.ocular_uv), ("roi", self.roi, PTP_UV))
                 if chs and (ptp[i, chs] > lim).any()]
            e = float(emg_all[i]) if self.emg else float("nan")
            if self.emg_lim is not None and e > self.emg_lim:
                r.append("emg")
            # Línea base EMG con los segmentos sin otro artefacto de los primeros CAL_S s; luego queda congelada.
            if self.emg and self.emg_lim is None and not r:
                self.emg_cal.append(e)
            clean.append(not r)
            why.extend(r)
            emg.append(e)
        self.n += 1
        if self.emg and self.emg_lim is None and self.n * HOP_S >= CAL_S and len(self.emg_cal) >= 10:
            self.emg_lim = float(np.mean(self.emg_cal) + 3 * np.std(self.emg_cal))
        valid = any(clean)
        self.invalid_run = 0 if valid else self.invalid_run + 1
        return {"clean": clean, "motivo": "+".join(sorted(set(why))), "valida": valid,
                "perdida": self.invalid_run > LOST_S / HOP_S, "emg_db": float(np.nanmean(emg)) if self.emg else None}


def blink_report(wins, markers):
    """Compara el rechazo con la verdad de campo del emulador (marcadores 'blink' e 'inject:blink:on/off').

    wins: [(t_fin_ventana, resultado de Rejector)], markers: [(t, etiqueta)], ambos en segundos.
    Un segmento “tiene parpadeo” si se solapa con su núcleo (pico ± 2σ del parpadeo sintético: +0.05 a
    +0.25 s desde el marcador); los trenes inyectados se excluyen de la fracción de ventanas válidas.
    """
    blinks = np.array([t for t, m in markers if m == "blink"])
    trains, on = [], None
    for t, m in markers:
        if m == "inject:blink:on":
            on = t
        elif m == "inject:blink:off" and on is not None:
            trains.append((on, t + 0.4))
            on = None
    hit = miss = fp = tn = 0
    outside = []
    for end, r in wins:
        n = len(r["clean"])
        for k, c in enumerate(r["clean"]):
            e = end - (n - 1 - k) * SEG_STEP_S
            if len(blinks) and ((blinks + 0.05 < e) & (blinks + 0.25 > e - SEG_S)).any():
                hit, miss = hit + (not c), miss + c
            else:
                fp, tn = fp + (not c), tn + c
        if not any(a <= end and end - WIN_S <= b for a, b in trains):
            outside.append(r["valida"])
    return {"parpadeos": int(len(blinks)),
            "rechazo_con_parpadeo": hit / (hit + miss) if hit + miss else float("nan"),
            "rechazo_sin_parpadeo": fp / (fp + tn) if fp + tn else float("nan"),
            "validas": float(np.mean([r["valida"] for _, r in wins])),
            "validas_fuera_de_trenes": float(np.mean(outside)) if outside else float("nan"),
            "ventanas_senal_perdida": int(sum(r["perdida"] for _, r in wins))}


def open_run(source, cfg):
    d = os.path.join(HERE, "runs", time.strftime("%Y%m%d_%H%M%S") + "_" + source.replace(":", "-").replace(" ", "_"))
    os.makedirs(d)
    with open(os.path.join(d, "config.json"), "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
    return d


def main():
    p = argparse.ArgumentParser(description="Pipeline en tiempo real MIRAI (Pasos 2–4)")
    p.add_argument("--name", default="AURA")
    p.add_argument("--source-id", default=None,
                   help="prefijo del source_id: 'mirai-sim-' (emulador) o 'AuraLSL-' (Aura.exe); sin él se listan los candidatos")
    p.add_argument("--seconds", type=float, default=None, help="duración; por defecto hasta Ctrl+C")
    p.add_argument("--timeout", type=float, default=15.0)
    p.add_argument("--iaf", type=float, default=10.0, help="IAF para las bandas (la calibrará el Paso 5)")
    a = p.parse_args()

    inlet = pylsl.StreamInlet(find_stream(a.name, a.source_id, a.timeout), max_buflen=60,
                              processing_flags=pylsl.proc_clocksync | pylsl.proc_dejitter)
    info = inlet.info()
    fs, nch = info.nominal_srate(), info.channel_count()
    if fs <= 0 or nch != len(AURA_CHANNELS):
        sys.exit(f"Se esperaba EEG regular de {len(AURA_CHANNELS)} canales; llegó {nch} ch a {fs} Hz")
    labels, _ = channel_meta(info)
    if labels and [l.upper() for l in labels] != [c.upper() for c in AURA_CHANNELS]:
        print(f"[aviso] etiquetas del stream {labels} ≠ orden AURA {AURA_CHANNELS}; se usa el orden AURA")
    line = float(info.desc().child_value("line_freq") or 60.0)  # Aura.exe no la publica: red de México

    filt = CausalFilter(fs, line, nch)
    win, hop = int(round(WIN_S * fs)), int(round(HOP_S * fs))
    # Canales malos declarados por la fuente (el emulador los publica); el chequeo propio llega en el Paso 5.
    bads = [c for c in (info.desc().child_value("bad_channels") or "").split() if c in AURA_CHANNELS]
    rej = Rejector(fs, bads)
    feat = Features(fs, a.iaf)
    idx = {c: i for i, c in enumerate(AURA_CHANNELS)}
    front = [idx[c] for c in THETA_ROI if c not in bads]
    post = [idx[c] for c in ALPHA_ROI if c not in bads]
    cfg = {"paso": 4, "stream": info.name(), "source_id": info.source_id(), "host": info.hostname(),
           "fs": fs, "line_freq": line, "channels": AURA_CHANNELS, "labels_stream": labels,
           "window_s": WIN_S, "hop_s": HOP_S, "bandpass_hz": filt.band, "bandpass_order": 4,
           "notch": filt.notch, "lsl_api_cfg": os.environ.get("LSLAPICFG"),
           "rechazo": {"segmento_s": SEG_S, "paso_segmento_s": SEG_STEP_S, "ptp_uv": PTP_UV,
                       "canales_oculares": rej.ocular_chs, "canales_malos": bads,
                       "emg": f"{EMG_BAND[0]:.0f}-{EMG_BAND[1]:.0f} Hz, mu+3sigma de los primeros {CAL_S:.0f} s"
                       if rej.emg else "NA (fs < 100 Hz)", "senal_perdida_s": LOST_S},
           "features": {"iaf": a.iaf, "theta_hz": [a.iaf - 6, a.iaf - 2], "alpha_hz": [a.iaf - 2, a.iaf + 2],
                        "roi_theta": [AURA_CHANNELS[i] for i in front], "roi_alpha": [AURA_CHANNELS[i] for i in post],
                        "fit_range_hz": feat.fit_range, "r2_min": 0.75, "psd": "periodograma Hamming por segmento limpio"},
           "started": time.strftime("%Y-%m-%d %H:%M:%S")}
    run = open_run(info.desc().child_value("source") or info.source_id(), cfg)

    mk_inlet = find_markers(info)

    fw = open(os.path.join(run, "ventanas.csv"), "w", newline="")
    wv = csv.writer(fw)
    wv.writerow(["ventana", "ts_ultima_muestra", "t_emision", "latencia_ms", "calculo_ms", "rechazo_ms",
                 "segmentos_limpios", "n_limpios", "motivo", "valida", "senal_perdida", "emg_db",
                 "features_ms", "theta_per", "alpha_per", "theta_exp", "alpha_exp", "theta_r2", "alpha_r2",
                 "theta_ok", "alpha_ok"]
                + [f"rms_{c}" for c in AURA_CHANNELS])
    fe = open(os.path.join(run, "eventos.csv"), "w", newline="")
    we = csv.writer(fe)
    we.writerow(["ts", "fuente", "evento"])

    # calculo_ms (criterio del Paso 2) = desde que llega el bloque que cierra la ventana hasta que la ventana
    # está lista (filtrar ese bloque + cortarla). rechazo_ms = Paso 3, medido aparte. CPU total: Paso 7.
    state = {"k": 0, "t_chunk": 0.0}
    emit_t, calc_ms, rej_ms, feat_ms, lat_ms, wins, feats, markers = [], [], [], [], [], [], [], []
    seg, step = int(round(SEG_S * fs)), int(round(SEG_STEP_S * fs))

    def on_window(w, ts_last):
        # Paso 3: rechazo de artefactos. Paso 4: features con los segmentos limpios. Pasos 5–6 se enganchan aquí.
        t_ready = time.perf_counter()
        c = (t_ready - state["t_chunk"]) * 1000
        r = rej(w)
        t_rej = time.perf_counter()
        rj = (t_rej - t_ready) * 1000
        o = {}
        if r["valida"]:
            f, psd = window_psd(w, r["clean"], fs, seg, step)
            o = feat(f, psd, front, post)
        fm = (time.perf_counter() - t_rej) * 1000
        now = pylsl.local_clock()
        rms = w.std(axis=0)
        wv.writerow([state["k"], f"{ts_last:.4f}", f"{now:.4f}", f"{(now - ts_last) * 1000:.1f}", f"{c:.3f}", f"{rj:.3f}",
                     "".join("1" if x else "0" for x in r["clean"]), sum(r["clean"]), r["motivo"],
                     int(r["valida"]), int(r["perdida"]), "" if r["emg_db"] is None else f"{r['emg_db']:.2f}",
                     f"{fm:.2f}"]
                    + [f"{o[k]:.4f}" if k in o else "" for k in
                       ("theta_per", "alpha_per", "theta_exp", "alpha_exp", "theta_r2", "alpha_r2")]
                    + [int(o[k]) if k in o else "" for k in ("theta_ok", "alpha_ok")]
                    + [f"{v:.2f}" for v in rms])
        emit_t.append(now)
        calc_ms.append(c)
        rej_ms.append(rj)
        if o:
            feat_ms.append(fm)
            feats.append(o)
        lat_ms.append((now - ts_last) * 1000)
        wins.append((ts_last, r))
        state["k"] += 1
        if state["k"] % 10 == 0:
            fw.flush()
            ok = np.mean([x["valida"] for _, x in wins[-10:]])
            print(f"  ventana {state['k']:5d}  ts={ts_last:11.3f}  latencia={lat_ms[-1]:5.1f} ms  "
                  f"cálculo={c:5.2f} ms  limpios={''.join('1' if x else '0' for x in r['clean'])}  "
                  f"válidas(últ. 10)={ok:.0%}{'  SEÑAL PERDIDA' if r['perdida'] else ''}"
                  + (f"  θ_per={o['theta_per']:5.2f}  α_per={o['alpha_per']:5.2f} dB  features={fm:4.1f} ms" if o else ""))

    wnd = Windower(win, hop, nch, on_window)
    print(f"Pipeline: {info.name()} ({info.source_id()}) | {fs:.0f} Hz | red {line:.0f} Hz | "
          f"pasa-banda {filt.band[0]:.0f}–{filt.band[1]:.0f} Hz | notch {'sí' if filt.notch else 'no'} | "
          f"ventana {WIN_S:.0f} s / avance {HOP_S:.0f} s")
    print(f"Registro: {run}\nCtrl+C para detener.\n")

    t_start = pylsl.local_clock()
    try:
        while a.seconds is None or pylsl.local_clock() - t_start < a.seconds:
            # timeout=0: solo lo ya disponible. Con timeout > 0, pull_chunk espera a llenar max_samples
            # y entrega tandas de ese tamaño (con 0.2 s la latencia llegaba a ~200 ms).
            x, ts = inlet.pull_chunk(timeout=0.0, max_samples=int(fs))
            if ts:
                state["t_chunk"] = time.perf_counter()
                wnd.push(filt(np.asarray(x, dtype=np.float64)), ts)
            else:
                time.sleep(0.005)
            if mk_inlet:
                while True:
                    m, mts = mk_inlet.pull_sample(timeout=0.0)
                    if m is None:
                        break
                    we.writerow([f"{mts:.4f}", "marcador", m[0]])
                    markers.append((mts, m[0]))
    except KeyboardInterrupt:
        print("\nDetenido por el usuario.")
    fw.close()
    fe.close()

    if len(emit_t) < 2:
        sys.exit("Menos de 2 ventanas: no hay reporte.")
    d = np.diff(emit_t)
    rep = {"ventanas": len(emit_t), "intervalo_s_media": float(d.mean()), "intervalo_s_min": float(d.min()),
           "intervalo_s_max": float(d.max()), "calculo_ms_p95": float(np.percentile(calc_ms, 95)),
           "calculo_ms_max": float(max(calc_ms)), "rechazo_ms_p95": float(np.percentile(rej_ms, 95)),
           "rechazo_ms_max": float(max(rej_ms)), "latencia_ms_p95": float(np.percentile(lat_ms, 95))}
    # Criterio del Paso 2: una ventana cada 1.0 s ± 1 bloque (los bloques llegan cada ~20 ms; margen de 0.1 s)
    # y cálculo < 10 ms.
    checks = {"ventana cada 1.0 s ± 1 bloque": bool(abs(d.mean() - HOP_S) < 0.01 and np.abs(d - HOP_S).max() < 0.1),
              "cálculo búfer + filtros < 10 ms (máx.)": bool(rep["calculo_ms_max"] < 10)}
    rep3 = blink_report(wins, markers)
    if rep3["parpadeos"]:  # solo hay verdad de campo con el emulador
        checks["segmentos con parpadeo rechazados ≥ 95 %"] = rep3["rechazo_con_parpadeo"] >= 0.95
        checks["segmentos sin parpadeo rechazados < 5 %"] = rep3["rechazo_sin_parpadeo"] < 0.05
        checks[f"ventanas válidas fuera de trenes ≥ {VALID_MIN:.0%}"] = rep3["validas_fuera_de_trenes"] >= VALID_MIN
    rep4 = {}
    if feats:
        rep4 = {"features_ms_p95": float(np.percentile(feat_ms, 95)), "features_ms_p99": float(np.percentile(feat_ms, 99)), "features_ms_max": float(max(feat_ms)),
                **{f"{n}_validas": float(np.mean([x[f"{n}_ok"] for x in feats])) for n in ("theta", "alpha")},
                **{f"{k}_mediana": float(np.median([x[k] for x in feats if x[k.split('_')[0] + '_ok']] or [np.nan]))
                   for k in ("theta_per", "alpha_per", "theta_exp", "alpha_exp", "theta_r2", "alpha_r2")}}
        # Criterio redefinido 29 oct: el peor caso es determinista (ventanas con 1 segmento limpio, ajuste ~90 ms)
        # y el límite real es el avance de 1 s y la latencia de 500 ms del Paso 7.
        checks["Welch + specparam ≤ 100 ms (p99)"] = rep4["features_ms_p99"] <= 100
        checks["Welch + specparam ≤ 250 ms (máx.)"] = rep4["features_ms_max"] <= 250
    with open(os.path.join(run, "config.json"), "r+", encoding="utf-8") as f:
        c = json.load(f)
        c["reporte"] = {**rep, **rep3, **rep4, "emg_umbral_db": rej.emg_lim, "checks": checks}
        f.seek(0)
        json.dump(c, f, indent=2, ensure_ascii=False)
        f.truncate()

    print("\n============== REPORTE PASOS 2–4 ==============")
    print(f"Ventanas                : {rep['ventanas']}")
    print(f"Intervalo entre ventanas: media {rep['intervalo_s_media']:.4f} s | "
          f"mín {rep['intervalo_s_min']:.3f} | máx {rep['intervalo_s_max']:.3f}")
    print(f"Cálculo búfer + filtros : p95 {rep['calculo_ms_p95']:.3f} ms | máx {rep['calculo_ms_max']:.3f} ms")
    print(f"Rechazo (Paso 3)        : p95 {rep['rechazo_ms_p95']:.3f} ms | máx {rep['rechazo_ms_max']:.3f} ms")
    print(f"Latencia (emisión − última muestra): p95 {rep['latencia_ms_p95']:.1f} ms")
    print(f"Ventanas válidas        : {rep3['validas']:.1%} (fuera de trenes inyectados: "
          f"{rep3['validas_fuera_de_trenes']:.1%}) | señal perdida en {rep3['ventanas_senal_perdida']} ventanas")
    if rep3["parpadeos"]:
        print(f"Parpadeos (marcadores)  : {rep3['parpadeos']} | segmentos con parpadeo rechazados "
              f"{rep3['rechazo_con_parpadeo']:.1%} | sin parpadeo rechazados {rep3['rechazo_sin_parpadeo']:.1%}")
    print(f"Umbral EMG              : {'NA' if rej.emg_lim is None else f'{rej.emg_lim:.1f} dB'}")
    if rep4:
        print(f"Features (Paso 4)       : Welch + specparam p95 {rep4['features_ms_p95']:.1f} ms | p99 {rep4['features_ms_p99']:.1f} ms | máx {rep4['features_ms_max']:.1f} ms"
              f" | R² ≥ 0.75 en θ {rep4['theta_validas']:.1%}, α {rep4['alpha_validas']:.1%}")
        print(f"                          mediana θ_per {rep4['theta_per_mediana']:.2f} dB, α_per {rep4['alpha_per_mediana']:.2f} dB, "
              f"χ front {rep4['theta_exp_mediana']:.2f}, χ post {rep4['alpha_exp_mediana']:.2f} (IAF {a.iaf:g} Hz)")
    for k, ok in checks.items():
        print(f"  [{'OK' if ok else 'FALLA'}] {k}")
    print(f"\nRESULTADO: {'PASA' if all(checks.values()) else 'NO PASA'}  (registro en {run})")
    sys.exit(0 if all(checks.values()) else 1)


if __name__ == "__main__":
    main()
