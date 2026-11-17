"""Chequeo de la Fase 1 del Go/NoGo (Tests/Plan_App_GoNoGo.md): base de datos + rutas del servidor, con un teléfono
simulado y una base temporal (no toca data/mirai.db ni lanza procesos).   Uso: python test_gonogo.py"""
import json
import os
import queue
import sqlite3
import statistics
import tempfile

import gonogo_db as gdb

gdb.DB = os.path.join(tempfile.mkdtemp(), "test.db")
gdb.init()

import sesion_aura_web as web  # noqa: E402  (después de apuntar la base al archivo temporal)

c = web.app.test_client()
N = gdb.PASADAS["pre"] * 9

# 1. Secuencia: 144 ensayos en 3 min, cada dígito 16 veces, nunca dos NoGo seguidos, reproducible por semilla.
assert N == 144 and gdb.PREP_MS + N * gdb.SOA_MS <= gdb.BLOQUE_S * 1000
for seed in range(300):
    s = gdb.secuencia(seed, 16)
    assert len(s) == N and all(s.count(d) == 16 for d in "123456789") and "33" not in s
assert gdb.secuencia(7, 16) == gdb.secuencia(7, 16) != gdb.secuencia(8, 16)

# 2. Orden de inicio: el dashboard abre el bloque y el teléfono (cola SSE) la recibe.
tel = queue.Queue()
web.S.gng_subs.append(tel)
orden = c.post("/api/gng/bloque/iniciar", json={"codigo": "t01", "tipo": "pre"}).get_json()
B, seq = orden["bloque"], orden["secuencia"]
assert len(seq) == N and orden["soa_ms"] == 1150 and orden["stim_ms"] == 250 and orden["nogo"] == 3
assert orden["codigo"] == "T01" and c.get("/gng").status_code == 200  # la app del teléfono se sirve en /gng
msg = tel.get_nowait()
assert "event: inicio" in msg and f'"bloque": {B}' in msg and seq in msg and web.S.gng["codigo"] == "T01"

# 3. Reloj: /api/gng/sync devuelve el reloj LSL y avanza.
t1, t2 = (c.post("/api/gng/sync").get_json()["t"] for _ in range(2))
assert isinstance(t1, float) and t2 >= t1

# 4. Teléfono simulado: desfase inicial, 144 ensayos en lotes con errores conocidos, todo reenviado, desfase final.
D0, D1, T0 = 1000.0, 1000.010, 5000.0  # el reloj del teléfono deriva 10 ms durante el bloque
c.post("/api/gng/bloque/sync", json={"bloque": B, "fase": "inicio", "desfase": D0, "tel": T0, "ida_vuelta_ms": 8,
                                     "cuadro_ms": 16.7})
go = [n for n in range(N) if seq[n] != "3"]
nogo = [n for n in range(N) if seq[n] == "3"]
comis, omis, antic = set(nogo[:5]), set(go[:4]), {go[10]}


def rt(n):
    if n in comis:
        return 250.0
    if n in antic:
        return 50.0
    if n in omis or seq[n] == "3":
        return None
    return 300.0 + n % 7 * 10


filas = [{"n": n, "t_on": 15000.0 + n * 1150, "rt": rt(n)} for n in range(N)]
for vuelta in range(2):  # la segunda vuelta es el reenvío completo: no debe duplicar ni cambiar nada
    for i in range(0, N, 10):
        r = c.post("/api/gng/ensayos", json={"bloque": B, "ensayos": filas[i:i + 10]})
        assert r.status_code == 200 and r.get_json()["ok"] == list(range(i, min(i + 10, N)))
c.post("/api/gng/ensayos", json={"bloque": B, "ensayos": [{"n": 0, "t_on": 1.0, "rt": 999.0}]})  # reenvío distinto: se ignora
T1 = filas[-1]["t_on"] + 1150
c.post("/api/gng/bloque/sync", json={"bloque": B, "fase": "fin", "desfase": D1, "tel": T1, "ida_vuelta_ms": 12})

# 5. Resumen = lo que se mandó.
(res,) = c.get("/api/gng/resumen?codigo=T01").get_json()
aciertos = [rt(n) for n in go if n not in omis and n not in antic]
assert res["codigo"] == "T01" and res["tipo"] == "pre" and res["ensayos"] == N and res["nogo"] == 16, res
assert (res["comisiones"], res["omisiones"], res["anticipaciones"], res["completo"]) == (5, 4, 1, 1), res
assert abs(res["tr_medio_ms"] - sum(aciertos) / len(aciertos)) < 1e-9, res
assert c.get("/api/gng/resumen").get_json() == [res] and c.get("/api/gng/resumen?codigo=NADIE").get_json() == []

# 6. Tiempos en el reloj LSL: desfase interpolado entre las dos sincronizaciones (deriva corregida).
db = sqlite3.connect(gdb.DB)
for n, t_tel, t_lsl in db.execute("SELECT n, inicio_tel, inicio_lsl FROM ensayos WHERE bloque_id = ? AND n IN (0, 71, 143)", (B,)):
    assert abs(t_lsl - (t_tel / 1000 + D0 + (D1 - D0) * (t_tel - T0) / (T1 - T0))) < 1e-9, (n, t_lsl)
assert db.execute("SELECT tr_ms FROM ensayos WHERE bloque_id = ? AND n = 0", (B,)).fetchone()[0] == rt(0)
assert db.execute("SELECT ida_vuelta_ms, telefono != '' FROM bloques JOIN sesiones s ON s.id = sesion_id").fetchone() == (12, 1)

# 7. Misma sesión para el mismo código; bloque incompleto mientras falten ensayos; entradas malas → 400.
B2 = c.post("/api/gng/bloque/iniciar", json={"codigo": "T01", "tipo": "post"}).get_json()["bloque"]
c.post("/api/gng/ensayos", json={"bloque": B2, "ensayos": filas[:3]})
r2 = c.get("/api/gng/resumen?codigo=T01").get_json()
assert len(r2) == 2 and r2[0]["sesion_id"] == r2[1]["sesion_id"] and (r2[1]["ensayos"], r2[1]["completo"]) == (3, 0)
FIN = {"fase": "fin", "desfase": D1, "tel": T1, "ida_vuelta_ms": 9}
assert c.post("/api/gng/bloque/iniciar", json={"codigo": "T01", "tipo": "practica"}).status_code == 400  # hay un bloque corriendo
c.post("/api/gng/bloque/sync", json={"bloque": B2, **FIN})  # el teléfono lo cierra (incompleto): ya se puede abrir otro
BP = c.post("/api/gng/bloque/iniciar", json={"codigo": "T01", "tipo": "practica"}).get_json()
assert len(BP["secuencia"]) == 18
c.post("/api/gng/bloque/sync", json={"bloque": BP["bloque"], **FIN})
for url, body in (("/api/gng/bloque/iniciar", {"codigo": "", "tipo": "pre"}),
                  ("/api/gng/bloque/iniciar", {"codigo": "T01", "tipo": "otro"}),
                  ("/api/gng/ensayos", {"bloque": 9999, "ensayos": filas[:1]}),
                  ("/api/gng/ensayos", {"bloque": B, "ensayos": [{"n": N, "t_on": 0, "rt": None}]}),
                  ("/api/gng/ensayos", {"bloque": B, "ensayos": [{"n": 1, "t_on": 0, "rt": -5}]}),
                  ("/api/gng/ensayos", {"bloque": B, "ensayos": "x"}),
                  ("/api/gng/bloque/sync", {"bloque": B, "fase": "medio", "desfase": 0, "tel": 0, "ida_vuelta_ms": 0}),
                  ("/api/gng/bloque/sync", {"bloque": B})):
    assert c.post(url, json=body).status_code == 400, (url, body)
assert db.execute("SELECT COUNT(*) FROM ensayos WHERE bloque_id = ?", (B,)).fetchone()[0] == N
db.close()
print(f"PASA · Fase 1 Go/NoGo: {N} ensayos, reenvío sin duplicados, resumen y tiempos LSL correctos")

# ---------- Fase 3: integración con el dashboard ----------
# 8. Resultados: mediana y desviación del TR, ensayos de un bloque, exportación CSV y la ruta /resultados.
assert abs(res["tr_medio_ms"] - statistics.mean(aciertos)) < 1e-9 and res["total"] == N and res["ida_vuelta_ms"] == 12
res = c.get("/api/gng/resumen?codigo=T01").get_json()[0]
assert abs(res["tr_mediana_ms"] - statistics.median(aciertos)) < 1e-9 and abs(res["tr_de_ms"] - statistics.stdev(aciertos)) < 1e-9
reg = c.get(f"/api/gng/ensayos?bloque={B}").get_json()
assert len(reg) == N and reg[0]["codigo"] == "T01" and [r["n"] for r in reg] == list(range(N))
csv_r = c.get("/api/gng/exportar?que=resumen&codigo=T01")
csv_e = c.get("/api/gng/exportar?que=ensayos&codigo=T01").get_data(as_text=True).strip().split("\n")
assert csv_r.mimetype == "text/csv" and "attachment" in csv_r.headers["Content-Disposition"]
assert len(csv_r.get_data(as_text=True).strip().split("\n")) == 1 + 3 and len(csv_e) == 1 + N + 3 and "resultado" in csv_e[0]
assert c.get("/resultados").status_code == 200 and c.get("/api/estado").get_json()["gng"]["telefonos"] == 1

# 9. Sesión del dashboard sin procesos reales: Start session exige el código, abre la sesión en la base y la enlaza
#    con la carpeta del pipeline; los bloques gonogo_pre y gonogo_post del plan arrancan solos y el teléfono los completa.
while not tel.empty():
    tel.get_nowait()
web.S.launch = lambda tag, args: None  # ni behavior_markers ni el pipeline: sus líneas se simulan abajo
PLAN = {"plan": "0 bloque:baseline 0.3 bloque:gonogo_pre 0.9 bloque:scroll 1.2 bloque:gonogo_post", "dur": "2"}
assert c.post("/api/sesion/iniciar", json=PLAN).get_json()["error"]  # sin código no arranca
assert c.post("/api/sesion/iniciar", json={**PLAN, "codigo": "s01"}).get_json()["error"] is None
assert c.post("/api/gng/bloque/iniciar", json={"codigo": "T01", "tipo": "practica"}).status_code == 400  # sesión de otro en vivo
with web.S.lock:
    web.S.on_line("pipeline", "Registro: C:/runs/sintetica")
    web.S.on_line("pipeline", "Pipeline en vivo")  # aquí arranca el reloj de la sesión y se programan los bloques
for tipo in ("pre", "post"):
    o = json.loads(tel.get(timeout=3).split("data: ", 1)[1])
    assert (o["tipo"], o["codigo"], len(o["secuencia"])) == (tipo, "S01", N), o
    c.post("/api/gng/bloque/sync", json={"bloque": o["bloque"], "fase": "inicio", "desfase": D0, "tel": T0, "ida_vuelta_ms": 7})
    assert len(c.post("/api/gng/ensayos", json={"bloque": o["bloque"], "ensayos": filas}).get_json()["ok"]) == N
    c.post("/api/gng/bloque/sync", json={"bloque": o["bloque"], **FIN})
s = c.get("/api/gng/resumen?codigo=S01").get_json()
assert [(r["tipo"], r["completo"], r["run_dir"]) for r in s] == [("pre", 1, "C:/runs/sintetica"), ("post", 1, "C:/runs/sintetica")], s
assert s[0]["sesion_id"] == s[1]["sesion_id"] != r2[0]["sesion_id"]
est = c.get("/api/estado").get_json()
assert est["gng"]["bloque"]["tipo"] == "post" and est["params"]["codigo"] == "S01"
assert sum("[gonogo]" in t and "finished" in t for t, _ in est["log"]) == 2
with web.S.lock:
    web.S.t_start = None
    web.S.btn.update(start=True)
print("PASA · Fase 3 Go/NoGo: sesión con código, bloques pre y post automáticos, completos y enlazados a su run_dir")

# 10. Modo red: el enlace corto del teléfono (<IP>:<puerto>/<clave>) abre la tarea Go/NoGo y nada más.
web.TOKEN, web.TEL = "token-largo", "abc234"
red = {"REMOTE_ADDR": "192.168.0.50"}  # otro equipo de la red (esta PC entra sin clave)
t = web.app.test_client()
assert t.get("/gng", environ_base=red).status_code == 403 and t.get("/abc235", environ_base=red).status_code == 403
r = t.get("/abc234?demo=practica", environ_base=red)
assert r.status_code == 302 and r.headers["Location"] == "/gng?demo=practica" and "tel=abc234" in r.headers["Set-Cookie"]
assert t.get("/gng", environ_base=red).status_code == 200 and t.post("/api/gng/sync", environ_base=red).status_code == 200
for metodo, url in (("get", "/"), ("get", "/api/estado"), ("get", "/api/eventos"), ("post", "/api/sesion/iniciar"),
                    ("post", "/api/abortar"), ("post", "/api/semaforo/iniciar")):  # el teléfono no entra al tablero
    assert getattr(t, metodo)(url, environ_base=red).status_code == 403, url
assert web.app.test_client().get("/api/estado?token=token-largo", environ_base=red).status_code == 200  # el token sí
assert c.get("/abc234").status_code == 302 and c.get("/api/estado").status_code == 200  # desde esta PC, todo igual
web.TOKEN = web.TEL = None
print("PASA · enlace corto del teléfono: abre la tarea, no el tablero")
