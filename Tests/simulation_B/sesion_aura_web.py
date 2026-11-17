"""
sesion_aura_web.py — la misma sesión en vivo de sesion_aura.py, con la interfaz en el navegador (MIRAI 2026) · VERSIÓN B

Servidor Flask local: sirve web/sesion_aura.html, lanza los módulos sin fusionarlos (semaforo_canales.py,
behavior_markers.py, realtime_pipeline.py) y manda su salida en vivo a la página (Server-Sent Events). La lógica de
sesion_aura.py está aquí (lectura de líneas, estados, botones, abortar, detener con Ctrl+Break); el cronómetro y el
aviso sonoro corren en la página. 11 nov: sin verificación del stream (check_lsl_stream.py ya no se lanza): la tarjeta
Electrodes muestra el semáforo por canal, que corre aparte de la sesión y puede seguir encendido durante ella.

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
import csv
import io
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

from flask import Flask, Response, abort, jsonify, redirect, request, send_from_directory

import gonogo_db as gdb

HERE = os.path.dirname(os.path.abspath(__file__))
os.environ.setdefault("LSLAPICFG", os.path.join(HERE, "lsl_api.cfg"))
import pylsl  # noqa: E402  (después de LSLAPICFG) — solo local_clock(): el reloj LSL para la tarea Go/NoGo
PY = sys.executable
ENV = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUNBUFFERED": "1"}  # θ, µ… por la tubería sin cp1252
ANSI = re.compile(r"\x1b\[[0-9;]*m")
# Sin lista de preparación (9 nov) ni verificación del stream (11 nov): semáforo de electrodos + sesión.
# Interfaz en inglés (9 nov): los textos que ve la página están en inglés; la salida de los scripts (registro y parte de
# algunos estados) sigue en español, y el servidor la lee por sus palabras clave en español (no cambiarlas).
# Los nombres de bloque vienen del plan y behavior_markers.py los usa tal cual (marcadores bloque:<nombre>).
# Protocolo del Progress Report (10 nov; scroll 45 → 30 min el 11 nov; de vuelta a 45 min el 16 nov): Baseline 2 min →
# Go/NoGo pre 3 min → Scrolling 45 min → Go/NoGo post 3 min → fin (53 min). La calibración (10 s de calidad + 90 s,
# hasta +60 s de extensión) cae dentro del baseline; el reporte compara los parpadeos de cada bloque contra el primero
# con ≥ 2 min completos, que es el baseline. Los bloques gonogo_* duran 180 s = gonogo_db.BLOQUE_S.
PROTOCOL_PLAN, PROTOCOL_DUR = "0 bloque:baseline 120 bloque:gonogo_pre 300 bloque:scroll 3000 bloque:gonogo_post", "3180"
# 16 nov: los bloques gonogo_* arrancan solos en el teléfono (Session.gng_auto); el investigador solo entrega el teléfono.
ACTION = {"baseline": "eyes open, steady gaze, stay still (calibration)",
          "gonogo_pre": "hand over the lab phone: Go/NoGo starts by itself (pre)", "scroll": "start scrolling short videos",
          "gonogo_post": "hand over the lab phone: Go/NoGo starts by itself (post)",
          "reposo": "put the phone down, eyes open, steady gaze"}
CODIGO = re.compile(r"[A-Z0-9_-]{1,16}")  # código de participante (sin datos personales)
TIPO = {"practica": "Practice", "pre": "Before", "post": "After"}
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
        self._mon_stopped = False
        self.log = []  # [(texto, clase)] — se borra al iniciar la sesión
        self.params = {"name": "AURA", "sid": "AuraLSL-", "iaf": "10", "dur": PROTOCOL_DUR, "per": "420",
                       "plan": PROTOCOL_PLAN, "codigo": ""}
        self.valid = []  # % válidas de cada grupo de 10 ventanas (disjuntos): su media es el promedio de la sesión
        # Biomarcadores en tiempo real (10 nov): theta tónica y alfa periódica, último valor (dB) y Z frente al baseline;
        # hist = [segundo de la sesión, Zθ, Zα, % válidas] cada 10 ventanas (Z = None antes de calibrar): línea de
        # progresión y resumen por etapa; ivs = [segundo, nivel] de cada intervención encendida.
        self.bio, self.hist, self.ivs = {}, [], []
        self.btn = {"mon": True, "mon_stop": False, "start": True, "stop": False, "abort_ses": False, "rep": False,
                    "clear": True}  # clear: solo sin sesión en vivo (12 nov)
        self.chan = {}  # semáforo: {canal: [g/y/r, σ µV, % segmentos > 150 µV]} del último segundo; {} = apagado
        self.mon_lbl = ("Monitor off", "")
        self.status = {k: ("—", "") for k in STATUS}
        self.session_aborted = False  # "Bloque: — (abortado)"
        # Go/NoGo: colas SSE de los teléfonos; sesión abierta en la base (iniciada = ya pasó por Start session);
        # gng_hasta = hasta cuándo (time.monotonic) hay un bloque corriendo en el teléfono; gng_ult = resumen del último.
        self.gng_subs, self.gng = [], {"codigo": None, "sesion": None, "iniciada": False}
        self.gng_hasta, self.gng_ult = 0.0, None

    # ---------- emisión a la página ----------
    def snapshot(self):
        return {"action": ACTION, "label": LABEL, "params": self.params,
                "btn": self.btn, "chan": self.chan, "mon_lbl": self.mon_lbl, "status": self.status, "plan": self.plan,
                "dur": self.dur, "frozen": self.frozen, "bio": self.bio, "hist": self.hist, "ivs": self.ivs, "aborted": self.session_aborted,
                "elapsed": None if self.t_start is None else time.monotonic() - self.t_start,
                "running": [t for t, p in self.procs.items() if p.poll() is None],
                "run_dir": self.run_dir,
                "gng": {"telefonos": len(self.gng_subs), "urls": GNG_URLS, "bloque": self.gng_ult, "tipo": TIPO}}

    def emit(self, kind, data, subs=None):
        msg = f"event: {kind}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
        for q in list(self.subs if subs is None else subs):
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
        if tag == "semaforo" and line.startswith("SEMAFORO "):  # una por segundo: al estado, no al registro
            self.chan = json.loads(line[9:])
            self.mon_lbl = ("Live · last 10 s, updated every second", "ok")
            return
        # "NO PASA" va en rojo (en la ventana salía verde porque contiene "PASA").
        bad = any(k in line for k in ("FALLA", "SESIÓN DETENIDA", "Traceback", "Error", "abortada", "NO PASA"))
        warn = "AVISO RUIDO" in line
        self.add_log(f"[{tag}] {line}", "err" if bad else "warn" if warn else ("ok" if "PASA" in line else ""))
        if tag != "pipeline":
            return
        if line.startswith("Pipeline") and self.t_start is None:
            self.t_start = time.monotonic()  # el bucle arranca aquí; behavior_markers cuenta desde esta conexión
            for t, nombre in self.plan:  # bloques gonogo_pre / gonogo_post: la orden al teléfono sale sola a su hora
                if nombre.startswith("gonogo_") and nombre[7:] in gdb.PASADAS:
                    tm = threading.Timer(t, self.gng_auto, (nombre[7:], self.t_start))
                    tm.daemon = True  # no retiene el cierre del servidor; gng_auto descarta los de sesiones viejas
                    tm.start()
        elif line.startswith("Registro:"):
            self.run_dir = line.split(":", 1)[1].strip()
            gdb.run_dir(self.gng["sesion"], self.run_dir)  # la sesión de la base queda enlazada con la carpeta del pipeline
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
        stopped = tag == "semaforo" and self._mon_stopped  # detenido con su botón: no es un fallo
        self.add_log(f"[{tag}] exited (code {code})" + (" · stopped" if stopped else ""),
                     "ok" if code == 0 or stopped else "err")
        if tag == "semaforo":
            self.btn.update(mon=True, mon_stop=False)
            self.chan = {}
            self.mon_lbl = (("Monitor off", "") if self._mon_stopped
                            else (f"Monitor exited (code {code}): see the log", "err"))
        elif tag == "pipeline":
            self.stop_proc("behavior")
            self.t_start = None
            self.btn.update(stop=False, abort_ses=False, start=True, clear=True)
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
        """Aborta la sesión (conducta + pipeline); el semáforo sigue, tiene su propio botón."""
        if self._launch_timer:
            self._launch_timer.cancel()
            self._launch_timer = None
        running = [t for t in self.running() if t != "semaforo"]
        if not running:
            return "No session process is running."
        self._aborted = True
        for tag in running:
            self.stop_proc(tag)
        self.t_start = None
        self.add_log(f"[system] Processes aborted manually: {', '.join(running)}", "err")
        self.btn.update(abort_ses=False, stop=False, start=True, clear=True)
        self.session_aborted = True
        return None

    def start_monitor(self, p):
        self.params.update({k: str(p[k]) for k in ("name", "sid") if k in p})
        self._mon_stopped = False
        self.btn.update(mon=False, mon_stop=True)
        self.chan = {}
        self.mon_lbl = ("Looking for the stream…", "")
        self.launch("semaforo", ["semaforo_canales.py", "--name", self.params["name"], "--source-id", self.params["sid"]])

    def stop_monitor(self):
        self._mon_stopped = True  # kill() da código ≠ 0: no es un fallo
        self.stop_proc("semaforo")

    # ---------- Go/NoGo ----------
    def gng_sesion(self, codigo, iniciar):
        """Sesión de la base para este participante: la práctica abre una y Start session la reutiliza; otra persona,
        o un nuevo Start session para la misma, abre otra."""
        if self.gng["codigo"] != codigo or self.gng["iniciada"]:
            self.gng = {"codigo": codigo, "sesion": gdb.sesion(codigo), "iniciada": False}
        self.gng["iniciada"] = iniciar

    def gng_start(self, codigo, tipo):
        """Abre un bloque (practica / pre / post) y manda la orden a los teléfonos; ValueError si no se puede."""
        live = not self.btn["start"]  # desde Start session hasta que el pipeline termina o se aborta
        if not CODIGO.fullmatch(codigo) or tipo not in gdb.PASADAS:
            raise ValueError("Participant code (letters, digits, - or _; max 16) and block type are required.")
        if live and codigo != self.gng["codigo"]:
            raise ValueError(f"A session is live for {self.gng['codigo']}: its Go/NoGo blocks cannot be mixed.")
        if not self.gng_subs:
            raise ValueError("No phone connected: open the Go/NoGo page (/gng) on the phone first.")
        if time.monotonic() < self.gng_hasta:
            raise ValueError("A Go/NoGo block is already running on the phone.")
        if not live:
            self.gng_sesion(codigo, False)
        orden = {**gdb.bloque(self.gng["sesion"], tipo, pylsl.local_clock()), "codigo": codigo}
        n = len(orden["secuencia"])
        self.gng_hasta = time.monotonic() + (orden["prep_ms"] + n * orden["soa_ms"]) / 1000
        self.gng_ult = gdb.resumen(bloque_id=orden["bloque"])[0]
        self.emit("inicio", orden, self.gng_subs)
        self.add_log(f"[gonogo] {TIPO[tipo]} block started for {codigo} ({n} trials)", "ok")
        return orden

    def gng_auto(self, tipo, t_start):
        """Temporizador del plan: arranca el bloque si sigue viva la misma sesión; si no se puede, lo deja en el registro."""
        with self.lock:
            if self.t_start != t_start:
                return
            try:
                self.gng_start(self.gng["codigo"], tipo)
            except ValueError as e:
                self.add_log(f"[gonogo] {TIPO[tipo]} block NOT started: {e}", "err")
            self.push_state()

    def start_session(self, p):
        codigo = str(p.get("codigo", "")).strip().upper()
        if not CODIGO.fullmatch(codigo):
            return "Enter the participant code (letters, digits, - or _; e.g. P01) before starting."
        self.params.update({k: str(p[k]) for k in ("name", "sid", "iaf", "dur", "per", "plan") if k in p})
        self.params["codigo"] = codigo
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
        self.gng_sesion(codigo, True)
        self.gng_ult = None
        self.log.clear()  # el registro empieza con la sesión (el semáforo no escribe en él salvo al arrancar)
        self.emit("clear", None)
        self.plan, self.dur, self.frozen = plan, dur, False
        self.run_dir, self.valid, self.bio, self.hist, self.ivs = None, [], {}, [], []
        self.session_aborted = False
        self.btn.update(start=False, rep=False, stop=True, abort_ses=True, clear=False)
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

    def clear_session(self):
        """Borra el registro y los datos de la última sesión que guarda el tablero (no toca runs/ ni el semáforo)."""
        if any(t in self.running() for t in ("pipeline", "behavior")):
            return "A session is live: stop or abort it first."
        self.log.clear()
        self.emit("clear", None)
        self.plan, self.dur, self.frozen, self.t_start = [], 0.0, False, None
        self.run_dir, self.valid, self.bio, self.hist, self.ivs = None, [], {}, [], []
        self.session_aborted = False
        self.gng_ult = None
        self.btn["rep"] = False
        for k in self.status:
            self.set_status(k, "—")
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
TOKEN = None  # solo con --lan: acceso completo al tablero desde la red
TEL = None  # solo con --lan: clave corta del teléfono, que solo abre la tarea Go/NoGo
GNG_URLS = []  # enlaces cortos de la tarea Go/NoGo para el teléfono (solo con --lan)


@app.before_request
def check_token():
    """Con --lan, cualquiera en la red podría lanzar o detener procesos: se exige el token impreso en la terminal.
    El teléfono entra con un enlace corto, <IP>:<puerto>/<clave>: la clave se le queda guardada un año y solo le abre
    la tarea Go/NoGo (/gng y /api/gng/…), no el tablero ni sus acciones. Por eso puede ser corta y fácil de teclear."""
    if TEL and request.path == f"/{TEL}":
        qs = request.query_string.decode()  # p. ej. ?demo=practica
        resp = redirect("/gng" + (f"?{qs}" if qs else ""))
        resp.set_cookie("tel", TEL, max_age=365 * 86400, httponly=True, samesite="Strict")
        return resp
    if TOKEN is None or request.remote_addr in ("127.0.0.1", "::1"):
        return None
    if request.args.get("token") == TOKEN or request.cookies.get("token") == TOKEN:
        return None
    if request.cookies.get("tel") == TEL and request.path.startswith(("/gng", "/api/gng/")):
        return None
    abort(403)


@app.after_request
def keep_token(resp):
    if TOKEN and request.args.get("token") == TOKEN:
        resp.set_cookie("token", TOKEN, httponly=True, samesite="Strict")
    return resp


@app.get("/")
@app.get("/resultados")  # misma página: la vista de resultados del Go/NoGo se muestra según la ruta
def index():
    return send_from_directory(os.path.join(HERE, "web"), "sesion_aura.html")


@app.get("/api/estado")
def estado():
    with S.lock:
        return jsonify({**S.snapshot(), "log": S.log})


def sse(subs, first):
    """Respuesta SSE: suscribe una cola a `subs`, manda first() y después cada mensaje que le llegue."""
    q = queue.Queue()
    with S.lock:
        subs.append(q)
        head = first()
        if subs is S.gng_subs:
            S.push_state()  # el dashboard muestra si hay un teléfono conectado

    def stream():
        try:
            yield head
            while True:
                try:
                    yield q.get(timeout=10)
                except queue.Empty:
                    # Evento (no comentario SSE) para que la página lo vea: si pasan 25 s sin nada, reconecta.
                    yield "event: ping\ndata: \n\n"
        finally:
            with S.lock:
                subs.remove(q)
                if subs is S.gng_subs:
                    S.push_state()

    return Response(stream(), mimetype="text/event-stream", headers={"Cache-Control": "no-cache"})


@app.get("/api/eventos")
def eventos():
    return sse(S.subs, lambda: f"event: full\ndata: {json.dumps({**S.snapshot(), 'log': S.log}, ensure_ascii=False)}\n\n")


def act(fn):
    """Ejecuta una acción con el candado, emite el estado nuevo y devuelve {error} si la acción lo pide."""
    with S.lock:
        err = fn()
        S.push_state()
    return jsonify({"error": err})


@app.post("/api/semaforo/iniciar")
def semaforo_iniciar():
    return act(lambda: S.start_monitor(request.get_json()))


@app.post("/api/semaforo/detener")
def semaforo_detener():
    return act(S.stop_monitor)


@app.post("/api/sesion/iniciar")
def sesion_iniciar():
    return act(lambda: S.start_session(request.get_json()))


@app.post("/api/sesion/detener")
def sesion_detener():
    return act(S.stop_session)


@app.post("/api/abortar")
def abortar():
    return act(S.abort_all)


@app.post("/api/sesion/limpiar")
def sesion_limpiar():
    return act(S.clear_session)


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


# ---------- Go/NoGo (Fase 1 de Tests/Plan_App_GoNoGo.md): sincronización, orden de inicio y recepción de ensayos ----------
# El teléfono mide los tiempos con su reloj y su desfase contra /api/gng/sync; la red no entra en el tiempo de reacción.
def gng(fn):
    """Ejecuta fn con el cuerpo JSON; los datos mal formados o de un bloque que no existe devuelven 400."""
    try:
        return jsonify(fn(request.get_json(silent=True) or {}))
    except (AttributeError, KeyError, TypeError, ValueError) as e:
        return jsonify({"error": str(e)}), 400


@app.get("/gng")
def gng_app():
    """La tarea en el teléfono (Fase 2). Autoprueba: /gng?demo=practica."""
    return send_from_directory(os.path.join(HERE, "web"), "gonogo.html")


@app.get("/api/gng/eventos")
def gng_eventos():
    """Canal del teléfono: aquí recibe la orden de inicio de cada bloque (evento 'inicio')."""
    return sse(S.gng_subs, lambda: "event: hola\ndata: {}\n\n")


@app.post("/api/gng/sync")
def gng_sync():
    """Reloj LSL de esta PC (el del pipeline); el teléfono calcula su desfase con la ida y vuelta."""
    return jsonify({"t": pylsl.local_clock()})


@app.post("/api/gng/bloque/iniciar")
def gng_iniciar():
    """Desde el dashboard: abre un bloque (practica / pre / post) y manda la orden a los teléfonos conectados."""
    def fn(p):
        with S.lock:
            orden = S.gng_start(str(p.get("codigo", "")).strip().upper(), p.get("tipo"))
            S.push_state()
        return orden
    return gng(fn)


@app.post("/api/gng/bloque/sync")
def gng_bloque_sync():
    """Desde el teléfono, al inicio y al final del bloque: su desfase contra el reloj LSL."""
    def fn(p):
        gdb.sync(int(p["bloque"]), p["fase"], float(p["desfase"]), float(p["tel"]), float(p["ida_vuelta_ms"]),
                 pylsl.local_clock(), p.get("cuadro_ms"), request.user_agent.string)
        if p["fase"] == "fin":  # llega después del último ensayo: el bloque terminó en el teléfono
            with S.lock:
                r = S.gng_ult = gdb.resumen(bloque_id=int(p["bloque"]))[0]
                S.gng_hasta = 0.0
                tr = "—" if r["tr_medio_ms"] is None else f"{r['tr_medio_ms']:.0f} ms"
                S.add_log(f"[gonogo] {TIPO[r['tipo']]} block finished for {r['codigo']}: {r['ensayos']}/{r['total']} "
                          f"trials · commission errors {r['comisiones']}/{r['nogo']} · omissions {r['omisiones']} · "
                          f"mean RT {tr}" + ("" if r["completo"] else " · INCOMPLETE"), "ok" if r["completo"] else "err")
                S.push_state()
        return {"error": None}
    return gng(fn)


@app.post("/api/gng/ensayos")
def gng_ensayos():
    """Desde el teléfono, entre estímulos: uno o varios ensayos. Responde los n guardados; reenviar no duplica."""
    def fn(p):
        ok = gdb.ensayos(int(p["bloque"]), p["ensayos"], pylsl.local_clock())
        S.gng_ult = gdb.resumen(bloque_id=int(p["bloque"]))[0]
        S.emit("gng", S.gng_ult)  # contadores en vivo de la tarjeta Go/NoGo
        return {"ok": ok}
    return gng(fn)


@app.get("/api/gng/resumen")
def gng_resumen():
    """Tabla por bloque (comisiones, omisiones, TR medio), de todos o de un participante (?codigo=P01)."""
    return jsonify(gdb.resumen(request.args.get("codigo")))


@app.get("/api/gng/ensayos")
def gng_registros():
    """Ensayos de un bloque, uno por uno (vista de resultados)."""
    return jsonify(gdb.registros(bloque_id=request.args.get("bloque", type=int) or 0))


@app.get("/api/gng/exportar")
def gng_exportar():
    """CSV para descargar: ?que=resumen (una fila por bloque) o ?que=ensayos (una por ensayo); ?codigo= filtra."""
    que, codigo = request.args.get("que", "resumen"), request.args.get("codigo")
    filas = gdb.registros(codigo) if que == "ensayos" else gdb.resumen(codigo)
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(filas[0]) if filas else ["sin_datos"], lineterminator="\n")
    w.writeheader()
    w.writerows(filas)
    nombre = f"gonogo_{'ensayos' if que == 'ensayos' else 'resumen'}{'_' + codigo if codigo else ''}.csv"
    return Response("﻿" + buf.getvalue(), mimetype="text/csv; charset=utf-8",  # BOM: Excel lo abre como UTF-8
                    headers={"Content-Disposition": f'attachment; filename="{nombre}"'})


def guardado(nombre, nuevo):
    """Secreto de --lan guardado en data/ (fuera de git): se crea una vez y no cambia al reiniciar el servidor, así el
    enlace y el acceso directo del teléfono siguen sirviendo."""
    path = os.path.join(HERE, "data", nombre)
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(nuevo())
    with open(path, encoding="utf-8") as f:
        return f.read().strip()


def main():
    global TOKEN, TEL
    ap = argparse.ArgumentParser(description="Sesión AURA en el navegador (servidor local)")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--lan", action="store_true", help="aceptar conexiones de la red local (con token)")
    ap.add_argument("--db", help="otra base de datos Go/NoGo (pruebas); por defecto data/mirai.db")
    a = ap.parse_args()
    if a.db:
        gdb.DB = os.path.abspath(a.db)
    gdb.init()
    atexit.register(S.shutdown)
    host = "127.0.0.1"
    print(f"Sesión AURA: http://localhost:{a.port}")
    if a.lan:
        host, TOKEN = "0.0.0.0", guardado("token.txt", lambda: secrets.token_urlsafe(8))
        # Clave del teléfono: 6 letras minúsculas y dígitos sin los que se confunden (0/o, 1/l/i), para teclearla.
        TEL = guardado("telefono.txt", lambda: "".join(secrets.choice("abcdefghjkmnpqrstuvwxyz23456789") for _ in range(6)))
        # Todas las IPv4 de esta PC (Wi-Fi, zona Wi-Fi propia…): el teléfono usa la de la red que comparte con ella.
        ips = sorted({i[4][0] for i in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET)} - {"127.0.0.1"})
        for ip in ips:
            print(f"Desde la red: http://{ip}:{a.port}/?token={TOKEN}")
            GNG_URLS.append(f"{ip}:{a.port}/{TEL}")  # sin http://: el navegador del teléfono lo pone solo
            print(f"  Go/NoGo en el teléfono: http://{GNG_URLS[-1]}")
    print("Ctrl+C para cerrar el servidor (y los procesos que sigan corriendo).")
    app.run(host=host, port=a.port, threaded=True, debug=False)


if __name__ == "__main__":
    main()
