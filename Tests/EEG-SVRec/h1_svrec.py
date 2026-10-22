"""
Validación de H1 con EEG-SVRec (Zhang et al., SIGIR 2024) · Fase C
=====================================================================
30 sujetos, 62 canales a 1000 Hz, 2-7 sesiones de scrolling de video corto por sujeto
(de 1.4 a 31 min; entre sesiones hay ~10 min de etiquetado y 5 min de descanso).
Cada video tiene muestras de inicio/fin en el .cnt y calificaciones 1-5 (inmersión, arousal, valencia...).

Mismo preprocesado y medidas que ds007537 (se importa h1_ds007537.clean): 1-40 Hz, 250 Hz,
interpolación MAD, parpadeos Fp1/Fp2, referencia promedio, ICA ocular, épocas de 2 s,
potencia total y PERIÓDICA (specparam) con bandas relativas a la IAF.

Tres análisis
  A. Dentro de la sesión (réplica de ds007537): cambio por minuto vs min 1-2 y pendiente por sesión.
  B. Entre sesiones (tiempo acumulado): nivel medio de cada sesión contra su orden.
  C. Por video: alfa/theta periódica vs inmersión reportada (Spearman por sujeto, rho contra 0).
Medidas primarias (Holm, 2 pruebas): pendiente de alfa periódica (H1a) y theta periódica (H1b) en A.
Todo lo demás es exploratorio.

Descarga por streaming: 2 procesos en paralelo; cada uno procesa un .cnt (Hugging Face, sha256
verificado), guarda un CSV pequeño en results/cache y BORRA el .cnt. Mientras tanto, 2 hilos descargan
el siguiente par. En disco nunca hay más de 4 sujetos (máx. ~14 GB). Si se interrumpe, se reanuda: los sujetos con caché no se vuelven a bajar.

Uso:
  python h1_svrec.py "C:/ruta/EEG-SVRec"                 (los 30 sujetos)
  python h1_svrec.py "C:/ruta/EEG-SVRec" 07 02 --keep    (piloto; --keep no borra los .cnt)
  python h1_svrec.py "C:/ruta/EEG-SVRec" --cache         (solo análisis de grupo con los sujetos en caché)
"""
import os
import sys
import json
import hashlib
import http.client
import urllib.request
import time
import threading
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, wait, FIRST_COMPLETED
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats
import mne

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "ds007537"))
import h1_ds007537 as h1  # noqa: E402  mismo preprocesado y medidas que ds007537

OUT = os.path.join(HERE, "results")
CACHE = os.path.join(OUT, "cache")
HF_API = "https://huggingface.co/api/datasets/hezy18/EEG-SVRec/tree/main/EEG"
HF_FILE = "https://huggingface.co/datasets/hezy18/EEG-SVRec/resolve/main/EEG/{}_data.cnt"
GH_META = "https://raw.githubusercontent.com/hezy18/EEG-SVRec/main/data/metadata/{}_behavior_MAES.json"
# .cnt dañados en Hugging Face (sha256 coincide, así se subieron): cabecera e inicio del registro en ceros.
# En 05 los ceros llegan al min 42.5 (sesiones 1-3). Se excluyen por integridad del archivo, no por resultados.
CORRUPT = {"05", "16", "17"}
SUBS = [f"{i:02d}" for i in range(1, 31) if f"{i:02d}" not in CORRUPT]
WORKERS = 2          # sujetos procesándose (y en disco) a la vez
EEG_HZ = 1000.0      # eeg_start_time/eeg_end_time son muestras del .cnt original a 1000 Hz
CNT_FORMAT = "int32"  # 69 canales × 4 B × 1000 Hz = 276 kB/s (cuadra con tamaño y duración de los 30 archivos); "auto" falla > 2 GB
MIN_EPOCHS_MIN = 10  # épocas válidas (20 s) para aceptar un minuto
MIN_EPOCHS_VID = 5   # 10 s para aceptar un video
MAX_MIN = 15         # pendiente dentro de la sesión sobre los primeros 15 min (diseño de 15 min)
MIN_KEEP = 0.40      # sesiones con < 40 % de épocas válidas se excluyen (mismo criterio que ds007537)
# Los .cnt vienen filtrados a 0.5-50 Hz y tienen una meseta de ruido/EMG de 15-48 Hz que sesga el ajuste
# 1/f en 2-40 Hz (piloto 07/02: R² 0.51-0.93, exponente ↓, sin pico alfa). En 2-20 Hz: R² 0.91-0.99, pico alfa en todos.
h1.FIT_RANGE = [2, 20]
TITLES = {**h1.METRICS, "emg_post": ("EMG posterior 25-40 Hz (control de músculo)", "dB")}
METRICS = [k for k in TITLES if k not in ("blink_et", "pupil_mm")]  # sin eye-tracker
PRIMARY = ["alpha_per", "theta_per"]
RATINGS = ["immersion", "arousal", "valance", "satisf"]
STD = {c.upper(): c for c in mne.channels.make_standard_montage("standard_1005").ch_names}
POST = [h1.ROI.index(c) for c in h1.ALPHA_ROI]
FRONT = [h1.ROI.index(c) for c in h1.THETA_ROI]


# ---------------------------------------------------------------------------- datos
def download(url, dst, sha256=None, size=None, tries=20):
    """Descarga por bloques a .part y renombra solo si el sha256 coincide.
    Si la conexión se corta (urllib termina SIN error y el archivo queda corto) o falla la red,
    reanuda desde el último byte con Range, hasta `tries` intentos."""
    if os.path.exists(dst):
        return dst
    tmp = dst + ".part"
    for attempt in range(tries):
        pos = os.path.getsize(tmp) if os.path.exists(tmp) else 0
        if size and pos >= size:
            break
        try:
            req = urllib.request.Request(url, headers={"Range": f"bytes={pos}-"} if pos else {})
            with urllib.request.urlopen(req, timeout=60) as r, open(tmp, "r+b" if pos else "wb") as f:
                f.seek(pos)
                if pos and r.status != 206:  # el servidor ignoró el Range: se empieza de cero
                    f.seek(0)
                    f.truncate()
                while chunk := r.read(1 << 20):
                    f.write(chunk)
        except (OSError, http.client.HTTPException):
            time.sleep(min(60, 5 * (attempt + 1)))
            continue
        if not size:
            break
    if size and os.path.getsize(tmp) != size:
        raise IOError(f"{os.path.basename(dst)}: incompleto tras {tries} intentos "
                      f"({os.path.getsize(tmp):,}/{size:,} bytes); se reanudará en la próxima corrida")
    h = hashlib.sha256()
    with open(tmp, "rb") as f:
        while chunk := f.read(1 << 20):
            h.update(chunk)
    if sha256 and h.hexdigest() != sha256:
        os.remove(tmp)
        raise IOError(f"{os.path.basename(dst)}: sha256 no coincide, se descartó")
    os.replace(tmp, dst)
    return dst


def remote_files():
    """{sujeto: {"oid": sha256, "size": bytes}} desde la API de Hugging Face."""
    with urllib.request.urlopen(HF_API, timeout=60) as r:
        return {os.path.basename(x["path"])[:2]: x["lfs"] for x in json.load(r)}


def videos(meta_path):
    """Videos con ventana EEG válida, ordenados en el tiempo (segundos del .cnt)."""
    with open(meta_path, encoding="utf-8") as f:
        meta = json.load(f)
    rows = [dict(item_id=k, **v) for k, v in meta.items()
            if v.get("eeg_end_time", -1) > v.get("eeg_start_time", 1e12)]
    df = pd.DataFrame(rows)
    df["t0"], df["t1"] = df.eeg_start_time / EEG_HZ, df.eeg_end_time / EEG_HZ
    return df.sort_values("t0").reset_index(drop=True)


def load_session(cnt, t0, t1):
    """Lee solo la ventana de la sesión (sin cargar el archivo completo) con nombres 10-05 estándar."""
    raw = mne.io.read_raw_cnt(cnt, preload=False, data_format=CNT_FORMAT)
    if raw.info["sfreq"] != EEG_HZ:
        raise ValueError(f"sfreq {raw.info['sfreq']} ≠ {EEG_HZ}: los índices de video no aplican")
    raw.crop(max(0, t0 - 5), min(raw.times[-1], t1 + 5)).load_data()
    # Sin mastoides (referencia) ni HEO/VEO/ECG/CB1/CB2 (no están en el montaje 10-05).
    keep = {c: STD[c.upper()] for c in raw.ch_names if c.upper() in STD and c.upper() not in ("M1", "M2")}
    raw.pick(list(keep)).rename_channels(keep)
    raw.set_channel_types({c: "eeg" for c in keep.values()})
    return raw


def epochs_psd(raw, s0, s1, tcrop0):
    """Como h1.epoch_psd pero devuelve el inicio de cada época válida (s desde el inicio de la sesión)."""
    seg = raw.copy().crop(s0 - tcrop0, min(s1 - tcrop0, raw.times[-1]))
    ep = mne.make_fixed_length_epochs(seg, duration=h1.EPOCH_S, preload=True).pick(h1.ROI)
    good = np.ptp(ep.get_data() * 1e6, axis=2).max(axis=1) < h1.PTP_UV
    psd = ep[good].compute_psd(method="welch", fmin=1, fmax=40, n_fft=int(h1.EPOCH_S * h1.FS))
    return psd.get_data() * 1e12, psd.freqs, np.arange(len(ep))[good] * h1.EPOCH_S, float(good.mean())


def measures(psd, freqs, f_alpha):
    bands = {"theta_iaf": (f_alpha - 6, f_alpha - 2, h1.THETA_ROI), "alpha_iaf": (f_alpha - 2, f_alpha + 2, h1.ALPHA_ROI),
             "theta_fix": (4, 8, h1.THETA_ROI), "alpha_fix": (8, 13, h1.ALPHA_ROI), "emg_post": (25, 40, h1.ALPHA_ROI)}
    r = {k: float(h1.band_db(psd, freqs, lo, hi, ch).mean()) for k, (lo, hi, ch) in bands.items()}
    spec = psd.mean(axis=0)
    r["alpha_per"], r["exp_post"], r["r2_post"] = h1.periodic(spec[POST].mean(0), freqs, f_alpha - 2, f_alpha + 2)
    r["theta_per"], r["exp_front"], r["r2_front"] = h1.periodic(spec[FRONT].mean(0), freqs, f_alpha - 6, f_alpha - 2)
    return r


def subject(sub, root, sha256, keep_raw):
    """Descarga → procesa → borra. Devuelve un mensaje de estado (corre en un proceso aparte)."""
    done = os.path.join(CACHE, f"{sub}_min.csv")
    if os.path.exists(done):
        return f"{sub}: en caché"
    cnt = os.path.join(root, "EEG", f"{sub}_data.cnt")
    try:
        download(HF_FILE.format(sub), cnt, sha256)
        vid = videos(os.path.join(root, "metadata", f"{sub}_behavior_MAES.json"))
        sess, missing = [], []
        file_end = mne.io.read_raw_cnt(cnt, preload=False, data_format=CNT_FORMAT).times[-1]
        for sid, v in vid.groupby("session_id"):
            s0, s1 = v.t0.min(), v.t1.max()
            if s1 > file_end:  # 02 y 04: el .cnt de Hugging Face termina antes que los metadatos
                missing.append(int(sid))
                continue
            raw = load_session(cnt, s0, s1)
            tcrop0 = max(0, s0 - 5)
            raw, n_ica, bads, blink_t = h1.clean(raw, skip=())
            psd, freqs, onset, keep = epochs_psd(raw, s0, s1, tcrop0)
            del raw
            # Cada época se asigna al video que la contiene completa; las de los huecos se descartan.
            t = s0 + onset
            idx = np.full(len(t), -1)
            for i, (a, b) in v[["t0", "t1"]].iterrows():
                idx[(t >= a) & (t + h1.EPOCH_S <= b)] = i
            sess.append(dict(sid=int(sid), s0=s0, s1=s1, psd=psd[idx >= 0], onset=onset[idx >= 0],
                             vid=idx[idx >= 0], keep=keep, n_ica=n_ica, bads=" ".join(bads),
                             blinks=blink_t + tcrop0))
        f_alpha = h1.iaf(np.concatenate([s["psd"] for s in sess]), freqs)  # IAF con todas las sesiones
        rows, vrows = [], []
        for order, s in enumerate(sess, 1):
            base = dict(sub=sub, session=s["sid"], order=order, mode=vid.loc[s["vid"][0], "session_mode"]
                        if len(s["vid"]) else "", dur_min=(s["s1"] - s["s0"]) / 60, iaf=f_alpha,
                        keep=s["keep"], ica_removed=s["n_ica"], bad_channels=s["bads"])
            minute = (s["onset"] // 60).astype(int)
            for mi in np.unique(minute):
                sel = minute == mi
                if sel.sum() < MIN_EPOCHS_MIN:
                    continue
                a = s["s0"] + 60 * mi
                b = min(a + 60, s["s1"])
                blink = ((s["blinks"] >= a) & (s["blinks"] < b)).sum() * 60.0 / (b - a)
                rows.append({**base, "minute": int(mi), "n_epochs": int(sel.sum()),
                             **measures(s["psd"][sel], freqs, f_alpha), "blink_eeg": blink})
            for i in np.unique(s["vid"]):
                sel = s["vid"] == i
                if sel.sum() < MIN_EPOCHS_VID:
                    continue
                v = vid.loc[i]
                blink = ((s["blinks"] >= v.t0) & (s["blinks"] < v.t1)).sum() * 60.0 / (v.t1 - v.t0)
                vrows.append({**base, "item_id": v.item_id, "video_order": v.video_order, "n_epochs": int(sel.sum()),
                              **{k: v.get(k, np.nan) for k in RATINGS},
                              **measures(s["psd"][sel], freqs, f_alpha), "blink_eeg": blink})
        os.makedirs(CACHE, exist_ok=True)
        pd.DataFrame(vrows).to_csv(os.path.join(CACHE, f"{sub}_video.csv"), index=False)
        pd.DataFrame(rows).to_csv(done, index=False)  # se escribe al final: su existencia = sujeto completo
        miss = f"; sesiones fuera del archivo: {missing}" if missing else ""
        return f"{sub}: OK ({len(sess)} sesiones, {len(rows)} minutos, {len(vrows)} videos{miss})"
    except Exception as e:
        return f"{sub}: ERROR {type(e).__name__}: {e}"
    finally:
        # ponytail: se borra también si falla, para que un error sistemático no llene el disco (usar --keep para depurar)
        if not keep_raw and os.path.exists(cnt):
            os.remove(cnt)


# ---------------------------------------------------------------------------- grupo
def holm(p):
    p = np.asarray(p, float)
    o = np.argsort(p)
    adj = np.maximum.accumulate((len(p) - np.arange(len(p))) * p[o])
    out = np.empty_like(p)
    out[o] = np.minimum(adj, 1)
    return out


def within(df):
    """A. Normaliza cada sesión a sus min 1-2; pendiente por sesión y media por sujeto."""
    df = df[(df.keep >= MIN_KEEP) & (df.minute < MAX_MIN)].copy()
    out = []
    for (sub, ses), d in df.groupby(["sub", "session"]):
        b = d[d.minute < h1.BASE_MIN][METRICS]
        if len(b) < h1.BASE_MIN:
            continue
        d = d.copy()
        d[METRICS] = d[METRICS] - b.mean()
        out.append(d)
    norm = pd.concat(out)
    rows = []
    for (sub, ses, order), d in norm.groupby(["sub", "session", "order"]):
        r = dict(sub=sub, session=ses, order=order)
        for k in METRICS:
            ok = d[k].notna()
            r[k] = float(np.polyfit(d.minute[ok], d[k][ok], 1)[0]) if ok.sum() >= 5 else np.nan
        rows.append(r)
    return norm, pd.DataFrame(rows)


def across(df):
    """B. Pendiente por sujeto del nivel medio de cada sesión contra el orden de sesión (≥ 3 sesiones)."""
    lvl = df[df.keep >= MIN_KEEP].groupby(["sub", "order"])[METRICS].mean().reset_index()
    rows = []
    for sub, d in lvl.groupby("sub"):
        if len(d) < 3:
            continue
        r = {"sub": sub}
        for k in METRICS:
            ok = d[k].notna()
            r[k] = float(np.polyfit(d.order[ok], d[k][ok], 1)[0]) if ok.sum() >= 3 else np.nan
            r[k + "_last_first"] = float(d[k].iloc[-1] - d[k].iloc[0])
        rows.append(r)
    cols = ["sub"] + METRICS + [k + "_last_first" for k in METRICS]
    return lvl, pd.DataFrame(rows, columns=cols).set_index("sub")


def per_video(vd):
    """C. rho de Spearman por sujeto entre la medida del video y la calificación (≥ 10 videos)."""
    rows = []
    vd = vd[vd.keep >= MIN_KEEP]
    for sub, d in vd.groupby("sub"):
        r = {"sub": sub}
        for k in ("alpha_per", "theta_per", "alpha_iaf", "exp_post", "emg_post"):
            for q in ("immersion", "arousal"):
                j = d[[k, q]].dropna()
                r[f"{k}~{q}"] = stats.spearmanr(j[k], j[q]).statistic if len(j) >= 10 and j[q].nunique() > 1 else np.nan
        j = d[["immersion", "video_order"]].dropna()
        r["immersion~video_order"] = stats.spearmanr(j.immersion, j.video_order).statistic if len(j) >= 10 else np.nan
        rows.append(r)
    return pd.DataFrame(rows).set_index("sub")


def report(sub_sl, s1_sl, acr, rho, n_ses):
    t = h1.test_vs_zero
    L = ["H1 · EEG-SVRec · scrolling de video corto (Fase C)", "=" * 66,
         f"Excluidos por archivo dañado en el repositorio: {', '.join(sorted(CORRUPT))}",
         f"Sujetos con datos: {sub_sl.index.nunique()}  ·  sesiones válidas: {n_ses}  "
         f"(excluidas si < {MIN_KEEP:.0%} de épocas válidas)", "",
         "A. DENTRO DE LA SESIÓN · pendiente (unidades/min) tras normalizar a min 1-2; media de sesiones por sujeto"]
    prim = {k: stats.ttest_1samp(sub_sl[k].dropna(), 0).pvalue for k in PRIMARY}
    adj = dict(zip(PRIMARY, holm(list(prim.values()))))
    for k in METRICS:
        tag = f"   ← PRIMARIA, p Holm = {adj[k]:.4f}" if k in PRIMARY else ""
        L.append(f"  [{k}] {TITLES[k][0]}{tag}")
        L.append(f"    todas las sesiones: {t(sub_sl[k])}")
        L.append(f"    solo sesión 1:      {t(s1_sl[k])}")
    L += ["  Control de artefacto (pendientes por sujeto, Spearman):",
          h1.spearman_line(sub_sl["alpha_per"], sub_sl["emg_post"], "Alfa periódica vs EMG posterior"),
          h1.spearman_line(sub_sl["theta_per"], sub_sl["emg_post"], "Theta periódico vs EMG posterior")]
    L += ["", "B. ENTRE SESIONES · pendiente del nivel medio de la sesión por número de sesión (sujetos con ≥ 3)"]
    for k in METRICS:
        L.append(f"  [{k}] pendiente: {t(acr[k])}")
        L.append(f"  {'':{len(k) + 2}} última − primera: {t(acr[k + '_last_first'])}")
    L += ["", "C. POR VIDEO · rho de Spearman por sujeto (≥ 10 videos), rho contra 0"]
    for c in rho.columns:
        L.append(f"  {c:28s} {t(rho[c])}")
    L += ["",
          "Notas:",
          "- El modo de sesión no está contrabalanceado (sujetos 1-21: aleatorio → mixto → personalizado;",
          "  22-30: personalizado → no personalizado), así que B está confundido con el tipo de feed.",
          "- Entre sesiones hay etiquetado y 5 min de descanso: B mide uso acumulado con pausas, no continuo.",
          "- Solo se usan épocas dentro de ventanas de video alineadas; los huecos se descartan.",
          "- Sin condición control: igual que ds007537, no separa fatiga de habituación o efecto del tiempo."]
    return "\n".join(L)


def plot(norm, lvl, path):
    keys = ["alpha_per", "theta_per", "exp_post", "alpha_iaf", "theta_iaf", "emg_post", "blink_eeg"]
    fig, axes = plt.subplots(2, len(keys), figsize=(20, 7.5))
    for ax, k in zip(axes[0], keys):
        per_sub = norm.groupby(["sub", "minute"])[k].mean().reset_index()
        d = per_sub.groupby("minute")[k]
        mu, se = d.mean(), d.sem()
        ax.plot(mu.index + 1, mu, "o-", color="#d62728", ms=4)
        ax.fill_between(mu.index + 1, mu - se, mu + se, color="#d62728", alpha=0.18)
        ax.axhline(0, color="gray", ls=":")
        ax.axvspan(0.5, h1.BASE_MIN + 0.5, color="gray", alpha=0.08)
        ax.set_title(TITLES[k][0], fontsize=9)
        ax.set_xlabel("Minuto de la sesión")
        ax.set_ylabel(f"Cambio vs min 1-2 ({TITLES[k][1]})", fontsize=8)
        ax.grid(ls="--", alpha=0.4)
    for ax, k in zip(axes[1], keys):
        z = lvl.copy()
        z[k] = z[k] - z.groupby("sub")[k].transform("first")
        d = z.groupby("order")[k]
        mu, se = d.mean(), d.sem()
        ax.errorbar(mu.index, mu, se, fmt="o-", color="#1f77b4", capsize=3)
        ax.axhline(0, color="gray", ls=":")
        ax.set_xlabel("Número de sesión")
        ax.set_ylabel(f"Nivel vs sesión 1 ({TITLES[k][1]})", fontsize=8)
        ax.grid(ls="--", alpha=0.4)
    fig.suptitle("H1 · EEG-SVRec: arriba, dentro de la sesión; abajo, entre sesiones (media ± EE entre sujetos)")
    fig.tight_layout()
    fig.savefig(path, dpi=150)


def process_all(root, subs, keep_raw):
    """Descarga y procesa los sujetos pendientes (2 a la vez, con descarga anticipada)."""
    os.makedirs(os.path.join(root, "EEG"), exist_ok=True)
    os.makedirs(os.path.join(root, "metadata"), exist_ok=True)
    for s in SUBS:  # metadatos de todos los sujetos (~40 KB cada uno)
        download(GH_META.format(s), os.path.join(root, "metadata", f"{s}_behavior_MAES.json"))
    lfs = remote_files()
    os.makedirs(OUT, exist_ok=True)
    log = open(os.path.join(OUT, "progreso.log"), "a", encoding="utf-8")
    # Progreso ponderado por tamaño del .cnt (descarga y procesamiento escalan con él); la caché cuenta como hecha.
    total = sum(lfs[s]["size"] for s in subs)
    done = sum(lfs[s]["size"] for s in subs if os.path.exists(os.path.join(CACHE, f"{s}_min.csv")))
    start, done0 = time.time(), done
    pending = [s for s in subs if not os.path.exists(os.path.join(CACHE, f"{s}_min.csv"))]
    print(f"En caché: {', '.join(s for s in subs if s not in pending) or 'ninguno'}", flush=True)
    # Descarga anticipada: los hilos bajan el siguiente par mientras los procesos trabajan.
    # Máx. 2*WORKERS .cnt en disco (2 procesándose + 2 esperando, ~14 GB); el slot se libera al borrar el .cnt.
    slots = threading.Semaphore(2 * WORKERS)

    def fetch(s):
        slots.acquire()
        cnt = os.path.join(root, "EEG", f"{s}_data.cnt")
        try:
            download(HF_FILE.format(s), cnt, lfs[s]["oid"], lfs[s]["size"])
        except Exception as e:  # el .part se conserva: la próxima corrida reanuda la descarga
            slots.release()
            return f"{s}: ERROR de descarga {type(e).__name__}: {e}"

    with ThreadPoolExecutor(WORKERS) as dl, ProcessPoolExecutor(WORKERS) as ex:
        waiting = {dl.submit(fetch, s): ("dl", s) for s in pending}
        while waiting:
            fin, _ = wait(waiting, return_when=FIRST_COMPLETED)
            for fut in fin:
                kind, s = waiting.pop(fut)
                try:
                    msg = fut.result()
                except Exception as e:  # p. ej. un proceso que muere por falta de memoria
                    msg = f"{s}: ERROR {type(e).__name__}: {e}"
                if kind == "dl" and msg is None:
                    waiting[ex.submit(subject, s, root, lfs[s]["oid"], keep_raw)] = ("proc", s)
                    continue
                if kind == "proc":
                    slots.release()
                done += lfs[s]["size"]
                frac, speed = done / total, (done - done0) / max(time.time() - start, 1)
                eta = f"{(total - done) / speed / 60:5.0f} min" if speed else "    —"
                bar = "█" * int(30 * frac) + "░" * (30 - int(30 * frac))
                line = (f"{time.strftime('%H:%M')} [{bar}] {frac:6.1%}  {done / 1e9:5.1f}/{total / 1e9:.1f} GB"
                        f"  ETA {eta}  ·  {msg}")
                print(line, flush=True)
                log.write(line + "\n")
                log.flush()


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        sys.exit(__doc__)
    root, subs, keep_raw = args[0], args[1:] or SUBS, "--keep" in sys.argv
    if "--cache" not in sys.argv:  # --cache: solo el análisis de grupo con lo ya procesado (sin red)
        process_all(root, subs, keep_raw)
    files = sorted(f for f in os.listdir(CACHE) if f.endswith("_min.csv"))
    if not files:
        sys.exit("No hay sujetos procesados.")
    df = pd.concat(pd.read_csv(os.path.join(CACHE, f), dtype={"sub": str}) for f in files)
    vd = pd.concat(pd.read_csv(os.path.join(CACHE, f.replace("_min", "_video")), dtype={"sub": str}) for f in files)
    norm, sl = within(df)
    sub_sl = sl.groupby("sub")[METRICS].mean()
    s1_sl = sl[sl.order == 1].set_index("sub")[METRICS]
    lvl, acr = across(df)
    rho = per_video(vd)
    txt = report(sub_sl, s1_sl, acr, rho, len(sl))
    df.to_csv(os.path.join(OUT, "svrec_por_minuto.csv"), index=False)
    vd.to_csv(os.path.join(OUT, "svrec_por_video.csv"), index=False)
    sl.to_csv(os.path.join(OUT, "svrec_pendientes_sesion.csv"), index=False)
    acr.to_csv(os.path.join(OUT, "svrec_entre_sesiones.csv"))
    rho.to_csv(os.path.join(OUT, "svrec_rho_video.csv"))
    df.groupby(["sub", "session"]).agg(dur_min=("dur_min", "first"), keep=("keep", "first"),
                                       ica_removed=("ica_removed", "first"), bad_channels=("bad_channels", "first"),
                                       r2_post_min=("r2_post", "min"), r2_front_min=("r2_front", "min")
                                       ).to_csv(os.path.join(OUT, "svrec_calidad.csv"))
    with open(os.path.join(OUT, "svrec_reporte.txt"), "w", encoding="utf-8") as f:
        f.write(txt)
    plot(norm, lvl, os.path.join(OUT, "svrec_trayectorias.png"))
    print(txt)
    print(f"\nResultados en {OUT}")


if __name__ == "__main__":
    assert np.allclose(holm([0.01, 0.04]), [0.02, 0.04]) and np.allclose(holm([0.04, 0.01]), [0.04, 0.02])
    main()
