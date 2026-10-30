"""
spectral_features.py — Paso 4 del Protocolo de Simulación (MIRAI 2026)

Por ventana: PSD de Welch con los segmentos limpios del Paso 3 → espectro medio de cada ROI → `periodic()` del
pipeline offline (h1_ds007537.py), sin reimplementarlo, para que tiempo real y H1 sean comparables:
  * theta_per en [IAF − 6, IAF − 2) Hz sobre la ROI frontal; alfa_per en [IAF − 2, IAF + 2) Hz sobre la posterior.
  * specparam: peak_width_limits [1, 8], max_n_peaks 6, aperiodic "fixed"; rango 2 – min(40, 0.8·fs/2) Hz.
  * R² < 0.75 → la feature de esa ventana es inválida (no se sustituye por potencia clásica).
"""
import os
import sys

import numpy as np
from scipy import signal

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "datasets workflow", "ds007537"))
import h1_ds007537 as h1  # noqa: E402  (periodic, FIT_RANGE)

R2_MIN = 0.75


def window_psd(w, clean, fs, seg, step):
    """PSD (canales, frecuencias) en µV²/Hz: periodograma Hamming de cada segmento limpio, promedio lineal.
    Hamming porque es la ventana de compute_psd(method='welch') de MNE en el offline."""
    segs = np.lib.stride_tricks.sliding_window_view(w, seg, axis=0)[::step][np.asarray(clean, dtype=bool)]
    f, p = signal.periodogram(segs, fs, window="hamming", axis=2)
    return f, p.mean(axis=0)


class Features:
    """theta_per / alfa_per (dB sobre el fondo 1/f), exponente aperiódico y R² de cada ROI."""

    def __init__(self, fs, iaf=10.0):
        self.fit_range = [2.0, min(40.0, 0.8 * fs / 2)]  # 2–40 Hz a 250 Hz; 2–20 Hz a 50 Hz (como EEG-SVRec)
        self.iaf = iaf  # la fija la calibración (Paso 5); hasta entonces, --iaf

    def __call__(self, f, psd, front, post):
        h1.FIT_RANGE = self.fit_range  # periodic() lee el rango de esta global del módulo offline
        out = {}
        for name, chs, lo, hi in (("theta", front, self.iaf - 6, self.iaf - 2),
                                  ("alpha", post, self.iaf - 2, self.iaf + 2)):
            if not chs:
                out.update({f"{name}_per": np.nan, f"{name}_exp": np.nan, f"{name}_r2": np.nan, f"{name}_ok": False})
                continue
            per, exp, r2 = h1.periodic(psd[chs].mean(axis=0), f, lo, hi)
            out.update({f"{name}_per": per, f"{name}_exp": exp, f"{name}_r2": r2, f"{name}_ok": bool(r2 >= R2_MIN)})
        return out
