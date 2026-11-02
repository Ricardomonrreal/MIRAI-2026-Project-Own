"""
realtime_pipeline.py — Pasos 2 a 7 del Protocolo de Simulación (MIRAI 2026) · VERSIÓN B

Versión B: (1) el Paso 3 se evalúa sobre los segmentos que contienen el pico de un parpadeo supraumbral
(blink_report); (2) sin veto EMG: la potencia 25–40 Hz se mide y se registra (emg_db) pero no descarta
segmentos; (3) specparam ajusta en 2–30 Hz (spectral_features.py), lo que deja fuera la mayor parte del EMG.

Recibe el EEG por LSL (emulador o AURA real), lo filtra en línea, entrega una ventana cada 1 s, marca qué
segmentos de 2 s están libres de artefactos (Fp1/ROI > 150 µV, EMG) y calcula theta_per / alfa_per con esos
segmentos (spectral_features.py). Paso 5 (calibration.py): chequeo de calidad en los primeros 10 s, calibración
congelada (μ, σ, IAF) y Z por ventana. Paso 6 (jitai.py): escalera de intervención; salida por LSL `MIRAI_JITAI`,
UDP/JSON local para la AR, consola y eventos.csv; el Nivel 2 escucha el stream de conducta `MIRAI_Behavior`.
Paso 7: `--offline <fuente>` pasa un archivo por el mismo código sin LSL (bloques de 20 ms, sin esperar); el reporte
añade CPU, memoria y deriva, y se guarda también en runs/<sesión>/reporte.md.
Contador de parpadeos (2 nov): Fp1 crudo a 1–10 Hz, umbral móvil recalculado cada 7 min (BlinkCounter); tasa en vivo en
ventanas.csv (parpadeos_min), parpadeos y umbrales en eventos.csv y, en el reporte, la tasa por bloque: marcadores
`bloque:<nombre>` del stream de conducta (p. ej. reposo / scroll) o fases del CSV de AURA.

  * Stream elegido por nombre + source_id con el entorno LSL cerrado a esta PC (lsl_api.cfg).
  * Todo en segundos: fs y red se leen del stream (250 Hz emulador, 250/50 Hz AURA).
  * Filtro causal con estado entre bloques: pasa-banda 1 Hz – min(40, 0.8·fs/2) + notch si cabe bajo Nyquist.
  * Las ventanas se cortan en múltiplos exactos del avance, aunque los bloques LSL lleguen de tamaños variables.
  * Registro por sesión en runs/<AAAAMMDD_HHMMSS>_<fuente>/: config.json, ventanas.csv, eventos.csv.

Uso:
  python realtime_pipeline.py --name AURA --source-id mirai-sim- --seconds 600   # emulador
  python realtime_pipeline.py --name AURA --source-id AuraLSL-                   # AURA real (Aura.exe de esta PC)
  python behavior_markers.py 0 bloque:reposo 420 bloque:scroll 840 bloque:reposo # antes: bloques de parpadeo (7 min)
  python realtime_pipeline.py --offline synthetic --duration 600 --inject alpha 300 30 25   # replay sin LSL
  python realtime_pipeline.py --offline ../../AURA/data/eeg_data_20260122_123839.csv --sin-fases
"""
import argparse
import bisect
import csv
import json
import os
import socket
import sys
import time

import numpy as np
from scipy import signal, stats

from check_lsl_stream import channel_meta, find_markers, find_stream  # fija LSLAPICFG antes de importar pylsl
from mock_lsl_streamer import AURA_CHANNELS, load_source
import calibration as cal
import jitai
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
EMG_VETO = False  # versión B: el EMG solo se mide (emg_db); la versión A descarta segmentos > μ + 3σ
LOST_S = 5.0  # más segundos seguidos sin ventanas válidas = señal perdida
VALID_MIN = 0.90  # criterio del Paso 3: fracción de ventanas válidas con ~15 parpadeos/min
BLINK_BAND = (1.0, 10.0)  # contador de parpadeos en Fp1: banda de h1_ds007537.detect_blinks
BLINK_PERIOD_S = 420.0  # umbral móvil (2 nov): cada 7 min se recalcula con los datos de esos 7 min
BLINK_EDGE_S = 2.0  # espera tras un tramo: su último pico (≤ 0.5 s) completo y lejos del borde del filtro sin desfase
BLINK_CTX_S = 5.0  # Fp1 que se conserva antes de cada tramo (contexto del filtro y de find_peaks)
HERE =os.path.dirname(os.path.abspath(__file__))


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
            if EMG_VETO and self.emg_lim is not None and e > self.emg_lim:
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


def blink_gain(fs, line):
    """Ganancia pico a pico del filtro sobre el parpadeo sintético (pico gaussiano de σ = 50 ms en 0.4 s)."""
    w = np.arange(int(0.4 * fs)) / fs
    x = np.zeros(int(4.4 * fs))
    x[int(2 * fs):int(2 * fs) + len(w)] = np.exp(-0.5 * ((w - 0.15) / 0.05) ** 2)
    return float(np.ptp(CausalFilter(fs, line, 1)(x[:, None])))


def blink_report(wins, markers, gain):
    """Versión B: compara el rechazo con la verdad de campo del emulador B ('blink:<µV>', 'inject:blink:on/off').

    Un parpadeo es supraumbral si su amplitud en Fp1 × `gain` (ganancia pico a pico del filtro) ≥ PTP_UV.
    Criterio: rechazo de los segmentos que CONTIENEN EL PICO (+0.15 s desde el marcador) de un parpadeo
    supraumbral. Los segmentos que solo rozan el núcleo (pico ± 2σ: +0.05 a +0.25 s) sin contener el pico, o que
    solo tocan parpadeos subumbral, se reportan aparte: llevan contaminación parcial pero no cuentan ni como
    aciertos ni como falsos rechazos. Los trenes inyectados se excluyen de la fracción de ventanas válidas.
    """
    blinks = [(t, float(m.split(":")[1]) if ":" in m else float("inf")) for t, m in markers
              if m == "blink" or m.startswith("blink:")]
    t_all = np.array([t for t, _ in blinks])
    supra = np.array([amp * gain >= PTP_UV for _, amp in blinks], dtype=bool)
    trains, on = [], None
    for t, m in markers:
        if m == "inject:blink:on":
            on = t
        elif m == "inject:blink:off" and on is not None:
            trains.append((on, t + 0.4))
            on = None
    hit = miss = fp = tn = sub_rej = sub_n = 0
    outside = []
    for end, r in wins:
        n = len(r["clean"])
        for k, c in enumerate(r["clean"]):
            e = end - (n - 1 - k) * SEG_STEP_S
            ov = (t_all + 0.05 < e) & (t_all + 0.25 > e - SEG_S) if len(t_all) else np.zeros(0, bool)
            pk = (t_all + 0.15 >= e - SEG_S) & (t_all + 0.15 <= e) if len(t_all) else np.zeros(0, bool)
            if (ov & pk & supra).any():
                hit, miss = hit + (not c), miss + c
            elif ov.any():
                sub_rej, sub_n = sub_rej + (not c), sub_n + 1
            else:
                fp, tn = fp + (not c), tn + c
        if not any(a <= end and end - WIN_S <= b for a, b in trains):
            outside.append(r["valida"])
    return {"parpadeos": int(len(blinks)), "parpadeos_supraumbral": int(supra.sum()),
            "parpadeos_subumbral": int((~supra).sum()), "ganancia_filtro": gain,
            "amplitud_minima_detectable_uv": PTP_UV / gain,
            "rechazo_con_parpadeo": hit / (hit + miss) if hit + miss else float("nan"),
            "rechazo_parcial": sub_rej / sub_n if sub_n else float("nan"),
            "segmentos_parciales": sub_n,
            "rechazo_sin_parpadeo": fp / (fp + tn) if fp + tn else float("nan"),
            "validas": float(np.mean([r["valida"] for _, r in wins])),
            "validas_fuera_de_trenes": float(np.mean(outside)) if outside else float("nan"),
            "ventanas_senal_perdida": int(sum(r["perdida"] for _, r in wins))}


def blink_peaks(y, fs, thr=None):
    """Parpadeos en Fp1 ya filtrado a 1–10 Hz, con la lógica de h1_ds007537.detect_blinks: picos de 40–500 ms de
    ancho, separados ≥ 0.3 s, con prominencia ≥ umbral. Sin `thr`, el umbral sale del propio tramo:
    máx(3 MAD, ½ mediana de las 20 prominencias mayores). Devuelve (índices, prominencias en µV, umbral)."""
    mad = np.median(np.abs(y - np.median(y))) * 1.4826
    pk, pr = signal.find_peaks(y, prominence=3 * mad if thr is None else thr, distance=max(1, int(0.3 * fs)),
                               width=(int(0.04 * fs), int(0.5 * fs)))
    p = pr["prominences"]
    if thr is None:
        thr = max(3 * mad, 0.5 * float(np.median(np.sort(p)[-20:]))) if len(p) else 3 * mad
    return pk[p >= thr], p[p >= thr], float(thr)


class BlinkCounter:
    """Contador de parpadeos en Fp1 (2 nov): blink_peaks() con umbral móvil sobre Fp1 crudo guardado en un búfer. Cada
    tramo se filtra a 1–10 Hz SIN desfase (sosfiltfilt) al analizarlo: el filtro causal deformaba el parpadeo (su
    lóbulo negativo superaba al pico) y la prominencia dejaba de servir (recall 14 % en el sintético).

      * Definitivo: cada `period_s` s (7 min) el período que acaba de cerrar se cuenta con su PROPIO umbral, calculado
        solo con ese período, igual que replay_offline.eeg_blinks sobre ese tramo. Va a eventos.csv y al reporte; es
        el que sirve para comparar bloques.
      * En vivo (provisional, consola y ventanas.csv): cada segundo, con el umbral del período anterior; el primero
        sale de los primeros `init_s` s. Si dentro del período cambia la amplitud (p. ej. mirar el teléfono), se desvía.
    """

    def __init__(self, fs, period_s=None, init_s=None):
        self.sos = signal.butter(4, BLINK_BAND, btype="band", fs=fs, output="sos")
        self.fs, self.period, self.init = fs, period_s or BLINK_PERIOD_S, init_s or CAL_S
        cap = int((self.period + BLINK_CTX_S + BLINK_EDGE_S + 3) * fs)  # período + contexto + espera + un bloque ≤ 1 s
        self.x, self.t, self.n = np.empty(cap), np.empty(cap), 0
        self.t0 = self.thr = self.live_cut = None
        self.live, self.blinks, self.periods = [], [], []  # t en vivo; (t, prominencia) definitivos; resumen por período

    def _detect(self, lo, thr=None, t_lo=-np.inf, t_hi=np.inf):
        """Parpadeos (t, prominencia) en [t_lo, t_hi) del búfer desde `lo`, filtrado entero (el resto es contexto para
        el filtro y find_peaks). Sin `thr`, el umbral sale de [t_lo, t_hi). Devuelve (parpadeos, umbral)."""
        y, t = signal.sosfiltfilt(self.sos, self.x[lo:self.n]), self.t[lo:self.n]
        if thr is None:
            thr = blink_peaks(y[(t >= t_lo) & (t < t_hi)], self.fs)[2]
        pk, pr, _ = blink_peaks(y, self.fs, thr)
        return [(float(a), float(b)) for a, b in zip(t[pk], pr) if t_lo <= a < t_hi], thr

    def push(self, x, ts):
        """x: Fp1 crudo (µV) del bloque; ts: sus marcas de tiempo. Devuelve los parpadeos definitivos del período
        que se cierra con este bloque, o None si no se cerró ninguno."""
        self.t0 = ts[0] if self.t0 is None else self.t0
        self.x[self.n:self.n + len(x)], self.t[self.n:self.n + len(x)] = x, ts
        self.n += len(x)
        new, start = None, self.t0 + len(self.periods) * self.period
        if ts[-1] >= start + self.period + BLINK_EDGE_S:
            new = self._close(start, start + self.period, own=True)
        if self.thr is None and ts[-1] - self.t0 >= self.init:
            self.thr = self._detect(0)[1]
        cut = ts[-1] - BLINK_EDGE_S
        if self.thr is not None and (self.live_cut is None or cut - self.live_cut >= HOP_S):
            # 1.ª vez desde el inicio; después, el último tramo con contexto a ambos lados.
            lo = 0 if self.live_cut is None else max(0, self.n - int((BLINK_CTX_S + BLINK_EDGE_S + HOP_S) * self.fs))
            for tp, _ in self._detect(lo, self.thr)[0]:
                if (self.live_cut is None or tp > self.live_cut) and tp <= cut and (not self.live or tp - self.live[-1] >= 0.3):
                    self.live.append(tp)
            self.live_cut = cut
        return new

    def _close(self, start, end, own):
        new, thr = self._detect(0, None if own or self.thr is None else self.thr, start, end)
        self.blinks += new
        self.periods.append({"inicio": float(start), "fin": float(end), "umbral_uv": thr, "parpadeos": len(new),
                             "umbral_propio": bool(own or self.thr is None)})
        self.thr = thr  # el conteo en vivo del período siguiente usa este umbral
        keep = self.t[:self.n] >= end - BLINK_CTX_S  # contexto del período siguiente
        m = int(keep.sum())
        self.x[:m], self.t[:m] = self.x[:self.n][keep], self.t[:self.n][keep]
        self.n = m
        return new

    def finish(self):
        """Cierra el último período: con su propio umbral si dura ≥ init_s; si no, con el del período anterior."""
        if not self.n or self.t0 is None:
            return None
        start, end = self.t0 + len(self.periods) * self.period, self.t[self.n - 1] + 1 / self.fs
        return self._close(start, end, own=end - start >= self.init) if end > start else None

    def rate(self, t):
        """Parpadeos en vivo de los últimos 60 s (provisional); None hasta tener umbral y 60 s de registro."""
        if self.live_cut is None or t - self.t0 < 60:
            return None
        return bisect.bisect_right(self.live, t) - bisect.bisect_right(self.live, t - 60)


def blink_match(det, true, lag=0.15, tol=0.25):
    """(recall, precisión) de los parpadeos detectados frente a la verdad de campo del emulador: el marcador va al
    inicio del parpadeo y el pico llega `lag` s después."""
    det, true = np.asarray(det, float), np.asarray(true, float) + lag
    if not len(det) or not len(true):
        return float("nan"), float("nan")
    d = np.abs(true[:, None] - det[None, :])
    return float((d.min(axis=1) <= tol).mean()), float((d.min(axis=0) <= tol).mean())


def blink_blocks(blinks, blocks, t_ini, t_fin):
    """Tasa de parpadeo por bloque (marcadores `bloque:<nombre>` o fases del CSV de AURA), uniendo los tramos del mismo
    nombre. Referencia: el primer bloque con ≥ 2 minutos completos; cada otro bloque se compara con ella por la razón
    de tasas y con Mann-Whitney sobre los conteos de cada minuto completo."""
    tb = np.array([t for t, _ in blinks], float)
    out = {}
    for i, (t0, nm) in enumerate(blocks):
        t0, t1 = max(t0, t_ini), min(blocks[i + 1][0] if i + 1 < len(blocks) else t_fin, t_fin)
        if t1 <= t0:
            continue
        d = out.setdefault(nm, {"dur_s": 0.0, "parpadeos": 0, "por_minuto": []})
        d["dur_s"] += float(t1 - t0)
        d["parpadeos"] += int(((tb >= t0) & (tb < t1)).sum())
        d["por_minuto"] += [int(((tb >= s) & (tb < s + 60)).sum()) for s in np.arange(t0, t1 - 60 + 1e-9, 60)]
    for d in out.values():
        d["tasa_min"] = d["parpadeos"] / (d["dur_s"] / 60)
    base = next((nm for nm, d in out.items() if len(d["por_minuto"]) >= 2), None)
    for nm, d in out.items():
        if base and nm != base and len(d["por_minuto"]) >= 2:
            b = out[base]
            d.update({"frente_a": base, "razon": d["tasa_min"] / b["tasa_min"] if b["tasa_min"] else None,
                      "p_mann_whitney": float(stats.mannwhitneyu(d["por_minuto"], b["por_minuto"]).pvalue)})
    return out


def open_run(source, cfg):
    d = os.path.join(HERE, "runs", time.strftime("%Y%m%d_%H%M%S") + "_" + source.replace(":", "-").replace(" ", "_"))
    os.makedirs(d)
    with open(os.path.join(d, "config.json"), "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
    return d


def write_report_md(run, cfg, rep, rep3, rep4, rep5, rep6, rep7, checks, repb=None):
    """Paso 7: reporte final de la sesión en runs/<sesión>/reporte.md."""
    f = lambda v, n=1: "—" if v is None else f"{v:.{n}f}"  # noqa: E731
    L = [f"# Reporte de sesión — {os.path.basename(run)}", "",
         f"- Modo: **{rep7['modo']}** · fuente `{cfg['source_id']}` · {cfg['fs']:.0f} Hz · red {cfg['line_freq']:.0f} Hz",
         f"- Ventanas: {rep['ventanas']} · válidas {rep3['validas']:.1%} (fuera de trenes inyectados "
         f"{rep3['validas_fuera_de_trenes']:.1%}) · señal perdida en {rep3['ventanas_senal_perdida']} ventanas", "",
         "## Tiempos y recursos", "", "| Métrica | Media | p95 | Máx. |", "|---|---|---|---|",
         f"| Procesamiento por ventana (ms) | {f(rep7['procesamiento_ms_media'])} | {f(rep7['procesamiento_ms_p95'])} | "
         f"{f(rep7['procesamiento_ms_max'])} |",
         f"| Welch + specparam (ms) | — | {f(rep4.get('features_ms_p95'))} | {f(rep4.get('features_ms_max'))} |"]
    if "latencia_ms_p95" in rep7:
        L.append(f"| Latencia emisión − última muestra (ms) | {f(rep7['latencia_ms_media'])} | {f(rep7['latencia_ms_p95'])} | "
                 f"{f(rep7['latencia_ms_max'])} |")
    L += ["", f"- CPU: {f(rep7.get('cpu_pct_nucleo'))} % de un núcleo · memoria {f(rep7.get('memoria_mb_inicio'), 0)} → "
          f"{f(rep7.get('memoria_mb_fin'), 0)} MB (pendiente 2.ª mitad {f(rep7.get('memoria_pendiente_mb_min'), 2)} MB/min)"
          + (f" · deriva {f(rep7.get('deriva_ppm'), 0)} ppm, latencia {f(rep7.get('latencia_pendiente_ms_min'), 2)} ms/min"
             if rep7["modo"] == "en vivo" else ""), ""]
    pr = rep5.get("parametros") or {}
    L += ["## Calibración (Paso 5)", "", f"- Estado: {rep5['estado']} {rep5['motivo']} · canales malos: "
          f"{', '.join(rep5['canales_malos']) or 'ninguno'}"]
    if pr:
        L.append(f"- {pr['fuente']} · IAF {pr['iaf']:g} Hz ({pr['iaf_de']})"
                 + (f" · Berger (potencia clásica) {pr['berger_db']:+.1f} dB" if "berger_db" in pr else ""))
        for n in ("theta", "alpha"):
            L.append(f"- {n}: μ {pr[n]['mu']:.2f} dB · σ_Z {pr[n]['sigma_z']:.3f} · RMS(Z) {f(rep5.get(f'z_{n}_rms'), 2)} "
                     f"(media {f(rep5.get(f'z_{n}_media'), 2)}, DE {f(rep5.get(f'z_{n}_sd'), 2)})")
    L += ["", "## JITAI (Paso 6)", "", f"- Activaciones: N1 {rep6['activaciones'][1]}, N2 {rep6['activaciones'][2]}, "
          f"N3 {rep6['activaciones'][3]}", "", "| t (s) | Nivel | Estado | Motivo |", "|---|---|---|---|"]
    t0 = rep6["eventos"][0]["ts"] if rep6["eventos"] else 0.0
    L += [f"| {e['ts']:.1f} | {e['nivel']} | {e['estado']} | {e['motivo']} |" for e in rep6["eventos"]]
    if rep7.get("fases"):
        L += ["", "## Fases del archivo", "", "| Fase | Inicio (s) | Ventanas | α_per (dB) | θ_per (dB) | N1 on (s) |",
              "|---|---|---|---|---|---|"]
        L += [f"| {x['fase']} | {x['inicio_s']:.1f} | {x['ventanas_con_features']} | {f(x['alpha_per_media'], 2)} | "
              f"{f(x['theta_per_media'], 2)} | {', '.join(f'{v:.1f}' for v in x['nivel1_on_s']) or '—'} |" for x in rep7["fases"]]
    if repb:
        t0b = repb["periodos"][0]["inicio"]
        L += ["", "## Parpadeos (Fp1)", "", f"- {repb['parpadeos']} parpadeos en {repb['minutos']:.1f} min "
              f"({repb['tasa_min']:.1f}/min) · umbral recalculado cada {cfg['parpadeos']['periodo_umbral_s'] / 60:g} min"
              + (f" · frente al emulador: recall {repb['recall']:.1%}, precisión {repb['precision']:.1%}" if "recall" in repb else ""),
              "", "| Período (min) | Umbral (µV) | Parpadeos | /min |", "|---|---|---|---|"]
        L += [f"| {(p_['inicio'] - t0b) / 60:.1f}–{(p_['fin'] - t0b) / 60:.1f} | {p_['umbral_uv']:.0f}"
              f"{'' if p_['umbral_propio'] else ' (anterior)'} | {p_['parpadeos']} | "
              f"{p_['parpadeos'] / ((p_['fin'] - p_['inicio']) / 60):.1f} |" for p_ in repb["periodos"]]
        if repb["bloques"]:
            L += ["", "| Bloque | Min | Parpadeos | /min | Frente a la referencia (minutos completos) |", "|---|---|---|---|---|"]
            L += [f"| {nm} | {d['dur_s'] / 60:.1f} | {d['parpadeos']} | {d['tasa_min']:.1f} | "
                  + (f"×{d['razon']:.2f} vs {d['frente_a']}, Mann-Whitney p = {d['p_mann_whitney']:.3f}"
                     if d.get("razon") is not None else "—") + " |" for nm, d in repb["bloques"].items()]
    L += ["", "## Criterios", ""] + [f"- [{'x' if ok else ' '}] {k}" for k, ok in checks.items()]
    L += ["", f"**Resultado: {'PASA' if all(checks.values()) else 'NO PASA'}**", ""]
    with open(os.path.join(run, "reporte.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L))


class OfflineInlet:
    """Sustituye al inlet de LSL en el replay sin LSL (Paso 7): entrega bloques de 20 ms tan rápido como se pidan,
    con la marca de tiempo de cada muestra (s desde el inicio del registro)."""

    def __init__(self, data, fs, block_s=0.02):
        self.x = np.ascontiguousarray(data.T, dtype=np.float64)
        self.fs, self.blk, self.ptr = fs, max(1, int(round(block_s * fs))), 0

    @property
    def done(self):
        return self.ptr >= len(self.x)

    def pull_chunk(self, timeout=0.0, max_samples=None):
        i, self.ptr = self.ptr, min(len(self.x), self.ptr + self.blk)
        return self.x[i:self.ptr], list(np.arange(i, self.ptr) / self.fs)


class OfflineMarkers:
    """Marcadores del archivo, entregados cuando el replay pasa por su muestra."""

    def __init__(self, events, fs, inlet):
        self.ev, self.fs, self.inlet, self.i = sorted(events), fs, inlet, 0

    def pull_sample(self, timeout=0.0):
        if self.i < len(self.ev) and self.ev[self.i][0] < self.inlet.ptr:
            s_, lab = self.ev[self.i]
            self.i += 1
            return [lab], s_ / self.fs
        return None, None


def mem_mb():
    """Working set del proceso en MB (Windows, sin dependencias externas); None en otros sistemas."""
    if os.name != "nt":
        return None
    import ctypes
    from ctypes import wintypes

    class PMC(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD)] + [
            (n, ctypes.c_size_t) for n in ("PeakWorkingSetSize", "WorkingSetSize", "QuotaPeakPagedPoolUsage",
                                           "QuotaPagedPoolUsage", "QuotaPeakNonPagedPoolUsage",
                                           "QuotaNonPagedPoolUsage", "PagefileUsage", "PeakPagefileUsage")]
    k32, psapi = ctypes.windll.kernel32, ctypes.windll.psapi
    k32.GetCurrentProcess.restype = wintypes.HANDLE
    psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(PMC), wintypes.DWORD]
    c = PMC()
    c.cb = ctypes.sizeof(c)
    psapi.GetProcessMemoryInfo(k32.GetCurrentProcess(), ctypes.byref(c), c.cb)
    return c.WorkingSetSize / 2 ** 20


def main():
    p = argparse.ArgumentParser(description="Pipeline en tiempo real MIRAI (Pasos 2–6)")
    p.add_argument("--name", default="AURA")
    p.add_argument("--source-id", default=None,
                   help="prefijo del source_id: 'mirai-sim-' (emulador) o 'AuraLSL-' (Aura.exe); sin él se listan los candidatos")
    p.add_argument("--seconds", type=float, default=None, help="duración; por defecto hasta Ctrl+C")
    p.add_argument("--timeout", type=float, default=15.0)
    p.add_argument("--iaf", type=float, default=10.0, help="IAF provisional hasta que la calibración (Paso 5) la fije")
    p.add_argument("--sigma-factor", type=float, default=1.0, help="factor de σ_suav (Paso 5; lo mide el Paso 7)")
    p.add_argument("--udp-port", type=int, default=5005, help="puerto UDP local de la AR (Paso 6)")
    p.add_argument("--sin-nivel2", action="store_true", help="desactiva el Nivel 2 (escenario H1 ✅ H2 ❌)")
    p.add_argument("--parpadeo-periodo", type=float, default=BLINK_PERIOD_S,
                   help="s entre recalibraciones del umbral de parpadeo (umbral móvil; 420 = 7 min)")
    g = p.add_argument_group("replay sin LSL (Paso 7)")
    g.add_argument("--offline", default=None, help="'synthetic', CSV de AURA o archivo EEG: se procesa sin LSL")
    g.add_argument("--fs", type=float, default=None)
    g.add_argument("--start", type=float, default=0.0)
    g.add_argument("--duration", type=float, default=None)
    g.add_argument("--ref", default="average")
    g.add_argument("--line-freq", type=float, default=None)
    g.add_argument("--seed", type=int, default=7)
    g.add_argument("--inject", nargs=4, action="append", default=[], metavar=("TIPO", "INICIO_S", "DUR_S", "AMP_UV"))
    g.add_argument("--sin-fases", action="store_true",
                   help="la calibración ignora los marcadores de fase (usa los primeros 90 s, Berger del Paso 7)")
    a = p.parse_args()

    offline = a.offline is not None
    if offline:
        specs = [(k_, float(t_), float(d_), float(v_)) for k_, t_, d_, v_ in a.inject]
        data, events, fs, line, meta = load_source(a.offline, a.fs, a.start, a.duration, a.ref, a.line_freq, a.iaf,
                                                   a.seed, specs)
        inlet = OfflineInlet(data, fs)
        mk_inlet = OfflineMarkers(events, fs, inlet)
        nch, labels = data.shape[0], list(AURA_CHANNELS)
        src = {"stream": "offline", "source_id": meta["source"], "host": socket.gethostname(), "source": meta["source"],
               "bad_channels": meta.get("bad_channels", "")}
    else:
        inlet = pylsl.StreamInlet(find_stream(a.name, a.source_id, a.timeout), max_buflen=60,
                                  processing_flags=pylsl.proc_clocksync | pylsl.proc_dejitter)
        info = inlet.info()
        fs, nch = info.nominal_srate(), info.channel_count()
        labels, _ = channel_meta(info)
        line = float(info.desc().child_value("line_freq") or 60.0)  # Aura.exe no la publica: red de México
        src = {"stream": info.name(), "source_id": info.source_id(), "host": info.hostname(),
               "source": info.desc().child_value("source") or info.source_id(),
               "bad_channels": info.desc().child_value("bad_channels") or ""}
    if fs <= 0 or nch != len(AURA_CHANNELS):
        sys.exit(f"Se esperaba EEG regular de {len(AURA_CHANNELS)} canales; llegó {nch} ch a {fs} Hz")
    if labels and [l.upper() for l in labels] != [c.upper() for c in AURA_CHANNELS]:
        print(f"[aviso] etiquetas del stream {labels} ≠ orden AURA {AURA_CHANNELS}; se usa el orden AURA")

    filt = CausalFilter(fs, line, nch)
    win, hop = int(round(WIN_S * fs)), int(round(HOP_S * fs))
    # Canales malos declarados por la fuente (el emulador los publica); el chequeo propio del Paso 5 se suma en
    # los primeros QC_S s y entonces se rehacen el rechazo y las ROI.
    bads = [c for c in src["bad_channels"].split() if c in AURA_CHANNELS]
    src_bads = list(bads)
    rej = Rejector(fs, bads)
    feat = Features(fs, a.iaf)
    idx = {c: i for i, c in enumerate(AURA_CHANNELS)}
    front = [idx[c] for c in THETA_ROI if c not in bads]
    post = [idx[c] for c in ALPHA_ROI if c not in bads]
    jcfg = jitai.CONFIG if not a.sin_nivel2 else {**jitai.CONFIG, "niveles": {**jitai.CONFIG["niveles"],
                                                    2: {**jitai.CONFIG["niveles"][2], "activo": False}}}
    jt = jitai.Jitai(jcfg, HOP_S)
    blk = BlinkCounter(fs, a.parpadeo_periodo) if "Fp1" not in bads else None
    cfg = {"paso": 7, "modo": "offline" if offline else "en vivo", "stream": src["stream"],
           "source_id": src["source_id"], "host": src["host"],
           "fs": fs, "line_freq": line, "channels": AURA_CHANNELS, "labels_stream": labels,
           "window_s": WIN_S, "hop_s": HOP_S, "bandpass_hz": filt.band, "bandpass_order": 4,
           "notch": filt.notch, "lsl_api_cfg": os.environ.get("LSLAPICFG"),
           "rechazo": {"segmento_s": SEG_S, "paso_segmento_s": SEG_STEP_S, "ptp_uv": PTP_UV,
                       "canales_oculares": rej.ocular_chs, "canales_malos": bads,
                       "emg": f"{EMG_BAND[0]:.0f}-{EMG_BAND[1]:.0f} Hz, " + (f"veto mu+3sigma de los primeros {CAL_S:.0f} s" if EMG_VETO else "solo medido (sin veto)")
                       if rej.emg else "NA (fs < 100 Hz)", "senal_perdida_s": LOST_S},
           "features": {"iaf": a.iaf, "theta_hz": [a.iaf - 6, a.iaf - 2], "alpha_hz": [a.iaf - 2, a.iaf + 2],
                        "roi_theta": [AURA_CHANNELS[i] for i in front], "roi_alpha": [AURA_CHANNELS[i] for i in post],
                        "fit_range_hz": feat.fit_range, "r2_min": 0.75, "psd": "periodograma Hamming por segmento limpio"},
           "jitai": jcfg, "udp": f"127.0.0.1:{a.udp_port}",
           "parpadeos": {"canal": "Fp1", "banda_hz": BLINK_BAND, "periodo_umbral_s": a.parpadeo_periodo,
                         "umbral": "máx(3 MAD, ½ mediana de las 20 prominencias mayores) de cada período",
                         "ancho_ms": [40, 500], "separacion_s": 0.3} if blk else "sin conteo: Fp1 malo",
           "started": time.strftime("%Y-%m-%d %H:%M:%S")}
    if offline:
        cfg["offline"] = {"fuente": a.offline, "inyecciones": a.inject, "seed": a.seed, "sin_fases": a.sin_fases}
    run = open_run(("offline_" if offline else "") + src["source"], cfg)

    if not offline:
        mk_inlet = find_markers(info)

    # Paso 6: salidas (LSL de marcadores con la marca de tiempo de la ventana que decidió, UDP/JSON local) y
    # entrada de conducta del Nivel 2 (stream MIRAI_Behavior de esta PC, si existe).
    # En el replay sin LSL no se publica nada (no debe llegar a la AR) ni se escucha conducta.
    jitai_out = udp = beh_inlet = None
    if not offline:
        jitai_out = pylsl.StreamOutlet(pylsl.StreamInfo("MIRAI_JITAI", "Markers", 1, pylsl.IRREGULAR_RATE,
                                                        pylsl.cf_string, "mirai-jitai"))
        udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        beh = [s_ for s_ in pylsl.resolve_byprop("name", "MIRAI_Behavior", timeout=2.0)
               if s_.hostname() == socket.gethostname()]
        beh_inlet = pylsl.StreamInlet(beh[0]) if beh else None
        print(f"Paso 6: salida LSL 'MIRAI_JITAI' + UDP 127.0.0.1:{a.udp_port} | conducta (Nivel 2): "
              + (f"'MIRAI_Behavior' ({beh[0].source_id()})" if beh else "sin stream MIRAI_Behavior")
              + (" | Nivel 2 desactivado" if a.sin_nivel2 else ""))
    os.system("")  # activa los colores ANSI en la consola de Windows
    color = {1: "\033[93m", 2: "\033[95m", 3: "\033[91m"}

    fw = open(os.path.join(run, "ventanas.csv"), "w", newline="")
    wv = csv.writer(fw)
    wv.writerow(["ventana", "ts_ultima_muestra", "t_corte", "t_emision", "latencia_ms", "calculo_ms", "rechazo_ms",
                 "segmentos_limpios", "n_limpios", "motivo", "valida", "senal_perdida", "emg_db",
                 "features_ms", "theta_per", "alpha_per", "theta_exp", "alpha_exp", "theta_r2", "alpha_r2",
                 "theta_ok", "alpha_ok", "cal_estado", "z_theta", "z_alpha"]
                + [f"rms_{c}" for c in AURA_CHANNELS] + ["parpadeos_min"])
    fe = open(os.path.join(run, "eventos.csv"), "w", newline="", encoding="utf-8")
    we = csv.writer(fe)
    we.writerow(["ts", "fuente", "evento"])
    bloques = []  # (ts, nombre) de los bloques para la tasa de parpadeo

    def log_blinks(new):
        """Período de parpadeo cerrado: cada parpadeo definitivo y el resumen con su umbral, en eventos.csv y consola."""
        pe = blk.periods[-1]
        for tp, pr_ in new:
            we.writerow([f"{tp:.4f}", "parpadeo", f"prominencia {pr_:.0f} µV"])
        msg = (f"{(pe['inicio'] - blk.t0) / 60:.1f}–{(pe['fin'] - blk.t0) / 60:.1f} min: {pe['parpadeos']} parpadeos "
               f"({pe['parpadeos'] / ((pe['fin'] - pe['inicio']) / 60):.1f}/min), umbral {pe['umbral_uv']:.0f} µV"
               + ("" if pe["umbral_propio"] else " (el del período anterior)"))
        we.writerow([f"{pe['fin']:.4f}", "parpadeo", msg])
        print(f"  PARPADEOS {msg}")

    # calculo_ms (criterio del Paso 2) = desde que llega el bloque que cierra la ventana hasta que la ventana
    # está lista (filtrar ese bloque + cortarla). rechazo_ms = Paso 3, medido aparte. CPU total: Paso 7.
    state = {"k": 0, "t_chunk": 0.0, "t0": None, "cal": None, "stop": "", "frozen": None}
    zs = []
    jev = []  # eventos del Paso 6

    def emit_jitai(events):
        for t_, lvl, est, why in events:
            msg = f"nivel:{lvl}:{est}"
            if jitai_out:
                jitai_out.push_sample([msg], t_)
                udp.sendto(json.dumps({"ts": t_, "nivel": lvl, "estado": est, "motivo": why,
                                       "accion": jcfg["niveles"][lvl]["nombre"]}).encode(),  # ASCII escapado
                           ("127.0.0.1", a.udp_port))
            we.writerow([f"{t_:.4f}", "jitai", f"{msg} ({why})"])
            jev.append((t_, lvl, est, why))
            print(f"  {color[lvl]}>>> NIVEL {lvl} {est.upper()} · {jcfg['niveles'][lvl]['nombre']} · {why}\033[0m")
    emit_t, calc_ms, rej_ms, feat_ms, lat_ms, wins, feats, markers = [], [], [], [], [], [], [], []
    proc_ms, feat_ts = [], []  # Paso 7: procesamiento por ventana (bloque → decisión) y ts de cada feature
    res = []  # Paso 7: (reloj, CPU del proceso, memoria MB) cada 10 ventanas
    seg, step = int(round(SEG_S * fs)), int(round(SEG_STEP_S * fs))

    def on_window(w, ts_last):
        # Paso 3: rechazo de artefactos. Paso 4: features con los segmentos limpios. Pasos 5–6 se enganchan aquí.
        nonlocal rej, front, post, blk
        t_cut = pylsl.local_clock()  # el búfer acaba de cortar la ventana: aquí se mide el intervalo del Paso 2
        t_ready = time.perf_counter()
        c = (t_ready - state["t_chunk"]) * 1000
        if state["cal"] is None:
            # Paso 5: chequeo de calidad con la ventana que cierra los primeros QC_S s; antes no se procesa nada.
            if ts_last - state["t0"] < cal.QC_S:
                return
            bads[:] = sorted(set(src_bads) | set(cal.bad_channels(w, AURA_CHANNELS)))
            rej = Rejector(fs, bads)
            front = [idx[c_] for c_ in THETA_ROI if c_ not in bads]
            post = [idx[c_] for c_ in ALPHA_ROI if c_ not in bads]
            print(f"Chequeo de calidad ({cal.QC_S:.0f} s): canales malos {bads or 'ninguno'} | ROI θ "
                  f"{[AURA_CHANNELS[i] for i in front]} | ROI α {[AURA_CHANNELS[i] for i in post]}")
            if blk and "Fp1" in bads:
                blk = None
                print("Fp1 malo: sin conteo de parpadeos")
            if not front or not post:
                state["stop"] = "sin canales válidos en la ROI " + ("frontal" if not front else "posterior")
                return
            state["cal"] = cal.Calibration(ts_last, WIN_S, a.sigma_factor)
            for m in markers:
                if not (a.sin_fases and m[1].startswith("file:")):
                    state["cal"].marker(*m)
        r = rej(w)
        t_rej = time.perf_counter()
        rj = (t_rej - t_ready) * 1000
        o = {}
        if r["valida"]:
            f, psd = window_psd(w, r["clean"], fs, seg, step)
            o = feat(f, psd, front, post)
        fm = (time.perf_counter() - t_rej) * 1000
        cb = state["cal"]
        z = cb.update(ts_last, o)
        if cb.state == "congelada" and state["frozen"] is None:
            state["frozen"] = repr(cb.params)
            feat.iaf = cb.params["iaf"]
            pr = cb.params
            print(f"\n  CALIBRACIÓN CONGELADA ({pr['fuente']}): IAF {pr['iaf']:g} Hz | μ θ {pr['theta']['mu']:.2f} / α "
                  f"{pr['alpha']['mu']:.2f} dB | σ_Z θ {pr['theta']['sigma_z']:.3f} / α {pr['alpha']['sigma_z']:.3f}"
                  + (f" | Berger {pr['berger_db']:+.1f} dB" if "berger_db" in pr else "") + "\n")
        elif cb.state == "abortada":
            state["stop"] = "calibración abortada: " + cb.msg
        if z is not None:
            zs.append(z)
        if cb.state == "congelada":
            pr = cb.params
            block = bool(o and jitai.chi_flat(o["alpha_exp"], pr["chi_post"]["mu"], pr["chi_post"]["sd"], r["emg_db"],
                                              rej.emg_lim, jcfg["calidad_chi_sigmas"]))
            emit_jitai(jt.window(ts_last, z, {n: bool(o.get(f"{n}_ok")) for n in ("theta", "alpha")}, block))
        now = pylsl.local_clock()
        proc_ms.append((time.perf_counter() - state["t_chunk"]) * 1000)
        if state["k"] % 10 == 0:
            res.append((time.perf_counter(), time.process_time(), mem_mb()))
        rms = w.std(axis=0)
        br = blk.rate(ts_last) if blk else None  # parpadeos en vivo de los últimos 60 s
        wv.writerow([state["k"], f"{ts_last:.4f}", f"{t_cut:.4f}", f"{now:.4f}", f"{(now - ts_last) * 1000:.1f}", f"{c:.3f}", f"{rj:.3f}",
                     "".join("1" if x else "0" for x in r["clean"]), sum(r["clean"]), r["motivo"],
                     int(r["valida"]), int(r["perdida"]), "" if r["emg_db"] is None else f"{r['emg_db']:.2f}",
                     f"{fm:.2f}"]
                    + [f"{o[k]:.4f}" if k in o else "" for k in
                       ("theta_per", "alpha_per", "theta_exp", "alpha_exp", "theta_r2", "alpha_r2")]
                    + [int(o[k]) if k in o else "" for k in ("theta_ok", "alpha_ok")]
                    + [cb.state] + ([f"{z['theta']:.3f}", f"{z['alpha']:.3f}"] if z else ["", ""])
                    + [f"{v:.2f}" for v in rms] + ["" if br is None else br])
        emit_t.append(t_cut)  # 30 oct: al cortar, no al emitir; el costo de los Pasos 3–5 tiene sus propios criterios
        calc_ms.append(c)
        rej_ms.append(rj)
        if o:
            feat_ts.append(ts_last)
            feat_ms.append(fm)
            feats.append({k: v for k, v in o.items() if not isinstance(v, np.ndarray) and v is not None})
        lat_ms.append((now - ts_last) * 1000)
        wins.append((ts_last, r))
        state["k"] += 1
        if state["k"] % 10 == 0:
            fw.flush()
            ok = np.mean([x["valida"] for _, x in wins[-10:]])
            print(f"  ventana {state['k']:5d}  ts={ts_last:11.3f}  "
                  + (f"proc={proc_ms[-1]:5.1f} ms  " if offline else f"latencia={lat_ms[-1]:5.1f} ms  ") +
                  f"cálculo={c:5.2f} ms  limpios={''.join('1' if x else '0' for x in r['clean'])}  "
                  f"válidas(últ. 10)={ok:.0%}{'  SEÑAL PERDIDA' if r['perdida'] else ''}"
                  + (f"  θ_per={o['theta_per']:5.2f}  α_per={o['alpha_per']:5.2f} dB  features={fm:4.1f} ms" if o else "")
                  + (f"  Zθ={z['theta']:+5.2f}  Zα={z['alpha']:+5.2f}" if z else f"  [{cb.state}]")
                  + (f"  parpadeos={br}/min" if br is not None else ""))

    wnd = Windower(win, hop, nch, on_window)
    print(f"Pipeline{' (replay sin LSL)' if offline else ''}: {src['stream']} ({src['source_id']}) | {fs:.0f} Hz | red {line:.0f} Hz | "
          f"pasa-banda {filt.band[0]:.0f}–{filt.band[1]:.0f} Hz | notch {'sí' if filt.notch else 'no'} | "
          f"ventana {WIN_S:.0f} s / avance {HOP_S:.0f} s")
    print(f"Registro: {run}\nCtrl+C para detener.\n")

    t_start = pylsl.local_clock()
    try:
        while ((a.seconds is None or pylsl.local_clock() - t_start < a.seconds) and not state["stop"]
               and not (offline and inlet.done)):
            # timeout=0: solo lo ya disponible. Con timeout > 0, pull_chunk espera a llenar max_samples
            # y entrega tandas de ese tamaño (con 0.2 s la latencia llegaba a ~200 ms).
            x, ts = inlet.pull_chunk(timeout=0.0, max_samples=int(fs))
            if ts:
                state["t_chunk"] = time.perf_counter()
                state["t0"] = ts[0] if state["t0"] is None else state["t0"]
                state["n"] = state.get("n", 0) + len(ts)
                state["ts_end"] = ts[-1]
                x = np.asarray(x, dtype=np.float64)
                if blk and (new := blk.push(x[:, idx["Fp1"]], ts)) is not None:
                    log_blinks(new)
                wnd.push(filt(x), ts)
            elif not offline:
                time.sleep(0.005)
            if mk_inlet:
                while True:
                    m, mts = mk_inlet.pull_sample(timeout=0.0)
                    if m is None:
                        break
                    we.writerow([f"{mts:.4f}", "marcador", m[0]])
                    markers.append((mts, m[0]))
                    # Fases del CSV de AURA como bloques; los TTL de BrainVision ('file:Stimulus/S 11') no.
                    if m[0].startswith("bloque:") or (m[0].startswith("file:") and "/" not in m[0]):
                        bloques.append((mts, m[0].split(":", 1)[1]))
                    if state["cal"] and not (a.sin_fases and m[0].startswith("file:")):
                        state["cal"].marker(mts, m[0])
            if beh_inlet:
                while True:
                    m, mts = beh_inlet.pull_sample(timeout=0.0)
                    if m is None:
                        break
                    we.writerow([f"{mts:.4f}", "conducta", m[0]])
                    if m[0].startswith("bloque:"):
                        bloques.append((mts, m[0].split(":", 1)[1]))
                    if state["cal"] and state["cal"].state == "congelada":
                        emit_jitai(jt.behavior(mts, m[0]))
    except KeyboardInterrupt:
        print("\nDetenido por el usuario.")
    if blk and (new := blk.finish()) is not None:
        log_blinks(new)
    fw.close()
    fe.close()
    if state["stop"]:
        print(f"\nSESIÓN DETENIDA: {state['stop']}")

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
    if offline:  # sin tiempo real, el intervalo entre ventanas y la latencia no significan nada
        del checks["ventana cada 1.0 s ± 1 bloque"]
    rep3 = blink_report(wins, markers, blink_gain(fs, line))
    if rep3["parpadeos"]:  # solo hay verdad de campo con el emulador
        checks["segmentos con el pico de un parpadeo supraumbral rechazados ≥ 95 %"] = rep3["rechazo_con_parpadeo"] >= 0.95
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
    cb = state["cal"]
    rep5 = {"estado": cb.state if cb else "sin calibrar", "motivo": state["stop"], "canales_malos": bads,
            "parametros": cb.params if cb else None}
    if cb and cb.state == "congelada":
        checks["calibración congelada"] = True
        checks["μ, σ e IAF sin cambios tras la calibración"] = repr(cb.params) == state["frozen"]
        for n in ("theta", "alpha"):
            zz = np.array([z_[n] for z_ in zs])
            rep5[f"z_{n}_frac_1_5"] = float(np.mean(np.abs(zz) >= 1.5))
            rep5[f"z_{n}_sd"] = float(zz.std())
            # RMS = √(media² + DE²): el error de μ es un desplazamiento fijo dentro de la sesión que la DE no ve.
            rep5[f"z_{n}_media"] = float(zz.mean())
            rep5[f"z_{n}_rms"] = float(np.sqrt(np.mean(zz ** 2)))
            espectral = any(m_.startswith(("inject:alpha", "inject:theta")) for _, m_ in markers)
            if rep3["parpadeos"] and not espectral:  # sintético sin inyecciones espectrales (los parpadeos solo invalidan)
                checks[f"RMS(Z_{n}) entre 0.7 y 1.4"] = 0.7 <= rep5[f"z_{n}_rms"] <= 1.4
    else:
        checks["calibración congelada"] = False
    # Paso 6: disparos frente a la verdad de campo (inyecciones del emulador).
    inj = {}
    for t_, m_ in markers:
        if m_.startswith("inject:") and m_.split(":")[1] in ("alpha", "theta"):
            k_ = m_.split(":")[1]
            inj.setdefault(k_, []).append(t_)
    rep6 = {"eventos": [{"ts": t_, "nivel": l_, "estado": e_, "motivo": w_} for t_, l_, e_, w_ in jev],
            "activaciones": {l_: sum(1 for e in jev if e[1] == l_ and e[2] == "on") for l_ in (1, 2, 3)}}
    for k_, lvl in (("alpha", 1), ("theta", 3)):
        pares = list(zip(inj.get(k_, [])[::2], inj.get(k_, [])[1::2]))  # cada inyección por separado
        for i_, (t0_, t1_) in enumerate(pares, 1):
            on_ = [e[0] - t0_ for e in jev if e[1] == lvl and e[2] == "on" and t0_ <= e[0] <= t1_ + WIN_S]
            rep6[f"nivel{lvl}_inyeccion{i_}_s"] = on_
            checks[f"nivel {lvl} una vez durante la inyección {i_} de {k_} ({t1_ - t0_:.0f} s, tras la persistencia)"] = (
                len(on_) == 1 and on_[0] >= jcfg["niveles"][lvl]["persistencia_s"])
    rep6["nivel1_desplazado_por_nivel3"] = any(e[1] == 1 and e[2] == "off" and "nivel 3" in e[3] for e in jev)
    rep6["nivel2_apagado"] = any(e[1] == 2 and e[2] == "off" and "sin eventos" in e[3] for e in jev)

    # Paso 7: procesamiento, latencias, recursos, deriva, detección y fases (Berger).
    pm = np.array(proc_ms)
    rep7 = {"modo": "offline" if offline else "en vivo", "procesamiento_ms_media": float(pm.mean()),
            "procesamiento_ms_p95": float(np.percentile(pm, 95)), "procesamiento_ms_max": float(pm.max())}
    if not offline:
        la = np.array(lat_ms)
        rep7.update({"latencia_ms_media": float(la.mean()), "latencia_ms_p95": float(np.percentile(la, 95)),
                     "latencia_ms_max": float(la.max())})
        checks["latencia de procesamiento < 500 ms (p95)"] = rep7["latencia_ms_p95"] < 500
        dur_min = (emit_t[-1] - emit_t[0]) / 60
        if state.get("ts_end") and state["ts_end"] > state["t0"]:
            fs_eff = (state["n"] - 1) / (state["ts_end"] - state["t0"])
            rep7["fs_efectiva"] = float(fs_eff)
            rep7["deriva_ppm"] = float((fs_eff / fs - 1) * 1e6)
        if dur_min >= 5:  # deriva frente al reloj de LSL: tendencia de la latencia a lo largo de la sesión
            rep7["latencia_pendiente_ms_min"] = float(np.polyfit((np.array(emit_t) - emit_t[0]) / 60, la, 1)[0])
            checks["sin deriva: pendiente de la latencia < 1 ms/min"] = abs(rep7["latencia_pendiente_ms_min"]) < 1
    if len(res) >= 4:
        r0 = res[1]  # tras el arranque (importaciones, primeras ventanas)
        rep7["cpu_pct_nucleo"] = float(100 * (res[-1][1] - r0[1]) / (res[-1][0] - r0[0]))
        mem = np.array([(t_, m_) for t_, _, m_ in res if m_ is not None])
        if len(mem):
            rep7.update({"memoria_mb_inicio": float(mem[1, 1]), "memoria_mb_fin": float(mem[-1, 1]),
                         "memoria_mb_max": float(mem[:, 1].max())})
            half = mem[len(mem) // 2:]
            if len(half) >= 3:
                rep7["memoria_pendiente_mb_min"] = float(np.polyfit((half[:, 0] - half[0, 0]) / 60, half[:, 1], 1)[0])
        if not offline:
            checks["CPU < 25 % de un núcleo"] = rep7["cpu_pct_nucleo"] < 25
            if not offline and (emit_t[-1] - emit_t[0]) / 60 >= 5 and "memoria_pendiente_mb_min" in rep7:
                checks["memoria estable: pendiente (2.ª mitad) < 1 MB/min"] = abs(rep7["memoria_pendiente_mb_min"]) < 1
    for i_, on_ in ((k_.split("inyeccion")[1].split("_")[0], v_) for k_, v_ in rep6.items()
                    if k_.startswith("nivel1_inyeccion")):
        rep7[f"deteccion_n1_inyeccion{i_}_s"] = on_[0] if on_ else None
        checks[f"Nivel 1 detecta la inyección {i_} de alfa en < 10 s"] = bool(on_) and on_[0] < 10
    # Fases del archivo (CSV de AURA): α_per y θ_per por fase y Nivel 1 en ojos cerrados (Berger).
    fases = [(t_, m_[5:]) for t_, m_ in markers if m_.startswith("file:")]
    if fases:
        fr = []
        for i_, (t0_, nm) in enumerate(fases):
            t1_ = fases[i_ + 1][0] if i_ + 1 < len(fases) else np.inf
            sel = [x for t_, x in zip(feat_ts, feats) if t0_ + WIN_S <= t_ <= t1_]
            al = [x["alpha_per"] for x in sel if x["alpha_ok"]]
            th = [x["theta_per"] for x in sel if x["theta_ok"]]
            on1 = [e[0] - t0_ for e in jev if e[1] == 1 and e[2] == "on" and t0_ <= e[0] <= t1_ + WIN_S]
            fr.append({"fase": nm, "inicio_s": float(t0_ - fases[0][0]), "dur_s": float(min(t1_, state.get("ts_end", t0_)) - t0_),
                       "ventanas_con_features": len(sel), "alpha_per_media": float(np.mean(al)) if al else None,
                       "theta_per_media": float(np.mean(th)) if th else None, "nivel1_on_s": on1})
        rep7["fases"] = fr
        fo = next((f_ for f_ in fr if f_["fase"] == cal.EYES_OPEN), None)
        fc = next((f_ for f_ in fr if f_["fase"] == cal.EYES_CLOSED), None)
        if fo and fc:
            ok_b = fo["alpha_per_media"] is not None and fc["alpha_per_media"] is not None
            rep7["berger_alpha_per_db"] = fc["alpha_per_media"] - fo["alpha_per_media"] if ok_b else None
            checks["Berger: α_per mayor con ojos cerrados que abiertos"] = bool(ok_b and rep7["berger_alpha_per_db"] > 0)
            checks["Berger: el Nivel 1 se dispara con ojos cerrados"] = bool(fc["nivel1_on_s"])
    # Parpadeos (conteo definitivo): por período de umbral y por bloque; con el emulador, frente a su verdad de campo.
    repb = None
    if blk and blk.periods:
        t_fin = blk.periods[-1]["fin"]
        mins = (t_fin - blk.t0) / 60
        repb = {"parpadeos": len(blk.blinks), "minutos": mins, "tasa_min": len(blk.blinks) / mins,
                "periodos": blk.periods, "bloques": blink_blocks(blk.blinks, bloques, blk.t0, t_fin)}
        truth = [t_ for t_, m_ in markers if m_ == "blink" or m_.startswith("blink:")]
        if truth:
            repb["recall"], repb["precision"] = blink_match([t_ for t_, _ in blk.blinks], truth)
    with open(os.path.join(run, "config.json"), "r+", encoding="utf-8") as f:
        c = json.load(f)
        c["parpadeos_reporte"] = repb
        c["calibracion"] = rep5
        c["jitai_reporte"] = rep6
        c["paso7"] = rep7
        c["reporte"] = {**rep, **rep3, **rep4, "emg_umbral_db": rej.emg_lim, "checks": checks}
        f.seek(0)
        json.dump(c, f, indent=2, ensure_ascii=False)
        f.truncate()

    print(f"\n============== REPORTE PASOS 2–7 ({rep7['modo']}) ==============")
    print(f"Ventanas                : {rep['ventanas']}")
    if not offline:
        print(f"Intervalo entre ventanas: media {rep['intervalo_s_media']:.4f} s | "
              f"mín {rep['intervalo_s_min']:.3f} | máx {rep['intervalo_s_max']:.3f}")
    print(f"Cálculo búfer + filtros : p95 {rep['calculo_ms_p95']:.3f} ms | máx {rep['calculo_ms_max']:.3f} ms")
    print(f"Rechazo (Paso 3)        : p95 {rep['rechazo_ms_p95']:.3f} ms | máx {rep['rechazo_ms_max']:.3f} ms")
    if not offline:
        print(f"Latencia (emisión − última muestra): p95 {rep['latencia_ms_p95']:.1f} ms")
    print(f"Ventanas válidas        : {rep3['validas']:.1%} (fuera de trenes inyectados: "
          f"{rep3['validas_fuera_de_trenes']:.1%}) | señal perdida en {rep3['ventanas_senal_perdida']} ventanas")
    if rep3["parpadeos"]:
        print(f"Parpadeos (marcadores)  : {rep3['parpadeos']} ({rep3['parpadeos_supraumbral']} supraumbral, "
              f"{rep3['parpadeos_subumbral']} subumbral; amplitud mínima detectable "
              f"{rep3['amplitud_minima_detectable_uv']:.0f} µV, ganancia del filtro {rep3['ganancia_filtro']:.3f})")
        print(f"Segmentos               : con el pico de un parpadeo supraumbral rechazados {rep3['rechazo_con_parpadeo']:.1%} | "
              f"parciales (rozan o subumbral) rechazados {rep3['rechazo_parcial']:.1%} (n={rep3['segmentos_parciales']}) | "
              f"sin parpadeo rechazados {rep3['rechazo_sin_parpadeo']:.1%}")
    print(f"Umbral EMG              : {'NA' if rej.emg_lim is None else f'{rej.emg_lim:.1f} dB'}{'' if EMG_VETO else ' (sin veto: solo referencia)'}")
    if rep4:
        print(f"Features (Paso 4)       : Welch + specparam p95 {rep4['features_ms_p95']:.1f} ms | p99 {rep4['features_ms_p99']:.1f} ms | máx {rep4['features_ms_max']:.1f} ms"
              f" | R² ≥ 0.75 en θ {rep4['theta_validas']:.1%}, α {rep4['alpha_validas']:.1%}")
        print(f"                          mediana θ_per {rep4['theta_per_mediana']:.2f} dB, α_per {rep4['alpha_per_mediana']:.2f} dB, "
              f"χ front {rep4['theta_exp_mediana']:.2f}, χ post {rep4['alpha_exp_mediana']:.2f} (IAF {feat.iaf:g} Hz)")
    if cb and cb.params:
        pr = cb.params
        print(f"Calibración (Paso 5)    : {pr['fuente']} | IAF {pr['iaf']:g} Hz ({pr['iaf_de']}) | malos {bads or 'ninguno'}"
              + (f" | Berger {pr['berger_db']:+.1f} dB" if "berger_db" in pr else ""))
        for n in ("theta", "alpha"):
            q = pr[n]
            print(f"   {n:5s}: μ {q['mu']:.2f} dB, σ_crudo {q['sigma_crudo']:.2f}, σ_Z {q['sigma_z']:.3f} (σ_suav {q['sigma_suav']:.3f} × "
                  f"f_ac {q['factor_autocorrelacion']:.2f}, σ_μ {q['sigma_mu']:.3f}; τ {q['tau_s']:.0f} s, {q['ventanas_validas']} ventanas) | "
                  f"RMS(Z) {rep5[f'z_{n}_rms']:.2f} (media {rep5[f'z_{n}_media']:+.2f}, DE {rep5[f'z_{n}_sd']:.2f}), "
                  f"|Z| ≥ 1.5 en {rep5[f'z_{n}_frac_1_5']:.1%}")
    elif cb:
        print(f"Calibración (Paso 5)    : {cb.state} {cb.msg}")
    print(f"JITAI (Paso 6)          : activaciones N1 {rep6['activaciones'][1]}, N2 {rep6['activaciones'][2]}, "
          f"N3 {rep6['activaciones'][3]} | N1 desplazado por N3: {'sí' if rep6['nivel1_desplazado_por_nivel3'] else 'no'}"
          f" | N2 apagado por falta de eventos: {'sí' if rep6['nivel2_apagado'] else 'no'}")
    t_ini = state["t0"] or 0.0  # inicio del registro
    for k_, lvl in (("alpha", 1), ("theta", 3)):
        for i_, (t0_, t1_) in enumerate(zip(inj.get(k_, [])[::2], inj.get(k_, [])[1::2]), 1):
            secs = [round(x, 1) for x in rep6[f"nivel{lvl}_inyeccion{i_}_s"]]
            print(f"   inyección {k_} {i_}: {t0_ - t_ini:6.1f}–{t1_ - t_ini:6.1f} s del registro | "
                  f"activaciones del nivel {lvl} a los {secs} s del inicio")
    for t_, l_, e_, w_ in jev:
        print(f"   {t_:11.3f}  nivel {l_} {e_:3s}  {w_}")
    print(f"Paso 7                  : procesamiento por ventana media {rep7['procesamiento_ms_media']:.1f} ms, p95 "
          f"{rep7['procesamiento_ms_p95']:.1f}, máx {rep7['procesamiento_ms_max']:.1f}"
          + (f" | latencia media {rep7['latencia_ms_media']:.1f} / p95 {rep7['latencia_ms_p95']:.1f} / máx "
             f"{rep7['latencia_ms_max']:.1f} ms" if "latencia_ms_p95" in rep7 else ""))
    if "cpu_pct_nucleo" in rep7:
        print(f"                          CPU {rep7['cpu_pct_nucleo']:.1f} % de un núcleo | memoria "
              f"{rep7.get('memoria_mb_inicio', float('nan')):.0f} → {rep7.get('memoria_mb_fin', float('nan')):.0f} MB "
              f"(máx {rep7.get('memoria_mb_max', float('nan')):.0f}; pendiente 2.ª mitad "
              f"{rep7.get('memoria_pendiente_mb_min', float('nan')):+.2f} MB/min)"
              + (f" | deriva {rep7['deriva_ppm']:+.0f} ppm" if "deriva_ppm" in rep7 else "")
              + (f", latencia {rep7['latencia_pendiente_ms_min']:+.2f} ms/min" if "latencia_pendiente_ms_min" in rep7 else ""))
    for f_ in rep7.get("fases", []):
        print(f"   fase {f_['fase']:22s} {f_['inicio_s']:6.1f} s ({f_['dur_s']:5.1f} s): {f_['ventanas_con_features']:3d} ventanas | "
              f"α_per {f_['alpha_per_media'] if f_['alpha_per_media'] is None else round(f_['alpha_per_media'], 2)} dB | "
              f"θ_per {f_['theta_per_media'] if f_['theta_per_media'] is None else round(f_['theta_per_media'], 2)} dB | "
              f"N1 on a los {[round(x, 1) for x in f_['nivel1_on_s']]} s")
    if repb:
        umb = ", ".join(f"{p_['umbral_uv']:.0f}" for p_ in repb["periodos"])
        print(f"Parpadeos (Fp1)         : {repb['parpadeos']} en {repb['minutos']:.1f} min ({repb['tasa_min']:.1f}/min) | "
              f"umbral por período {umb} µV"
              + (f" | frente al emulador: recall {repb['recall']:.1%}, precisión {repb['precision']:.1%}" if "recall" in repb else ""))
        for nm, d in repb["bloques"].items():
            print(f"   bloque {nm:22s} {d['dur_s'] / 60:5.1f} min: {d['parpadeos']:4d} parpadeos, {d['tasa_min']:5.1f}/min"
                  + (f" | ×{d['razon']:.2f} frente a {d['frente_a']}, Mann-Whitney p = {d['p_mann_whitney']:.3f}"
                     if d.get("razon") is not None else ""))
    elif not blk:
        print("Parpadeos (Fp1)         : sin conteo (Fp1 malo)")
    for k, ok in checks.items():
        print(f"  [{'OK' if ok else 'FALLA'}] {k}")
    print(f"\nRESULTADO: {'PASA' if all(checks.values()) else 'NO PASA'}  (registro en {run})")
    write_report_md(run, cfg, rep, rep3, rep4, rep5, rep6, rep7, checks, repb)
    sys.exit(0 if all(checks.values()) else 1)


if __name__ == "__main__":
    main()
