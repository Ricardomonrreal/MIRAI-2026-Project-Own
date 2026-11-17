"""
gonogo_db.py — base de datos de la tarea Go/NoGo (MIRAI 2026) · Fase 1 de Tests/Plan_App_GoNoGo.md

Un archivo SQLite (data/mirai.db, fuera de git) con participantes, sesiones, bloques y ensayos, y la vista
resumen_bloque (comisiones, omisiones y TR medio por bloque: la tabla de la diapositiva 9). Sin datos personales:
solo el código del participante. No importa pylsl ni Flask: el servidor (sesion_aura_web.py) le pasa los tiempos LSL.

Tarea (Plan §3): SART de Perzl et al. (2024). Dígitos 1–9, 250 ms cada uno, 1150 ms entre inicios, NoGo = 3
(1 de cada 9). La secuencia son pasadas barajadas de 1–9 (número exacto de NoGo, nunca dos 3 seguidos). El servidor
decide el resultado de cada ensayo con la secuencia que él generó: el teléfono solo manda si hubo toque y cuándo.

Tiempos: el teléfono manda sus marcas (ms de performance.now) y el desfase con el reloj LSL medido al inicio y al
final del bloque; inicio_lsl se guarda con el desfase inicial y, al llegar el final, se recalcula interpolando entre
los dos (deriva del reloj del teléfono). inicio_tel y los dos desfases se conservan: todo es recalculable.

Chequeo: python test_gonogo.py
"""
import json
import os
import random
import sqlite3
import statistics
from contextlib import contextmanager

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "data", "mirai.db")  # test_gonogo.py lo cambia por un archivo temporal

NOGO, STIM_MS, SOA_MS, PREP_MS, ANTICIP_MS = 3, 250, 1150, 10_000, 100
BLOQUE_S = 180  # duración de los bloques gonogo_* en el plan del dashboard
# Pasadas completas de 9 dígitos que caben en el bloque menos la preparación: 16 → 144 ensayos (165.6 s).
PASADAS = {"practica": 2, "pre": 0, "post": 0}
PASADAS["pre"] = PASADAS["post"] = (BLOQUE_S * 1000 - PREP_MS) // SOA_MS // 9

SCHEMA = f"""
CREATE TABLE IF NOT EXISTS participantes (
    id INTEGER PRIMARY KEY, codigo TEXT UNIQUE NOT NULL, creado TEXT DEFAULT (datetime('now', 'localtime')));
CREATE TABLE IF NOT EXISTS sesiones (
    id INTEGER PRIMARY KEY, participante_id INTEGER NOT NULL REFERENCES participantes(id),
    inicio TEXT DEFAULT (datetime('now', 'localtime')), run_dir TEXT, telefono TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS bloques (
    id INTEGER PRIMARY KEY, sesion_id INTEGER NOT NULL REFERENCES sesiones(id), tipo TEXT NOT NULL,
    semilla INTEGER NOT NULL, secuencia TEXT NOT NULL, parametros TEXT NOT NULL, inicio_lsl REAL, fin_lsl REAL,
    desfase_inicio REAL, tel_sync_inicio REAL, desfase_fin REAL, tel_sync_fin REAL, ida_vuelta_ms REAL,
    cuadro_ms REAL);
CREATE TABLE IF NOT EXISTS ensayos (
    bloque_id INTEGER NOT NULL REFERENCES bloques(id), n INTEGER NOT NULL, estimulo INTEGER NOT NULL,
    inicio_tel REAL NOT NULL, inicio_lsl REAL, respondio INTEGER NOT NULL, tr_ms REAL, resultado TEXT NOT NULL,
    recibido_lsl REAL, PRIMARY KEY (bloque_id, n));
DROP VIEW IF EXISTS resumen_bloque;  -- una vista no guarda datos: se recrea en cada arranque para tenerla al día
CREATE VIEW resumen_bloque AS
SELECT p.codigo, s.id AS sesion_id, s.inicio AS sesion_inicio, s.run_dir, b.id AS bloque_id, b.tipo,
       LENGTH(b.secuencia) AS total, b.ida_vuelta_ms,
       COUNT(e.n) AS ensayos, COALESCE(SUM(e.estimulo = {NOGO}), 0) AS nogo,
       COALESCE(SUM(e.resultado = 'comision'), 0) AS comisiones,
       COALESCE(SUM(e.resultado = 'omision'), 0) AS omisiones,
       COALESCE(SUM(e.resultado = 'anticipacion'), 0) AS anticipaciones,
       AVG(CASE WHEN e.resultado = 'acierto' THEN e.tr_ms END) AS tr_medio_ms,
       (COUNT(e.n) = LENGTH(b.secuencia) AND b.desfase_fin IS NOT NULL) AS completo
FROM bloques b JOIN sesiones s ON s.id = b.sesion_id JOIN participantes p ON p.id = s.participante_id
LEFT JOIN ensayos e ON e.bloque_id = b.id GROUP BY b.id;
"""


@contextmanager
def conn():
    """Una conexión por operación (el servidor Flask atiende en varios hilos); confirma al salir sin error."""
    c = sqlite3.connect(DB, timeout=5)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    try:
        yield c
        c.commit()
    finally:
        c.close()


def init():
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    with conn() as c:
        c.execute("PRAGMA journal_mode = WAL")  # lecturas del dashboard sin bloquear las escrituras del teléfono
        c.executescript(SCHEMA)


def secuencia(semilla, pasadas):
    """Dígitos del bloque: `pasadas` permutaciones de 1–9 seguidas, sin dos NoGo consecutivos entre pasadas."""
    rng, out = random.Random(semilla), []
    for _ in range(pasadas):
        p = list(range(1, 10))
        rng.shuffle(p)
        while out and out[-1] == NOGO == p[0]:
            rng.shuffle(p)
        out += p
    return "".join(map(str, out))


def sesion(codigo):
    """Crea el participante si no existe y abre una sesión nueva; devuelve su id."""
    with conn() as c:
        c.execute("INSERT OR IGNORE INTO participantes(codigo) VALUES (?)", (codigo,))
        pid = c.execute("SELECT id FROM participantes WHERE codigo = ?", (codigo,)).fetchone()[0]
        return c.execute("INSERT INTO sesiones(participante_id) VALUES (?)", (pid,)).lastrowid


def run_dir(sesion_id, ruta):
    with conn() as c:
        c.execute("UPDATE sesiones SET run_dir = ? WHERE id = ?", (ruta, sesion_id))


def bloque(sesion_id, tipo, t_lsl, semilla=None):
    """Abre un bloque (practica / pre / post) y devuelve la orden de inicio que se manda al teléfono."""
    semilla = random.SystemRandom().randrange(2 ** 31) if semilla is None else semilla
    par = {"nogo": NOGO, "stim_ms": STIM_MS, "soa_ms": SOA_MS, "prep_ms": PREP_MS, "anticip_ms": ANTICIP_MS}
    seq = secuencia(semilla, PASADAS[tipo])
    with conn() as c:
        bid = c.execute("INSERT INTO bloques(sesion_id, tipo, semilla, secuencia, parametros, inicio_lsl) "
                        "VALUES (?, ?, ?, ?, ?, ?)", (sesion_id, tipo, semilla, seq, json.dumps(par), t_lsl)).lastrowid
    return {"bloque": bid, "tipo": tipo, "secuencia": seq, **par}


def sync(bloque_id, fase, desfase, tel, ida_vuelta_ms, t_lsl, cuadro_ms=None, telefono=""):
    """Sincronización de relojes que mide el teléfono: desfase (s) = reloj LSL − reloj del teléfono, tomado en la
    marca `tel` (ms del teléfono). fase 'inicio' antes del primer ensayo; 'fin' cierra el bloque y recalcula
    inicio_lsl de sus ensayos interpolando el desfase entre las dos medidas."""
    if fase not in ("inicio", "fin"):
        raise ValueError(f"fase desconocida: {fase!r}")
    with conn() as c:
        b = c.execute("SELECT desfase_inicio, tel_sync_inicio FROM bloques WHERE id = ?", (bloque_id,)).fetchone()
        if b is None:
            raise KeyError(f"bloque {bloque_id} no existe")
        if fase == "inicio":
            c.execute("UPDATE bloques SET desfase_inicio = ?, tel_sync_inicio = ?, ida_vuelta_ms = ?, cuadro_ms = ? "
                      "WHERE id = ?", (desfase, tel, ida_vuelta_ms, cuadro_ms, bloque_id))
            c.execute("UPDATE sesiones SET telefono = ? WHERE telefono = '' AND id = "
                      "(SELECT sesion_id FROM bloques WHERE id = ?)", (telefono, bloque_id))
            return
        c.execute("UPDATE bloques SET desfase_fin = ?, tel_sync_fin = ?, fin_lsl = ?, "
                  "ida_vuelta_ms = MAX(COALESCE(ida_vuelta_ms, 0), ?) WHERE id = ?",
                  (desfase, tel, t_lsl, ida_vuelta_ms, bloque_id))
        d0, t0 = b["desfase_inicio"], b["tel_sync_inicio"]
        if d0 is not None and tel > t0:
            c.execute("UPDATE ensayos SET inicio_lsl = inicio_tel / 1000.0 + ? + ? * (inicio_tel - ?) / ? "
                      "WHERE bloque_id = ?", (d0, desfase - d0, t0, tel - t0, bloque_id))


def ensayos(bloque_id, filas, t_lsl):
    """Guarda ensayos [{n, t_on (ms del teléfono), rt (ms o None)}]. Reenviar un ensayo ya guardado no lo cambia.
    Devuelve los n recibidos, para que el teléfono los saque de su cola."""
    with conn() as c:
        b = c.execute("SELECT secuencia, desfase_inicio FROM bloques WHERE id = ?", (bloque_id,)).fetchone()
        if b is None:
            raise KeyError(f"bloque {bloque_id} no existe")
        seq, d0, ok = b["secuencia"], b["desfase_inicio"], []
        for f in filas:
            n, t_on, rt = int(f["n"]), float(f["t_on"]), f.get("rt")
            rt = None if rt is None else float(rt)
            if not 0 <= n < len(seq) or (rt is not None and not 0 <= rt <= 2 * SOA_MS):
                raise ValueError(f"ensayo fuera de rango: n={n}, rt={rt}")
            d = int(seq[n])
            res = (("rechazo" if rt is None else "comision") if d == NOGO else
                   "omision" if rt is None else "anticipacion" if rt < ANTICIP_MS else "acierto")
            c.execute("INSERT OR IGNORE INTO ensayos VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                      (bloque_id, n, d, t_on, None if d0 is None else t_on / 1000 + d0, rt is not None, rt, res, t_lsl))
            ok.append(n)
    return ok


def _filtro(codigo, bloque_id):
    if bloque_id is not None:
        return " WHERE bloque_id = ?", (bloque_id,)
    return (" WHERE codigo = ?", (codigo,)) if codigo else ("", ())


def resumen(codigo=None, bloque_id=None):
    """Filas de resumen_bloque (todas, las de un participante o la de un bloque), en orden de creación, más la
    mediana y la desviación estándar del TR de los aciertos (SQLite no las trae)."""
    w, arg = _filtro(codigo, bloque_id)
    with conn() as c:
        filas = [dict(r) for r in c.execute("SELECT * FROM resumen_bloque" + w + " ORDER BY bloque_id", arg)]
        for f in filas:
            tr = [r[0] for r in c.execute("SELECT tr_ms FROM ensayos WHERE bloque_id = ? AND resultado = 'acierto'",
                                          (f["bloque_id"],))]
            f["tr_mediana_ms"] = statistics.median(tr) if tr else None
            f["tr_de_ms"] = statistics.stdev(tr) if len(tr) > 1 else None
    return filas


def registros(codigo=None, bloque_id=None):
    """Ensayos uno por uno (todos, los de un participante o los de un bloque) con su participante, sesión y bloque."""
    w, arg = _filtro(codigo, bloque_id)
    with conn() as c:
        return [dict(r) for r in c.execute(
            "SELECT p.codigo, s.id AS sesion_id, b.id AS bloque_id, b.tipo, e.n, e.estimulo, e.resultado, e.tr_ms, "
            "e.inicio_tel, e.inicio_lsl, e.recibido_lsl FROM ensayos e JOIN bloques b ON b.id = e.bloque_id "
            "JOIN sesiones s ON s.id = b.sesion_id JOIN participantes p ON p.id = s.participante_id"
            + w + " ORDER BY bloque_id, e.n", arg)]
