"""
Control positivo de H1b con Cao et al. (2019) · Fase B
========================================================
"Multi-channel EEG recordings during a sustained-attention driving task" (Sci Data 2019),
Figshare 6427334, CC BY 4.0. 27 sujetos, 62 sesiones de 60-90 min de conducción continua en simulador
(sin pausas, después de comer), 30 canales EEG a 500 Hz. Desvíos de carril al azar: 251/252 = inicio
del desvío, 253 = inicio de la respuesta → tiempo de reacción (TR), medida CONDUCTUAL de fatiga.

Pregunta: ¿el pipeline de ds007537/EEG-SVRec detecta el aumento de theta frontal-medial cuando
sabemos que hay fatiga? Si sí, el theta nulo/débil en scrolling significa "poco tiempo o poco esfuerzo",
no "el método no ve theta".

Mismo preprocesado y medidas (h1_ds007537.clean, épocas de 2 s, specparam 2-40 Hz, bandas por IAF).
Ventanas de 5 min; línea base = primera ventana. Pendiente por sesión, media por sujeto.
  Primarias (Holm): pendiente de theta periódico Fz/FCz y pendiente de log(TR) (chequeo de fatiga).
  TR < 200 ms se excluyen (anticipación); "lapse" = fracción de cada ventana con un desvío sin corregir.
  Secundarias: alfa periódica Pz/Oz/O1/O2, potencia total, exponente 1/f, parpadeo; rho theta~TR por sesión.

Descarga por streaming (2 sesiones a la vez, md5 de Figshare verificado, se borra el .set al terminar).
Uso:
  python h1b_cao2019.py "C:/ruta/Cao2019"                                   (todas las sesiones)
  python h1b_cao2019.py "C:/ruta/Cao2019" s01_051017m s02_050921m --keep    (piloto)
  python h1b_cao2019.py "C:/ruta/Cao2019" --cache                           (solo análisis de grupo)
"""
import os
import sys
import json
import hashlib
import urllib.request
from concurrent.futures import ProcessPoolExecutor, as_completed
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats
import mne

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "ds007537"))
sys.path.insert(0, os.path.join(HERE, "..", "EEG-SVRec"))
import h1_ds007537 as h1  # noqa: E402
from h1_svrec import download, holm, STD  # noqa: E402  descarga reanudable, Holm, nombres 10-05

# h1_svrec cambia el ajuste a 2-20 Hz por la meseta de ruido de SU dataset; Cao 2019 es crudo → rango original.
h1.FIT_RANGE = [2, 40]
# Este montaje no tiene POz: la ROI posterior se adapta (h1.* se leen al llamar a sus funciones).
h1.ALPHA_ROI = ["Pz", "Oz", "O1", "O2"]
h1.ROI = h1.THETA_ROI + h1.ALPHA_ROI
POST = [h1.ROI.index(c) for c in h1.ALPHA_ROI]
FRONT = [h1.ROI.index(c) for c in h1.THETA_ROI]

OUT = os.path.join(HERE, "results")
CACHE = os.path.join(OUT, "cache")
FIGSHARE = "https://api.figshare.com/v2/articles/6427334"
WORKERS = 2
WIN_S = 300          # ventanas de 5 min
MIN_EPOCHS = 60      # 2 min de épocas válidas para aceptar una ventana
MIN_KEEP = 0.40      # mismo criterio de exclusión que ds007537 / EEG-SVRec
DEV, RESP = {"251", "252"}, "253"
# Theta fásico (preespecificado antes de ver datos): ventanas en s respecto al inicio del desvío.
PH_FREQS = np.arange(4.0, 9.0)
PH_BASE, PH_POST, PH_TONIC, PH_CURVE = (-0.6, -0.1), (0.1, 0.5), (-30.0, -1.0), (-0.6, 1.5)
MIN_RT = 0.2        # TR < 200 ms: ya estaba corrigiendo (anticipación), no es reacción al desvío
METRICS = ["theta_per", "alpha_per", "theta_iaf", "alpha_iaf", "theta_fix", "alpha_fix", "exp_post", "blink_eeg",
           "log_rt", "lapse"]
TITLES = {**h1.METRICS, "alpha_per": ("Alfa posterior periódica Pz/Oz/O1/O2", "dB"),
          "log_rt": ("log10 tiempo de reacción (fatiga conductual)", "log s"),
          "lapse": ("Fracción del tiempo con desvío sin corregir (lapsos)", "fracción")}
PRIMARY = ["theta_per", "log_rt"]
# Acople EEG-conducta entre ventanas (secundario). Piloto s01: al dormirse sube theta TOTAL, no el periódico.
COUPLING = [(e, c) for e in ("theta_per", "theta_iaf", "alpha_per") for c in ("log_rt", "lapse")]


# ---------------------------------------------------------------------------- sesión
def reaction_times(raw):
    """(inicio del desvío, TR en s): primera respuesta 253 tras cada desvío y antes del siguiente.
    Incluye TR < MIN_RT (ya estaba girando); se filtran al calcular la mediana, no aquí, para los lapsos."""
    on, d = raw.annotations.onset, np.asarray(raw.annotations.description)
    out = []
    for i in np.where(np.isin(d, list(DEV)))[0]:
        nxt = np.where((on > on[i]) & (np.isin(d, list(DEV | {RESP}))))[0]
        if len(nxt) and d[nxt[0]] == RESP:
            out.append((on[i], on[nxt[0]] - on[i]))
    return np.array(out).reshape(-1, 2)


def lapse_fraction(rt, a, b):
    """Fracción de [a, b) con un desvío sin corregir. Capta episodios de sueño (p. ej. s01: 521 s sin
    responder), que dejan ventanas SIN desvíos nuevos y por tanto sin TR."""
    if not len(rt):
        return np.nan
    t0, t1 = rt[:, 0], rt[:, 0] + rt[:, 1]
    return float(np.clip(np.minimum(t1, b) - np.maximum(t0, a), 0, None).sum() / (b - a))


def phasic(raw, rt):
    """Theta FÁSICO Fz/FCz alineado al inicio de cada desvío (ensayo a ensayo) y su curso temporal.
    Potencia Morlet 4-8 Hz sobre el registro continuo (sin efectos de borde por época).
      ersp_db  = post (0.1-0.5 s) relativo a base (-0.6…-0.1 s)  → la medida clásica
      post_db  = post absoluto                                   → inmune a una base "inflada" por la fatiga
      tonic_db = mediana de theta en los 30 s previos            → estado tónico local (H1b)"""
    sf = raw.info["sfreq"]
    x = raw.get_data(picks=h1.THETA_ROI)
    p = mne.time_frequency.tfr_array_morlet(x[None], sf, PH_FREQS, n_cycles=PH_FREQS / 2.0,
                                            output="power")[0].mean(axis=(0, 1)) * 1e12  # µV²
    grid = np.arange(PH_CURVE[0], PH_CURVE[1] + 1e-9, 0.05)
    rows, curves = [], []
    for t0, r in rt:
        def idx(a, b):
            return slice(int(round((t0 + a) * sf)), int(round((t0 + b) * sf)))
        if r < MIN_RT or t0 + PH_TONIC[0] < 0 or t0 + PH_CURVE[1] > raw.times[-1]:
            continue
        if np.ptp(x[:, idx(-0.6, 0.6)] * 1e6, axis=1).max() >= h1.PTP_UV:
            continue
        base, post = p[idx(*PH_BASE)].mean(), p[idx(*PH_POST)].mean()
        rows.append(dict(onset=t0, rt=r, log_rt=np.log10(r), ersp_db=10 * np.log10(post / base),
                         post_db=10 * np.log10(post), base_db=10 * np.log10(base),
                         tonic_db=10 * np.log10(np.median(p[idx(*PH_TONIC)]))))
        curves.append(10 * np.log10(p[np.round((t0 + grid) * sf).astype(int)] / base))
    tr = pd.DataFrame(rows)
    if len(tr) < 10:
        return tr, pd.DataFrame()
    slow = (tr.rt > tr.rt.median()).to_numpy()
    c = np.array(curves)
    curve = pd.DataFrame({"t": grid, "rapidos": c[~slow].mean(0), "lentos": c[slow].mean(0)})
    return tr, curve


def session(name, root, md5, size, url, keep_raw):
    done = os.path.join(CACHE, f"{name}.csv")
    ph_done = os.path.join(CACHE, f"{name}_fasico.csv")
    if os.path.exists(done) and os.path.exists(ph_done):
        return f"{name}: en caché"
    path = os.path.join(root, f"{name}.set")
    try:
        download(url, path, size=size)
        with open(path, "rb") as f:
            if hashlib.md5(f.read()).hexdigest() != md5:
                os.remove(path)
                raise IOError("md5 no coincide, se descartó")
        raw = mne.io.read_raw_eeglab(path, preload=True)
        rt = reaction_times(raw)
        keep = {c: STD[c.upper()] for c in raw.ch_names if c.upper() in STD and c.upper() not in ("A1", "A2")}
        raw.pick(list(keep)).rename_channels(keep)
        raw.set_channel_types({c: "eeg" for c in keep.values()})
        dur = raw.times[-1]
        raw, n_ica, bads, blink_t = h1.clean(raw, skip=())
        tr, curve = phasic(raw, rt)
        psd, freqs, onset, keep_frac = epochs(raw)
        f_alpha = h1.iaf(psd, freqs)
        rows = []
        win = (onset // WIN_S).astype(int)
        for w in np.unique(win):
            sel = win == w
            if sel.sum() < MIN_EPOCHS:
                continue
            a, b = w * WIN_S, min((w + 1) * WIN_S, dur)
            r_in = rt[(rt[:, 0] >= a) & (rt[:, 0] < b), 1] if len(rt) else np.array([])
            r_in = r_in[r_in >= MIN_RT]
            rows.append(dict(session=name, sub=name[:3], platform=name[-1], window=int(w), n_epochs=int(sel.sum()),
                             iaf=f_alpha, keep=keep_frac, ica_removed=n_ica, bad_channels=" ".join(bads),
                             **measures(psd[sel], freqs, f_alpha),
                             blink_eeg=((blink_t >= a) & (blink_t < b)).sum() * 60.0 / (b - a),
                             n_dev=len(r_in), log_rt=float(np.log10(np.median(r_in))) if len(r_in) else np.nan,
                             lapse=lapse_fraction(rt, a, b)))
        os.makedirs(CACHE, exist_ok=True)
        curve.assign(session=name).to_csv(os.path.join(CACHE, f"{name}_curso.csv"), index=False)
        pd.DataFrame(rows).to_csv(done, index=False)
        tr.assign(session=name, sub=name[:3], keep=keep_frac).to_csv(ph_done, index=False)  # al final: = completo
        return (f"{name}: OK ({dur / 60:.0f} min, {len(rows)} ventanas, {len(rt)} desvíos, {len(tr)} ensayos fásicos, "
                f"épocas válidas {keep_frac:.0%})")
    except Exception as e:
        return f"{name}: ERROR {type(e).__name__}: {e}"
    finally:
        if not keep_raw and os.path.exists(path):
            os.remove(path)


def epochs(raw):
    ep = mne.make_fixed_length_epochs(raw, duration=h1.EPOCH_S, preload=True).pick(h1.ROI)
    good = np.ptp(ep.get_data() * 1e6, axis=2).max(axis=1) < h1.PTP_UV
    psd = ep[good].compute_psd(method="welch", fmin=1, fmax=40, n_fft=int(h1.EPOCH_S * h1.FS))
    return psd.get_data() * 1e12, psd.freqs, np.arange(len(ep))[good] * h1.EPOCH_S, float(good.mean())


def measures(psd, freqs, f_alpha):
    bands = {"theta_iaf": (f_alpha - 6, f_alpha - 2, h1.THETA_ROI), "alpha_iaf": (f_alpha - 2, f_alpha + 2, h1.ALPHA_ROI),
             "theta_fix": (4, 8, h1.THETA_ROI), "alpha_fix": (8, 13, h1.ALPHA_ROI)}
    r = {k: float(h1.band_db(psd, freqs, lo, hi, ch).mean()) for k, (lo, hi, ch) in bands.items()}
    spec = psd.mean(axis=0)
    r["alpha_per"], r["exp_post"], r["r2_post"] = h1.periodic(spec[POST].mean(0), freqs, f_alpha - 2, f_alpha + 2)
    r["theta_per"], r["exp_front"], r["r2_front"] = h1.periodic(spec[FRONT].mean(0), freqs, f_alpha - 6, f_alpha - 2)
    return r


# ---------------------------------------------------------------------------- grupo
def analyse(df):
    df = df[df.keep >= MIN_KEEP].copy()
    norm, rows = [], []
    for name, d in df.groupby("session"):
        d = d.sort_values("window").copy()
        base = d[d.window == d.window.min()][METRICS].iloc[0]
        d[METRICS] = d[METRICS] - base
        norm.append(d)
        r = dict(session=name, sub=d["sub"].iloc[0], platform=d.platform.iloc[0])
        for k in METRICS:
            ok = d[k].notna()
            r[k] = float(np.polyfit(d.window[ok] * WIN_S / 60, d[k][ok], 1)[0]) if ok.sum() >= 5 else np.nan
        for e, c in COUPLING:
            j = d[[e, c]].dropna()
            r[f"rho_{e}~{c}"] = stats.spearmanr(j[e], j[c]).statistic if len(j) >= 5 and j[c].nunique() > 1 else np.nan
        rows.append(r)
    return pd.concat(norm), pd.DataFrame(rows)


def report(sl, n_ses):
    rhos = [f"rho_{e}~{c}" for e, c in COUPLING]
    sub = sl.groupby("sub")[METRICS + rhos].mean()
    t = h1.test_vs_zero
    adj = dict(zip(PRIMARY, holm([stats.ttest_1samp(sub[k].dropna(), 0).pvalue for k in PRIMARY])))
    L = ["H1b · Cao 2019 · control positivo (conducción sostenida 60-90 min)", "=" * 66,
         f"Sujetos: {len(sub)}  ·  sesiones válidas: {n_ses}  (excluidas si < {MIN_KEEP:.0%} de épocas válidas)",
         "Pendiente = unidades por MINUTO tras normalizar a la primera ventana de 5 min; media de sesiones por sujeto.", ""]
    for k in METRICS:
        tag = f"   ← PRIMARIA, p Holm = {adj[k]:.4f}" if k in PRIMARY else ""
        L.append(f"[{k}] {TITLES[k][0]}{tag}")
        L.append(f"  {t(sub[k])}")
    L += ["", "Acople EEG-conducta (rho de Spearman entre ventanas, por sesión → media por sujeto):",
] + [f"  {r[4:]:22s} {t(sub[r])}" for r in rhos] + [          "", "Lectura: si log_rt sube (hubo fatiga) y theta_per sube, el pipeline detecta theta de fatiga.",
          "Si log_rt sube pero theta_per no, el método no capta theta tónico y hay que revisarlo antes de la Fase D."]
    return "\n".join(L)


PH_PAIRS = [("ersp_db", "log_rt"), ("post_db", "log_rt"), ("tonic_db", "log_rt"),
            ("ersp_db", "tonic_db"), ("post_db", "tonic_db")]


def phasic_report(tr):
    """Exploratorio: rho de Spearman entre ensayos, por sesión → media por sujeto → contra 0."""
    tr = tr[tr.keep >= MIN_KEEP]
    rows = []
    for name, d in tr.groupby("session"):
        if len(d) < 20:
            continue
        r = {"sub": d["sub"].iloc[0], "ersp_media": d.ersp_db.mean(), "n": len(d)}
        for a, b in PH_PAIRS:
            r[f"{a}~{b}"] = stats.spearmanr(d[a], d[b]).statistic
        rows.append(r)
    s = pd.DataFrame(rows)
    sub = s.groupby("sub").mean(numeric_only=True)
    t = h1.test_vs_zero
    L = ["", "THETA FÁSICO Fz/FCz al inicio del desvío (exploratorio; ensayos con TR ≥ 0.2 s)",
         f"Sesiones con ≥ 20 ensayos: {len(s)} · ensayos: {int(s.n.sum())}",
         f"  ¿Hay respuesta fásica? ERSP medio 0.1-0.5 s (dB vs -0.6…-0.1 s): {t(sub['ersp_media'])}",
         "  Acople ensayo a ensayo (rho por sesión → media por sujeto):"]
    L += [f"    {a + ' ~ ' + b:22s} {t(sub[f'{a}~{b}'])}" for a, b in PH_PAIRS]
    L += ["  Predicción (fatiga → menos control): ersp/post ~ log_rt < 0 y ~ tonic_db < 0; tonic ~ log_rt > 0.",
          "  Si ersp~tonic < 0 pero post~tonic no, es artefacto de la línea base inflada, no menos control."]
    return "\n".join(L), s


def plot_curve(cur, path):
    m = cur.groupby("t")[["rapidos", "lentos"]].mean()
    se = cur.groupby("t")[["rapidos", "lentos"]].sem()
    fig, ax = plt.subplots(figsize=(7, 4))
    for c, col, lab in (("rapidos", "#1a9850", "Respuestas rápidas (alerta)"), ("lentos", "#d73027", "Respuestas lentas (fatiga)")):
        ax.plot(m.index, m[c], color=col, lw=2, label=lab)
        ax.fill_between(m.index, m[c] - se[c], m[c] + se[c], color=col, alpha=0.18)
    ax.axvline(0, color="k", lw=1)
    ax.axvspan(*PH_POST, color="gray", alpha=0.12, label="Ventana fásica 0.1-0.5 s")
    ax.axhline(0, color="gray", ls=":")
    ax.set_xlabel("Tiempo desde el inicio del desvío (s)")
    ax.set_ylabel("Theta Fz/FCz (dB vs -0.6…-0.1 s)")
    ax.set_title("Theta fásico al desvío: ensayos rápidos vs lentos (media ± EE entre sesiones)", fontsize=9)
    ax.legend(fontsize=8)
    ax.grid(ls="--", alpha=0.4)
    fig.tight_layout()
    fig.savefig(path, dpi=150)


def plot(norm, path):
    keys = ["log_rt", "lapse", "theta_per", "theta_iaf", "alpha_per", "alpha_iaf", "exp_post"]
    fig, axes = plt.subplots(1, len(keys), figsize=(20, 4))
    for ax, k in zip(axes, keys):
        d = norm.groupby(["sub", "window"])[k].mean().reset_index().groupby("window")[k]
        mu, se = d.mean(), d.sem()
        x = (mu.index + 0.5) * WIN_S / 60
        ax.plot(x, mu, "o-", color="#7b3294", ms=4)
        ax.fill_between(x, mu - se, mu + se, color="#7b3294", alpha=0.18)
        ax.axhline(0, color="gray", ls=":")
        ax.set_title(TITLES[k][0], fontsize=9)
        ax.set_xlabel("Minuto de conducción")
        ax.set_ylabel(f"Cambio vs min 0-5 ({TITLES[k][1]})", fontsize=8)
        ax.grid(ls="--", alpha=0.4)
    fig.suptitle("H1b · Cao 2019: evolución en conducción sostenida (media ± EE entre sujetos)")
    fig.tight_layout()
    fig.savefig(path, dpi=150)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        sys.exit(__doc__)
    root, wanted, keep_raw = args[0], args[1:], "--keep" in sys.argv
    os.makedirs(root, exist_ok=True)
    os.makedirs(OUT, exist_ok=True)
    if "--cache" not in sys.argv:
        with urllib.request.urlopen(FIGSHARE, timeout=60) as r:
            files = {f["name"][:-4]: f for f in json.load(r)["files"] if f["name"].endswith(".set")}
        names = wanted or sorted(files)
        with ProcessPoolExecutor(WORKERS) as ex, open(os.path.join(OUT, "progreso.log"), "a", encoding="utf-8") as log:
            futs = [ex.submit(session, n, root, files[n]["computed_md5"], files[n]["size"], files[n]["download_url"],
                              keep_raw) for n in names]
            for i, fut in enumerate(as_completed(futs), 1):
                line = f"[{i:2d}/{len(names)}  {i / len(names):5.1%}]  {fut.result()}"
                print(line, flush=True)
                log.write(line + "\n")
    files = sorted(os.listdir(CACHE)) if os.path.isdir(CACHE) else []
    csvs = [f for f in files if f.endswith(".csv") and not f.endswith(("_fasico.csv", "_curso.csv"))]
    if not csvs:
        sys.exit("No hay sesiones procesadas.")
    df = pd.concat(pd.read_csv(os.path.join(CACHE, f)) for f in csvs)
    norm, sl = analyse(df)
    txt = report(sl, len(sl))
    ph = [f for f in files if f.endswith("_fasico.csv") and os.path.getsize(os.path.join(CACHE, f)) > 10]
    if ph:
        tr = pd.concat(pd.read_csv(os.path.join(CACHE, f)) for f in ph)
        ph_txt, ph_ses = phasic_report(tr)
        txt += "\n" + ph_txt
        tr.to_csv(os.path.join(OUT, "cao_fasico_ensayos.csv"), index=False)
        ph_ses.to_csv(os.path.join(OUT, "cao_fasico_rho_sesion.csv"), index=False)
        cur = [f for f in files if f.endswith("_curso.csv") and os.path.getsize(os.path.join(CACHE, f)) > 10]
        if cur:
            plot_curve(pd.concat(pd.read_csv(os.path.join(CACHE, f)) for f in cur),
                       os.path.join(OUT, "cao_fasico_curso.png"))
    df.to_csv(os.path.join(OUT, "cao_por_ventana.csv"), index=False)
    sl.to_csv(os.path.join(OUT, "cao_pendientes_sesion.csv"), index=False)
    df.groupby("session").agg(keep=("keep", "first"), ica_removed=("ica_removed", "first"),
                              bad_channels=("bad_channels", "first"), r2_post_min=("r2_post", "min"),
                              r2_front_min=("r2_front", "min"), n_ventanas=("window", "size")
                              ).to_csv(os.path.join(OUT, "cao_calidad.csv"))
    with open(os.path.join(OUT, "cao_reporte.txt"), "w", encoding="utf-8") as f:
        f.write(txt)
    plot(norm, os.path.join(OUT, "cao_trayectorias.png"))
    print(txt)
    print(f"\nResultados en {OUT}")


if __name__ == "__main__":
    main()
