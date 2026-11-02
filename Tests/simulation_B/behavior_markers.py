"""
behavior_markers.py — marcadores de conducta de prueba para el Nivel 2 del Paso 6 (MIRAI 2026) · VERSIÓN B

Publica el stream LSL `MIRAI_Behavior` (sustituto de la tarea Scroll-NoGo mientras no exista) y envía cada marcador
a los segundos indicados, contados desde que se conecta el primer receptor (el pipeline). Los marcadores
`bloque:<nombre>` no van al Nivel 2: delimitan los bloques de la tasa de parpadeo del reporte (2 nov).

Uso (antes de lanzar el pipeline):
  python behavior_markers.py 200 nogo:error 220 nogo:slow
  python behavior_markers.py 0 bloque:reposo 420 bloque:scroll 840 bloque:reposo
"""
import argparse
import os
import time

os.environ.setdefault("LSLAPICFG", os.path.join(os.path.dirname(os.path.abspath(__file__)), "lsl_api.cfg"))
import pylsl  # noqa: E402  (después de LSLAPICFG: entorno LSL cerrado a esta PC)


def main():
    p = argparse.ArgumentParser(description="Marcadores de conducta de prueba (stream MIRAI_Behavior)")
    p.add_argument("eventos", nargs="+", help="pares <segundos> <marcador>, p. ej. 200 nogo:error 220 nogo:slow")
    a = p.parse_args()
    if len(a.eventos) % 2:
        p.error("se esperan pares <segundos> <marcador>")
    plan = sorted((float(t), m) for t, m in zip(a.eventos[::2], a.eventos[1::2]))
    out = pylsl.StreamOutlet(pylsl.StreamInfo("MIRAI_Behavior", "Markers", 1, pylsl.IRREGULAR_RATE,
                                              pylsl.cf_string, "mirai-sim-behavior"))
    print("Stream 'MIRAI_Behavior' publicado; esperando al pipeline...")
    while not out.wait_for_consumers(1.0):
        pass
    t0 = time.monotonic()
    for t, m in plan:
        time.sleep(max(0.0, t - (time.monotonic() - t0)))
        out.push_sample([m])
        print(f"  t={time.monotonic() - t0:6.1f} s  → {m}")
    time.sleep(2.0)  # deja que el último marcador llegue antes de cerrar el stream


if __name__ == "__main__":
    main()
