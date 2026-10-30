"""
check_lsl_stream.py — Criterio de validación del Paso 1 (MIRAI 2026)

Se conecta a un stream LSL (el emulador o la AURA real) y comprueba durante N segundos:
  * tasa efectiva = 250 Hz (marcas de tiempo y reloj del receptor),
  * sin huecos ni marcas de tiempo repetidas o hacia atrás,
  * sin deriva entre las marcas de tiempo y el reloj del sistema,
  * latencia de entrega (reloj local − marca de la última muestra del bloque),
  * metadatos: canales, unidades, frecuencia de red; RMS por canal en µV.
También imprime los marcadores de '<nombre>_Markers' si existen.

Uso:
  python check_lsl_stream.py                  # 'AURA', 60 s
  python check_lsl_stream.py --name AURA --seconds 300
"""
import argparse
import os
import socket
import sys
import time

import numpy as np

# Entorno LSL cerrado a esta PC (ver lsl_api.cfg); debe fijarse antes de importar pylsl.
os.environ.setdefault("LSLAPICFG", os.path.join(os.path.dirname(os.path.abspath(__file__)), "lsl_api.cfg"))
import pylsl


def channel_meta(info):
    labels, units = [], []
    ch = info.desc().child("channels").child("channel")
    while not ch.empty():
        labels.append(ch.child_value("label"))
        units.append(ch.child_value("unit"))
        ch = ch.next_sibling()
    return labels, units


def find_stream(name, source_id, timeout=15.0):
    """El único stream `name` que corre en ESTA PC y cuyo source_id empieza por `source_id`.

    El nombre no identifica la fuente: Aura.exe abierto publica 'AURA' aunque no haya diadema, el
    emulador también, y otras PCs de la red con Aura igual (si LSLAPICFG no los filtra). Por eso se
    exige el prefijo del source_id ('mirai-sim-' emulador, 'AuraLSL-' Aura.exe) y el host local; sin
    prefijo, o si no hay exactamente un candidato, se listan todos y se sale. Se acumula la búsqueda
    al menos 4 s porque una búsqueda corta a veces solo capta uno de los candidatos.
    """
    host = socket.gethostname().lower()
    print(f"Buscando stream '{name}' en esta PC ({socket.gethostname()}) con source_id '{source_id or '?'}*'...")
    found, t0 = {}, time.time()
    while time.time() - t0 < (4.0 if found else timeout):
        for s in pylsl.resolve_streams(1.0):
            if s.name() == name:
                found[s.uid()] = s
    mine = [s for s in found.values()
            if source_id and s.hostname().lower() == host and s.source_id().startswith(source_id)]
    if len(mine) == 1:
        s = mine[0]
        print(f"Conectando a source_id={s.source_id()}  host={s.hostname()}  {s.nominal_srate():.0f} Hz")
        return s
    for s in found.values():
        where = "esta PC" if s.hostname().lower() == host else "otra PC, se ignora"
        print(f"  - source_id={s.source_id()}  host={s.hostname()} ({where})  {s.nominal_srate():.0f} Hz")
    if not found:
        sys.exit(f"No hay ningún stream '{name}'. ¿Está corriendo mock_lsl_streamer.py o Aura.exe?")
    if not source_id:
        sys.exit("Indica --source-id (prefijo): 'mirai-sim-' para el emulador o 'AuraLSL-' para Aura.exe.")
    if not mine:
        sys.exit(f"Ningún stream '{name}' de esta PC tiene un source_id que empiece por '{source_id}'.")
    sys.exit(f"{len(mine)} streams '{name}' de esta PC empiezan por '{source_id}': usa un prefijo más largo.")


def find_markers(info):
    """Inlet del stream de marcadores del mismo emisor (source_id + '-markers', mismo host) o None."""
    for s in pylsl.resolve_byprop("source_id", f"{info.source_id()}-markers", timeout=2):
        if s.hostname() == info.hostname():
            return pylsl.StreamInlet(s, processing_flags=pylsl.proc_clocksync)
    return None


def main():
    p = argparse.ArgumentParser(description="Validador de stream LSL (Paso 1)")
    p.add_argument("--name", default="AURA")
    p.add_argument("--seconds", type=float, default=60.0)
    p.add_argument("--timeout", type=float, default=15.0, help="segundos para encontrar el stream")
    p.add_argument("--source-id", default=None,
                   help="prefijo del source_id: 'mirai-sim-' (emulador) o 'AuraLSL-' (Aura.exe); sin él se listan los candidatos")
    a = p.parse_args()

    inlet = pylsl.StreamInlet(find_stream(a.name, a.source_id, a.timeout), max_buflen=60,
                              processing_flags=pylsl.proc_clocksync)
    info = inlet.info()
    fs, nch = info.nominal_srate(), info.channel_count()
    labels, units = channel_meta(info)
    line = info.desc().child_value("line_freq") or "?"
    print(f"Stream: {info.name()} | tipo {info.type()} | {nch} ch | nominal {fs:.1f} Hz | red {line} Hz")
    print(f"Canales: {labels} | unidades: {set(units) or '?'}")

    mk_inlet = find_markers(info)
    if mk_inlet:
        print(f"Marcadores: {a.name}_Markers conectado")

    inlet.open_stream()
    ts_all, x_all, lat, recv = [], [], [], []
    n_markers = 0
    t_start = pylsl.local_clock()
    print(f"Midiendo {a.seconds:.0f} s...\n")
    next_report = 10.0
    while pylsl.local_clock() - t_start < a.seconds:
        x, ts = inlet.pull_chunk(timeout=0.2, max_samples=1024)
        now = pylsl.local_clock()
        if ts:
            ts_all.extend(ts)
            x_all.append(np.asarray(x, dtype=np.float32))
            lat.append(now - ts[-1])
            recv.append((now, len(ts)))
        if mk_inlet:
            while True:
                m, mts = mk_inlet.pull_sample(timeout=0.0)
                if m is None:
                    break
                n_markers += 1
                if n_markers <= 30:
                    print(f"  [marcador] t={mts - t_start:8.3f} s  {m[0]}")
        el = now - t_start
        if el >= next_report:
            print(f"  t={el:6.1f} s  muestras={len(ts_all):>8d}")
            next_report += 10.0

    if len(ts_all) < 2:
        sys.exit("No llegaron muestras.")
    ts = np.array(ts_all)
    x = np.concatenate(x_all)
    d = np.diff(ts)
    span = ts[-1] - ts[0]
    rate_ts = (len(ts) - 1) / span
    rt = np.array([r[0] for r in recv])
    cum = np.cumsum([r[1] for r in recv])
    rate_rx = (cum[-1] - cum[0]) / (rt[-1] - rt[0])
    gaps = int(np.sum(d > 1.5 / fs))
    back = int(np.sum(d <= 0))
    # Deriva: (reloj receptor − marca de tiempo) usando la envolvente inferior por tramos de 5 s.
    # El mínimo de cada tramo elimina el jitter de envío (0-20 ms) y deja solo la tendencia.
    off = rt - ts[cum - 1]
    bins = ((rt - rt[0]) // 5).astype(int)
    tb = np.array([rt[bins == b].mean() for b in np.unique(bins)]) - rt[0]
    ob = np.array([off[bins == b].min() for b in np.unique(bins)])
    slope = np.polyfit(tb, ob, 1)[0] * 60 * 1000 if len(tb) >= 3 else 0.0
    drift_total = slope * span / 60
    lat = np.array(lat) * 1000
    rms = x.std(axis=0)

    print("\n================ REPORTE PASO 1 ================")
    print(f"Muestras recibidas        : {len(ts)} en {span:.2f} s")
    print(f"Tasa por marcas de tiempo : {rate_ts:.4f} Hz")
    print(f"Tasa por reloj del receptor: {rate_rx:.4f} Hz")
    print(f"Huecos (> 1.5 periodos)   : {gaps}")
    print(f"Marcas repetidas/atrás    : {back}")
    print(f"Deriva                    : {slope:+.3f} ms/min ({drift_total:+.2f} ms acumulados)")
    print(f"Latencia de entrega       : media {lat.mean():.1f} ms | p95 {np.percentile(lat, 95):.1f} ms | máx {lat.max():.1f} ms")
    print(f"Marcadores recibidos      : {n_markers}")
    print("RMS por canal (µV)        : " + "  ".join(f"{c}={r:.1f}" for c, r in zip(labels or range(nch), rms)))

    # La marca de una muestra va hasta un periodo por detrás del envío: a 50 Hz eso suma 20 ms.
    lat_max = 50 + 1000 / fs
    bad = [str(c) for c, r in zip(labels or range(nch), rms) if not 1 < r < 200]
    checks = {
        f"tasa = {fs:.0f} Hz ±0.1 %": abs(rate_ts - fs) / fs < 1e-3 and abs(rate_rx - fs) / fs < 5e-3,
        "sin huecos": gaps == 0,
        "marcas monótonas": back == 0,
        "deriva acumulada < 5 ms": abs(drift_total) < 5.0,
        f"latencia p95 < {lat_max:.0f} ms": np.percentile(lat, 95) < lat_max,
        "8 canales": nch == 8,
        "amplitud en rango µV (1-200 RMS)" + (f" — fuera: {', '.join(bad)}" if bad else ""): not bad,
    }
    print("------------------------------------------------")
    for k, ok in checks.items():
        print(f"  [{'OK' if ok else 'FALLA'}] {k}")
    verdict = all(checks.values())
    print(f"\nRESULTADO: {'PASA' if verdict else 'NO PASA'}")
    sys.exit(0 if verdict else 1)


if __name__ == "__main__":
    main()
