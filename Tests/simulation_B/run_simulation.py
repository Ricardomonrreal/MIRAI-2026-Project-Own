"""
run_simulation.py — Paso 7 del Protocolo de Simulación (MIRAI 2026) · VERSIÓN B: lanzador y benchmark

  * live:    emulador (mock_lsl_streamer.py) + marcadores de conducta opcionales (behavior_markers.py) + pipeline en
             tiempo real; mide latencias, CPU, memoria y deriva (Pasos 2–7) y deja runs/<sesión>/reporte.md.
  * offline: el mismo pipeline sin LSL (realtime_pipeline.py --offline), tan rápido como sea posible.

Uso:
  python run_simulation.py live --fs 250 --minutos 20
  python run_simulation.py live --fs 50 --minutos 10 --inject alpha 250 30 25 --conducta 115 nogo:error 125 nogo:slow
  python run_simulation.py offline ../../AURA/data/eeg_data_20260122_123839.csv --sin-fases
"""
import argparse
import glob
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable


def latest_report(t0):
    runs = [d for d in glob.glob(os.path.join(HERE, "runs", "*")) if os.path.getmtime(d) >= t0]
    rep = [os.path.join(d, "reporte.md") for d in sorted(runs) if os.path.exists(os.path.join(d, "reporte.md"))]
    return rep[-1] if rep else None


def main():
    p = argparse.ArgumentParser(description="Lanzador y benchmark del pipeline MIRAI (Paso 7)")
    sp = p.add_subparsers(dest="modo", required=True)
    lv = sp.add_parser("live", help="emulador + pipeline en tiempo real")
    lv.add_argument("--fs", type=float, default=250.0)
    lv.add_argument("--minutos", type=float, default=20.0)
    lv.add_argument("--seed", type=int, default=7)
    lv.add_argument("--inject", nargs=4, action="append", default=[], metavar=("TIPO", "INICIO_S", "DUR_S", "AMP_UV"))
    lv.add_argument("--conducta", nargs="+", default=[], help="pares <segundos> <marcador> para el Nivel 2")
    of = sp.add_parser("offline", help="replay sin LSL; el resto de argumentos pasa a realtime_pipeline.py")
    of.add_argument("fuente")
    a, rest = p.parse_known_args()

    t0 = time.time()
    if a.modo == "offline":
        code = subprocess.call([PY, "realtime_pipeline.py", "--offline", a.fuente, *rest], cwd=HERE)
    else:
        name = f"AURAB_RS{a.fs:.0f}"
        secs = a.minutos * 60
        procs = []
        if a.conducta:
            procs.append(subprocess.Popen([PY, "behavior_markers.py", *a.conducta], cwd=HERE))
        inj = [x for spec in a.inject for x in ("--inject", *spec)]
        procs.append(subprocess.Popen([PY, "mock_lsl_streamer.py", "--duration", str(secs + 60), "--fs", str(a.fs),
                                       "--name", name, "--seed", str(a.seed), "--wait", *inj], cwd=HERE,
                                      stdout=subprocess.DEVNULL))
        time.sleep(2.0)
        code = subprocess.call([PY, "realtime_pipeline.py", "--name", name, "--source-id", "mirai-sim-",
                                "--seconds", str(secs), *rest], cwd=HERE)
        for pr in procs:
            try:
                pr.wait(timeout=90)
            except subprocess.TimeoutExpired:
                pr.kill()
    rep = latest_report(t0)
    print(f"\nReporte: {rep or 'no se generó'}")
    sys.exit(code)


if __name__ == "__main__":
    main()
