"""
replay_offline.py · VERSIÓN B — Pasos 2–3 sobre un archivo real, sin LSL ni tiempo real (base del --offline del Paso 7).

Lee el archivo con los mismos lectores del emulador (load_file / load_aura_csv), lo pasa en bloques de 20 ms
por CausalFilter → Windower → Rejector y compara el rechazo con dos referencias de parpadeo:
  * eye-tracker (ds007537, BIDS beh/*cyclopean*): tramos de 60–500 ms sin pupila, alineados por el primer TTL.
    Las ventanas con > 20 % de pupila perdida (mirando el teléfono) no se evalúan, como en h1_ds007537.py.
  * detector EEG offline (misma lógica que h1_ds007537.detect_blinks, solo con Fp1): para datasets sin ET.

Uso:
  python replay_offline.py --source <ds007537>/sub-01/eeg/sub-01_task-phoneuse_eeg.vhdr
  python replay_offline.py --source <EEG-SVRec>/EEG/01_data.cnt --ref M1,M2 --line-freq 50 --start 60 --duration 1800
  python replay_offline.py --source <ds007537>/sub-01/eeg/sub-01_task-phoneuse_eeg.vhdr --equivalencia   # Paso 4
"""
import argparse
import json
import os
import sys
import time

import numpy as np
from scipy import signal

from mock_lsl_streamer import AURA_CHANNELS, FS_OUT, load_aura_csv, load_file
from realtime_pipeline import (ALPHA_ROI, HERE, PTP_UV, SEG_S, SEG_STEP_S, THETA_ROI, WIN_S, CausalFilter, Rejector,
                               Windower)

ET_MAX_MISSING = 0.20  # como h1_ds007537: con más pérdida de pupila el sujeto mira el teléfono


def eeg_blinks(fp1, fs):
    """Picos de parpadeo en Fp1 (1–10 Hz, prominencia > ½ mediana de los 20 mayores y > 3 MAD, ancho 40–500 ms).
    Misma lógica que h1_ds007537.detect_blinks, que promedia Fp1/Fp2; AURA solo tiene Fp1."""
    v = signal.sosfiltfilt(signal.butter(4, [1, 10], btype="band", fs=fs, output="sos"), fp1)
    mad = np.median(np.abs(v - np.median(v))) * 1.4826
    pk, pr = signal.find_peaks(v, prominence=3 * mad, distance=int(0.3 * fs), width=(int(0.04 * fs), int(0.5 * fs)))
    if not len(pk):
        return np.array([])
    return pk[pr["prominences"] > 0.5 * np.median(np.sort(pr["prominences"])[-20:])] / fs


def et_blinks(vhdr):
    """(intervalos de parpadeo [inicio, fin] s, tiempos ET s, pupila perdida bool) en el tiempo del EEG, o None."""
    sys.path.insert(0, os.path.join(HERE, "..", "datasets workflow", "ds007537"))
    import h1_ds007537 as h1
    eeg_dir = os.path.dirname(vhdr)
    sub = os.path.basename(os.path.dirname(eeg_dir))
    events = os.path.join(eeg_dir, f"{sub}_task-phoneuse_events.tsv")
    if not os.path.exists(events):
        return None
    et = h1.eyetrack(os.path.dirname(os.path.dirname(eeg_dir)), sub, h1.markers(events))
    if et is None:
        return None
    t, pupil = et
    miss = np.isnan(pupil)
    d = np.diff(np.r_[0, miss.astype(int), 0])
    on, off = np.where(d == 1)[0], np.where(d == -1)[0]
    keep = ((off - on) >= h1.BLINK_SAMPLES[0]) & ((off - on) <= h1.BLINK_SAMPLES[1])
    return np.c_[t[on[keep]], t[off[keep] - 1]], t, miss


def score(wins, intervals, valid_win=None):
    """Rechazo de segmentos con / sin parpadeo. intervals: [[ini, fin]] s; valid_win(fin) → si se evalúa."""
    hit = miss = fp = tn = 0
    for end, r in wins:
        if valid_win is not None and not valid_win(end):
            continue
        n = len(r["clean"])
        for k, c in enumerate(r["clean"]):
            e = end - (n - 1 - k) * SEG_STEP_S
            if ((intervals[:, 0] < e) & (intervals[:, 1] > e - SEG_S)).any():
                hit, miss = hit + (not c), miss + c
            else:
                fp, tn = fp + (not c), tn + c
    return {"segmentos_con_parpadeo": hit + miss, "rechazo_con_parpadeo": hit / max(hit + miss, 1),
            "segmentos_sin_parpadeo": fp + tn, "rechazo_sin_parpadeo": fp / max(fp + tn, 1)}


def equivalence(x, fs, line, bads, t, vhdr):
    """Paso 4: features por minuto del pipeline en tiempo real frente a h1_por_minuto.csv (ds007537).

    Se guardan los segmentos limpios únicos (cada segmento aparece en varias ventanas solapadas) y se agrupan
    como el offline: minutos de teléfono desde phone_on y un bloque de video; IAF del sujeto en el offline."""
    import pandas as pd
    from spectral_features import Features
    import h1_ds007537 as h1  # ya en sys.path por spectral_features
    eeg_dir = os.path.dirname(vhdr)
    sub = os.path.basename(os.path.dirname(eeg_dir))
    m = h1.markers(os.path.join(eeg_dir, f"{sub}_task-phoneuse_events.tsv"))
    ref = pd.read_csv(os.path.join(HERE, "..", "datasets workflow", "ds007537", "results", "h1_por_minuto.csv"))
    ref = ref[ref["sub"] == sub]
    iaf = float(ref["iaf"].iloc[0])
    seg = int(round(SEG_S * fs))
    segs = {}  # fin del segmento (s) → periodograma Hamming (canales, frecuencias)

    rej = Rejector(fs, bads)

    def on(w, tt):
        r = rej(w)
        n = len(r["clean"])
        for k, c in enumerate(r["clean"]):
            e = round(float(tt) - (n - 1 - k) * SEG_STEP_S, 3)
            if c and e not in segs:
                s0 = len(w) - seg - (n - 1 - k) * int(round(SEG_STEP_S * fs))
                segs[e] = signal.periodogram(w[s0:s0 + seg].T, fs, window="hamming", axis=1)
    filt = CausalFilter(fs, line, x.shape[1])
    wnd = Windower(int(round(WIN_S * fs)), int(round(fs)), x.shape[1], on)
    blk = max(1, int(0.02 * fs))
    for i in range(0, len(x), blk):
        wnd.push(filt(x[i:i + blk]), t[i:i + blk])

    feat = Features(fs, iaf)
    front = [AURA_CHANNELS.index(c) for c in THETA_ROI if c not in bads]
    post = [AURA_CHANNELS.index(c) for c in ALPHA_ROI if c not in bads]
    ends = np.array(sorted(segs))
    rows = []
    for _, r in ref.iterrows():
        if r["cond"] == "phone":
            t0 = m["phone_on"] + 60 * r["minute"]
            t1 = min(t0 + 60, m["phone_off"])
        else:
            t0, t1 = m["video_on"], m["video_off"]
        sel = ends[(ends - SEG_S >= t0) & (ends <= t1)]
        if not len(sel):
            continue
        f = segs[sel[0]][0]
        psd = np.mean([segs[e][1] for e in sel], axis=0)
        o = feat(f, psd, front, post)
        rows.append({"cond": r["cond"], "minuto": int(r["minute"]), "segmentos": len(sel),
                     "alpha_off": r["alpha_per"], "alpha_rt": o["alpha_per"],
                     "theta_off": r["theta_per"], "theta_rt": o["theta_per"],
                     "chi_post_off": r["exp_post"], "chi_post_rt": o["alpha_exp"],
                     "r2_post_rt": o["alpha_r2"], "r2_front_rt": o["theta_r2"]})
    df = pd.DataFrame(rows)
    print(f"\n====== EQUIVALENCIA PASO 4 · {sub} · IAF {iaf:g} Hz (offline: ROI Fz/FCz y Pz/POz/O1/O2, ICA) ======")
    print(df.round(3).to_string(index=False))
    res = {"sujeto": sub, "iaf": iaf, "minutos": len(df)}
    for k in ("alpha", "theta", "chi_post"):
        a, b = df[f"{k}_off"], df[f"{k}_rt"]
        res[k] = {"r": float(np.corrcoef(a, b)[0, 1]), "sesgo_medio_db": float((b - a).mean()),
                  "rango_offline": [float(a.min()), float(a.max())]}
        print(f"{k:9s}: r = {res[k]['r']:.3f} | sesgo medio (RT − offline) = {res[k]['sesgo_medio_db']:+.3f} | "
              f"rango offline {a.min():.2f} – {a.max():.2f}")
    ok = res["alpha"]["r"] >= 0.8 and abs(res["alpha"]["sesgo_medio_db"]) < 0.5
    print(f"Criterio (alfa_per r ≥ 0.8 y |sesgo| < 0.5 dB): {'PASA' if ok else 'NO PASA'}")
    run = os.path.join(HERE, "runs", time.strftime("%Y%m%d_%H%M%S") + f"_equivalencia_{sub}")
    os.makedirs(run)
    df.to_csv(os.path.join(run, "minutos.csv"), index=False)
    with open(os.path.join(run, "reporte.json"), "w", encoding="utf-8") as fh:
        json.dump({**res, "pasa": ok}, fh, indent=2, ensure_ascii=False)
    print(f"Reporte: {run}")


def main():
    p = argparse.ArgumentParser(description="Replay offline de los Pasos 2–3 sobre un archivo real")
    p.add_argument("--source", required=True)
    p.add_argument("--start", type=float, default=0.0)
    p.add_argument("--duration", type=float, default=None)
    p.add_argument("--ref", default="average")
    p.add_argument("--line-freq", type=float, default=None)
    p.add_argument("--fs", type=float, default=None, help="por defecto 250 (CSV de AURA: su fs nativa)")
    p.add_argument("--ocular-uv", type=float, nargs="+", default=[PTP_UV],
                   help="umbral(es) pico a pico del canal ocular a comparar (µV); las ROI siempre usan 150")
    p.add_argument("--sin-emg", action="store_true", help="desactiva el veto EMG (para separar su efecto)")
    p.add_argument("--equivalencia", action="store_true",
                   help="Paso 4: compara features por minuto con h1_por_minuto.csv (solo ds007537)")
    a = p.parse_args()

    t0 = time.time()
    if a.source.lower().endswith(".csv"):
        data, events, bads, fs = load_aura_csv(a.source, a.start, a.duration, a.fs)
        line = a.line_freq or 60.0
    else:
        fs = a.fs or FS_OUT
        data, events, lf, bads = load_file(a.source, a.start, a.duration, a.ref, fs)
        line = a.line_freq or lf or 50.0
    x = data.T.astype(np.float64)
    print(f"Cargado en {time.time() - t0:.0f} s: {x.shape[0] / fs / 60:.1f} min a {fs:.0f} Hz | red {line:.0f} Hz | "
          f"canales malos: {bads or 'ninguno'}")

    t = a.start + np.arange(len(x)) / fs  # tiempo del registro original (el del ET y los eventos)
    if a.equivalencia:
        return equivalence(x, fs, line, bads, t, a.source)
    eb = eeg_blinks(x[:, AURA_CHANNELS.index("Fp1")], fs) + a.start
    et = et_blinks(a.source) if a.source.lower().endswith(".vhdr") else None
    run = os.path.join(HERE, "runs", time.strftime("%Y%m%d_%H%M%S") + "_offline_" + os.path.basename(a.source))
    os.makedirs(run)
    reps = []
    for ocular_uv in a.ocular_uv:
        filt, rej, wins = CausalFilter(fs, line, x.shape[1]), Rejector(fs, bads, ocular_uv), []
        rej.emg = rej.emg and not a.sin_emg
        wnd = Windower(int(round(WIN_S * fs)), int(round(fs)), x.shape[1], lambda v, tt: wins.append((tt, rej(v))))
        blk = max(1, int(0.02 * fs))
        t1 = time.perf_counter()
        for i in range(0, len(x), blk):
            wnd.push(filt(x[i:i + blk]), t[i:i + blk])
        proc_ms = (time.perf_counter() - t1) * 1000 / max(len(wins), 1)

        motivos = {}
        for _, r in wins:
            for k in r["motivo"].split("+") if r["motivo"] else ["(ninguno)"]:
                motivos[k] = motivos.get(k, 0) + 1
        rep = {"fuente": os.path.basename(a.source), "inicio_s": a.start, "min": round(x.shape[0] / fs / 60, 1),
               "fs": fs, "ref": a.ref, "canales_malos": bads, "canales_oculares": rej.ocular_chs,
               "umbral_ocular_uv": ocular_uv, "umbral_roi_uv": PTP_UV, "ventanas": len(wins),
               "ventanas_validas": float(np.mean([r["valida"] for _, r in wins])),
               "segmentos_limpios": float(np.mean([np.mean(r["clean"]) for _, r in wins])),
               "ventanas_senal_perdida": int(sum(r["perdida"] for _, r in wins)),
               "motivos_por_ventana": motivos, "emg_umbral_db": rej.emg_lim, "ms_por_ventana": round(proc_ms, 2),
               "detector_eeg": {"parpadeos_min": round(len(eb) / (x.shape[0] / fs / 60), 1),
                                **score(wins, np.c_[eb - 0.1, eb + 0.1])}}  # pico ± 100 ms
        if et is not None:
            iv, et_t, et_miss = et

            def et_ok(end):  # ventana evaluable: ET presente y con poca pupila perdida
                s = (et_t >= end - WIN_S) & (et_t < end)
                return s.sum() > 0.5 * WIN_S * 100 and et_miss[s].mean() <= ET_MAX_MISSING
            span = (et_t >= a.start) & (et_t <= t[-1])
            rep["eye_tracker"] = {"ventanas_evaluables": int(sum(et_ok(e) for e, _ in wins)),
                                  "parpadeos_min": round(((iv[:, 0] >= a.start) & (iv[:, 0] <= t[-1])).sum()
                                                         / (span.sum() / 100 / 60), 1),
                                  **score(wins, iv, et_ok)}
        reps.append(rep)

        print(f"\n====== REPLAY OFFLINE · PASOS 2–3 · umbral ocular {ocular_uv:.0f} µV (ROI {PTP_UV:.0f} µV) ======")
        print(f"Ventanas              : {rep['ventanas']} ({rep['min']} min) | {rep['ms_por_ventana']} ms de cálculo por ventana")
        print(f"Ventanas válidas      : {rep['ventanas_validas']:.1%} | segmentos limpios {rep['segmentos_limpios']:.1%} | "
              f"señal perdida en {rep['ventanas_senal_perdida']} ventanas")
        print(f"Motivos (por ventana) : {motivos}")
        print(f"Umbral EMG            : {'NA' if rej.emg_lim is None else f'{rej.emg_lim:.1f} dB'} | ocular en {rej.ocular_chs}")
        for k in ("eye_tracker", "detector_eeg"):
            if k in rep:
                r = rep[k]
                extra = f" | ventanas evaluables {r['ventanas_evaluables']}" if k == "eye_tracker" else ""
                print(f"Ref. {k:<17}: {r['parpadeos_min']} parpadeos/min | segmentos con parpadeo rechazados "
                      f"{r['rechazo_con_parpadeo']:.1%} (n={r['segmentos_con_parpadeo']}) | sin parpadeo rechazados "
                      f"{r['rechazo_sin_parpadeo']:.1%} (n={r['segmentos_sin_parpadeo']}){extra}")
    with open(os.path.join(run, "reporte.json"), "w", encoding="utf-8") as f:
        json.dump(reps, f, indent=2, ensure_ascii=False)
    print(f"\nReporte: {run}")


if __name__ == "__main__":
    main()
