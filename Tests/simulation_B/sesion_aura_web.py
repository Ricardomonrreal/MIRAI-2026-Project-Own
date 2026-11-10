"""
sesion_aura_web.py — la misma sesión en vivo de sesion_aura.py, con la interfaz en el navegador (MIRAI 2026) · VERSIÓN B

Servidor Flask local: sirve web/sesion_aura.html, lanza los mismos tres módulos sin fusionarlos (check_lsl_stream.py,
behavior_markers.py, realtime_pipeline.py) y manda su salida en vivo a la página (Server-Sent Events). La lógica de
sesion_aura.py está aquí (lectura de líneas, estados, botones, abortar, detener con Ctrl+Break) salvo la lista de
preparación, que ya no forma parte de la página (Paso 1 = verificación, Paso 2 = sesión); el cronómetro y el aviso
sonoro corren en la página. sesion_aura.py (tkinter) sigue disponible y no cambia.

Sin terminal: doble clic en servidor_web.bat (consola minimizada + abre la página; si ya corre, solo la abre). Usa
la ruta absoluta de esta carpeta, así que una copia o acceso directo funciona desde cualquier lugar.
Uso (desde una terminal: Detener necesita una consola compartida para mandar Ctrl+Break al pipeline):
  python sesion_aura_web.py              # http://localhost:8000, solo esta PC
  python sesion_aura_web.py --lan        # también desde la red (tablet/celular): http://<IP de la PC>:8000/?token=…
Ctrl+C en la terminal cierra el servidor y los procesos que sigan corriendo (sin reporte, como cerrar la ventana).
El navegador no puede leer LSL ni lanzar procesos: por eso este servidor tiene que estar encendido.
"""
import argparse
import atexit
import json
import os
import queue
import re
import secrets
import signal
import socket
import subprocess
import sys
import threading
import time

from flask import Flask, Response, abort, jsonify, request, send_from_directory

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable
ENV = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUNBUFFERED": "1"}  # θ, µ… por la tubería sin cp1252
ANSI = re.compile(r"\x1b\[[0-9;]*m")
# Sin lista de preparación (9 nov): la página empieza en la verificación (Paso 1) y la sesión es el Paso 2.
# Interfaz en inglés (9 nov): los textos que ve la página están en inglés; la salida de los scripts (registro y parte de
# algunos estados) sigue en español, y el servidor la lee por sus palabras clave en español (no cambiarlas).
# Los nombres de bloque vienen del plan y behavior_markers.py los usa tal cual (marcadores bloque:<nombre>).
# Protocolo del Progress Report (10 nov): Baseline 2 min → Go/NoGo pre 3 min → Scrolling 45 min → Go/NoGo post 3 min →
# fin. La calibración (10 s de calidad + 90 s, hasta +60 s de extensión) cae dentro del baseline; el reporte compara los
# parpadeos de cada bloque contra el primero con ≥ 2 min completos, que es el baseline.
PROTOCOL_PLAN, PROTOCOL_DUR = "0 bloque:baseline 120 bloque:gonogo_pre 300 bloque:scroll 3000 bloque:gonogo_post", "3180"
ACTION = {"baseline": "eyes open, steady gaze, stay still (calibration)",
          "gonogo_pre": "start the Go/NoGo task (pre)", "scroll": "start scrolling short videos",
          "gonogo_post": "start the Go/NoGo task (post)", "reposo": "put the phone down, eyes open, steady gaze"}
LABEL = {"baseline": "Baseline", "gonogo_pre": "Go/NoGo · pre", "scroll": "Scrolling", "gonogo_post": "Go/NoGo · post",
         "reposo": "Rest"}
# Sin "Run" (9 nov): la carpeta de la sesión ya no se muestra; run_dir se sigue guardando para el reporte.
STATUS = ("Quality", "Calibration", "Valid windows", "Noise", "Blinks", "Blink threshold", "Intervention")
# Frases fijas del pipeline, calibration.py y jitai.py que llegan a los estados (no al registro). Orden: frases largas
# antes que sus partes. ponytail: lista a mano; si se agregan mensajes nuevos en esos scripts, añadirlos aquí.
EN = [("SESIÓN DETENIDA", "SESSION STOPPED"), ("calibración abortada", "calibration aborted"),
      ("sin canales válidos en la ROI", "no valid channels in the ROI"), ("ventanas válidas", "valid windows"),
      ("menos de", "fewer than"), ("extensiones de", "extensions of"), ("tras", "after"),
      ("canales malos", "bad channels"), ("ninguno", "none"), ("fases AURA", "AURA phases"), ("primeros", "first"),
      ("(el del período anterior)", "(previous period's)"), ("parpadeos", "blinks"), ("umbral", "threshold"),
      ("cue de conciencia", "awareness cue"), ("fricción", "friction"), ("pausa restaurativa", "restorative pause"),
      ("eventos de conducta en", "behavior events in"), ("sin eventos de conducta", "without behavior events"),
      ("durante", "for"), ("invalida", "invalidates")]


def en(s):
    for es_, en_ in EN:
        s = s.replace(es_, en_)
    return s
# Colores de sesion_aura.py → clases de la página: rojo #A32D2D = err, verde #0F6E56 = ok, naranja #B5590B = warn.


class Session:
    """Equivalente de SessionApp sin la ventana: guarda el estado y lo emite a todas las páginas conectadas."""

    def __init__(self):
        self.lock = threading.RLock()
        self.subs = []  # una cola por página conectada (SSE)
        self.procs = {}
        self.t_start = self.run_dir = None
        self.plan, self.dur, self.frozen = [], 0.0, False
        self._launch_timer = None
        self._aborted = False
        self.log = []  # [(texto, clase)] — se borra al iniciar la verificación, como en la ventana
        self.params = {"name": "AURA", "sid": "AuraLSL-", "chk_s": "120", "iaf": "10", "dur": PROTOCOL_DUR, "per": "420",
                       "plan": PROTOCOL_PLAN}
        self.valid = []  # % válidas de cada grupo de 10 ventanas (disjuntos): su media es el promedio de la sesión
        # Biomarcadores en tiempo real (10 nov): theta tónica y alfa periódica, último valor (dB) y Z frente al baseline;
        # hist = [segundo de la sesión, Zθ, Zα, % válidas] cada 10 ventanas (Z = None antes de calibrar): línea de
        # progresión y resumen por etapa; ivs = [segundo, nivel] de cada intervención encendida.
        self.bio, self.hist, self.ivs = {}, [], []
        self.btn = {"check": True, "ok": False, "abort_chk": False, "start": False, "stop": False, "abort_ses": False,
                    "rep": False}
        self.check_lbl = ("Not verified", "")
        self.status = {k: ("—", "") for k in STATUS}
        self.session_aborted = False  # "Bloque: — (abortado)"

    # ---------- emisión a la página ----------
    def snapshot(self):
        return {"action": ACTION, "label": LABEL, "params": self.params,
                "btn": self.btn, "check_lbl": self.check_lbl, "status": self.status, "plan": self.plan,
                "dur": self.dur, "frozen": self.frozen, "bio": self.bio, "hist": self.hist, "ivs": self.ivs, "aborted": self.session_aborted,
                "elapsed": None if self.t_start is None else time.monotonic() - self.t_start,
                "running": [t for t, p in self.procs.items() if p.poll() is None],
                "run_dir": self.run_dir}

    def emit(self, kind, data):
        msg = f"event: {kind}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
        for q in list(self.subs):
            q.put(msg)

    def push_state(self):
        self.emit("state", self.snapshot())

    def add_log(self, text, cls=""):
        self.log.append((text, cls))
        self.emit("log", [text, cls])

    def set_status(self, k, txt, color=""):
        self.status[k] = (txt, color)

    # ---------- procesos ----------
    def launch(self, tag, args):
        p = subprocess.Popen([PY, "-u", *args], cwd=HERE, env=ENV, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             text=True, encoding="utf-8", errors="replace",
                             creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0))
        self.procs[tag] = p
        threading.Thread(target=self._read, args=(tag, p), daemon=True).start()
        return p

    def _read(self, tag, p):
        for line in p.stdout:
            with self.lock:
                self.on_line(tag, ANSI.sub("", line.rstrip()))
                self.push_state()
        p.wait()
        with self.lock:
            self.on_exit(tag, p)
            self.push_state()

    def on_line(self, tag, line):
        # "NO PASA" va en rojo (en la ventana salía verde porque contiene "PASA").
        bad = any(k in line for k in ("FALLA", "SESIÓN DETENIDA", "Traceback", "Error", "abortada", "NO PASA"))
        warn = "AVISO RUIDO" in line
        self.add_log(f"[{tag}] {line}", "err" if bad else "warn" if warn else ("ok" if "PASA" in line else ""))
        if tag != "pipeline":
            return
        if line.startswith("Pipeline") and self.t_start is None:
            self.t_start = time.monotonic()  # el bucle arranca aquí; behavior_markers cuenta desde esta conexión
        elif line.startswith("Registro:"):
            self.run_dir = line.split(":", 1)[1].strip()
        elif line.startswith("Chequeo de calidad"):
            self.set_status("Quality", en(line.split(":", 1)[1].strip()), "err" if "malos ['Fp1'" in line else "")
        elif "CALIBRACIÓN CONGELADA" in line:
            self.frozen = True
            self.set_status("Calibration", en(line.strip().replace("CALIBRACIÓN CONGELADA", "frozen")), "ok")
        elif "SESIÓN DETENIDA" in line:
            self.set_status("Calibration", en(line.strip()), "err")
        elif "NIVEL" in line and ">>>" in line:
            self.set_status("Intervention", en(line.split(">>>", 1)[1].strip().replace("NIVEL", "LEVEL")))
            if (lv := re.search(r"NIVEL (\d) ON", line)) and self.t_start is not None:
                self.ivs.append([round(time.monotonic() - self.t_start), int(lv.group(1))])
        if m := re.search(r"válidas\(últ\. 10\)=(\d+)%", line):
            self.valid.append(int(m.group(1)))
            self.set_status("Valid windows", f"{m.group(1)}% last 10 · avg {sum(self.valid) / len(self.valid):.0f}% "
                                             f"over {len(self.valid) * 10} windows")
            # θ_per/α_per solo vienen si la ventana tuvo features; Zθ/Zα, desde que la calibración se congela.
            per = re.search(r"θ_per=\s*(-?[\d.]+)\s+α_per=\s*(-?[\d.]+)", line)
            z = re.search(r"Zθ=\s*([+-]?[\d.]+)\s+Zα=\s*([+-]?[\d.]+)", line)
            for i, k in enumerate(("theta", "alpha"), 1):
                b = self.bio.setdefault(k, {"per": None, "z": None})
                if per:
                    b["per"] = float(per.group(i))
                if z:
                    b["z"] = float(z.group(i))
            if self.t_start is not None:
                self.hist.append([round(time.monotonic() - self.t_start), float(z.group(1)) if z else None,
                                  float(z.group(2)) if z else None, int(m.group(1))])
            self.set_status("Noise", "no warning")  # el pipeline imprime AVISO RUIDO justo después, si lo hay
        if warn:
            # Canales con ≥ 50 % de segmentos de 2 s > 150 µV (umbral de rechazo); "invalida" = sin segmento limpio.
            # Rojo si alguno invalida ventanas por sí solo; naranja si solo está ruidoso. Revisar gel/contacto de esos.
            chs = en(line.split(":", 1)[1].strip())
            self.set_status("Noise", chs + " → check contact", "err" if "invalidates" in chs else "warn")
        if m := re.search(r"parpadeos=(\S+)/min", line):
            self.set_status("Blinks", f"{m.group(1)}/min (live, provisional)")
        elif line.strip().startswith("PARPADEOS"):  # cierre de período: línea propia, la tasa en vivo no la tapa
            self.set_status("Blink threshold", en(line.strip()[10:]) + " (final)")
        elif "[" in line and "calibrando" in line:
            self.set_status("Calibration", "calibrating… stay still, relax forehead and jaw")

    def on_exit(self, tag, p):
        if self.procs.get(tag) is not p:  # ya reemplazado por un lanzamiento nuevo
            return
        code = self.procs.pop(tag).returncode
        self.add_log(f"[{tag}] exited (code {code})", "ok" if code == 0 else "err")
        if tag == "check":
            self.btn.update(check=True, abort_chk=False)
            if self._aborted:
                self.check_lbl = ("Verification aborted manually", "err")
                self.btn["ok"] = False
            else:
                self.check_lbl = (f"Finished (code {code}): review the log and decide", "")
                self.btn["ok"] = True
        elif tag == "pipeline":
            self.stop_proc("behavior")
            self.t_start = None
            self.btn.update(stop=False, abort_ses=False, start=True)
            if self.run_dir and os.path.exists(os.path.join(self.run_dir, "reporte.md")):
                self.btn["rep"] = True
            self.emit("bell", None)

    def stop_proc(self, tag):
        p = self.procs.get(tag)
        if p and p.poll() is None:
            try:
                p.kill()
            except Exception:
                pass

    def running(self):
        return [tag for tag, p in self.procs.items() if p.poll() is None]

    # ---------- acciones (las confirmaciones las pide la página antes de llamar) ----------
    def abort_all(self):
        if self._launch_timer:
            self._launch_timer.cancel()
            self._launch_timer = None
        running = self.running()
        if not running:
            return "No process is running."
        self._aborted = True
        for tag in list(self.procs):
            self.stop_proc(tag)
        self.t_start = None
        self.add_log(f"[system] Processes aborted manually: {', '.join(running)}", "err")
        self.btn.update(check=True, abort_chk=False, abort_ses=False, stop=False, start=self.btn["ok"])
        if "pipeline" in running or "behavior" in running:
            self.session_aborted = True
        return None

    def start_check(self, p):
        self.params.update({k: str(p[k]) for k in ("name", "sid", "chk_s") if k in p})
        self._aborted = False
        self.btn.update(check=False, ok=False, start=False, abort_chk=True)
        self.check_lbl = (f"Verifying ({self.params['chk_s']} s)…", "")
        self.log.clear()
        self.emit("clear", None)
        self.launch("check", ["check_lsl_stream.py", "--name", self.params["name"], "--source-id",
                              self.params["sid"], "--seconds", self.params["chk_s"]])

    def check_ok(self):
        self.check_lbl = ("Verification accepted", "ok")
        self.btn["start"] = True

    def start_session(self, p):
        self.params.update({k: str(p[k]) for k in ("name", "sid", "iaf", "dur", "per", "plan") if k in p})
        tok = self.params["plan"].split()
        try:
            if len(tok) % 2:
                raise ValueError
            plan = sorted((float(t), m.split(":", 1)[1]) for t, m in zip(tok[::2], tok[1::2]))
            float(self.params["iaf"]), float(self.params["per"])
            dur = float(self.params["dur"])
        except (ValueError, IndexError):
            return "Check IAF, duration, period and blocks (<seconds> bloque:<name>)."
        self._aborted = False
        self.plan, self.dur, self.frozen = plan, dur, False
        self.run_dir, self.valid, self.bio, self.hist, self.ivs = None, [], {}, [], []
        self.session_aborted = False
        self.btn.update(start=False, rep=False, stop=True, abort_ses=True)
        for k in self.status:
            self.set_status(k, "—")
        self.launch("behavior", ["behavior_markers.py", *tok])

        def launch_pipeline():
            with self.lock:
                if self._launch_timer is None:  # abortado durante la espera
                    return
                self._launch_timer = None
                self.launch("pipeline", [
                    "realtime_pipeline.py", "--name", self.params["name"], "--source-id", self.params["sid"],
                    "--seconds", self.params["dur"], "--iaf", self.params["iaf"], "--parpadeo-periodo",
                    self.params["per"]])
                self.push_state()

        # El pipeline busca MIRAI_Behavior 2 s al arrancar: el stream de conducta tiene que existir antes.
        self._launch_timer = threading.Timer(1.5, launch_pipeline)
        self._launch_timer.start()
        return None

    def stop_session(self):
        p = self.procs.get("pipeline")
        if p and p.poll() is None:
            p.send_signal(signal.CTRL_BREAK_EVENT if os.name == "nt" else signal.SIGINT)

    def shutdown(self):
        if self._launch_timer:
            self._launch_timer.cancel()
        for tag in list(self.procs):
            self.stop_proc(tag)


S = Session()
app = Flask(__name__, static_folder=None)
TOKEN = None  # solo con --lan


@app.before_request
def check_token():
    """Con --lan, cualquiera en la red podría lanzar o detener procesos: se exige el token impreso en la terminal."""
    if TOKEN is None or request.remote_addr in ("127.0.0.1", "::1"):
        return None
    if request.args.get("token") == TOKEN or request.cookies.get("token") == TOKEN:
        return None
    abort(403)


@app.after_request
def keep_token(resp):
    if TOKEN and request.args.get("token") == TOKEN:
        resp.set_cookie("token", TOKEN, httponly=True, samesite="Strict")
    return resp


@app.get("/")
def index():
    return send_from_directory(os.path.join(HERE, "web"), "sesion_aura.html")


@app.get("/api/estado")
def estado():
    with S.lock:
        return jsonify({**S.snapshot(), "log": S.log})


@app.get("/api/eventos")
def eventos():
    q = queue.Queue()
    with S.lock:
        S.subs.append(q)
        first = f"event: full\ndata: {json.dumps({**S.snapshot(), 'log': S.log}, ensure_ascii=False)}\n\n"

    def stream():
        try:
            yield first
            while True:
                try:
                    yield q.get(timeout=10)
                except queue.Empty:
                    # Evento (no comentario SSE) para que la página lo vea: si pasan 25 s sin nada, reconecta.
                    yield "event: ping\ndata: \n\n"
        finally:
            with S.lock:
                S.subs.remove(q)

    return Response(stream(), mimetype="text/event-stream", headers={"Cache-Control": "no-cache"})


def act(fn):
    """Ejecuta una acción con el candado, emite el estado nuevo y devuelve {error} si la acción lo pide."""
    with S.lock:
        err = fn()
        S.push_state()
    return jsonify({"error": err})


@app.post("/api/verificacion/iniciar")
def verif_iniciar():
    return act(lambda: S.start_check(request.get_json()))


@app.post("/api/verificacion/ok")
def verif_ok():
    return act(S.check_ok)


@app.post("/api/sesion/iniciar")
def sesion_iniciar():
    return act(lambda: S.start_session(request.get_json()))


@app.post("/api/sesion/detener")
def sesion_detener():
    return act(S.stop_session)


@app.post("/api/abortar")
def abortar():
    return act(S.abort_all)


@app.post("/api/reporte/abrir")
def reporte_abrir():
    """Como en la ventana: abre reporte.md con el programa predeterminado de esta PC."""
    if not S.run_dir or not os.path.exists(os.path.join(S.run_dir, "reporte.md")):
        return jsonify({"error": "There is no report for this session yet."})
    os.startfile(os.path.join(S.run_dir, "reporte.md"))
    return jsonify({"error": None})


@app.get("/api/reporte")
def reporte_ver():
    """Para verlo desde otro dispositivo de la red, donde os.startfile no llega."""
    if not S.run_dir or not os.path.exists(os.path.join(S.run_dir, "reporte.md")):
        abort(404)
    with open(os.path.join(S.run_dir, "reporte.md"), encoding="utf-8") as f:
        return Response(f.read(), content_type="text/plain; charset=utf-8")


def main():
    global TOKEN
    ap = argparse.ArgumentParser(description="Sesión AURA en el navegador (servidor local)")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--lan", action="store_true", help="aceptar conexiones de la red local (con token)")
    a = ap.parse_args()
    atexit.register(S.shutdown)
    host = "127.0.0.1"
    print(f"Sesión AURA: http://localhost:{a.port}")
    if a.lan:
        host, TOKEN = "0.0.0.0", secrets.token_urlsafe(8)
        ip = socket.gethostbyname(socket.gethostname())
        print(f"Desde la red: http://{ip}:{a.port}/?token={TOKEN}")
    print("Ctrl+C para cerrar el servidor (y los procesos que sigan corriendo).")
    app.run(host=host, port=a.port, threaded=True, debug=False)


if __name__ == "__main__":
    main()
