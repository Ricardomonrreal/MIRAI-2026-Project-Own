"""
spectral_features.py — Paso 4 del Protocolo de Simulación (MIRAI 2026)

Por ventana: PSD de Welch con los segmentos limpios del Paso 3 → espectro medio de cada ROI → el ajuste de `periodic()` del
pipeline offline (h1_ds007537.py), con los mismos parámetros, para que tiempo real y H1 sean comparables:
  * theta_per en [IAF − 6, IAF − 2) Hz sobre la ROI frontal; alfa_per en [IAF − 2, IAF + 2) Hz sobre la posterior.
  * specparam: peak_width_limits [1, 8], max_n_peaks 6, aperiodic "fixed"; rango 2 – min(30, 0.8·fs/2) Hz (versión B).
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


def fit_roi(spec, f):
    """El mismo ajuste que h1.periodic() (test_realtime_pipeline lo comprueba), pero devuelve el espectro aplanado
    completo (log10 PSD − fondo aperiódico) para poder recalcular las bandas cuando el Paso 5 fije la IAF."""
    fm = h1.SpectralModel(peak_width_limits=[1, 8], max_n_peaks=6, aperiodic_mode="fixed", verbose=False)
    fm.fit(f, spec, h1.FIT_RANGE)
    off, exp = fm.get_params("aperiodic")
    with np.errstate(divide="ignore"):  # f = 0 → −inf; ninguna banda lo incluye
        flat = np.log10(spec) - (off - exp * np.log10(f))
    return flat, float(exp), float(fm.get_metrics("gof"))


def band_per(flat, f, lo, hi):
    """Potencia periódica media de [lo, hi) en dB, como el return de h1.periodic()."""
    return 10 * float(flat[(f >= lo) & (f < hi)].mean())


def bands(iaf):
    return {"theta": (iaf - 6, iaf - 2), "alpha": (iaf - 2, iaf + 2)}


class Features:
    """theta_per / alfa_per (dB sobre el fondo 1/f), exponente aperiódico y R² de cada ROI.

    Además devuelve f, el espectro aplanado de cada ROI (*_flat) y el PSD posterior medio (post_psd), que usa la
    calibración del Paso 5 para fijar la IAF y recalcular las features de las ventanas de calibración."""

    def __init__(self, fs, iaf=10.0):
        self.fit_range = [2.0, min(30.0, 0.8 * fs / 2)]  # versión B: 2–30 Hz a 250 Hz (fuera del EMG); 2–20 Hz a 50 Hz
        self.iaf = iaf  # la fija la calibración (Paso 5); hasta entonces, --iaf

    def __call__(self, f, psd, front, post):
        h1.FIT_RANGE = self.fit_range  # fit_roi() lee el rango de esta global del módulo offline, como periodic()
        out = {"f": f, "post_psd": psd[post].mean(axis=0) if post else None}
        for name, chs in (("theta", front), ("alpha", post)):
            if not chs:
                out.update({f"{name}_per": np.nan, f"{name}_exp": np.nan, f"{name}_r2": np.nan, f"{name}_ok": False,
                            f"{name}_flat": None})
                continue
            flat, exp, r2 = fit_roi(psd[chs].mean(axis=0), f)
            out.update({f"{name}_per": band_per(flat, f, *bands(self.iaf)[name]), f"{name}_exp": exp, f"{name}_r2": r2,
                        f"{name}_ok": bool(r2 >= R2_MIN), f"{name}_flat": flat})
        return out
