"""
mock_lsl_streamer.py — Paso 1 del Protocolo de Simulación (MIRAI 2026)

Emula la diadema AURA publicando EEG CRUDO de 8 canales por LSL, muestra a muestra
y sincronizado con el reloj real, para que `realtime_pipeline.py` no distinga la
simulación del hardware.

Cambios respecto al borrador del protocolo (revisión del 28 oct):
  * Formatos reales de los datasets: BrainVision (.vhdr, ds007537) y Neuroscan (.cnt,
    EEG-SVRec, 1000 Hz). También acepta .edf/.bdf/.set/.fif (lector genérico de MNE).
  * Remuestreo a 250 Hz con antialiasing (SVRec viene a 1000 Hz).
  * Unidades en µV (MNE entrega voltios; sin la conversión el veto de 150 µV nunca se activaría).
  * Stream "AURA" tipo EEG (el nombre del stream crudo de AURA). `AURA_Power` de VRehab.py es un
    stream de potencias ya procesadas, no EEG crudo.
  * Re-referencia configurable antes de quedarse con los 8 canales (ds007537 está referido a Cz).
  * Envío por bloques con marcas de tiempo calculadas desde el índice de muestra:
    sin deriva aunque `sleep` en Windows tenga ~15 ms de granularidad.
  * Fuente sintética (ruido 1/f + alfa + theta + parpadeos + red) para tener el lazo vivo
    sin descargar datos, e inyección de eventos con verdad de campo.
  * Stream de marcadores "<nombre>_Markers" con los eventos inyectados, los parpadeos sintéticos
    y las anotaciones del archivo. Sirve para validar el veto (Paso 3), la escalera JITAI (Paso 6)
    y medir latencia (Paso 7).
  * La frecuencia de red (50/60 Hz) viaja en los metadatos del stream para que el pipeline
    elija el notch correcto (SVRec = 50 Hz; Cancún = 60 Hz).

Uso:
  python mock_lsl_streamer.py                                  # sintético, 20 min
  python mock_lsl_streamer.py --inject alpha 120 20 15         # ojos cerrados simulados (Berger)
  python mock_lsl_streamer.py --source "D:/ds007537/sub-01/eeg/sub-01_task-phoneuse_eeg.vhdr" --start 60
  python mock_lsl_streamer.py --source "D:/EEG-SVRec/EEG/01_data.cnt" --ref M1,M2 --line-freq 50
  python mock_lsl_streamer.py --source ../../AURA/data/eeg_data_20260122_123839.csv   # replay AURA real (50 Hz)
  python mock_lsl_streamer.py --fs 50 --inject alpha 120 20 15                         # sintético a la fs del CSV
  python mock_lsl_streamer.py --help
"""
import argparse
import os
import sys
import time

import numpy as np
from scipy import signal

# Entorno LSL cerrado a esta PC (ver lsl_api.cfg); debe fijarse antes de importar pylsl.
os.environ.setdefault("LSLAPICFG", os.path.join(os.path.dirname(os.path.abspath(__file__)), "lsl_api.cfg"))
import pylsl

# Montaje AURA y orden de canales del stream (fijo: el pipeline indexa por esta lista).
# Orden por defecto del software AURA (CH1..CH8); Cz sustituye a FCz (AURA no tiene FCz).
AURA_CHANNELS = ["Fp1", "F3", "Fz", "F4", "Cz", "Pz", "O1", "O2"]
FS_OUT = 250.0
FRONTAL_THETA = {"Fz": 1.0, "Cz": 0.8, "F3": 0.6, "F4": 0.6}
POSTERIOR_ALPHA = {"Pz": 0.7, "O1": 1.0, "O2": 1.0}
BLINK_SPREAD = {"Fp1": 1.0, "Fz": 0.35, "F3": 0.4, "F4": 0.3, "Cz": 0.15}
NOT_FOR_AVERAGE = {"M1", "M2", "A1", "A2"}  # mastoides/lóbulos: referencias, no se promedian


def montage_1005():
    """Montaje 10-05 de MNE ('standard_1005' pasa a 'colin27_1005' desde MNE 1.13)."""
    import mne
    name = "colin27_1005" if "colin27_1005" in mne.channels.get_builtin_montages() else "standard_1005"
    return mne.channels.make_standard_montage(name)


# --------------------------------------------------------------------------- fuentes
def synthetic(duration, fs, line_freq, iaf, seed):
    """EEG sintético plausible en µV. Devuelve (datos [canales, muestras], eventos [(muestra, etiqueta)])."""
    rng = np.random.default_rng(seed)
    n = int(round(duration * fs))
    nch = len(AURA_CHANNELS)
    idx = {c: i for i, c in enumerate(AURA_CHANNELS)}

    # Fondo aperiódico 1/f^chi (chi ~ 1.5), con un componente común (conducción de volumen).
    f = np.fft.rfftfreq(n, 1 / fs)
    shape = np.zeros_like(f)
    shape[1:] = 1.0 / f[1:] ** (1.5 / 2)
    def pink():
        x = np.fft.irfft(np.fft.rfft(rng.standard_normal(n)) * shape, n)
        return x / x.std()
    common = pink()
    data = np.stack([0.6 * common + 0.8 * pink() for _ in range(nch)]) * 10.0  # ~10 µV RMS

    def narrow(fc, bw=2.0):
        sos = signal.butter(2, [fc - bw / 2, fc + bw / 2], btype="band", fs=fs, output="sos")
        x = signal.sosfiltfilt(sos, rng.standard_normal(n))
        # Envolvente lenta (el alfa real fluctúa en ráfagas de segundos).
        env = signal.sosfiltfilt(signal.butter(2, 0.2, fs=fs, output="sos"), rng.standard_normal(n))
        env = 1 + 0.5 * env / env.std()
        return np.clip(env, 0.2, None) * x / x.std()

    alpha, theta = narrow(iaf), narrow(iaf - 4)
    for c, w in POSTERIOR_ALPHA.items():
        data[idx[c]] += 6.0 * w * alpha
    for c in ("Fz", "Cz", "F3", "F4"):
        data[idx[c]] += 1.5 * alpha  # alfa frontal residual
    for c, w in FRONTAL_THETA.items():
        data[idx[c]] += 3.0 * w * theta

    # Parpadeos de Poisson (~15/min), 150-300 µV en Fp1.
    events = []
    t = rng.exponential(4.0)
    while t < duration - 1:
        s = int(t * fs)
        add_blink(data, s, fs, rng.uniform(150, 300), idx)
        events.append((s, "blink"))
        t += max(0.5, rng.exponential(4.0))

    # Ruido de red. Por encima de Nyquist (fs = 50 Hz) se omite: se asume el antialiasing del
    # equipo; sin él, 60 Hz muestreado a 50 Hz caería exactamente en 10 Hz (alfa).
    if line_freq < fs / 2:
        tt = np.arange(n) / fs
        data += 2.0 * np.sin(2 * np.pi * line_freq * tt + rng.uniform(0, 2 * np.pi, (nch, 1)))
    return data.astype(np.float32), events


def add_blink(data, s, fs, amp, idx):
    w = np.arange(int(0.4 * fs)) / fs
    shape = amp * np.exp(-0.5 * ((w - 0.15) / 0.05) ** 2)  # pico monofásico de ~300 ms
    e = min(data.shape[1], s + len(shape))
    for c, k in BLINK_SPREAD.items():
        data[idx[c], s:e] += k * shape[: e - s]


def load_file(path, start, duration, ref, fs):
    """Lee un registro con MNE y lo deja como lo entregaría AURA: 8 canales, `fs` Hz, µV."""
    import mne
    mne.set_log_level("ERROR")
    ext = os.path.splitext(path)[1].lower()
    kw = {"data_format": "int32"} if ext == ".cnt" else {}  # mismo ajuste que h1_svrec.py
    raw = mne.io.read_raw(path, preload=False, **kw)

    tmax = raw.times[-1] if duration is None else min(start + duration, raw.times[-1])
    if start >= tmax:
        sys.exit(f"--start {start} s está fuera del registro ({raw.times[-1]:.0f} s)")
    raw.crop(start, tmax)

    mont = montage_1005()
    std = {c.upper(): c for c in mont.ch_names}
    upper = {c.upper(): c for c in raw.ch_names}
    missing = [c for c in AURA_CHANNELS if c.upper() not in upper]
    if missing:
        sys.exit(f"Faltan canales AURA en el archivo: {missing}. Disponibles: {raw.ch_names}")
    ref_chs = [] if ref in ("average", "none") else [r.strip() for r in ref.split(",")]
    for r in ref_chs:
        if r.upper() not in upper:
            sys.exit(f"Canal de referencia {r} no está en el archivo")

    # Canales de cuero cabelludo (montaje 10-05) + referencias pedidas. Fuera EOG/ECG/GSR/PPG.
    keep = [c for c in raw.ch_names if c.upper() in std or c.upper() in {r.upper() for r in ref_chs}]
    raw.pick(keep).load_data()
    raw.rename_channels({c: std[c.upper()] for c in raw.ch_names if c.upper() in std})
    raw.set_channel_types({c: "eeg" for c in raw.ch_names})
    if raw.info["sfreq"] != fs:
        raw.resample(fs)  # incluye filtro antialiasing

    # Canales rotos (criterio MAD de h1_ds007537.py). std == 0 es la referencia de registro (p. ej. Cz).
    sd = raw.get_data().std(axis=1)
    med = np.median(sd[sd > 0])
    bads = [c for c, s in zip(raw.ch_names, sd) if s > 0 and (s > 5 * med or s < 0.05 * med)]
    raw.info["bads"] = bads
    aura_bad = [c for c in bads if c.upper() in {a.upper() for a in AURA_CHANNELS}]
    if aura_bad:
        raw.set_montage(mont, on_missing="ignore")
        raw.interpolate_bads(reset_bads=False, exclude=[b for b in bads if b not in aura_bad])
        print(f"[aviso] canales AURA rotos interpolados: {aura_bad}")
    print(f"Canales rotos detectados (excluidos de la referencia): {bads or 'ninguno'}")

    if ref == "average":
        raw.info["bads"] = bads + [c for c in raw.ch_names if c.upper() in NOT_FOR_AVERAGE]
        raw.set_eeg_reference("average")
    elif ref_chs:
        raw.set_eeg_reference([upper[r.upper()] if upper[r.upper()] in raw.ch_names else r for r in ref_chs])

    names = {c.upper(): c for c in raw.ch_names}
    data = raw.get_data(picks=[names[c.upper()] for c in AURA_CHANNELS]) * 1e6  # V -> µV

    events = []
    if len(raw.annotations):
        ev, ev_id = mne.events_from_annotations(raw)
        inv = {v: k for k, v in ev_id.items()}
        events = [(int(s - raw.first_samp), f"file:{inv[i]}") for s, _, i in ev if s >= raw.first_samp]
    return data.astype(np.float32), events, raw.info.get("line_freq"), bads


def load_aura_csv(path, start, duration, fs):
    """CSV grabado desde la AURA: timestamp, phase, label, channel_0..channel_7 (µV, orden CH1..CH8).

    Las marcas de tiempo del CSV tienen jitter y retrocesos (asignadas al recibir), así que se usa
    el índice de muestra; fs nativa = muestras / duración (≈ 50 Hz en la prueba de enero 2026).
    Cada cambio de `phase` se emite como marcador `file:<fase>`.
    """
    import csv
    with open(path, newline="") as fh:
        rows = list(csv.reader(fh))
    hdr, rows = rows[0], rows[1:]
    cols = [hdr.index(f"channel_{i}") for i in range(len(AURA_CHANNELS))]
    t = np.array([float(r[0]) for r in rows])
    data = np.array([[float(r[c]) for c in cols] for r in rows]).T
    phase = [r[hdr.index("phase")] for r in rows] if "phase" in hdr else []
    fs_in = float(round((len(t) - 1) / (t[-1] - t[0])))
    fs = fs or fs_in  # sin --fs se transmite a la fs nativa
    print(f"CSV AURA: {len(t)} muestras, fs nativa ≈ {fs_in:.0f} Hz → stream a {fs:.0f} Hz")

    s0 = int(start * fs_in)
    s1 = len(t) if duration is None else min(len(t), s0 + int(duration * fs_in))
    if s0 >= s1:
        sys.exit(f"--start {start} s está fuera del registro ({len(t) / fs_in:.0f} s)")
    data, phase = data[:, s0:s1], phase[s0:s1]
    events = [(i, f"file:{p}") for i, p in enumerate(phase) if i == 0 or p != phase[i - 1]]

    # Mismo criterio MAD que load_file; aquí solo se reportan (canal muerto = std ~0).
    sd = data.std(axis=1)
    med = np.median(sd)
    bads = [c for c, s in zip(AURA_CHANNELS, sd) if s > 5 * med or s < 0.05 * med]
    print(f"Canales rotos/muertos (no se interpolan): {bads or 'ninguno'}")

    if fs != fs_in:
        from fractions import Fraction
        r = Fraction(fs / fs_in).limit_denominator(1000)
        data = signal.resample_poly(data, r.numerator, r.denominator, axis=1)
        events = [(int(s * fs / fs_in), lab) for s, lab in events]
    return data.astype(np.float32), events, bads, fs


# --------------------------------------------------------------------------- inyección
def inject(data, events, specs, fs, iaf):
    """Suma eventos con verdad de campo. spec = (tipo, inicio_s, duración_s, amplitud_µV)."""
    idx = {c: i for i, c in enumerate(AURA_CHANNELS)}
    for kind, t0, dur, amp in specs:
        s0, n = int(t0 * fs), int(dur * fs)
        if s0 >= data.shape[1]:
            print(f"[aviso] inyección {kind}@{t0}s fuera del registro, se ignora")
            continue
        n = min(n, data.shape[1] - s0)
        if kind == "blink":  # tren de parpadeos a 1 Hz
            for k in range(0, n, int(fs)):
                add_blink(data, s0 + k, fs, amp, idx)
                events.append((s0 + k, "blink"))
        else:
            freq, weights = (iaf, POSTERIOR_ALPHA) if kind == "alpha" else (iaf - 4, FRONTAL_THETA)
            ramp = min(int(0.5 * fs), n // 2)
            env = np.ones(n)
            env[:ramp] = 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, ramp))
            env[n - ramp:] = env[:ramp][::-1]
            wave = amp * env * np.sin(2 * np.pi * freq * np.arange(n) / fs)
            for c, w in weights.items():
                data[idx[c], s0:s0 + n] += (w * wave).astype(np.float32)
        events.append((s0, f"inject:{kind}:on"))
        events.append((s0 + n, f"inject:{kind}:off"))


# --------------------------------------------------------------------------- LSL
def make_outlet(name, fs, meta):
    info = pylsl.StreamInfo(name, "EEG", len(AURA_CHANNELS), fs, pylsl.cf_float32, f"mirai-sim-{name}")
    d = info.desc()
    d.append_child_value("manufacturer", "MIRAI-2026 mock_lsl_streamer")
    for k, v in meta.items():
        d.append_child_value(k, str(v))
    chns = d.append_child("channels")
    for c in AURA_CHANNELS:
        ch = chns.append_child("channel")
        ch.append_child_value("label", c)
        ch.append_child_value("unit", "microvolts")
        ch.append_child_value("type", "EEG")
    return pylsl.StreamOutlet(info, chunk_size=0, max_buffered=360)


def stream(data, events, fs, name, chunk_ms, loop, wait, meta):
    outlet = make_outlet(name, fs, meta)
    mk = pylsl.StreamOutlet(pylsl.StreamInfo(f"{name}_Markers", "Markers", 1, pylsl.IRREGULAR_RATE,
                                             pylsl.cf_string, f"mirai-sim-{name}-markers"))
    events = sorted(events)
    n_total = data.shape[1]
    print(f"Stream LSL '{name}' (EEG, {len(AURA_CHANNELS)} ch, {fs:.0f} Hz, µV) + '{name}_Markers'")
    print(f"Canales: {', '.join(AURA_CHANNELS)} | duración {n_total / fs:.1f} s | loop={loop}")
    if wait:
        print("Esperando consumidor...")
        while not outlet.wait_for_consumers(1.0):
            pass
    print("Transmitiendo. Ctrl+C para detener.\n")

    data_t = np.ascontiguousarray(data.T)  # (muestras, canales) para push_chunk
    sent, ev_ptr, cycle = 0, 0, 0
    t0 = pylsl.local_clock()
    next_report = 10.0
    try:
        while True:
            target = int((pylsl.local_clock() - t0) * fs)
            if not loop:
                target = min(target, n_total)
            if target > sent:
                idx = np.arange(sent, target) % n_total
                outlet.push_chunk(data_t[idx], t0 + (target - 1) / fs)  # ts de la última muestra
                # Marcadores con la marca de tiempo exacta de su muestra.
                while events:
                    if ev_ptr >= len(events):
                        if not loop:
                            break
                        ev_ptr, cycle = 0, cycle + 1
                    s, label = events[ev_ptr]
                    g = s + cycle * n_total
                    if g >= target:
                        break
                    mk.push_sample([label], t0 + g / fs)
                    ev_ptr += 1
                sent = target
            el = pylsl.local_clock() - t0
            if el >= next_report:
                lag = (el * fs - sent) / fs * 1000
                print(f"  t={el:7.1f} s  muestras={sent:>9d}  tasa={sent / el:8.3f} Hz  retraso={lag:5.1f} ms")
                next_report += 10.0
            if not loop and sent >= n_total:
                print("\nFin del registro.")
                break
            time.sleep(chunk_ms / 1000)
    except KeyboardInterrupt:
        print("\nDetenido por el usuario.")
    el = pylsl.local_clock() - t0
    print(f"Enviadas {sent} muestras en {el:.2f} s → {sent / el:.3f} Hz (nominal {fs:.0f} Hz)")


# --------------------------------------------------------------------------- main
def main():
    p = argparse.ArgumentParser(description="Emulador LSL de la diadema AURA (MIRAI 2026, Paso 1)")
    p.add_argument("--source", default="synthetic",
                   help="'synthetic', CSV de AURA (.csv) o ruta a .vhdr/.cnt/.edf/.bdf/.set/.fif")
    p.add_argument("--fs", type=float, default=None,
                   help="frecuencia del stream (250 por defecto; CSV de AURA: su fs nativa, ~50)")
    p.add_argument("--start", type=float, default=0.0, help="segundo de inicio dentro del archivo")
    p.add_argument("--duration", type=float, default=None,
                   help="segundos a transmitir (sintético: 1200 por defecto; archivo: todo)")
    p.add_argument("--ref", default="average",
                   help="'average', 'none' o canales separados por coma (p. ej. M1,M2 / TP9,TP10)")
    p.add_argument("--line-freq", type=float, default=None,
                   help="frecuencia de red del REGISTRO (sintético 60; si el archivo no la trae, 50)")
    p.add_argument("--iaf", type=float, default=10.0, help="frecuencia alfa individual para sintético/inyección")
    p.add_argument("--inject", nargs=4, action="append", default=[],
                   metavar=("TIPO", "INICIO_S", "DUR_S", "AMP_UV"),
                   help="alpha|theta|blink; repetible. Ej.: --inject alpha 120 20 15")
    p.add_argument("--name", default="AURA", help="nombre del stream LSL (AURA real = 'AURA')")
    p.add_argument("--chunk-ms", type=float, default=20.0, help="periodo de envío (10-20 ms)")
    p.add_argument("--loop", action="store_true", help="repetir el registro indefinidamente")
    p.add_argument("--wait", action="store_true", help="no empezar hasta que haya un receptor")
    p.add_argument("--seed", type=int, default=7)
    a = p.parse_args()

    specs = []
    for kind, t0, dur, amp in a.inject:
        if kind not in ("alpha", "theta", "blink"):
            p.error(f"tipo de inyección desconocido: {kind}")
        specs.append((kind, float(t0), float(dur), float(amp)))

    fs = a.fs or FS_OUT
    if a.source == "synthetic":
        line = a.line_freq or 60.0
        data, events = synthetic(a.duration or 1200.0, fs, line, a.iaf, a.seed)
        meta = {"source": "synthetic", "reference": "n/a", "line_freq": line, "seed": a.seed}
    elif not os.path.exists(a.source):
        sys.exit(f"No existe: {a.source}")
    elif a.source.lower().endswith(".csv"):
        print(f"Cargando {a.source} ...")
        data, events, bads, fs = load_aura_csv(a.source, a.start, a.duration, a.fs)
        line = a.line_freq or 60.0
        meta = {"source": os.path.basename(a.source), "start_s": a.start, "reference": "device",
                "line_freq": line, "bad_channels": " ".join(bads) or "none"}
    else:
        print(f"Cargando {a.source} ...")
        data, events, lf, bads = load_file(a.source, a.start, a.duration, a.ref, fs)
        line = a.line_freq or lf or 50.0
        meta = {"source": os.path.basename(a.source), "start_s": a.start, "reference": a.ref,
                "line_freq": line, "bad_channels": " ".join(bads) or "none"}
    meta["iaf"] = a.iaf
    inject(data, events, specs, fs, a.iaf)

    # Chequeo de unidades: EEG típico 5-50 µV RMS; < 0.01 sugiere voltios sin convertir.
    rms = np.sqrt(np.mean(np.square(data - data.mean(axis=1, keepdims=True)), axis=1))
    print("RMS por canal (µV): " + "  ".join(f"{c}={r:.1f}" for c, r in zip(AURA_CHANNELS, rms)))
    if np.median(rms) < 0.01 or np.median(rms) > 500:
        print("[aviso] amplitudes fuera de rango EEG: revisa unidades/referencia")
    print(f"Red: {line:.0f} Hz | eventos/marcadores: {len(events)}")
    stream(data, events, fs, a.name, a.chunk_ms, a.loop, a.wait, meta)


if __name__ == "__main__":
    main()
