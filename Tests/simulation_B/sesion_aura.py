"""
sesion_aura.py — sesión en vivo con la AURA en una sola ventana (MIRAI 2026) · VERSIÓN B

Junta los tres módulos sin fusionarlos: cada uno sigue siendo su propio script y aquí solo se lanzan en orden, con el
usuario marcando cada paso. Mismos pasos que la versión web (web/sesion_aura.html); sin lista de preparación (9 nov).
  1. Verificación: check_lsl_stream.py; al terminar, el usuario la da por buena (o la repite).
  2. Sesión: behavior_markers.py (bloques) y, 1.5 s después, realtime_pipeline.py. Cronómetro con el bloque actual y la
     próxima acción manual (barra espaciadora en Aura, empezar el scroll…). Detener = Ctrl+Break al pipeline, que lo
     trata como Ctrl+C y escribe igual su reporte.

Uso (desde una terminal: Detener necesita una consola compartida para mandar Ctrl+Break):
  python sesion_aura.py
Con el emulador (prueba sin diadema): nombre del stream AURA y prefijo mirai-sim- con
  python mock_lsl_streamer.py --name AURA --duration 1500 --wait
"""
import os
import queue
import re
import signal
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable
ENV = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUNBUFFERED": "1"}  # θ, µ… por la tubería sin cp1252
ANSI = re.compile(r"\x1b\[[0-9;]*m")
ACTION = {"reposo": "deja el teléfono, ojos abiertos y mirada fija", "scroll": "empieza el scroll (videos cortos)"}


def fmt(s):
    return f"{int(s // 60)}:{int(s % 60):02d}"


class SessionApp:
    def __init__(self, root):
        self.root = root
        self.q = queue.Queue()
        self.procs = {}
        self.t_start = self.run_dir = None
        self.plan = []
        self._launch_timer = None
        self._aborted = False
        self.root.title("MIRAI · sesión en vivo con la AURA")
        self.root.geometry("1380x820")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.paned.pack(fill=tk.BOTH, expand=True)
        self._build_controls()
        self._build_log()
        self.root.after(100, self.poll)

    # ---------- interfaz ----------
    def _build_controls(self):
        c = ttk.Frame(self.paned, padding=12, width=480)
        self.paned.add(c, weight=0)
        bold = ("Arial", 10, "bold")

        lbl_chk = ttk.Label(c, text="Paso 1 · Verificación del stream", font=bold)
        lbl_chk.pack(anchor="w", fill=tk.X)
        f_chk = ttk.Frame(c)
        f_chk.pack(fill=tk.X, pady=2)
        self.name_var, self.sid_var, self.chk_s_var = tk.StringVar(value="AURA"), tk.StringVar(value="AuraLSL-"), tk.StringVar(value="120")
        for i, (lbl, var, w) in enumerate([("Stream", self.name_var, 6), ("Prefijo source_id", self.sid_var, 8),
                                           ("Duración (s)", self.chk_s_var, 4)]):
            f_chk.columnconfigure(2 * i, weight=0)
            f_chk.columnconfigure(2 * i + 1, weight=1)
            ttk.Label(f_chk, text=lbl).grid(row=0, column=2 * i, padx=(0 if i == 0 else 6, 2), sticky="w")
            ttk.Entry(f_chk, textvariable=var, width=w).grid(row=0, column=2 * i + 1, sticky="ew")
        f_chk_btns = ttk.Frame(c)
        f_chk_btns.pack(fill=tk.X, pady=2)
        self.btn_check = ttk.Button(f_chk_btns, text="Iniciar verificación", command=self.start_check)
        self.btn_check.pack(side=tk.LEFT)
        self.btn_ok = ttk.Button(f_chk_btns, text="Verificación OK · continuar", command=self.check_ok, state=tk.DISABLED)
        self.btn_ok.pack(side=tk.LEFT, padx=6)
        self.btn_abort_chk = ttk.Button(f_chk_btns, text="Abortar", command=self.abort_all, state=tk.DISABLED)
        self.btn_abort_chk.pack(side=tk.LEFT)
        self.check_lbl = ttk.Label(c, text="Sin verificar")
        self.check_lbl.pack(anchor="w", fill=tk.X)

        ttk.Separator(c).pack(fill=tk.X, pady=8)
        lbl_ses = ttk.Label(c, text="Paso 2 · Sesión", font=bold)
        lbl_ses.pack(anchor="w", fill=tk.X)
        f_ses = ttk.Frame(c)
        f_ses.pack(fill=tk.X, pady=2)
        self.iaf_var, self.dur_var, self.per_var = tk.StringVar(value="10"), tk.StringVar(value="1260"), tk.StringVar(value="420")
        for i, (lbl, var) in enumerate([("IAF (Hz)", self.iaf_var), ("Duración (s)", self.dur_var),
                                        ("Umbral parpadeo cada (s)", self.per_var)]):
            f_ses.columnconfigure(2 * i, weight=0)
            f_ses.columnconfigure(2 * i + 1, weight=1)
            ttk.Label(f_ses, text=lbl).grid(row=0, column=2 * i, padx=(0 if i == 0 else 6, 2), sticky="w")
            ttk.Entry(f_ses, textvariable=var, width=4).grid(row=0, column=2 * i + 1, sticky="ew")
        lbl_plan = ttk.Label(c, text="Bloques: pares <segundos> bloque:<nombre>")
        lbl_plan.pack(anchor="w", fill=tk.X)
        self.plan_var = tk.StringVar(value="0 bloque:reposo 420 bloque:scroll 840 bloque:reposo")
        ttk.Entry(c, textvariable=self.plan_var).pack(fill=tk.X, anchor="w", pady=(2, 4))
        f_ses_btns = ttk.Frame(c)
        f_ses_btns.pack(fill=tk.X, pady=4)
        self.btn_start = ttk.Button(f_ses_btns, text="Iniciar sesión", command=self.start_session, state=tk.DISABLED)
        self.btn_start.pack(side=tk.LEFT)
        self.btn_stop = ttk.Button(f_ses_btns, text="Detener sesión", command=self.stop_session, state=tk.DISABLED)
        self.btn_stop.pack(side=tk.LEFT, padx=6)
        self.btn_abort_ses = ttk.Button(f_ses_btns, text="Abortar", command=self.abort_all, state=tk.DISABLED)
        self.btn_abort_ses.pack(side=tk.LEFT)
        self.btn_rep = ttk.Button(f_ses_btns, text="Abrir reporte", command=self.open_report, state=tk.DISABLED)
        self.btn_rep.pack(side=tk.LEFT, padx=6)

        ttk.Separator(c).pack(fill=tk.X, pady=8)
        self.clock = ttk.Label(c, text="0:00 / 0:00", font=("Arial", 22, "bold"))
        self.clock.pack(anchor="w", fill=tk.X)
        self.block_lbl = ttk.Label(c, text="Bloque: —", font=bold)
        self.block_lbl.pack(anchor="w", fill=tk.X)
        self.next_lbl = tk.Label(c, text="Siguiente: —", font=("Arial", 11), anchor="w", justify=tk.LEFT)
        self.next_lbl.pack(anchor="w", fill=tk.X, pady=(2, 8))
        self.next_fg = self.next_lbl.cget("fg")
        self.status = {k: ttk.Label(c, text=f"{k}: —") for k in
                       ("Calidad", "Calibración", "Ventanas válidas", "Ruido", "Parpadeos", "Umbral parpadeo",
                        "Intervención", "Registro")}
        for lbl in self.status.values():
            lbl.pack(anchor="w", fill=tk.X)

        self._last_c_w = None

        def on_resize(event):
            if event.width == self._last_c_w:
                return
            self._last_c_w = event.width
            w = max(100, event.width - 24)
            self.next_lbl.config(wraplength=w)
            self.check_lbl.config(wraplength=w)
            self.block_lbl.config(wraplength=w)
            lbl_chk.config(wraplength=w)
            lbl_ses.config(wraplength=w)
            lbl_plan.config(wraplength=w)
            for lbl in self.status.values():
                lbl.config(wraplength=w)

            # Marcador de tiempo responsivo (escalado y wraplength)
            clock_font_size = max(15, min(24, int(w / 18)))
            self.clock.config(font=("Arial", clock_font_size, "bold"), wraplength=w)

        c.bind("<Configure>", on_resize)

    def _build_log(self):
        log_frame = ttk.Frame(self.paned, padding=(0, 8, 8, 8))
        self.paned.add(log_frame, weight=1)
        self.log = scrolledtext.ScrolledText(log_frame, font=("Consolas", 9), wrap=tk.NONE)
        self.log.pack(fill=tk.BOTH, expand=True)
        self.log.tag_config("err", foreground="#A32D2D")
        self.log.tag_config("ok", foreground="#0F6E56")
        self.log.tag_config("warn", foreground="#B5590B")  # AVISO RUIDO del pipeline

    def set_status(self, k, txt, color=None):
        self.status[k].config(text=f"{k}: {txt}", foreground=color or "")

    # ---------- procesos ----------
    def launch(self, tag, args):
        p = subprocess.Popen([PY, "-u", *args], cwd=HERE, env=ENV, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             text=True, encoding="utf-8", errors="replace",
                             creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0))
        threading.Thread(target=self._read, args=(tag, p), daemon=True).start()
        self.procs[tag] = p
        return p

    def _read(self, tag, p):
        for line in p.stdout:
            self.q.put((tag, ANSI.sub("", line.rstrip())))
        p.wait()
        self.q.put((tag, None))  # fin del proceso

    def poll(self):
        try:
            while True:
                tag, line = self.q.get_nowait()
                if line is None:
                    self.on_exit(tag)
                else:
                    self.on_line(tag, line)
        except queue.Empty:
            pass
        self.tick()
        self.root.after(100, self.poll)

    def on_line(self, tag, line):
        bad = any(k in line for k in ("FALLA", "SESIÓN DETENIDA", "Traceback", "Error", "abortada"))
        warn = "AVISO RUIDO" in line
        self.log.insert(tk.END, f"[{tag}] {line}\n", "err" if bad else "warn" if warn else ("ok" if "PASA" in line else ""))
        self.log.see(tk.END)
        if tag != "pipeline":
            return
        if line.startswith("Pipeline") and self.t_start is None:
            self.t_start = time.monotonic()  # el bucle arranca aquí; behavior_markers cuenta desde esta conexión
        elif line.startswith("Registro:"):
            self.run_dir = line.split(":", 1)[1].strip()
            self.set_status("Registro", os.path.basename(self.run_dir))
        elif line.startswith("Chequeo de calidad"):
            self.set_status("Calidad", line.split(":", 1)[1].strip(), "#A32D2D" if "malos ['Fp1'" in line else None)
        elif "CALIBRACIÓN CONGELADA" in line:
            self.frozen = True
            self.set_status("Calibración", line.strip().replace("CALIBRACIÓN CONGELADA", "congelada"), "#0F6E56")
        elif "SESIÓN DETENIDA" in line:
            self.set_status("Calibración", line.strip(), "#A32D2D")
        elif "NIVEL" in line and ">>>" in line:
            self.set_status("Intervención", line.split(">>>", 1)[1].strip())
        if m := re.search(r"válidas\(últ\. 10\)=(\d+%)", line):
            self.set_status("Ventanas válidas", m.group(1) + " de las últimas 10")
            self.set_status("Ruido", "sin aviso")  # el pipeline imprime AVISO RUIDO justo después, si lo hay
        if warn:
            # Canales con ≥ 50 % de segmentos de 2 s > 150 µV (umbral de rechazo); "invalida" = sin segmento limpio.
            # Rojo si alguno invalida ventanas por sí solo; naranja si solo está ruidoso. Revisar gel/contacto de esos.
            chs = line.split(":", 1)[1].strip()
            self.set_status("Ruido", chs + " → revisar contacto", "#A32D2D" if "invalida" in chs else "#B5590B")
        if m := re.search(r"parpadeos=(\S+)/min", line):
            self.set_status("Parpadeos", f"{m.group(1)}/min (en vivo, provisional)")
        elif line.strip().startswith("PARPADEOS"):  # cierre de período: línea propia, la tasa en vivo no la tapa
            self.set_status("Umbral parpadeo", line.strip()[10:] + " (definitivo)")
        elif "[" in line and "calibrando" in line:
            self.set_status("Calibración", "calibrando… quieto, frente y mandíbula relajadas")

    def on_exit(self, tag):
        code = self.procs.pop(tag).returncode
        self.log.insert(tk.END, f"[{tag}] terminó (código {code})\n", "ok" if code == 0 else "err")
        self.log.see(tk.END)
        if tag == "check":
            self.btn_check.config(state=tk.NORMAL)
            self.btn_abort_chk.config(state=tk.DISABLED)
            if self._aborted:
                self.check_lbl.config(text="Verificación abortada manualmente", foreground="#A32D2D")
                self.btn_ok.config(state=tk.DISABLED)
            else:
                self.check_lbl.config(text=f"Terminó (código {code}): revisa el registro y decide")
                self.btn_ok.config(state=tk.NORMAL)
        elif tag == "pipeline":
            self.stop_proc("conducta")
            self.t_start = None
            self.btn_stop.config(state=tk.DISABLED)
            self.btn_abort_ses.config(state=tk.DISABLED)
            self.btn_start.config(state=tk.NORMAL)
            if self.run_dir and os.path.exists(os.path.join(self.run_dir, "reporte.md")):
                self.btn_rep.config(state=tk.NORMAL)
            self.root.bell()

    def stop_proc(self, tag):
        p = self.procs.get(tag)
        if p and p.poll() is None:
            try:
                p.kill()
            except Exception:
                pass

    def abort_all(self):
        if self._launch_timer:
            self.root.after_cancel(self._launch_timer)
            self._launch_timer = None
        running = [tag for tag, p in self.procs.items() if p.poll() is None]
        if not running:
            messagebox.showinfo("Abortar", "No hay ningún proceso en ejecución.")
            return
        if not messagebox.askyesno("Abortar", f"¿Forzar el cierre de los procesos en ejecución ({', '.join(running)})?"):
            return
        self._aborted = True
        for tag in list(self.procs):
            self.stop_proc(tag)
        self.t_start = None
        self.log.insert(tk.END, f"[sistema] Procesos abortados manualmente: {', '.join(running)}\n", "err")
        self.log.see(tk.END)
        self.btn_check.config(state=tk.NORMAL)
        self.btn_abort_chk.config(state=tk.DISABLED)
        self.btn_abort_ses.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.DISABLED)
        self.btn_start.config(state=tk.NORMAL if self.btn_ok.instate(["!disabled"]) else tk.DISABLED)
        if "pipeline" in running or "conducta" in running:
            self.block_lbl.config(text="Bloque: — (abortado)")
            self.next_lbl.config(text="Siguiente: —", fg=self.next_fg)

    # ---------- pasos ----------
    def start_check(self):
        self._aborted = False
        self.btn_check.config(state=tk.DISABLED)
        self.btn_ok.config(state=tk.DISABLED)
        self.btn_start.config(state=tk.DISABLED)
        self.btn_abort_chk.config(state=tk.NORMAL)
        self.check_lbl.config(text=f"Verificando ({self.chk_s_var.get()} s)…", foreground="")
        self.log.delete("1.0", tk.END)
        self.launch("check", ["check_lsl_stream.py", "--name", self.name_var.get(), "--source-id", self.sid_var.get(),
                              "--seconds", self.chk_s_var.get()])

    def check_ok(self):
        self.check_lbl.config(text="Verificación dada por buena", foreground="#0F6E56")
        self.btn_start.config(state=tk.NORMAL)

    def start_session(self):
        tok = self.plan_var.get().split()
        try:
            if len(tok) % 2:
                raise ValueError
            self.plan = sorted((float(t), m.split(":", 1)[1]) for t, m in zip(tok[::2], tok[1::2]))
            float(self.iaf_var.get()), float(self.per_var.get())
            dur = float(self.dur_var.get())
        except (ValueError, IndexError):
            return messagebox.showerror("Sesión", "Revisa IAF, duración, período y bloques (<segundos> bloque:<nombre>).")
        if not messagebox.askyesno("Sesión", "¿Aura ya está grabando (botón rojo)?"):
            return
        self._aborted = False
        self.dur, self.done, self.frozen = dur, set(), False
        self.run_dir = None
        self.btn_start.config(state=tk.DISABLED)
        self.btn_rep.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        self.btn_abort_ses.config(state=tk.NORMAL)
        for k in self.status:
            self.set_status(k, "—")
        self.launch("conducta", ["behavior_markers.py", *tok])
        # El pipeline busca MIRAI_Behavior 2 s al arrancar: el stream de conducta tiene que existir antes.
        self._launch_timer = self.root.after(1500, lambda: self.launch("pipeline", [
            "realtime_pipeline.py", "--name", self.name_var.get(), "--source-id", self.sid_var.get(),
            "--seconds", self.dur_var.get(), "--iaf", self.iaf_var.get(), "--parpadeo-periodo", self.per_var.get()]))

    def stop_session(self):
        p = self.procs.get("pipeline")
        if p and p.poll() is None and messagebox.askyesno("Detener", "¿Detener la sesión? El pipeline escribirá su reporte."):
            p.send_signal(signal.CTRL_BREAK_EVENT if os.name == "nt" else signal.SIGINT)

    def open_report(self):
        os.startfile(os.path.join(self.run_dir, "reporte.md"))

    def tick(self):
        """Cronómetro de la sesión: bloque actual y próxima acción manual (con aviso sonoro al cambiar)."""
        if self.t_start is None:
            return
        el = time.monotonic() - self.t_start
        self.clock.config(text=f"{fmt(el)} / {fmt(self.dur)}")
        cur = [n for t, n in self.plan if t <= el]
        self.block_lbl.config(text=f"Bloque: {cur[-1] if cur else '—'}"
                              + ("  ·  calibración: quieto, frente y mandíbula relajadas" if el < 160 and not self.frozen else ""))
        steps = [(t, f"{n}: pulsa la barra espaciadora en Aura y {ACTION.get(n, 'cambia de bloque')}")
                 for t, n in self.plan if t > 0] + [(self.dur, "fin: barra espaciadora y detén la grabación en Aura")]
        nxt = [(t, a) for t, a in steps if t > el]
        for t, a in steps:  # aviso en el momento del cambio
            if t <= el and t not in self.done:
                self.done.add(t)
                self.root.bell()
        if nxt:
            t, a = nxt[0]
            soon = t - el < 15
            self.next_lbl.config(text=f"Siguiente en {fmt(t - el)} ({fmt(t)}): {a}",
                                 fg="#A32D2D" if soon else self.next_fg, font=("Arial", 11, "bold" if soon else "normal"))

    def on_close(self):
        if any(p.poll() is None for p in self.procs.values()) and not messagebox.askyesno(
                "Salir", "Hay procesos corriendo. ¿Cerrarlos y salir? (sin reporte)"):
            return
        for tag in list(self.procs):
            self.stop_proc(tag)
        self.root.destroy()


def main():
    root = tk.Tk()
    SessionApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
