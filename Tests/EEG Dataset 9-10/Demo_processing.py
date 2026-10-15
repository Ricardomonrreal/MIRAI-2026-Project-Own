"""
Visualizador de señales EEG (Stroop) - versión mejorada con Trim de 3s
=====================================================================
Mejoras:
  1. Trim automático de los primeros 3 segundos para eliminar transitorios de encendido y ruido inicial.
  2. Autoescalado robusto por canal (ignora picos/artefactos para que la señal se vea bien).
  3. Slider de ventanas temporales (epochs) + duración de ventana configurable.
  4. Ventana de Densidad Espectral de Potencia (PSD, método de Welch) con bandas
     Delta/Theta/Alpha/Beta e índices de carga cognitiva.
  5. Biomarcadores del scope (theta tónico/fásico, alfa tónico, FAA) y comparaciones entre niveles.
"""
import os
import re
import numpy as np
import pandas as pd
import matplotlib
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from scipy import signal
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# ----------------------------------------------------------------------------
# Configuración
# ----------------------------------------------------------------------------
DIRECTORY_PATH = "raw_data/raw_data/Stroop_Data"
DEFAULT_FS = 250.0  # Hz (OpenBCI Cyton)
CHANNEL_NAMES = ['Fp1', 'Fp2', 'F7', 'F3', 'FZ', 'F4', 'F8', 'C2']
FRONTAL = ['Fp1', 'Fp2', 'F7', 'F3', 'FZ', 'F4', 'F8']
BANDS = {
    "Delta": (0, 4),
    "Theta": (4, 8),
    "Alpha": (8, 13),
    "Beta": (13, 30),
}
BAND_EDGES = [0, 4, 8, 13, 30]
BAND_COLORS = {"Delta": "#9e9e9e", "Theta": "#1f77b4", "Alpha": "#2ca02c",
               "Beta": "#ff7f0e"}
WINDOW_OPTIONS = ["1 s", "2 s", "5 s", "10 s", "20 s", "30 s", "60 s", "Todo"]
LEVEL_PREFIX = {"Natural": 'n', "Low level": 'l', "Mid level": 'm', "High level": 'h'}


# ----------------------------------------------------------------------------
# Procesamiento y Pipeline
# ----------------------------------------------------------------------------
def numeric_sort_key(filename):
    m = re.search(r'(\d+)\.txt$', filename)
    return int(m.group(1)) if m else 0


def load_eeg(path):
    """Lee un .txt (col 0 = índice de muestra, cols 1-8 = canales). Devuelve (n, 8)."""
    df = pd.read_csv(path, delimiter=",", header=None, comment='%',
                     skipinitialspace=True, engine="python", on_bad_lines="skip")
    df = df.iloc[:, 1:9].apply(pd.to_numeric, errors="coerce").dropna()
    return df.to_numpy(dtype=float)


def preprocess(x, fs, bandpass=True, notch=None, trim_seconds=3.0):
    """Pipeline: 
       1. Recorta los primeros N segundos para eliminar transitorios de encendido.
       2. Quita offset (DC) y aplica filtros opcionales de fase cero.
    """
    # 1. Trim de los primeros 3 segundos
    trim_samples = int(trim_seconds * fs)
    if len(x) > trim_samples:
        x = x[trim_samples:]
        
    # 2. Centrado y filtros
    x = x - x.mean(axis=0)
    nyq = fs / 2
    if bandpass and len(x) > 100:
        sos = signal.butter(4, [1.0, min(40.0, nyq * 0.95)], btype="band", fs=fs, output="sos")
        x = signal.sosfiltfilt(sos, x, axis=0)
    if notch and notch < nyq and len(x) > 100:
        b, a = signal.iirnotch(notch, Q=30, fs=fs)
        x = signal.filtfilt(b, a, x, axis=0)
    return x


def compute_psd(x, fs):
    """PSD de Welch por canal. Devuelve f, P (ch, nf) en unidades^2/Hz."""
    nperseg = int(min(len(x), 2 * fs))
    f, P = signal.welch(x, fs=fs, nperseg=nperseg, noverlap=nperseg // 2,
                        window="hann", axis=0, detrend="constant")
    return f, P.T


def band_powers(f, P):
    """Potencia absoluta por banda. P: (ch, nf) -> dict banda -> (ch,)."""
    df = f[1] - f[0]
    out = {}
    for name, (lo, hi) in BANDS.items():
        m = (f >= lo) & (f < hi)
        out[name] = P[:, m].sum(axis=1) * df
    return out


def cognitive_indices(bp):
    eps = 1e-12
    th, al, be = bp["Theta"], bp["Alpha"], bp["Beta"]
    return {
        "Theta/Alpha": th / (al + eps),
        "Beta/Alpha": be / (al + eps),
        "Engagement β/(α+θ)": be / (al + th + eps),
    }


# ----------------------------------------------------------------------------
# Biomarcadores del scope
# ----------------------------------------------------------------------------
THETA_CH = 'FZ'                  
ALPHA_PREF = ['O1', 'O2', 'Pz']  
ALPHA_FALLBACK = ['C2']          
FAA_L, FAA_R = 'F3', 'F4'        


def ch_index(name):
    for i, n in enumerate(CHANNEL_NAMES):
        if n.upper() == name.upper():
            return i
    return None


def alpha_channels():
    pref = [ch_index(n) for n in ALPHA_PREF if ch_index(n) is not None]
    if pref:
        return pref, "/".join(ALPHA_PREF)
    fb = [ch_index(n) for n in ALPHA_FALLBACK if ch_index(n) is not None]
    return fb, "/".join(ALPHA_FALLBACK) + " (proxy)"


def band_filter(x, fs, lo, hi):
    hi = min(hi, fs / 2 * 0.95)
    if lo <= 0:
        sos = signal.butter(4, hi, btype="low", fs=fs, output="sos")
    else:
        sos = signal.butter(4, [lo, hi], btype="band", fs=fs, output="sos")
    return signal.sosfiltfilt(sos, x, axis=0)


def detect_theta_bursts(fz, fs, ratio=2.5, min_dur=0.15, max_dur=3.0, merge_gap=0.1):
    fz = np.asarray(fz, dtype=float)
    if len(fz) < 100:
        z = np.zeros(len(fz))
        return z, z, z + 1e-9, []
    th = band_filter(fz, fs, *BANDS["Theta"])
    env = np.abs(signal.hilbert(th))
    k = max(1, int(0.25 * fs))
    env = np.convolve(env, np.ones(k) / k, mode="same")
    w = max(int(10 * fs), 3)
    base = pd.Series(env).rolling(w, center=True, min_periods=max(1, w // 4)).median().to_numpy()
    base = np.maximum(base, 1e-9)
    mask = env > ratio * base
    d = np.diff(np.r_[0, mask.astype(int), 0])
    starts, ends = np.where(d == 1)[0], np.where(d == -1)[0]
    regs = []
    for s0, e0 in zip(starts, ends):
        if regs and (s0 - regs[-1][1]) / fs < merge_gap:
            regs[-1][1] = e0
        else:
            regs.append([s0, e0])
    bursts = [(s0 / fs, e0 / fs, float(env[s0:e0].max()))
              for s0, e0 in regs if min_dur <= (e0 - s0) / fs <= max_dur]
    return th, env, base, bursts


def _metrics_from_bp(bp):
    eps = 1e-12
    th_i = ch_index(THETA_CH)
    a_idx, _ = alpha_channels()
    l, r = ch_index(FAA_L), ch_index(FAA_R)
    theta = float(bp["Theta"][th_i]) if th_i is not None else np.nan
    alpha = float(np.mean(bp["Alpha"][a_idx])) if a_idx else np.nan
    faa = (float(np.log(bp["Alpha"][r] + eps) - np.log(bp["Alpha"][l] + eps))
           if l is not None and r is not None else np.nan)
    return theta, alpha, faa


def biomarker_summary(x, fs, bursts, dur):
    f, P = compute_psd(x, fs)
    bp = band_powers(f, P)
    tot = sum(bp.values())
    theta, alpha, faa = _metrics_from_bp(bp)
    th_i = ch_index(THETA_CH)
    return {
        "theta_fz": theta,
        "theta_fz_rel": float(bp["Theta"][th_i] / tot[th_i] * 100) if th_i is not None else np.nan,
        "alpha": alpha,
        "faa": faa,
        "n_bursts": len(bursts),
        "burst_rate": len(bursts) / (dur / 60.0) if dur > 0 else np.nan,
        "burst_dur": float(np.mean([b[1] - b[0] for b in bursts])) if bursts else np.nan,
        "burst_amp": float(np.mean([b[2] for b in bursts])) if bursts else np.nan,
    }


def window_biomarkers(x, fs, bursts, win_s, step_s):
    n, win, step = len(x), int(win_s * fs), max(1, int(step_s * fs))
    starts = np.arange(0, n - win + 1, step)
    bstart = np.array([b[0] for b in bursts]) if bursts else np.array([])
    out = {"t": [], "theta": [], "alpha": [], "faa": [], "rate": []}
    for s0 in starts:
        f, P = compute_psd(x[s0:s0 + win], fs)
        theta, alpha, faa = _metrics_from_bp(band_powers(f, P))
        t0 = s0 / fs
        cnt = int(np.sum((bstart >= t0) & (bstart < t0 + win_s))) if len(bstart) else 0
        out["t"].append(t0 + win_s / 2)
        out["theta"].append(theta)
        out["alpha"].append(alpha)
        out["faa"].append(faa)
        out["rate"].append(cnt / (win_s / 60.0))
    return {k: np.array(v, dtype=float) for k, v in out.items()}


def slope(t_min, v):
    ok = np.isfinite(v) & np.isfinite(t_min)
    if ok.sum() < 3:
        return np.nan
    return float(np.polyfit(t_min[ok], v[ok], 1)[0])


def robust_limits(y, robust=True, pad=0.12):
    lo, hi = (np.percentile(y, [0.5, 99.5]) if robust else (y.min(), y.max()))
    if hi - lo < 1e-9:
        lo, hi = lo - 1, hi + 1
    m = (hi - lo) * pad
    return lo - m, hi + m


# ----------------------------------------------------------------------------
# Ventana PSD y Biomarcadores
# ----------------------------------------------------------------------------
class PSDWindow(tk.Toplevel):
    def __init__(self, app):
        super().__init__(app.root)
        self.app = app
        self.title("Densidad Espectral de Potencia - Carga cognitiva")
        self.geometry("1250x800")

        top = ttk.Frame(self, padding=8)
        top.pack(side=tk.TOP, fill=tk.X)
        ttk.Label(top, text="Segmento:").pack(side=tk.LEFT)
        self.seg_var = tk.StringVar(value="Epoch actual")
        seg = ttk.Combobox(top, textvariable=self.seg_var, state="readonly", width=16,
                           values=["Epoch actual", "Registro completo"])
        seg.pack(side=tk.LEFT, padx=(4, 12))
        ttk.Label(top, text="Eje Y:").pack(side=tk.LEFT)
        self.scale_var = tk.StringVar(value="Logarítmico (dB)")
        sc = ttk.Combobox(top, textvariable=self.scale_var, state="readonly", width=16,
                          values=["Logarítmico (dB)", "Lineal"])
        sc.pack(side=tk.LEFT, padx=(4, 12))
        self.avg_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(top, text="Solo promedio de canales", variable=self.avg_var,
                        command=self.refresh).pack(side=tk.LEFT, padx=(0, 12))
        ttk.Button(top, text="Actualizar", command=self.refresh).pack(side=tk.LEFT)
        seg.bind("<<ComboboxSelected>>", lambda e: self.refresh())
        sc.bind("<<ComboboxSelected>>", lambda e: self.refresh())

        nb = ttk.Notebook(self)
        nb.pack(fill=tk.BOTH, expand=True)
        tab1, tabB, tab2, tab3 = ttk.Frame(nb), ttk.Frame(nb), ttk.Frame(nb), ttk.Frame(nb)
        nb.add(tab1, text="Espectro del archivo")
        nb.add(tabB, text="Biomarcadores del scope")
        nb.add(tab2, text="Comparar niveles (bandas)")
        nb.add(tab3, text="Comparar niveles (biomarcadores)")

        # Pestaña 1
        self.fig = Figure(figsize=(11, 7))
        gs = self.fig.add_gridspec(2, 2, height_ratios=[1.6, 1], width_ratios=[1.6, 1])
        self.ax_psd = self.fig.add_subplot(gs[0, :])
        self.ax_bar = self.fig.add_subplot(gs[1, 0])
        self.ax_txt = self.fig.add_subplot(gs[1, 1])
        self.canvas = FigureCanvasTkAgg(self.fig, master=tab1)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        NavigationToolbar2Tk(self.canvas, tab1)

        # Pestaña biomarcadores
        self.fig3 = Figure(figsize=(11, 7.5))
        self.canvas3 = FigureCanvasTkAgg(self.fig3, master=tabB)
        self.canvas3.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        NavigationToolbar2Tk(self.canvas3, tabB)

        # Pestaña 2
        bar = ttk.Frame(tab2, padding=6)
        bar.pack(fill=tk.X)
        ttk.Button(bar, text="Calcular comparación (todos los archivos)",
                   command=self.compare_levels).pack(side=tk.LEFT)
        self.cmp_status = ttk.Label(bar, text="  Usa los canales visibles y los filtros actuales.")
        self.cmp_status.pack(side=tk.LEFT)
        self.fig2 = Figure(figsize=(11, 6))
        self.canvas2 = FigureCanvasTkAgg(self.fig2, master=tab2)
        self.canvas2.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Pestaña 3
        bar3 = ttk.Frame(tab3, padding=6)
        bar3.pack(fill=tk.X)
        ttk.Button(bar3, text="Calcular biomarcadores (todos los archivos)",
                   command=self.compare_biomarkers).pack(side=tk.LEFT)
        self.bm_status = ttk.Label(bar3, text="  Barras = media ± desv. est.; puntos = archivos individuales.")
        self.bm_status.pack(side=tk.LEFT)
        self.fig4 = Figure(figsize=(11, 6))
        self.canvas4 = FigureCanvasTkAgg(self.fig4, master=tab3)
        self.canvas4.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        self.refresh()

    def _segment(self):
        a = self.app
        if a.data is None:
            return None
        if self.seg_var.get() == "Registro completo":
            seg = a.data
        else:
            i0, i1 = a.window_bounds()
            seg = a.data[i0:i1]
        idx = a.visible_idx()
        return seg[:, idx], [CHANNEL_NAMES[i] for i in idx]

    def refresh(self):
        self.refresh_biomarkers()
        res = self._segment()
        if res is None:
            return
        seg, names = res
        fs = self.app.fs
        if len(seg) < int(fs):
            return
        f, P = compute_psd(seg, fs)
        m = (f > 0) & (f <= 30)
        log = self.scale_var.get().startswith("Log")

        ax = self.ax_psd
        ax.clear()
        for name, (lo, hi) in BANDS.items():
            ax.axvspan(lo, hi, color=BAND_COLORS[name], alpha=0.10)
            ax.text((lo + hi) / 2, 0.98, name, transform=ax.get_xaxis_transform(),
                    ha="center", va="top", fontsize=9, color=BAND_COLORS[name], fontweight="bold")
        mean_psd = P.mean(axis=0)
        if not self.avg_var.get():
            for k, n in enumerate(names):
                y = 10 * np.log10(P[k, m] + 1e-20) if log else P[k, m]
                ax.plot(f[m], y, lw=0.9, alpha=0.75, label=n)
        y = 10 * np.log10(mean_psd[m] + 1e-20) if log else mean_psd[m]
        ax.plot(f[m], y, color="k", lw=2.2, label="Promedio")
        ax.set_xlim(0, 30)
        ax.set_xticks(BAND_EDGES)
        ax.set_xticklabels([str(e) for e in BAND_EDGES])
        ax.set_xlabel("Frecuencia (Hz)")
        ax.set_ylabel("PSD (dB re 1 µV²/Hz)" if log else "PSD (µV²/Hz)")
        ax.set_title(f"PSD de Welch - {self.app.current_label()} "
                     f"({len(seg) / fs:.1f} s)")
        ax.grid(True, ls="--", alpha=0.4)
        ax.legend(ncol=min(len(names) + 1, 9), fontsize=8, loc="lower left")

        bp = band_powers(f, P)
        tot = sum(v for v in bp.values())
        rel = {k: float(np.mean(v / tot)) * 100 for k, v in bp.items()}
        ax = self.ax_bar
        ax.clear()
        ax.bar(list(rel.keys()), list(rel.values()), color=[BAND_COLORS[k] for k in rel])
        for i, v in enumerate(rel.values()):
            ax.text(i, v + 0.5, f"{v:.1f}%", ha="center", fontsize=9)
        ax.set_ylabel("Potencia relativa (%)")
        ax.set_title("Distribución de potencia por banda (0-30 Hz)")
        ax.set_ylim(0, max(rel.values()) * 1.2)
        ax.grid(True, axis="y", ls="--", alpha=0.4)

        idx = cognitive_indices(bp)
        ax = self.ax_txt
        ax.clear()
        ax.axis("off")
        lines = ["Índices de carga cognitiva", "(promedio de canales mostrados)", ""]
        for k, v in idx.items():
            lines.append(f"{k}:  {np.mean(v):.2f}")
        fr = [i for i, n in enumerate(names) if n in FRONTAL]
        if fr:
            lines += ["", f"θ frontal (µV²):  {np.mean(bp['Theta'][fr]):.2f}",
                      f"α (µV²):  {np.mean(bp['Alpha']):.2f}"]
        ax.text(0.0, 1.0, "\n".join(lines), va="top", fontsize=10, family="monospace")
        self.fig.tight_layout()
        self.canvas.draw_idle()

    def refresh_biomarkers(self):
        a = self.app
        if a.data is None or a.theta_fz is None:
            return
        fs = a.fs
        n = len(a.data)
        if self.seg_var.get() == "Registro completo":
            i0, i1 = 0, n
        else:
            i0, i1 = a.window_bounds()
        t0, t1 = i0 / fs, i1 / fs
        dur = t1 - t0
        fig = self.fig3
        fig.clear()
        if dur < 4:
            fig.text(0.5, 0.5, "Se necesitan al menos 4 s de segmento.", ha="center", va="center", fontsize=12)
            self.canvas3.draw_idle()
            return
        ratio = a.burst_ratio
        bursts = [b for b in a.bursts if b[0] >= t0 and b[1] <= t1]
        rel = [(b[0] - t0, b[1] - t0, b[2]) for b in bursts]
        seg = a.data[i0:i1]
        a_idx, a_label = alpha_channels()

        gs = fig.add_gridspec(3, 2, height_ratios=[1.1, 1, 1], width_ratios=[1.5, 1])
        ax0 = fig.add_subplot(gs[0, :])
        t = np.arange(i0, i1) / fs
        ax0.plot(t, a.theta_fz[i0:i1], color=BAND_COLORS["Theta"], lw=0.8, label="Theta Fz (4-8 Hz)")
        ax0.plot(t, a.env_fz[i0:i1], color="k", lw=1.1, label="Envolvente")
        ax0.plot(t, ratio * a.base_fz[i0:i1], "--", color="gray", lw=1.1,
                 label=f"Umbral ({ratio:g}× base)")
        for k, b in enumerate(bursts):
            ax0.axvspan(b[0], b[1], color="#d62728", alpha=0.28,
                        label="Ráfaga fásica (FM-theta)" if k == 0 else None)
        ax0.set_xlim(t0, t1)
        lo, hi = robust_limits(a.theta_fz[i0:i1], False)
        ax0.set_ylim(lo, hi)
        ax0.set_xlabel("Tiempo (s)")
        ax0.set_ylabel("µV")
        ax0.set_title(f"Theta Fz - Ráfagas detectadas: {len(bursts)}", fontsize=10)
        ax0.grid(True, ls="--", alpha=0.4)
        ax0.legend(ncol=4, fontsize=8, loc="upper right")

        win_s = float(np.clip(dur / 6, 4, 10))
        step_s = win_s / 2
        enough = dur >= 8
        ax1 = fig.add_subplot(gs[1, 0])
        ax2 = fig.add_subplot(gs[2, 0], sharex=ax1)
        ax3 = fig.add_subplot(gs[1, 1])
        ax4 = fig.add_subplot(gs[2, 1])
        for ax in (ax3, ax4):
            ax.axis("off")
        
        if enough:
            wb = window_biomarkers(seg, fs, rel, win_s, step_s)
            unit, ulabel = (60.0, "min") if dur >= 120 else (1.0, "s")
            tc = (t0 + wb["t"]) / unit
            t_min = (wb["t"]) / 60.0
            nb_ = max(1, int(round(0.2 * len(tc))))
            def norm(v):
                base = np.nanmean(v[:nb_])
                return v / base if np.isfinite(base) and base > 0 else v * np.nan
            th_n, al_n = norm(wb["theta"]), norm(wb["alpha"])
            ax1.plot(tc, th_n, color=BAND_COLORS["Theta"], lw=2.2, label="Theta tónico")
            ax1.plot(tc, al_n, color=BAND_COLORS["Alpha"], lw=2.2, label=f"Alfa tónico")
            ax1.axhline(1.0, color="gray", ls=":", lw=1)
            ax1.set_ylabel("Relativo a base")
            ax1.legend(fontsize=8, loc="best")
            ax1.grid(True, ls="--", alpha=0.4)
            ax1.tick_params(labelbottom=False)

            ax2.bar(tc, wb["rate"], width=step_s / unit * 0.9, color="#d62728", alpha=0.45)
            ax2.set_ylabel("Ráfagas/min", color="#d62728")
            ax2b = ax2.twinx()
            ax2b.plot(tc, wb["faa"], color="#1f77b4", lw=2, marker="o", ms=3)
            ax2b.axhline(0, color="gray", ls=":", lw=1)
            ax2b.set_ylabel("FAA", color="#1f77b4")
            ax2.set_xlabel(f"Tiempo ({ulabel})")
            ax2.grid(True, ls="--", alpha=0.4)

        s = biomarker_summary(seg, fs, rel, dur)
        def fmt(v, f="{:.2f}"):
            return f.format(v) if np.isfinite(v) else "n/d"
        L = [f"Biomarcadores ({dur:.1f} s post-trim)", "",
             f"θ tónico Fz:      {fmt(s['theta_fz'])} µV²",
             f"α tónico {a_label}: {fmt(s['alpha'])} µV²",
             f"FAA (F4 vs F3):   {fmt(s['faa'])}",
             f"Ráfagas θ (Fz):   {s['n_bursts']}  ({fmt(s['burst_rate'], '{:.1f}')}/min)"]
        ax3.text(0.0, 1.0, "\n".join(L), va="top", fontsize=8.5, family="monospace", transform=ax3.transAxes)
        fig.tight_layout()
        self.canvas3.draw_idle()

    def compare_biomarkers(self):
        a = self.app
        self.bm_status.config(text="  Calculando...")
        self.update_idletasks()
        ratio = a.ratio_value()
        keys = ["theta_fz", "alpha", "faa", "burst_rate"]
        res = {lvl: {k: [] for k in keys} for lvl in a.levels_dict}
        th_i = ch_index(THETA_CH)
        for lvl, files in a.levels_dict.items():
            for fn in files:
                try:
                    x = preprocess(load_eeg(os.path.join(a.directory, fn)), a.fs,
                                   a.bandpass_var.get(), a.notch_value())
                    dur = len(x) / a.fs
                    if dur < 4:
                        continue
                    _, _, _, bursts = detect_theta_bursts(x[:, th_i], a.fs, ratio)
                    s = biomarker_summary(x, a.fs, bursts, dur)
                except Exception:
                    continue
                for k in keys:
                    res[lvl][k].append(s[k])
        _, a_label = alpha_channels()
        titles = {"theta_fz": "Theta tónico Fz (µV²)", "alpha": f"Alfa tónico {a_label} (µV²)",
                  "faa": "FAA = ln α(F4) − ln α(F3)", "burst_rate": "Ráfagas theta fásico (por min)"}
        fig = self.fig4
        fig.clear()
        levels = list(res)
        colors = ["#7f7f7f", "#2ca02c", "#ff7f0e", "#d62728"]
        for j, k in enumerate(keys):
            ax = fig.add_subplot(2, 2, j + 1)
            for i, l in enumerate(levels):
                v = np.array([z for z in res[l][k] if np.isfinite(z)])
                if len(v) == 0:
                    continue
                ax.bar(i, v.mean(), yerr=v.std() if len(v) > 1 else 0, capsize=4,
                       color=colors[i % 4], alpha=0.55)
                ax.scatter(np.full(len(v), i) + np.linspace(-0.12, 0.12, len(v)), v,
                           color="k", s=14, zorder=3)
            ax.set_xticks(range(len(levels)))
            ax.set_xticklabels(levels, fontsize=8)
            ax.set_title(titles[k], fontsize=10)
            ax.grid(True, axis="y", ls="--", alpha=0.4)
            if k == "faa":
                ax.axhline(0, color="gray", lw=1)
        fig.tight_layout()
        self.canvas4.draw_idle()
        self.bm_status.config(text="  Listo.")

    def compare_levels(self):
        a = self.app
        idx = a.visible_idx()
        self.cmp_status.config(text="  Calculando...")
        self.update_idletasks()
        results, rel_bands = {}, {}
        for level, files in a.levels_dict.items():
            vals, rb = {}, {b: [] for b in BANDS}
            for fn in files:
                try:
                    x = preprocess(load_eeg(os.path.join(a.directory, fn)), a.fs,
                                   a.bandpass_var.get(), a.notch_value())
                    if len(x) < int(a.fs):
                        continue
                    f, P = compute_psd(x[:, idx], a.fs)
                except Exception:
                    continue
                bp = band_powers(f, P)
                tot = sum(bp.values())
                for k, v in cognitive_indices(bp).items():
                    vals.setdefault(k, []).append(float(np.mean(v)))
                for b in BANDS:
                    rb[b].append(float(np.mean(bp[b] / tot)) * 100)
            results[level], rel_bands[level] = vals, rb
        self.fig2.clear()
        levels = list(results.keys())
        keys = ["Theta/Alpha", "Beta/Alpha", "Engagement β/(α+θ)"]
        for j, k in enumerate(keys):
            ax = self.fig2.add_subplot(2, 3, j + 1)
            mu = [np.mean(results[l].get(k, [np.nan])) for l in levels]
            sd = [np.std(results[l].get(k, [np.nan])) for l in levels]
            ax.bar(levels, mu, yerr=sd, capsize=4, color="#4c78a8")
            ax.set_title(k, fontsize=10)
            ax.tick_params(axis="x", labelsize=8, rotation=20)
            ax.grid(True, axis="y", ls="--", alpha=0.4)
        ax = self.fig2.add_subplot(2, 1, 2)
        w = 0.8 / len(BANDS)
        x0 = np.arange(len(levels))
        for i, b in enumerate(BANDS):
            m = [np.mean(rel_bands[l][b]) if rel_bands[l][b] else np.nan for l in levels]
            ax.bar(x0 + i * w, m, w, label=b, color=BAND_COLORS[b])
        ax.set_xticks(x0 + 0.4 - w / 2)
        ax.set_xticklabels(levels)
        ax.set_ylabel("Potencia relativa (%)")
        ax.set_title("Potencia relativa por banda y nivel (Post-Trim 3s)")
        ax.legend(ncol=5, fontsize=8)
        ax.grid(True, axis="y", ls="--", alpha=0.4)
        self.fig2.tight_layout()
        self.canvas2.draw_idle()
        self.cmp_status.config(text="  Listo.")


# ----------------------------------------------------------------------------
# Aplicación principal
# ----------------------------------------------------------------------------
class EEGViewer:
    def __init__(self, root, directory):
        self.root = root
        self.directory = directory
        self.data = None          
        self.fs = DEFAULT_FS
        self.axes, self.lines = [], []
        self.psd_win = None
        self.band_cache = {}
        self.burst_patches = []
        self.bursts = []
        self.theta_fz = self.env_fz = self.base_fz = None
        self.burst_ratio = 2.5
        self.band_show_var = tk.StringVar(value="Cruda (filtrada)")
        self.ratio_var = tk.StringVar(value="2.5")
        self.root.title("Visualizador de Señales EEG")
        self.root.geometry("1450x880")

        self._scan_directory()
        self._build_controls()
        self._build_plot()

        self.level_combobox.set(list(self.levels_dict)[0])
        self.on_level_changed()

    def _scan_directory(self):
        files = [f for f in os.listdir(self.directory) if f.endswith('.txt')]
        self.levels_dict = {
            lvl: sorted([f for f in files if f.lower().startswith(p)], key=numeric_sort_key)
            for lvl, p in LEVEL_PREFIX.items()
        }

    def _build_controls(self):
        c = ttk.Frame(self.root, padding=12)
        c.pack(side=tk.LEFT, fill=tk.Y)
        bold = ("Arial", 10, "bold")

        ttk.Label(c, text="Nivel:", font=bold).pack(anchor="w")
        self.level_var = tk.StringVar()
        self.level_combobox = ttk.Combobox(c, textvariable=self.level_var, state="readonly",
                                           values=list(self.levels_dict), width=28)
        self.level_combobox.pack(pady=(2, 10))
        self.level_combobox.bind("<<ComboboxSelected>>", self.on_level_changed)

        ttk.Label(c, text="Archivo:", font=bold).pack(anchor="w")
        self.file_var = tk.StringVar()
        self.file_combobox = ttk.Combobox(c, textvariable=self.file_var, state="readonly", width=28)
        self.file_combobox.pack(pady=(2, 10))
        self.file_combobox.bind("<<ComboboxSelected>>", lambda e: self.load_file())

        ttk.Separator(c).pack(fill=tk.X, pady=6)
        ttk.Label(c, text="Frecuencia de muestreo (Hz):", font=bold).pack(anchor="w")
        self.fs_var = tk.StringVar(value=str(int(DEFAULT_FS)))
        fs_e = ttk.Entry(c, textvariable=self.fs_var, width=10)
        fs_e.pack(anchor="w", pady=(2, 8))
        fs_e.bind("<Return>", lambda e: self.load_file())

        ttk.Label(c, text="Filtros:", font=bold).pack(anchor="w")
        self.bandpass_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(c, text="Pasa-banda 1-40 Hz", variable=self.bandpass_var,
                        command=self.load_file).pack(anchor="w")
        self.notch_var = tk.StringVar(value="Sin notch")
        nb = ttk.Combobox(c, textvariable=self.notch_var, state="readonly", width=14,
                          values=["Sin notch", "Notch 50 Hz", "Notch 60 Hz"])
        nb.pack(anchor="w", pady=(2, 8))
        nb.bind("<<ComboboxSelected>>", lambda e: self.load_file())

        ttk.Separator(c).pack(fill=tk.X, pady=6)
        ttk.Label(c, text="Escalado:", font=bold).pack(anchor="w")
        self.autoscale_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(c, text="Autoescala por canal", variable=self.autoscale_var,
                        command=self.redraw).pack(anchor="w")
        self.robust_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(c, text="Robusta (ignora artefactos)", variable=self.robust_var,
                        command=self.redraw).pack(anchor="w", pady=(0, 8))

        ttk.Label(c, text="Señal mostrada:", font=bold).pack(anchor="w")
        bs = ttk.Combobox(c, textvariable=self.band_show_var, state="readonly", width=18,
                          values=["Cruda (filtrada)"] + list(BANDS))
        bs.pack(anchor="w", pady=(2, 4))
        bs.bind("<<ComboboxSelected>>", lambda e: self.redraw())
        ttk.Label(c, text="Umbral ráfaga theta Fz (× base):").pack(anchor="w")
        sp = ttk.Spinbox(c, from_=1.5, to=6.0, increment=0.5, width=6,
                         textvariable=self.ratio_var, command=self.on_ratio_changed)
        sp.pack(anchor="w", pady=(2, 8))
        sp.bind("<Return>", lambda e: self.on_ratio_changed())

        ttk.Label(c, text="Canales visibles:", font=bold).pack(anchor="w")
        self.ch_vars = []
        for n in CHANNEL_NAMES:
            v = tk.BooleanVar(value=True)
            ttk.Checkbutton(c, text=n, variable=v, command=self.rebuild_axes).pack(anchor="w")
            self.ch_vars.append(v)

        ttk.Separator(c).pack(fill=tk.X, pady=8)
        ttk.Button(c, text="Analizar PSD / carga cognitiva", command=self.open_psd).pack(fill=tk.X)
        ttk.Button(c, text="Cambiar carpeta de datos...", command=self.change_dir).pack(fill=tk.X, pady=(6, 0))
        self.info_label = ttk.Label(c, text="", wraplength=210, justify="left")
        self.info_label.pack(anchor="w", pady=10)

    def _build_plot(self):
        right = ttk.Frame(self.root)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.fig = Figure(figsize=(10, 8))
        self.canvas = FigureCanvasTkAgg(self.fig, master=right)

        nav = ttk.Frame(right, padding=(8, 4))
        nav.pack(side=tk.BOTTOM, fill=tk.X)
        ttk.Label(nav, text="Ventana:").pack(side=tk.LEFT)
        self.win_var = tk.StringVar(value="10 s")
        wc = ttk.Combobox(nav, textvariable=self.win_var, values=WINDOW_OPTIONS,
                          state="readonly", width=7)
        wc.pack(side=tk.LEFT, padx=(4, 10))
        wc.bind("<<ComboboxSelected>>", lambda e: self.on_window_changed())
        ttk.Button(nav, text="◀", width=3, command=lambda: self.step(-1)).pack(side=tk.LEFT)
        self.start_var = tk.DoubleVar(value=0.0)
        self.slider = ttk.Scale(nav, from_=0, to=1, variable=self.start_var,
                                orient=tk.HORIZONTAL, command=lambda v: self.redraw())
        self.slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=6)
        ttk.Button(nav, text="▶", width=3, command=lambda: self.step(1)).pack(side=tk.LEFT)
        self.time_label = ttk.Label(nav, text="", width=26, anchor="e")
        self.time_label.pack(side=tk.LEFT, padx=(8, 0))

        NavigationToolbar2Tk(self.canvas, right).pack(side=tk.BOTTOM, fill=tk.X)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        self.root.bind("<Left>", lambda e: self.step(-1))
        self.root.bind("<Right>", lambda e: self.step(1))

    def notch_value(self):
        s = self.notch_var.get()
        return 50.0 if "50" in s else 60.0 if "60" in s else None

    def visible_idx(self):
        idx = [i for i, v in enumerate(self.ch_vars) if v.get()]
        return idx or list(range(len(CHANNEL_NAMES)))

    def window_seconds(self):
        s = self.win_var.get()
        if self.data is None or s == "Todo":
            return len(self.data) / self.fs if self.data is not None else 1.0
        return min(float(s.split()[0]), len(self.data) / self.fs)

    def window_bounds(self):
        w = self.window_seconds()
        i0 = int(round(self.start_var.get() * self.fs))
        i0 = max(0, min(i0, max(0, len(self.data) - int(w * self.fs))))
        return i0, min(len(self.data), i0 + int(round(w * self.fs)))

    def current_label(self):
        return self.file_var.get()

    def on_level_changed(self, event=None):
        files = self.levels_dict.get(self.level_var.get(), [])
        self.file_combobox['values'] = files
        if files:
            self.file_combobox.set(files[0])
            self.load_file()
        else:
            self.file_var.set('')
            self.data = None

    def load_file(self):
        fn = self.file_var.get()
        if not fn:
            return
        try:
            self.fs = float(self.fs_var.get())
            raw = load_eeg(os.path.join(self.directory, fn))
            if raw.shape[0] < 10 or raw.shape[1] < 8:
                raise ValueError("El archivo no contiene 8 canales válidos.")
            # Aquí se ejecuta automáticamente el Trim de 3s + filtros
            self.data = preprocess(raw, self.fs, self.bandpass_var.get(), self.notch_value(), trim_seconds=3.0)
            self.band_cache = {}
            self.update_bursts()
        except Exception as e:
            messagebox.showerror("Error al cargar", f"{fn}\n\n{e}")
            return
        dur = len(self.data) / self.fs
        self.info_label.config(text=f"{len(self.data)} muestras\n{dur:.1f} s a {self.fs:g} Hz")
        self.start_var.set(0.0)
        self.on_window_changed()
        if self.psd_win is not None and self.psd_win.winfo_exists():
            self.psd_win.refresh()

    def on_window_changed(self):
        if self.data is None:
            return
        dur = len(self.data) / self.fs
        self.slider.configure(to=max(dur - self.window_seconds(), 1e-6))
        self.start_var.set(min(self.start_var.get(), max(dur - self.window_seconds(), 0)))
        self.rebuild_axes()

    def step(self, direction):
        if self.data is None:
            return
        w = self.window_seconds()
        dur = len(self.data) / self.fs
        self.start_var.set(float(np.clip(self.start_var.get() + direction * w / 2, 0, max(dur - w, 0))))
        self.redraw()

    def rebuild_axes(self):
        self.fig.clear()
        idx = self.visible_idx()
        self.axes = self.fig.subplots(len(idx), 1, sharex=True, squeeze=False)[:, 0]
        self.lines = []
        self.burst_patches = []
        for ax, ch in zip(self.axes, idx):
            (ln,) = ax.plot([], [], color="#1f4e9c", lw=0.8)
            self.lines.append((ch, ln))
            ax.set_ylabel(f"{CHANNEL_NAMES[ch]}\n(µV)", fontsize=8, fontweight="bold")
            ax.grid(True, ls="--", alpha=0.5)
            ax.tick_params(labelsize=8)
            if ax is not self.axes[-1]:
                ax.tick_params(labelbottom=False)
        self.axes[-1].set_xlabel("Tiempo (s)", fontsize=10)
        self.fig.subplots_adjust(left=0.08, right=0.985, top=0.94, bottom=0.07, hspace=0.12)
        self.redraw()

    def redraw(self):
        if self.data is None or not self.lines:
            return
        i0, i1 = self.window_bounds()
        t = np.arange(i0, i1) / self.fs
        if len(t) < 2:
            return
        src = self.display_data()
        for ax, (ch, ln) in zip(self.axes, self.lines):
            y = src[i0:i1, ch]
            ln.set_data(t, y)
            if self.autoscale_var.get():
                ax.set_ylim(*robust_limits(y, self.robust_var.get()))
            ax.set_xlim(t[0], t[-1])
        for p in self.burst_patches:
            try:
                p.remove()
            except Exception:
                pass
        self.burst_patches = []
        band = self.band_show_var.get()
        if band == "Theta":
            fz = ch_index(THETA_CH)
            for ax, (ch, ln) in zip(self.axes, self.lines):
                if ch == fz:
                    for b0, b1, _ in self.bursts:
                        if b1 > t[0] and b0 < t[-1]:
                            self.burst_patches.append(ax.axvspan(max(b0, t[0]), min(b1, t[-1]),
                                                                 color="#d62728", alpha=0.25))
        extra = "" if band.startswith("Cruda") else f" | banda {band} {BANDS[band][0]}-{BANDS[band][1]} Hz"
        self.fig.suptitle(f"Señales EEG - {self.file_var.get()}{extra}", fontsize=11, fontweight="bold")
        self.time_label.config(text=f"{t[0]:.1f} – {t[-1]:.1f} s de {len(self.data) / self.fs:.1f} s")
        self.canvas.draw_idle()

    def display_data(self):
        b = self.band_show_var.get()
        if b.startswith("Cruda") or len(self.data) < 100:
            return self.data
        if b not in self.band_cache:
            self.band_cache[b] = band_filter(self.data, self.fs, *BANDS[b])
        return self.band_cache[b]

    def ratio_value(self):
        try:
            return float(np.clip(float(self.ratio_var.get()), 1.2, 10.0))
        except ValueError:
            return 2.5

    def update_bursts(self):
        self.burst_ratio = self.ratio_value()
        fz = ch_index(THETA_CH)
        self.theta_fz, self.env_fz, self.base_fz, self.bursts = detect_theta_bursts(
            self.data[:, fz], self.fs, self.burst_ratio)

    def on_ratio_changed(self):
        if self.data is None:
            return
        self.update_bursts()
        self.redraw()
        if self.psd_win is not None and self.psd_win.winfo_exists():
            self.psd_win.refresh()

    def open_psd(self):
        if self.data is None:
            return
        if self.psd_win is not None and self.psd_win.winfo_exists():
            self.psd_win.lift()
            self.psd_win.refresh()
        else:
            self.psd_win = PSDWindow(self)

    def change_dir(self):
        d = filedialog.askdirectory(title="Selecciona la carpeta con los .txt")
        if d:
            self.directory = d
            self._scan_directory()
            self.level_combobox['values'] = list(self.levels_dict)
            self.on_level_changed()


def main():
    root = tk.Tk()
    directory = DIRECTORY_PATH
    if not os.path.isdir(directory):
        directory = filedialog.askdirectory(title="Selecciona la carpeta Stroop_Data")
        if not directory:
            root.destroy()
            return
    EEGViewer(root, directory)
    root.mainloop()


if __name__ == "__main__":
    main()