"""
Visualizador de señales EEG (F3, F4, Fz, Pz, O1, O2) con Modulación Automática
=============================================================================
Características principales:
  1. Electrodos objetivo de investigación: F3, F4, Fz, Pz, O1, O2.
  2. Modulación automática de canales:
     - Detecta automáticamente si el archivo posee todos los canales o solo un subconjunto.
     - Compatible con datasets clásicos de 8 canales (ej. Stroop OpenBCI Cyton: detecta y extrae F3, F4 y Fz).
     - Compatible con archivos limpios de 6 canales (F3, F4, Fz, Pz, O1, O2) o CSVs con encabezado.
  3. Representación visual integrada del montaje 10-20 (vista superior):
     - Muestra la cabeza, orientación (Frente, Izq., Der.) y posición anatómica de cada electrodo.
     - Códigos de color por biomarcador (Theta Fz en púrpura, FAA F3/F4 en azul, Alfa posterior en verde).
     - Indicadores de estado en tiempo real (activo vs. ausente en el archivo cargado).
  4. Preprocesamiento: trim automático de 3s, centrado, pasa-banda 1-40 Hz, notch y reparación de artefactos.
  5. Análisis PSD e índices cognitivos (Theta Fz, Alfa posterior, FAA).
"""
import os
import re
import numpy as np
import pandas as pd
import matplotlib
import matplotlib.patches as patches
import matplotlib.lines as mlines
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from scipy import signal, ndimage
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# ----------------------------------------------------------------------------
# Configuración de canales y biomarcadores
# ----------------------------------------------------------------------------
DIRECTORY_PATH = "raw_data/raw_data/Stroop_Data"
DEFAULT_FS = 250.0  # Hz

# Electrodos objetivo para las investigaciones
TARGET_CHANNELS = ['F3', 'F4', 'Fz', 'Pz', 'O1', 'O2']
FRONTAL_TARGETS = ['F3', 'F4', 'Fz']
POSTERIOR_TARGETS = ['Pz', 'O1', 'O2']

# Asignaciones clave de biomarcadores
THETA_CH = 'Fz'
ALPHA_CHANNELS = ['Pz', 'O1', 'O2']
FAA_L, FAA_R = 'F3', 'F4'

BANDS = {
    "Delta": (0, 4),
    "Theta": (4, 8),
    "Alpha": (8, 13),
    "Beta": (13, 30),
}
BAND_EDGES = [0, 4, 8, 13, 30]
BAND_COLORS = {
    "Delta": "#9e9e9e",
    "Theta": "#1f77b4",
    "Alpha": "#2ca02c",
    "Beta": "#ff7f0e"
}
WINDOW_OPTIONS = ["1 s", "2 s", "5 s", "10 s", "20 s", "30 s", "60 s", "Todo"]
LEVEL_PREFIX = {"Natural": 'n', "Low level": 'l', "Mid level": 'm', "High level": 'h'}


# ----------------------------------------------------------------------------
# Representación Gráfica del Montaje de Electrodos (10-20)
# ----------------------------------------------------------------------------
def draw_electrode_map(ax, available_channels=None, title="Dónde se mide cada biomarcador (vista superior)", show_legend=True):
    """
    Dibuja la vista superior del montaje de electrodos según la imagen de referencia:
    - Frente (superior), Izq. (izquierda), Der. (derecha).
    - Círculos de color:
        * Púrpura (#7c62db): Theta Fz
        * Azul (#2a82e4): FAA F3 / F4
        * Verde (#1ba06f): Alfa posterior O1, O2, Pz
    - Los canales presentes en available_channels se iluminan; los ausentes se muestran atenuados en gris.
    """
    if available_channels is None:
        available_channels = TARGET_CHANNELS
        
    avail_upper = set(c.upper() for c in available_channels)
    
    ax.clear()
    ax.set_aspect("equal")
    ax.axis("off")
    
    # 1. Cabeza (círculo principal con relleno beige suave)
    head_circ = patches.Circle((0, 0), 1.0, facecolor="#f8f7f3", edgecolor="#4a4a4a", lw=2.4, zorder=1)
    ax.add_patch(head_circ)
    
    # 2. Nariz (triángulo arriba)
    nose = patches.Polygon([(-0.13, 0.98), (0.0, 1.18), (0.13, 0.98)],
                           facecolor="#f8f7f3", edgecolor="#4a4a4a", lw=2.2, zorder=2)
    ax.add_patch(nose)
    
    # 3. Orejas (elipses)
    ear_l = patches.Ellipse((-1.01, 0.0), 0.11, 0.30, facecolor="#f8f7f3", edgecolor="#4a4a4a", lw=2.2, zorder=0)
    ear_r = patches.Ellipse((1.01, 0.0), 0.11, 0.30, facecolor="#f8f7f3", edgecolor="#4a4a4a", lw=2.2, zorder=0)
    ax.add_patch(ear_l)
    ax.add_patch(ear_r)
    
    # 4. Textos de orientación
    ax.text(0.0, 1.28, "Frente", ha="center", va="bottom", fontsize=11, color="#555555", fontweight="bold")
    ax.text(-1.26, 0.0, "Izq.", ha="right", va="center", fontsize=11, color="#555555", fontweight="bold")
    ax.text(1.26, 0.0, "Der.", ha="left", va="center", fontsize=11, color="#555555", fontweight="bold")
    
    # 5. Coordenadas y definición de electrodos
    # (Nombre, (x, y), color_activo, posición_etiqueta)
    electrodes = [
        ("F3", (-0.42, 0.44), "#2a82e4", "top"),
        ("Fz", (0.0, 0.44), "#7c62db", "top"),
        ("F4", (0.42, 0.44), "#2a82e4", "top"),
        ("Pz", (0.0, -0.14), "#1ba06f", "top"),
        ("O1", (-0.30, -0.68), "#1ba06f", "bottom"),
        ("O2", (0.30, -0.68), "#1ba06f", "bottom"),
    ]
    
    for name, (x, y), color, txt_pos in electrodes:
        is_active = name.upper() in avail_upper
        c_fill = color if is_active else "#eae8e4"
        c_edge = color if is_active else "#b0aca5"
        c_txt = color if is_active else "#9e9a93"
        alpha = 1.0 if is_active else 0.55
        
        # Círculo del electrodo
        dot = patches.Circle((x, y), 0.082, facecolor=c_fill, edgecolor=c_edge,
                             lw=2.2 if is_active else 1.2, alpha=alpha, zorder=5)
        ax.add_patch(dot)
        
        # Etiqueta
        ty = y + 0.11 if txt_pos == "top" else y - 0.11
        status_suffix = "" if is_active else "\n(n/d)"
        fontweight = "bold" if is_active else "normal"
        ax.text(x, ty, f"{name}{status_suffix}", ha="center",
                va="bottom" if txt_pos == "top" else "top",
                fontsize=10.5, color=c_txt, fontweight=fontweight, zorder=6)
                
    # Texto "Parieto-occipital"
    has_post = any(n.upper() in avail_upper for n in ["PZ", "O1", "O2"])
    post_color = "#007a50" if has_post else "#9e9a93"
    ax.text(0.0, -0.92, "Parieto-occipital", ha="center", va="top",
            fontsize=11.5, fontweight="bold", color=post_color)
    
    # Leyenda al pie
    if show_legend:
        legend_elements = [
            mlines.Line2D([0], [0], marker='o', color='w', label='Alfa: O1, O2, Pz',
                          markerfacecolor='#1ba06f', markersize=10),
            mlines.Line2D([0], [0], marker='o', color='w', label='Theta: Fz',
                          markerfacecolor='#7c62db', markersize=10),
            mlines.Line2D([0], [0], marker='o', color='w', label='FAA: F3 / F4 (referencia)',
                          markerfacecolor='#2a82e4', markersize=10),
        ]
        ax.legend(handles=legend_elements, loc='lower center', bbox_to_anchor=(0.5, -0.17),
                  ncol=3, frameon=False, fontsize=9.5)
                  
    if title:
        ax.set_title(title, fontsize=13, fontweight="bold", pad=14)
        
    ax.set_xlim(-1.45, 1.45)
    ax.set_ylim(-1.22, 1.38)


# ----------------------------------------------------------------------------
# Procesamiento de Señales y Carga Inteligente
# ----------------------------------------------------------------------------
def numeric_sort_key(filename):
    m = re.search(r'(\d+)\.(?:txt|csv)$', filename)
    return int(m.group(1)) if m else 0


def load_eeg(path):
    """
    Carga registros EEG adaptándose automáticamente a los canales disponibles en el archivo.
    
    Estrategia de modulación automática:
    1. Si el archivo posee encabezados con nombres de canales:
       Detecta cuáles de TARGET_CHANNELS están presentes y extrae exactamente esos.
    2. Si es un archivo sin encabezados numérico (ej. OpenBCI Cyton Stroop: >= 8 columnas):
       El montaje estándar OpenBCI Stroop es [Fp1, Fp2, F7, F3, Fz, F4, F8, C2].
       Extrae los canales objetivo disponibles: F3 (col 4), F4 (col 6) y Fz (col 5).
    3. Si tiene exactamente 6 o 7 columnas (índice + 6):
       Mapea directamente a TARGET_CHANNELS = ['F3', 'F4', 'Fz', 'Pz', 'O1', 'O2'].
    4. Si tiene 3 columnas:
       Mapea a ['F3', 'F4', 'Fz'].
       
    Devuelve: (data_matrix (n, n_canales), lista_canales_detectados)
    """
    try:
        # Inspeccionar primeras filas para detectar nombres de columnas
        preview = pd.read_csv(path, nrows=5, comment='%', skipinitialspace=True, sep=r'[,\t]+', engine="python")
        col_map = {str(c).strip().lower(): c for c in preview.columns}
        
        # Buscar cuáles de TARGET_CHANNELS están presentes en el encabezado
        matched = [ch for ch in TARGET_CHANNELS if ch.lower() in col_map]
        if matched:
            cols_to_use = [col_map[ch.lower()] for ch in matched]
            df = pd.read_csv(path, comment='%', skipinitialspace=True, sep=r'[,\t]+',
                             engine="python", usecols=cols_to_use)
            df = df[cols_to_use].apply(pd.to_numeric, errors="coerce").dropna()
            return df.to_numpy(dtype=float), matched
    except Exception:
        pass

    # Lectura numérica sin encabezados
    df = pd.read_csv(path, delimiter=",", header=None, comment='%',
                     skipinitialspace=True, engine="python", on_bad_lines="skip")
    df = df.apply(pd.to_numeric, errors="coerce").dropna(how="all")
    n_cols = df.shape[1]
    
    if n_cols >= 8:
        # Formato OpenBCI Cyton (Stroop Data)
        # Col 0 = muestra, 1=Fp1, 2=Fp2, 3=F7, 4=F3, 5=Fz, 6=F4, 7=F8, 8=C2
        # Extraemos F3, F4, Fz (Pz, O1, O2 no existen en este montaje de hardware)
        df_target = df.iloc[:, [4, 6, 5]].copy()
        df_target.columns = ['F3', 'F4', 'Fz']
        df_target = df_target.dropna()
        return df_target.to_numpy(dtype=float), ['F3', 'F4', 'Fz']
        
    elif n_cols == 7:
        # Columna 0 es índice, columnas 1..6 son los 6 canales objetivo
        df_target = df.iloc[:, 1:7].dropna()
        return df_target.to_numpy(dtype=float), list(TARGET_CHANNELS)
        
    elif n_cols == 6:
        # Exactamente 6 canales directos
        df_target = df.iloc[:, 0:6].dropna()
        return df_target.to_numpy(dtype=float), list(TARGET_CHANNELS)
        
    elif n_cols == 4:
        # Columna 0 índice + 3 canales frontales
        df_target = df.iloc[:, 1:4].dropna()
        return df_target.to_numpy(dtype=float), ['F3', 'F4', 'Fz']
        
    elif n_cols == 3:
        # 3 canales frontales
        df_target = df.iloc[:, 0:3].dropna()
        return df_target.to_numpy(dtype=float), ['F3', 'F4', 'Fz']
        
    else:
        raise ValueError(
            f"El archivo contiene {n_cols} columnas numéricas y no coincide con un formato soportado."
        )


def repair_artifacts(x, fs, thr_uv=150.0, pad_s=0.15, max_frac=0.25):
    """Reparación de picos e interferencias mediante interpolación local."""
    x = x.copy()
    bad = ndimage.binary_dilation(np.abs(x) > thr_uv,
                                  structure=np.ones((int(pad_s * fs) * 2 + 1, 1)))
    idx = np.arange(len(x))
    for ch in range(x.shape[1]):
        b = bad[:, ch]
        if b.any() and b.mean() <= max_frac:
            x[b, ch] = np.interp(idx[b], idx[~b], x[~b, ch])
    return x


def preprocess(x, fs, bandpass=True, notch=None, trim_seconds=3.0):
    """Pipeline: trim inicial (3s) -> centrado DC -> filtros -> reparar artefactos."""
    x = x[int(trim_seconds * fs):] if len(x) > int(trim_seconds * fs) else x

    # Centrado para remover offsets de electrodo
    x = x - np.median(x, axis=0)

    nyq = fs / 2
    if bandpass and len(x) > 100:
        sos = signal.butter(4, [1.0, min(40.0, nyq * 0.95)], btype="band", fs=fs, output="sos")
        x = signal.sosfiltfilt(sos, x, axis=0)
    if notch and notch < nyq and len(x) > 100:
        b, a = signal.iirnotch(notch, Q=30, fs=fs)
        x = signal.filtfilt(b, a, x, axis=0)

    return repair_artifacts(x, fs)


def compute_psd(x, fs):
    """PSD de Welch por canal."""
    nperseg = int(min(len(x), 2 * fs))
    f, P = signal.welch(x, fs=fs, nperseg=nperseg, noverlap=nperseg // 2,
                        window="hann", axis=0, detrend="constant")
    return f, P.T


def band_powers(f, P):
    """Potencia absoluta en µV² para cada banda."""
    df = f[1] - f[0]
    out = {}
    for name, (lo, hi) in BANDS.items():
        m = (f >= lo) & (f < hi)
        out[name] = P[:, m].sum(axis=1) * df
    return out


def cognitive_indices(bp):
    """Cálculo de ratios de carga cognitiva."""
    eps = 1e-12
    th, al, be = bp["Theta"], bp["Alpha"], bp["Beta"]
    return {
        "Theta/Alpha": th / (al + eps),
        "Beta/Alpha": be / (al + eps),
        "Engagement β/(α+θ)": be / (al + th + eps),
    }


def alpha_channels(channels):
    """Encuentra los índices y etiqueta de los canales alfa posteriores disponibles."""
    ch_map = {n.upper(): i for i, n in enumerate(channels)}
    idx = [ch_map[n.upper()] for n in ALPHA_CHANNELS if n.upper() in ch_map]
    label = "/".join([channels[i] for i in idx]) if idx else "N/A"
    return idx, label


def band_filter(x, fs, lo, hi):
    """Filtro pasa-banda Butterworth."""
    hi = min(hi, fs / 2 * 0.95)
    if lo <= 0:
        sos = signal.butter(4, hi, btype="low", fs=fs, output="sos")
    else:
        sos = signal.butter(4, [lo, hi], btype="band", fs=fs, output="sos")
    return signal.sosfiltfilt(sos, x, axis=0)


def _metrics_from_bp(bp, channels):
    """Extrae theta Fz, alfa posterior y FAA de forma modular según los canales presentes."""
    eps = 1e-12
    ch_map = {n.upper(): i for i, n in enumerate(channels)}
    
    th_i = ch_map.get(THETA_CH.upper(), None)
    a_idx, _ = alpha_channels(channels)
    l = ch_map.get(FAA_L.upper(), None)
    r = ch_map.get(FAA_R.upper(), None)
    
    theta = float(bp["Theta"][th_i]) if th_i is not None else np.nan
    alpha = float(np.mean(bp["Alpha"][a_idx])) if a_idx else np.nan
    faa = (float(np.log(bp["Alpha"][r] + eps) - np.log(bp["Alpha"][l] + eps))
           if (l is not None and r is not None) else np.nan)
           
    return theta, alpha, faa


def biomarker_summary(x, fs, dur, channels):
    """Resumen de biomarcadores tónicos adaptado a los canales activos."""
    f, P = compute_psd(x, fs)
    bp = band_powers(f, P)
    tot = sum(bp.values())
    theta, alpha, faa = _metrics_from_bp(bp, channels)
    ch_map = {n.upper(): i for i, n in enumerate(channels)}
    th_i = ch_map.get(THETA_CH.upper(), None)
    
    rel_theta = (float(bp["Theta"][th_i] / tot[th_i] * 100)
                 if (th_i is not None and tot[th_i] > 0) else np.nan)
                 
    return {
        "theta_fz": theta,
        "theta_fz_rel": rel_theta,
        "alpha": alpha,
        "faa": faa,
    }


def window_biomarkers(x, fs, win_s, step_s, channels):
    """Evolución temporal de biomarcadores en ventanas deslizantes."""
    n, win, step = len(x), int(win_s * fs), max(1, int(step_s * fs))
    starts = np.arange(0, n - win + 1, step)
    out = {"t": [], "theta": [], "alpha": [], "faa": []}
    for s0 in starts:
        f, P = compute_psd(x[s0:s0 + win], fs)
        theta, alpha, faa = _metrics_from_bp(band_powers(f, P), channels)
        t0 = s0 / fs
        out["t"].append(t0 + win_s / 2)
        out["theta"].append(theta)
        out["alpha"].append(alpha)
        out["faa"].append(faa)
    return {k: np.array(v, dtype=float) for k, v in out.items()}


def robust_limits(y, robust=True, pad=0.12):
    lo, hi = (np.percentile(y, [0.5, 99.5]) if robust else (y.min(), y.max()))
    if hi - lo < 1e-9:
        lo, hi = lo - 1, hi + 1
    m = (hi - lo) * pad
    return lo - m, hi + m


# ----------------------------------------------------------------------------
# Ventana Secundaria: PSD y Biomarcadores
# ----------------------------------------------------------------------------
class PSDWindow(tk.Toplevel):
    def __init__(self, app):
        super().__init__(app.root)
        self.app = app
        self.title("Densidad Espectral de Potencia & Biomarcadores Cognitivos")
        self.geometry("1220x820")

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
        tab1, tabB = ttk.Frame(nb), ttk.Frame(nb)
        nb.add(tab1, text="Espectro del archivo")
        nb.add(tabB, text="Biomarcadores del scope")

        # Pestaña 1: Espectro y distribución de potencia
        self.fig = Figure(figsize=(11, 7))
        gs = self.fig.add_gridspec(2, 2, height_ratios=[1.6, 1], width_ratios=[1.6, 1])
        self.ax_psd = self.fig.add_subplot(gs[0, :])
        self.ax_bar = self.fig.add_subplot(gs[1, 0])
        self.ax_txt = self.fig.add_subplot(gs[1, 1])
        self.canvas = FigureCanvasTkAgg(self.fig, master=tab1)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        NavigationToolbar2Tk(self.canvas, tab1)

        # Pestaña 2: Biomarcadores tónicos y mapa integrado
        self.fig3 = Figure(figsize=(11, 7.5))
        self.canvas3 = FigureCanvasTkAgg(self.fig3, master=tabB)
        self.canvas3.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        NavigationToolbar2Tk(self.canvas3, tabB)

        self.refresh()

    def _segment(self):
        a = self.app
        if a.data is None or not a.channels:
            return None
        if self.seg_var.get() == "Registro completo":
            seg = a.data
        else:
            i0, i1 = a.window_bounds()
            seg = a.data[i0:i1]
        idx = a.visible_idx()
        return seg[:, idx], [a.channels[i] for i in idx]

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
        ax.set_title(f"PSD de Welch - {self.app.current_label()} ({len(seg) / fs:.1f} s)")
        ax.grid(True, ls="--", alpha=0.4)
        ax.legend(ncol=min(len(names) + 1, 7), fontsize=8, loc="lower left")

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
        lines = ["Índices de carga cognitiva", "(canales visibles en pantalla)", ""]
        for k, v in idx.items():
            lines.append(f"{k}:  {np.mean(v):.2f}")
            
        fr = [i for i, n in enumerate(names) if n in FRONTAL_TARGETS]
        if fr:
            lines += ["", f"θ frontal (µV²):  {np.mean(bp['Theta'][fr]):.2f}"]
            
        post = [i for i, n in enumerate(names) if n in POSTERIOR_TARGETS]
        if post:
            lines += [f"α posterior (µV²):  {np.mean(bp['Alpha'][post]):.2f}"]
        else:
            lines += ["α posterior: n/d (requiere Pz, O1 u O2)"]
            
        ax.text(0.0, 1.0, "\n".join(lines), va="top", fontsize=10, family="monospace")
        self.fig.tight_layout()
        self.canvas.draw_idle()

    def refresh_biomarkers(self):
        a = self.app
        if a.data is None or not a.channels:
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

        seg = a.data[i0:i1]
        ch_map = {c.upper(): i for i, c in enumerate(a.channels)}
        has_fz = THETA_CH.upper() in ch_map
        has_faa = (FAA_L.upper() in ch_map) and (FAA_R.upper() in ch_map)
        _, a_label = alpha_channels(a.channels)
        has_alpha = a_label != "N/A"

        gs = fig.add_gridspec(3, 2, height_ratios=[1.1, 1, 1], width_ratios=[1.5, 1])
        ax0 = fig.add_subplot(gs[0, :])
        t = np.arange(i0, i1) / fs

        if has_fz:
            th_sig = band_filter(seg[:, ch_map[THETA_CH.upper()]], fs, *BANDS["Theta"])
            ax0.plot(t, th_sig, color=BAND_COLORS["Theta"], lw=0.9, label=f"Theta {THETA_CH} (4-8 Hz)")
            lo, hi = robust_limits(th_sig, False)
            ax0.set_ylim(lo, hi)
            ax0.set_title(f"Señal Theta {THETA_CH} filtrada (4-8 Hz) - Control cognitivo / Fatiga", fontsize=10)
        else:
            ax0.text(0.5, 0.5, f"Canal {THETA_CH} no disponible en este registro.", ha="center", va="center", fontsize=10, color="gray")
            ax0.set_title(f"Theta {THETA_CH} (No disponible)", fontsize=10)
            
        ax0.set_xlim(t0, t1)
        ax0.set_xlabel("Tiempo (s)")
        ax0.set_ylabel("µV")
        ax0.grid(True, ls="--", alpha=0.4)
        if has_fz:
            ax0.legend(loc="upper right", fontsize=8)

        win_s = float(np.clip(dur / 6, 4, 10))
        step_s = win_s / 2
        enough = dur >= 8
        ax1 = fig.add_subplot(gs[1, 0])
        ax2 = fig.add_subplot(gs[2, 0], sharex=ax1)
        ax3 = fig.add_subplot(gs[1, 1])
        ax4 = fig.add_subplot(gs[2, 1])
        ax3.axis("off")

        if enough:
            wb = window_biomarkers(seg, fs, win_s, step_s, a.channels)
            unit, ulabel = (60.0, "min") if dur >= 120 else (1.0, "s")
            tc = (t0 + wb["t"]) / unit
            nb_ = max(1, int(round(0.2 * len(tc))))

            def norm(v):
                base = np.nanmean(v[:nb_])
                return v / base if np.isfinite(base) and base > 0 else v * np.nan

            if has_fz:
                th_n = norm(wb["theta"])
                ax1.plot(tc, th_n, color=BAND_COLORS["Theta"], lw=2.2, label=f"Theta tónico ({THETA_CH})")
            if has_alpha:
                al_n = norm(wb["alpha"])
                ax1.plot(tc, al_n, color=BAND_COLORS["Alpha"], lw=2.2, label=f"Alfa tónico ({a_label})")
                
            ax1.axhline(1.0, color="gray", ls=":", lw=1)
            ax1.set_ylabel("Relativo a base")
            if has_fz or has_alpha:
                ax1.legend(fontsize=8, loc="best")
            ax1.grid(True, ls="--", alpha=0.4)
            ax1.tick_params(labelbottom=False)

            if has_faa:
                ax2.plot(tc, wb["faa"], color="#1f77b4", lw=2, marker="o", ms=3, label=f"FAA (ln α({FAA_R}) − ln α({FAA_L}))")
                ax2.axhline(0, color="gray", ls=":", lw=1)
                ax2.set_ylabel("FAA")
                ax2.legend(fontsize=8, loc="best")
            else:
                ax2.text(0.5, 0.5, "FAA no disponible (requiere F3 y F4)", ha="center", va="center", color="gray", fontsize=9)
                ax2.set_ylabel("FAA (n/d)")
                
            ax2.set_xlabel(f"Tiempo ({ulabel})")
            ax2.grid(True, ls="--", alpha=0.4)

        s = biomarker_summary(seg, fs, dur, a.channels)

        def fmt(v, f="{:.2f}"):
            return f.format(v) if np.isfinite(v) else "n/d"

        L = [
            f"Biomarcadores ({dur:.1f} s post-trim)",
            "",
            f"Canales presentes: {', '.join(a.channels)}",
            "",
            f"θ tónico {THETA_CH}:        {fmt(s['theta_fz'])} µV²  ({fmt(s['theta_fz_rel'], '{:.1f}')}% rel)" if has_fz else f"θ tónico {THETA_CH}:        No disponible",
            f"α tónico {a_label}: {fmt(s['alpha'])} µV²" if has_alpha else "α posterior:       No disponible (Faltan Pz/O1/O2)",
            f"FAA ({FAA_R} vs {FAA_L}):   {fmt(s['faa'])}" if has_faa else "FAA:               No disponible (Faltan F3 o F4)",
        ]
        ax3.text(0.0, 1.0, "\n".join(L), va="top", fontsize=9, family="monospace", transform=ax3.transAxes)
        
        # Mini representación visual del mapa de electrodos en ax4
        draw_electrode_map(ax4, a.channels, title="", show_legend=False)
        ax4.set_title("Montaje 10-20 activo", fontsize=9, fontweight="bold", pad=4)
        
        fig.tight_layout()
        self.canvas3.draw_idle()


# ----------------------------------------------------------------------------
# Aplicación Principal: EEGViewer con Pestaña de Mapa Integrada
# ----------------------------------------------------------------------------
class EEGViewer:
    def __init__(self, root, directory):
        self.root = root
        self.directory = directory
        self.data = None          
        self.channels = []  # Lista dinámica de canales presentes en el archivo cargado
        self.fs = DEFAULT_FS
        self.axes, self.lines = [], []
        self.psd_win = None
        self.band_cache = {}
        self.band_show_var = tk.StringVar(value="Cruda (filtrada)")
        self.root.title("Visualizador de Señales EEG & Biomarcadores (10-20)")
        self.root.geometry("1480x880")

        self._scan_directory()
        self._build_controls()
        self._build_plot()

        if self.levels_dict:
            self.level_combobox.set(list(self.levels_dict)[0])
            self.on_level_changed()

    def _scan_directory(self):
        files = [f for f in os.listdir(self.directory) if f.endswith(('.txt', '.csv'))]
        matched = {}
        for lvl, p in LEVEL_PREFIX.items():
            sub = sorted([f for f in files if f.lower().startswith(p)], key=numeric_sort_key)
            if sub:
                matched[lvl] = sub
        if matched:
            self.levels_dict = matched
        else:
            self.levels_dict = {"Todos": sorted(files, key=numeric_sort_key)}

    def _build_controls(self):
        c = ttk.Frame(self.root, padding=12)
        c.pack(side=tk.LEFT, fill=tk.Y)
        bold = ("Arial", 10, "bold")

        ttk.Label(c, text="Nivel / Carpeta:", font=bold).pack(anchor="w")
        self.level_var = tk.StringVar()
        self.level_combobox = ttk.Combobox(c, textvariable=self.level_var, state="readonly",
                                           values=list(self.levels_dict), width=28)
        self.level_combobox.pack(pady=(2, 8))
        self.level_combobox.bind("<<ComboboxSelected>>", self.on_level_changed)

        ttk.Label(c, text="Archivo:", font=bold).pack(anchor="w")
        self.file_var = tk.StringVar()
        self.file_combobox = ttk.Combobox(c, textvariable=self.file_var, state="readonly", width=28)
        self.file_combobox.pack(pady=(2, 8))
        self.file_combobox.bind("<<ComboboxSelected>>", lambda e: self.load_file())

        ttk.Separator(c).pack(fill=tk.X, pady=6)
        ttk.Label(c, text="Frecuencia de muestreo (Hz):", font=bold).pack(anchor="w")
        self.fs_var = tk.StringVar(value=str(int(DEFAULT_FS)))
        fs_e = ttk.Entry(c, textvariable=self.fs_var, width=10)
        fs_e.pack(anchor="w", pady=(2, 6))
        fs_e.bind("<Return>", lambda e: self.load_file())

        ttk.Label(c, text="Filtros:", font=bold).pack(anchor="w")
        self.bandpass_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(c, text="Pasa-banda 1-40 Hz", variable=self.bandpass_var,
                        command=self.load_file).pack(anchor="w")
        self.notch_var = tk.StringVar(value="Sin notch")
        nb = ttk.Combobox(c, textvariable=self.notch_var, state="readonly", width=14,
                          values=["Sin notch", "Notch 50 Hz", "Notch 60 Hz"])
        nb.pack(anchor="w", pady=(2, 6))
        nb.bind("<<ComboboxSelected>>", lambda e: self.load_file())

        ttk.Separator(c).pack(fill=tk.X, pady=6)
        ttk.Label(c, text="Escalado:", font=bold).pack(anchor="w")
        self.autoscale_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(c, text="Autoescala por canal", variable=self.autoscale_var,
                        command=self.redraw).pack(anchor="w")
        self.robust_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(c, text="Robusta (ignora artefactos)", variable=self.robust_var,
                        command=self.redraw).pack(anchor="w", pady=(0, 6))

        ttk.Label(c, text="Señal mostrada:", font=bold).pack(anchor="w")
        bs = ttk.Combobox(c, textvariable=self.band_show_var, state="readonly", width=18,
                          values=["Cruda (filtrada)"] + list(BANDS))
        bs.pack(anchor="w", pady=(2, 6))
        bs.bind("<<ComboboxSelected>>", lambda e: self.redraw())

        # Contenedor dinámico de checkboxes según canales detectados
        ttk.Label(c, text="Canales detectados en archivo:", font=bold).pack(anchor="w", pady=(4, 2))
        self.ch_frame = ttk.Frame(c)
        self.ch_frame.pack(anchor="w", fill=tk.X)
        self.ch_vars = []

        ttk.Separator(c).pack(fill=tk.X, pady=8)
        ttk.Button(c, text="🧠 Ver mapa de electrodos",
                   command=lambda: self.main_notebook.select(1)).pack(fill=tk.X, pady=(2, 4))
        ttk.Button(c, text="📊 Analizar PSD / biomarcadores", command=self.open_psd).pack(fill=tk.X, pady=2)
        ttk.Button(c, text="📁 Cambiar carpeta de datos...", command=self.change_dir).pack(fill=tk.X, pady=(4, 0))
        
        self.info_label = ttk.Label(c, text="", wraplength=220, justify="left")
        self.info_label.pack(anchor="w", pady=8)

    def _build_plot(self):
        right = ttk.Frame(self.root)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Notebook principal con dos pestañas: Señales Continuas y Mapa de Electrodos
        self.main_notebook = ttk.Notebook(right)
        self.main_notebook.pack(fill=tk.BOTH, expand=True)

        # ----------------------------------------------------
        # Pestaña 1: Señales EEG
        # ----------------------------------------------------
        tab_signals = ttk.Frame(self.main_notebook)
        self.main_notebook.add(tab_signals, text="  📈 Señales EEG  ")

        self.fig = Figure(figsize=(10, 8))
        self.canvas = FigureCanvasTkAgg(self.fig, master=tab_signals)

        nav = ttk.Frame(tab_signals, padding=(8, 4))
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

        NavigationToolbar2Tk(self.canvas, tab_signals).pack(side=tk.BOTTOM, fill=tk.X)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # ----------------------------------------------------
        # Pestaña 2: Representación Visual del Montaje (10-20)
        # ----------------------------------------------------
        tab_map = ttk.Frame(self.main_notebook)
        self.main_notebook.add(tab_map, text="  🧠 Mapa de Electrodos (10-20)  ")

        self.fig_map = Figure(figsize=(7.5, 7.5))
        self.ax_map = self.fig_map.add_subplot(1, 1, 1)
        self.canvas_map = FigureCanvasTkAgg(self.fig_map, master=tab_map)
        self.canvas_map.get_tk_widget().pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        info_map_frame = ttk.Frame(tab_map, padding=16)
        info_map_frame.pack(side=tk.RIGHT, fill=tk.BOTH, padx=10, expand=False)
        
        ttk.Label(info_map_frame, text="Estado del Registro", font=("Arial", 12, "bold")).pack(anchor="w", pady=(0, 8))
        self.map_status_label = ttk.Label(info_map_frame, text="", wraplength=340, justify="left", font=("Arial", 10))
        self.map_status_label.pack(anchor="w", pady=4)
        
        ttk.Separator(info_map_frame).pack(fill=tk.X, pady=12)
        ttk.Button(info_map_frame, text="📈 Ver señales continuas",
                   command=lambda: self.main_notebook.select(0)).pack(fill=tk.X, pady=4)
        ttk.Button(info_map_frame, text="📊 Analizar PSD / biomarcadores",
                   command=self.open_psd).pack(fill=tk.X, pady=4)

        self.root.bind("<Left>", lambda e: self.step(-1))
        self.root.bind("<Right>", lambda e: self.step(1))

    def notch_value(self):
        s = self.notch_var.get()
        return 50.0 if "50" in s else 60.0 if "60" in s else None

    def visible_idx(self):
        idx = [i for i, v in enumerate(self.ch_vars) if v.get()]
        return idx or list(range(len(self.channels)))

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
            self.channels = []

    def _update_channel_checkboxes(self):
        """Reconstruye dinámicamente los checkboxes según los canales detectados en el archivo."""
        for w in self.ch_frame.winfo_children():
            w.destroy()
        self.ch_vars = []
        for n in self.channels:
            v = tk.BooleanVar(value=True)
            cb = ttk.Checkbutton(self.ch_frame, text=n, variable=v, command=self.rebuild_axes)
            cb.pack(anchor="w")
            self.ch_vars.append(v)

    def update_map(self):
        """Actualiza el mapa de electrodos y el texto informativo según los canales del archivo."""
        draw_electrode_map(self.ax_map, self.channels)
        self.fig_map.tight_layout()
        self.canvas_map.draw_idle()

        avail_upper = set(c.upper() for c in self.channels)
        missing = [c for c in TARGET_CHANNELS if c.upper() not in avail_upper]

        lines = [
            f"Archivo actual: {self.current_label()}",
            f"Frecuencia: {self.fs:g} Hz | Muestras: {len(self.data) if self.data is not None else 0}",
            f"Canales disponibles ({len(self.channels)}): {', '.join(self.channels)}",
            ""
        ]
        if missing:
            lines += [
                f"⚠️ Canales ausentes ({len(missing)}): {', '.join(missing)}",
                "• Este archivo no contiene electrodos parieto-occipitales (Pz, O1, O2).",
                "• El programa se ha modulado automáticamente para procesar únicamente los canales existentes.",
                ""
            ]
        else:
            lines += [
                "✅ Todos los electrodos objetivo (6/6) están presentes en este registro.",
                ""
            ]

        lines += [
            "Disponibilidad de biomarcadores:",
            f" • Theta Fz: {'✅ DISPONIBLE' if 'FZ' in avail_upper else '❌ NO DISPONIBLE (Falta Fz)'}",
            f" • FAA (F3 / F4): {'✅ DISPONIBLE' if ('F3' in avail_upper and 'F4' in avail_upper) else '❌ NO DISPONIBLE (Faltan F3 o F4)'}",
            f" • Alfa posterior (Pz, O1, O2): {'✅ DISPONIBLE' if any(c in avail_upper for c in ['PZ', 'O1', 'O2']) else '❌ NO DISPONIBLE (Faltan Pz/O1/O2)'}",
        ]
        self.map_status_label.config(text="\n".join(lines))

    def load_file(self):
        fn = self.file_var.get()
        if not fn:
            return
        try:
            self.fs = float(self.fs_var.get())
            raw, detected_channels = load_eeg(os.path.join(self.directory, fn))
            if raw.shape[0] < 10 or raw.shape[1] < 1:
                raise ValueError("El archivo no contiene suficientes muestras o canales legibles.")
                
            self.channels = detected_channels
            self.data = preprocess(raw, self.fs, self.bandpass_var.get(), self.notch_value(), trim_seconds=3.0)
            self.band_cache = {}
        except Exception as e:
            messagebox.showerror("Error al cargar", f"{fn}\n\n{e}")
            return
            
        dur = len(self.data) / self.fs
        missing = [c for c in TARGET_CHANNELS if c not in self.channels]
        status_txt = f"{len(self.channels)} canales ({', '.join(self.channels)})\n{dur:.1f} s a {self.fs:g} Hz"
        if missing:
            status_txt += f"\nAusentes: {', '.join(missing)}"
        self.info_label.config(text=status_txt)
        
        self.start_var.set(0.0)
        self._update_channel_checkboxes()
        self.on_window_changed()
        self.update_map()
        
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
        if self.data is None or not self.channels:
            self.canvas.draw_idle()
            return
            
        idx = self.visible_idx()
        self.axes = self.fig.subplots(len(idx), 1, sharex=True, squeeze=False)[:, 0]
        self.lines = []
        for ax, ch in zip(self.axes, idx):
            (ln,) = ax.plot([], [], color="#1f4e9c", lw=0.8)
            self.lines.append((ch, ln))
            ax.set_ylabel(f"{self.channels[ch]}\n(µV)", fontsize=8, fontweight="bold")
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

        band = self.band_show_var.get()
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

    def open_psd(self):
        if self.data is None:
            return
        if self.psd_win is not None and self.psd_win.winfo_exists():
            self.psd_win.lift()
            self.psd_win.refresh()
        else:
            self.psd_win = PSDWindow(self)

    def change_dir(self):
        d = filedialog.askdirectory(title="Selecciona la carpeta con los archivos EEG (.txt o .csv)")
        if d:
            self.directory = d
            self._scan_directory()
            self.level_combobox['values'] = list(self.levels_dict)
            if self.levels_dict:
                self.level_combobox.set(list(self.levels_dict)[0])
                self.on_level_changed()


def main():
    root = tk.Tk()
    directory = DIRECTORY_PATH
    if not os.path.isdir(directory):
        directory = filedialog.askdirectory(title="Selecciona la carpeta de datos EEG")
        if not directory:
            root.destroy()
            return
    EEGViewer(root, directory)
    root.mainloop()


if __name__ == "__main__":
    main()