# MIRAI 2026 · Análisis de la semana, tamaño de muestra y uso de regresión (9 nov 2026)

Contexto: hipótesis vigentes en [Revision_Literatura_Hipotesis.md](Revision_Literatura_Hipotesis.md) §6 y plan en
[Plan_Avances.md](Plan_Avances.md). H4 queda fuera (en pausa).

---

## 1. Cambios de la semana pasada (2–8 nov)

En resumen: el pipeline pasó de simulación a datos reales de la AURA y ya cumple de sobra con el tiempo real. El mayor
riesgo para el experimento es otro: la señal real se degrada a partir de los ~25 min. Hubo 5 commits, todos en
`Tests/simulation_B` y en la documentación del protocolo.

| Fecha | Commit | Qué cambió |
|---|---|---|
| 2 nov | `1a03921` Paso 6–7 | Motor JITAI (`jitai.py`): histéresis, persistencia, prioridad 3 > 2 > 1 y Nivel 2 por conducta (`behavior_markers.py`). Lanzador `run_simulation.py` y modo replay `--offline`. Benchmark de 20 min: latencia media 35 ms, CPU 5.5 %, sin fuga de memoria ni deriva. `Diagrama_Pipeline.md`. |
| 2 nov | `714c017` | Contador de parpadeos en Fp1 con umbral que se recalcula cada 7 min. En sintético detecta el 100 %; en ds007537 da 8 → 18/min y ρ = 0.74 frente al eye-tracker. |
| 4 nov | `e3f2a0c` | Primera grabación real. En la AURA el parpadeo sale negativo, así que el pipeline invierte Fp1; con eso el contador encuentra los 13 parpadeos del tramo de prueba. |
| 5 nov | `97c8779` | `sesion_aura.py`: interfaz que encadena preparación → verificación → sesión, con cronómetro y estados. Primera sesión en vivo de 40 min. |
| 6 nov | `3c9dd4c` | Referencia promedio para la AURA real (hay ~9–12 mV de 60 Hz iguales en todos los canales). Carpeta `Tests/Recordings` y lector de `AURA_RAW`. Aviso de ruido por canal. |

**Lo que avanzó:**
- El lazo completo ya corre con la diadema.
- La calibración se congela con datos reales: 95.6 % de ventanas válidas en los primeros 90 s.
- El contador de parpadeos funciona en real: en la sesión del 5 nov, 11.8 → 17.9/min entre bloques (p = 0.014).

**Lo que sigue abierto:**
1. **Calidad de contacto en sesiones largas.** En la sesión del 5 nov las ventanas válidas pasaron de ~97 % a 0 % entre
   18:15 y 18:17, unos 25 min después de empezar (F4 ya avisaba desde 18:09). El protocolo pide 45–60 min. Sin
   resolver esto (más gel, una pausa para rehidratar los electrodos o sesiones más cortas) no hay datos para H1.
2. **60 Hz de modo común.** La referencia promedio lo compensa, pero el origen probable es la REF o la falta de bias.
   Hay que revisarlo en el hardware.
3. **Nivel 1 (alfa) del JITAI.** Da 2–11 disparos espurios por cada 20 min de sintético y tarda 12–36 s en detectar,
   cuando el objetivo es menos de 10 s. Sigue pendiente del ajuste del Paso 7.
4. **Faltan piezas para las hipótesis.** No existen todavía la tarea Scroll-NoGo (sin ella H2 y H3 no se pueden probar)
   ni la app AR. El efecto Berger tampoco se ha comprobado con una grabación buena de la AURA.
5. **n = 1.** Todo lo real viene de una o dos sesiones.

---

## 2. ¿Cuántas pruebas hacen falta?

Hay tres niveles distintos, y conviene no mezclarlos.

**a) Pruebas técnicas (antes de reclutar).** No se deciden con estadística, sino con un criterio de aceptación.
Propuesta: **3 sesiones seguidas de la duración completa (45–60 min) con ≥ 90 % de ventanas válidas en todo el
registro, y Berger ≥ 3 dB en O1/O2.** Hoy no se cumple: la sesión del 5 nov se pierde a los 25 min.

**b) Piloto (n ≈ 10–15).** Sirve para medir factibilidad, deserción, variabilidad y fiabilidad entre sesiones. **No
sirve para estimar el tamaño del efecto.** Con n = 12 y un efecto real moderado (dz = 0.4), la potencia es del 24 %:
el piloto puede dar "nulo" o un efecto inflado casi por azar.

**c) Estudio principal.** El diseño es intra-sujeto: cada persona hace scroll y documental en días distintos,
contrabalanceado. La prueba central de H1 (tiempo × condición) y la de H2 (pre/post NoGo × condición) se reducen a una
t pareada sobre la diferencia de cambios. Participantes necesarios para 80 % de potencia (t pareada, dos colas):

| Efecto (dz) | α = .05 | α = .025 (Holm, 2 pruebas) | 90 % de potencia |
|---|---|---|---|
| 0.3 (pequeño) | 90 | 109 | 119 |
| 0.4 | 52 | 62 | 68 |
| **0.5 (moderado)** | **34** | **41** | 44 |
| 0.66 (ds007537) | 21 | 25 | 27 |
| 0.8 | 15 | 18 | 19 |

**Qué efecto esperar:**
- **Tran 2020 (g ≈ 1.0)** mide el aumento con el tiempo frente a la línea base, no la diferencia entre condiciones. El
  documental también cansa: en el trabajo EEG del grupo de Jacquet el theta frontal subió en ambas condiciones. La
  interacción será bastante menor que 1.0.
- **Jacquet 2023**, errores NoGo (conducta, 40 + 40 entre grupos, F = 5.23): d ≈ 0.52. Es la mejor referencia para la
  parte conductual de H2.
- **ds007537, alfa_per:** dz ≈ 0.67, pero con n = 12 y un resultado frágil, probablemente inflado.
- **Cao 2019, fásico:** ERSP −0.22 dB, no significativo con n = 27. Para la parte EEG de H2 y H3 hay que esperar un
  efecto pequeño (dz ≤ 0.3).

**Recomendación:**
- Planear con **dz = 0.5 → 41 participantes** (Holm sobre H1 y H2 conductual), más **20–25 % de pérdidas** por calidad
  de señal y por quien no vuelve el segundo día: **~50 reclutados, ~100 sesiones**.
- El theta fásico NoGo necesitaría ~100 participantes: lo realista es declararlo **secundario** en el prerregistro.
- **Para negar una hipótesis** (TOST, equivalencia; aproximación normal):

  | Límite de equivalencia | Participantes |
  |---|---|
  | ±0.5 dz | ~35 |
  | ±0.4 dz | ~55 |

  Con menos que eso, un nulo es "inconcluso", no "negativo".
- **Correlaciones entre sujetos** (p. ej. "quien más sube en theta, más errores"): r = .3 necesita 85 participantes y
  r = .4 necesita 47. Es mejor plantearlas dentro de cada sujeto.
- **Si el n realista es 15–20**, la potencia para dz = 0.5 queda en ~55 %. En ese caso conviene un **diseño bayesiano
  secuencial**: mínimo 20 participantes; detener al llegar a BF₁₀ > 6 o < 1/6, con un máximo de ~50; y reportar
  tamaños de efecto con intervalos. Este diseño también puede dar evidencia a favor del nulo, cosa que la prueba p no
  hace.
- **Por sesión:** como regla práctica, apuntar a ≥ 30 ensayos NoGo limpios por momento (pre / post / dentro del feed).
  Con el rechazo por Fp1, eso significa presentar ~50–60.

---

## 3. ¿Conviene usar regresión para dar más fuerza a la validación?

Depende del tipo de regresión.

**Regresión inferencial (modelos mixtos): sí, y debería ser el análisis principal** (ya está en el plan de
prerregistro). Un modelo como

```
alfa_per ~ minuto × condición + exponente_1/f + parpadeos + (1 + minuto | sujeto)
```

- **usa toda la sesión**, no solo el inicio y el final;
- **tolera ventanas perdidas**, que en la AURA las habrá;
- **controla covariables:** exponente 1/f, somnolencia y EMG;
- **lo que prueba H1 es el coeficiente `minuto:condición`.**

Límites: la potencia de la interacción la sigue mandando el número de **sujetos** (más ventanas reducen el ruido dentro
de cada sesión, no la variabilidad entre personas), y nunca hay que tratar las ventanas como independientes: esa
pseudo-replicación produce falsos positivos.

**Regresión predictiva (predecir condición o desempeño, ML): no fortalece la validación ni la negación de H1–H3.**
- **No responde lo que plantean.** Las hipótesis afirman una dirección (sube o baja). Una buena precisión de predicción
  solo dice que hay información, no hacia dónde va ni por qué.
- **Puede acertar por razones equivocadas.** El scroll y el documental difieren en estímulo visual, movimiento ocular,
  parpadeo y tensión muscular. Un clasificador que separe las condiciones puede estar leyendo eso y no fatiga, y el
  alfa es justo la señal más sensible al estímulo visual.
- **Con n de 15–40 y muchas variables, sobreajusta.** La validación cruzada solo es honesta si se deja fuera al sujeto
  completo (leave-one-subject-out).
- **No puede dar evidencia de un nulo.**

**Donde sí aporta:** en la hipótesis complementaria H1-estado y en la justificación del JITAI. Por ejemplo, una
regresión logística mixta dentro de cada sujeto,

```
error_NoGo ~ theta_tónico_previo + alfa_per_previo + minuto + (1 | sujeto)
```

que pregunta si el EEG de los segundos previos predice un fallo **más allá del tiempo transcurrido** (el análogo del
ρ = +0.30, 27/27, de Cao). Para que sea defendible:
- compararla con un modelo base que use solo el tiempo y reportar la mejora;
- evaluarla dejando fuera a un sujeto cada vez, con prueba de permutación;
- prerregistrarla como secundaria.

Eso además respalda el lado de ingeniería (el AUC individual del disparador), que el plan ya separa de las hipótesis
científicas.

**En una frase:** los modelos mixtos son la forma correcta de probar H1–H3; la predicción sirve para demostrar que el
EEG tiene valor práctico para disparar la intervención, pero no para confirmar ni negar las hipótesis.
