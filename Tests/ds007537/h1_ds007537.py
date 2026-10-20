"""
Validación de H1 con OpenNeuro ds007537 (Mishra et al., 2026)
===============================================================
H1 (fatiga, componente tónico): durante 10 min de uso libre del smartphone, la potencia
theta frontal-medial (Fz/FCz) y la alfa posterior (Pz/POz/O1/O2), normalizadas a los
primeros 2 min, AUMENTAN con el tiempo. Se espera un efecto más claro en video corto (S)
que en juegos (G).

Pipeline por sujeto
  1. Lee BrainVision (64 EEG + GSR/PPG); Cz es la referencia de registro (plana).
  2. Recorta [S12 inicial - 5 s, S23 final + 5 s], filtra 1-40 Hz (quita también la red de 50 Hz), remuestrea a 250 Hz.
  3. Interpola canales rotos (MAD), detecta parpadeos en Fp1, referencia promedio e ICA (infomax)
     para quitar los componentes oculares.
  4. Sesión smartphone = [primer S12, primer S13); video = [primer S22, primer S23).
  5. Épocas de 2 s; se rechazan las de amplitud pico a pico > 150 µV en los canales de interés.
  6. PSD de Welch por época, frecuencia alfa individual (IAF) del sujeto y bandas relativas a la IAF.
  7. Por minuto:
       - potencia total (dB) theta Fz/FCz y alfa Pz/POz/O1/O2 (bandas IAF y fijas);
       - potencia PERIÓDICA (dB sobre el fondo 1/f, specparam) y exponente aperiódico;
       - parpadeos/min desde el EEG (Fp1) y desde el eye-tracker;
       - diámetro pupilar (eye-tracker alineado con los pulsos TTL).
  8. Cambio contra los minutos 1-2 y pendiente por sujeto.
Grupo: pendientes contra 0 (t y Wilcoxon), S vs G (Mann-Whitney), minutos finales vs iniciales,
correlación con SAS/MPPUS y relaciones entre la alfa y los marcadores de activación.

Uso:
  python h1_ds007537.py "C:/ruta/ds007537"            (todos los sujetos con datos descargados)
  python h1_ds007537.py "C:/ruta/ds007537" sub-01      (uno o varios sujetos)
Los resultados por sujeto se guardan en results/cache_v2 para no recalcular.
"""
import os
import sys
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats, ndimage, signal
import mne
from specparam import SpectralModel

mne.set_log_level("ERROR")
sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "results")
CACHE = os.path.join(OUT, "cache_v2")

FS = 250.0
EPOCH_S = 2.0
PTP_UV = 150.0
THETA_ROI = ["Fz", "FCz"]
ALPHA_ROI = ["Pz", "POz", "O1", "O2"]
ROI = THETA_ROI + ALPHA_ROI
BASE_MIN = 2  # minutos iniciales usados como línea base
MARK = {"sync": 11, "phone_on": 12, "phone_off": 13, "video_on": 22, "video_off": 23}
APP = {"S": "Video corto", "G": "Juego", "R": "Lectura"}
# Registros con < 40 % de épocas válidas en el video y ruido alto en el smartphone (ver h1_calidad.csv)
EXCLUDE = {"sub-22", "sub-23", "sub-27"}
FIT_RANGE = [2, 40]  # Hz, ajuste de specparam
ET_HZ = 100.0        # muestreo del Tobii Pro Glasses 2
BLINK_SAMPLES = (6, 50)  # 60-500 ms sin pupila = parpadeo (más largo = pérdida de registro)
ET_MAX_MISSING = 0.20    # al mirar el teléfono el Tobii pierde la pupila; minutos peores se anulan

METRICS = {  # columna: (título, unidad)
    "theta_iaf": ("Theta tónico Fz/FCz (potencia total)", "dB"),
    "alpha_iaf": ("Alfa posterior (potencia total)", "dB"),
    "theta_per": ("Theta periódico Fz/FCz (sobre 1/f)", "dB"),
    "alpha_per": ("Alfa posterior periódica (sobre 1/f)", "dB"),
    "exp_post": ("Exponente aperiódico posterior", "u.a."),
    "theta_fix": ("Theta 4-8 Hz (banda fija)", "dB"),
    "alpha_fix": ("Alfa 8-13 Hz (banda fija)", "dB"),
    "blink_eeg": ("Parpadeos/min (EEG, Fp1)", "/min"),
    "blink_et": ("Parpadeos/min (eye-tracker)", "/min"),
    "pupil_mm": ("Diámetro pupilar", "mm"),
}


# ---------------------------------------------------------------------------- sujeto
def markers(events_tsv):
    ev = pd.read_csv(events_tsv, sep="\t")
    ev = ev[ev["trial_type"].astype(str).str.startswith("Stimulus")]
    first = ev.groupby("value")["onset"].min()
    return {k: float(first[v]) for k, v in MARK.items()}


def is_downloaded(vhdr):
    eeg = vhdr[:-5] + ".eeg"
    return os.path.exists(eeg) and os.path.getsize(eeg) > 1_000_000


def preprocess(vhdr, m):
    raw = mne.io.read_raw_brainvision(vhdr, preload=False)
    raw.set_channel_types({c: "misc" for c in ("GSR", "PPG") if c in raw.ch_names})
    raw.crop(max(0, m["phone_on"] - 5), min(raw.times[-1], m["video_off"] + 5)).load_data()
    raw.pick("eeg")
    raw.filter(1.0, 40.0, picks="eeg")  # el pasa-bajas a 40 Hz ya elimina la red de 50 Hz
    raw.resample(FS)
    # Canales muertos o saturados (p. ej. P7/PO4 en sub-03): se interpolan antes de la referencia promedio.
    # Cz se excluye porque es la referencia de registro (vale 0) y se reconstruye con la referencia promedio.
    # MAD en vez de std: los parpadeos (transitorios) no hacen que Fp1/Fp2 parezcan canales rotos.
    x = raw.get_data()
    sd = np.median(np.abs(x - np.median(x, axis=1, keepdims=True)), axis=1)
    med = np.median(sd)
    raw.info["bads"] = [c for c, s in zip(raw.ch_names, sd) if c != "Cz" and (s > 5 * med or s < 0.05 * med)]
    bads = list(raw.info["bads"])
    if bads:
        raw.set_montage("standard_1005", on_missing="ignore")
        raw.interpolate_bads(reset_bads=True)
    blink_t = detect_blinks(raw)
    raw.set_eeg_reference("average")
    ica = mne.preprocessing.ICA(n_components=20, method="infomax", random_state=97, max_iter=800)
    ica.fit(raw, decim=2, reject=dict(eeg=500e-6))
    eog_ic, _ = ica.find_bads_eog(raw, ch_name=["Fp1", "Fp2"], threshold=3.0)
    ica.exclude = eog_ic[:3]  # ponytail: solo ojos; añadir ICLabel si el músculo resulta un problema
    ica.apply(raw)
    return raw, len(ica.exclude), bads, blink_t


def detect_blinks(raw):
    """Parpadeos en (Fp1+Fp2)/2, 1-10 Hz, ANTES de la ICA y con la referencia Cz original.
    Umbral adaptativo por persona: prominencia > la mitad de la mediana de sus 20 picos más grandes
    (y > 3 MAD), ancho 40-500 ms, separación ≥ 300 ms. Calibrado contra el eye-tracker en registros
    limpios (sensibilidad 0.83-0.98). find_eog_events de MNE contaba ~8 veces de más (sacadas).
    Es la misma medida que AURA podrá dar con Fp1/Fp2."""
    sf = raw.info["sfreq"]
    v = raw.get_data(picks=["Fp1", "Fp2"]).mean(axis=0) * 1e6
    sos = signal.butter(4, [1, 10], btype="band", fs=sf, output="sos")
    v = signal.sosfiltfilt(sos, v)
    mad = np.median(np.abs(v - np.median(v))) * 1.4826
    pk, pr = signal.find_peaks(v, prominence=3 * mad, distance=int(0.3 * sf),
                               width=(int(0.04 * sf), int(0.5 * sf)))
    prom = pr["prominences"]
    if len(prom) == 0:
        return np.array([])
    top = np.median(np.sort(prom)[-20:])
    return pk[prom > 0.5 * top] / sf


def epoch_psd(raw, t0, t1, tcrop0):
    """PSD (épocas, canales ROI, frecuencias) en µV²/Hz y minuto de cada época válida."""
    seg = raw.copy().crop(t0 - tcrop0, t1 - tcrop0)
    ep = mne.make_fixed_length_epochs(seg, duration=EPOCH_S, preload=True).pick(ROI)
    data = ep.get_data() * 1e6
    good = np.ptp(data, axis=2).max(axis=1) < PTP_UV
    psd = ep[good].compute_psd(method="welch", fmin=1, fmax=40, n_fft=int(EPOCH_S * FS))
    minute = (np.arange(len(ep))[good] * EPOCH_S // 60).astype(int)
    return psd.get_data() * 1e12, psd.freqs, minute, float(good.mean())


def iaf(psd, freqs):
    """Frecuencia alfa individual: pico de 7-13 Hz en la ROI posterior (10 Hz si no hay pico claro)."""
    spec = psd[:, [ROI.index(c) for c in ALPHA_ROI], :].mean(axis=(0, 1))
    m = (freqs >= 7) & (freqs <= 13)
    f, p = freqs[m], spec[m]
    k = int(np.argmax(p))
    return float(f[k]) if 0 < k < len(p) - 1 else 10.0


def band_db(psd, freqs, lo, hi, chans):
    m = (freqs >= lo) & (freqs < hi)
    idx = [ROI.index(c) for c in chans]
    pw = psd[:, idx][:, :, m].sum(axis=2) * (freqs[1] - freqs[0])  # µV² por época y canal
    return 10 * np.log10(pw.mean(axis=1))


def periodic(spec, freqs, lo, hi):
    """Ajusta specparam (1/f + picos) y devuelve la potencia media de [lo, hi) por ENCIMA del
    fondo aperiódico (dB), el exponente aperiódico y el R² del ajuste."""
    fm = SpectralModel(peak_width_limits=[1, 8], max_n_peaks=6, aperiodic_mode="fixed", verbose=False)
    fm.fit(freqs, spec, FIT_RANGE)
    off, exp = fm.get_params("aperiodic")
    m = (freqs >= lo) & (freqs < hi)
    flat = np.log10(spec[m]) - (off - exp * np.log10(freqs[m]))
    return 10 * float(flat.mean()), float(exp), float(fm.get_metrics("gof"))


def eyetrack(root, sub, m):
    """Pupila (mm) y muestras perdidas del Tobii, en el tiempo del EEG (alineado por el primer TTL)."""
    base = os.path.join(root, sub, "beh", f"{sub}_task-phoneuse_recording-cyclopean_physio")
    if not os.path.exists(base + ".tsv.gz") or os.path.getsize(base + ".tsv.gz") < 1000:
        return None
    with open(base + ".json", encoding="utf-8") as f:
        cols = json.load(f)["Columns"]
    x = pd.read_csv(base + ".tsv.gz", sep="\t", header=None, names=cols,
                    usecols=["timestamp", "pupil_size_left", "pupil_size_right"])
    ev = pd.read_csv(base + "events.tsv.gz", sep="\t", header=None,
                     names=["onset", "duration", "trial_type", "direction", "value"])
    first_ttl = ev[(ev.direction == "in") & (ev.trial_type == "TTL_high")].onset.min()
    # El primer pulso recibido es el primer S11 del EEG; deriva medida ~20 ppm (≈20 ms en la sesión).
    t = ((x.timestamp - first_ttl) / 1e6 + m["sync"]).to_numpy()
    lft, rgt = x.pupil_size_left.to_numpy(), x.pupil_size_right.to_numpy()
    pupil = np.where((lft > 0) & (rgt > 0), (lft + rgt) / 2,
                     np.where(lft > 0, lft, np.where(rgt > 0, rgt, np.nan)))
    return t, pupil


def et_window(et, t0, t1):
    """Pupila mediana (sin los 100 ms alrededor de cada pérdida) y parpadeos/min en [t0, t1)."""
    if et is None:
        return np.nan, np.nan
    t, pupil = et
    sel = (t >= t0) & (t < t1)
    if sel.sum() < ET_HZ * (t1 - t0) * 0.5:
        return np.nan, np.nan
    p = pupil[sel]
    miss = np.isnan(p)
    if miss.mean() > ET_MAX_MISSING:
        return np.nan, np.nan
    near = ndimage.binary_dilation(miss, iterations=int(0.1 * ET_HZ))
    d = np.diff(np.r_[0, miss.astype(int), 0])
    runs = np.where(d == -1)[0] - np.where(d == 1)[0]
    blinks = int(((runs >= BLINK_SAMPLES[0]) & (runs <= BLINK_SAMPLES[1])).sum())
    return float(np.nanmedian(np.where(near, np.nan, p))), blinks * 60.0 / (t1 - t0)


def subject(root, sub):
    cache = os.path.join(CACHE, f"{sub}.csv")
    if os.path.exists(cache):
        return pd.read_csv(cache)
    vhdr = os.path.join(root, sub, "eeg", f"{sub}_task-phoneuse_eeg.vhdr")
    m = markers(os.path.join(root, sub, "eeg", f"{sub}_task-phoneuse_events.tsv"))
    raw, n_ica, bads, blink_t = preprocess(vhdr, m)
    tcrop0 = max(0, m["phone_on"] - 5)
    blink_t = blink_t + tcrop0  # a tiempo absoluto del registro EEG (raw recortado empieza en tcrop0)
    et = eyetrack(root, sub, m)
    psd_p, freqs, minute_p, keep_p = epoch_psd(raw, m["phone_on"], m["phone_off"], tcrop0)
    psd_v, _, _, keep_v = epoch_psd(raw, m["video_on"], m["video_off"], tcrop0)
    f_alpha = iaf(np.concatenate([psd_p, psd_v]), freqs)  # IAF con ambas condiciones
    bands = {
        "theta_iaf": (f_alpha - 6, f_alpha - 2, THETA_ROI),
        "alpha_iaf": (f_alpha - 2, f_alpha + 2, ALPHA_ROI),
        "theta_fix": (4, 8, THETA_ROI),
        "alpha_fix": (8, 13, ALPHA_ROI),
    }
    post = [ROI.index(c) for c in ALPHA_ROI]
    front = [ROI.index(c) for c in THETA_ROI]
    rows = []
    for cond, psd, minute in (("phone", psd_p, minute_p), ("video", psd_v, None)):
        if minute is None:
            minute = np.full(len(psd), -1)  # video = un solo bloque
        for mi in np.unique(minute):
            sel = minute == mi
            if cond == "phone":
                t0 = m["phone_on"] + 60 * mi
                t1 = min(t0 + 60, m["phone_off"])
            else:
                t0, t1 = m["video_on"], m["video_off"]
            row = dict(sub=sub, cond=cond, minute=int(mi), n_epochs=int(sel.sum()), iaf=f_alpha,
                       ica_removed=n_ica, bad_channels=" ".join(bads), keep_phone=keep_p, keep_video=keep_v)
            for name, (lo, hi, ch) in bands.items():
                row[name] = float(band_db(psd[sel], freqs, lo, hi, ch).mean())
            spec = psd[sel].mean(axis=0)  # (canales ROI, frecuencias), promedio lineal de épocas
            row["alpha_per"], row["exp_post"], row["r2_post"] = periodic(
                spec[post].mean(axis=0), freqs, f_alpha - 2, f_alpha + 2)
            row["theta_per"], row["exp_front"], row["r2_front"] = periodic(
                spec[front].mean(axis=0), freqs, f_alpha - 6, f_alpha - 2)
            row["blink_eeg"] = float(((blink_t >= t0) & (blink_t < t1)).sum() * 60.0 / (t1 - t0))
            row["pupil_mm"], row["blink_et"] = et_window(et, t0, t1)
            rows.append(row)
    df = pd.DataFrame(rows)
    os.makedirs(CACHE, exist_ok=True)
    df.to_csv(cache, index=False)
    return df


# ---------------------------------------------------------------------------- grupo
def questionnaires(root):
    out = {}
    for name in ("sas", "mppus"):
        p = os.path.join(root, "phenotype", f"{name}.tsv")
        if os.path.exists(p) and os.path.getsize(p) > 1000:
            t = pd.read_csv(p, sep="\t").set_index("participant_id")
            out[name] = t.filter(regex=r"^Q\d+$").sum(axis=1)  # ponytail: suma simple, sin ítems invertidos
    return pd.DataFrame(out)


def normalize(df):
    """Cambio relativo a la media de los minutos iniciales de la sesión de smartphone."""
    metrics = list(METRICS)
    out = []
    for sub, d in df.groupby("sub"):
        base = d[(d.cond == "phone") & (d.minute < BASE_MIN)][metrics].mean()
        d = d.copy()
        d[metrics] = d[metrics] - base
        out.append(d)
    return pd.concat(out), metrics


def slopes(norm, metrics):
    rows = []
    for sub, d in norm[(norm.cond == "phone") & (norm.minute <= 9)].groupby("sub"):
        r = {"sub": sub}
        for k in metrics:
            ok = d[k].notna()
            r[k + "_slope"] = float(np.polyfit(d.minute[ok], d[k][ok], 1)[0]) if ok.sum() >= 5 else np.nan
            r[k + "_late"] = float(d[d.minute >= 8][k].mean())
        rows.append(r)
    return pd.DataFrame(rows).set_index("sub")


def test_vs_zero(x):
    x = x.dropna()
    if len(x) < 3:
        return "n<3"
    t = stats.ttest_1samp(x, 0)
    w = stats.wilcoxon(x)
    pos = int((x > 0).sum())
    return (f"n={len(x):2d}  media={x.mean():+.3f}  ↑{pos}/{len(x)}  t={t.statistic:+.2f} p={t.pvalue:.4f}  "
            f"Wilcoxon p={w.pvalue:.4f}")


def spearman_line(a, b, label):
    j = pd.concat([a, b], axis=1).dropna()
    if len(j) < 5:
        return f"  {label}: n<5"
    r = stats.spearmanr(j.iloc[:, 0], j.iloc[:, 1])
    return f"  {label}: rho={r.statistic:+.2f} p={r.pvalue:.4f} (n={len(j)})"


def report(sl, meta, q, metrics, excluded):
    lines = ["H1 · ds007537 · cambio tónico durante 10 min de smartphone", "=" * 66,
             f"Sujetos: {len(sl)}  (excluidos: {', '.join(sorted(excluded)) or 'ninguno'})",
             "Pendiente = unidades/min tras normalizar a min 1-2. Tardío = media de min 9-10 vs min 1-2.",
             "↑k/n = sujetos con valor positivo.", ""]
    groups = {"Todos": sl.index, **{APP[a]: meta.index[meta.app_type == a] for a in ("S", "G")}}
    for k in metrics:
        title, unit = METRICS[k]
        lines.append(f"[{k}] {title} ({unit})")
        for g, idx in groups.items():
            idx = [i for i in idx if i in sl.index]
            lines.append(f"  {g:12s} pendiente: {test_vs_zero(sl.loc[idx, k + '_slope'])}")
            lines.append(f"  {'':12s} tardío:    {test_vs_zero(sl.loc[idx, k + '_late'])}")
        s = sl.loc[[i for i in groups['Video corto'] if i in sl.index], k + "_slope"].dropna()
        g = sl.loc[[i for i in groups['Juego'] if i in sl.index], k + "_slope"].dropna()
        if len(s) >= 3 and len(g) >= 3:
            u = stats.mannwhitneyu(s, g)
            lines.append(f"  Video corto vs Juego (Mann-Whitney): U={u.statistic:.0f} p={u.pvalue:.4f}")
        for qn in q.columns:
            lines.append(spearman_line(sl[k + "_slope"], q[qn], f"Spearman pendiente vs {qn.upper()}"))
        lines.append("")
    lines += ["[Relaciones entre sujetos] (pendientes, Spearman)",
              spearman_line(sl["blink_eeg_slope"], sl["blink_et_slope"],
                            "Validación: parpadeo EEG vs eye-tracker"),
              spearman_line(sl["alpha_iaf_slope"], sl["alpha_per_slope"], "Alfa total vs alfa periódica"),
              spearman_line(sl["alpha_iaf_slope"], sl["exp_post_slope"], "Alfa total vs exponente 1/f"),
              spearman_line(sl["alpha_per_slope"], sl["blink_eeg_slope"], "Alfa periódica vs parpadeo EEG"),
              spearman_line(sl["alpha_per_slope"], sl["pupil_mm_slope"], "Alfa periódica vs pupila"),
              "",
              "Nota: el video siempre va DESPUÉS del smartphone (orden fijo), así que el contraste",
              "smartphone vs video está confundido con el tiempo; H1 se evalúa dentro de la sesión.",
              "La pupila también depende del brillo de la pantalla (contenido variable).",
              "Se usa como apoyo, no como medida principal."]
    return "\n".join(lines)


def plot(norm, meta, path):
    keys = ["theta_iaf", "alpha_iaf", "theta_per", "alpha_per", "exp_post", "blink_eeg", "blink_et", "pupil_mm"]
    fig, axes = plt.subplots(2, 4, figsize=(17, 7.5), sharex=True)
    colors = {"S": "#d62728", "G": "#1f77b4"}
    phone = norm[(norm.cond == "phone") & (norm.minute <= 9)].merge(
        meta[["app_type"]], left_on="sub", right_index=True)
    for ax, k in zip(axes.ravel(), keys):
        title, unit = METRICS[k]
        for a, c in colors.items():
            sub = phone[phone.app_type == a]
            d = sub.groupby("minute")[k]
            mu, se = d.mean(), d.sem()
            ax.plot(mu.index + 1, mu, color=c, lw=2, marker="o", ms=4,
                    label=f"{APP[a]} (n={sub['sub'].nunique()})")
            ax.fill_between(mu.index + 1, mu - se, mu + se, color=c, alpha=0.18)
        allmu = phone.groupby("minute")[k].mean()
        ax.plot(allmu.index + 1, allmu, color="k", lw=1.4, ls="--", label="Todos")
        ax.axhline(0, color="gray", ls=":")
        ax.axvspan(0.5, BASE_MIN + 0.5, color="gray", alpha=0.08)
        ax.set_title(title, fontsize=10)
        ax.set_ylabel(f"Cambio vs min 1-2 ({unit})", fontsize=9)
        ax.grid(ls="--", alpha=0.4)
    for ax in axes[1]:
        ax.set_xlabel("Minuto de uso del smartphone")
    axes[0, 0].legend(fontsize=8)
    fig.suptitle("H1 · ds007537: evolución tónica y marcadores de activación (media ± EE)")
    fig.tight_layout()
    fig.savefig(path, dpi=150)


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    root = sys.argv[1]
    meta = pd.read_csv(os.path.join(root, "participants.tsv"), sep="\t").set_index("participant_id")
    subs = [s for s in (sys.argv[2:] or list(meta.index)) if s not in EXCLUDE]
    frames = []
    for sub in subs:
        vhdr = os.path.join(root, sub, "eeg", f"{sub}_task-phoneuse_eeg.vhdr")
        if not is_downloaded(vhdr):
            print(f"{sub}: sin datos descargados, se omite")
            continue
        print(f"{sub}: procesando...", flush=True)
        try:
            frames.append(subject(root, sub))
        except Exception as e:
            print(f"{sub}: ERROR {e}")
    if not frames:
        sys.exit("No hay sujetos procesados.")
    df = pd.concat(frames)
    norm, metrics = normalize(df)
    sl = slopes(norm, metrics)
    q = questionnaires(root)
    os.makedirs(OUT, exist_ok=True)
    df.to_csv(os.path.join(OUT, "h1_por_minuto.csv"), index=False)
    sl.join(meta).join(q).to_csv(os.path.join(OUT, "h1_pendientes.csv"))
    txt = report(sl, meta, q, metrics, EXCLUDE)
    with open(os.path.join(OUT, "h1_reporte.txt"), "w", encoding="utf-8") as f:
        f.write(txt)
    plot(norm, meta, os.path.join(OUT, "h1_trayectorias.png"))
    qc = df.groupby("sub").agg(iaf=("iaf", "first"), ica_removed=("ica_removed", "first"),
                               bad_channels=("bad_channels", "first"), keep_phone=("keep_phone", "first"),
                               keep_video=("keep_video", "first"), r2_post_min=("r2_post", "min"),
                               r2_front_min=("r2_front", "min"))
    qc.to_csv(os.path.join(OUT, "h1_calidad.csv"))
    print(txt)
    print(f"\nResultados en {OUT}")


if __name__ == "__main__":
    main()
