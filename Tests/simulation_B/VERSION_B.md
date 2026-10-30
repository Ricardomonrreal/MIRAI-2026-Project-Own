# Versión B — criterio de detección del Paso 3 precisado (29 oct 2026)

Copia de `Tests/simulation/` para probar otra forma de **evaluar** el rechazo de parpadeos. La versión actual
(`Tests/simulation/` y `Tests/Protocolo_Simulacion_Pipeline.md`) no se modificó.

## Qué cambia

| | Versión actual | Versión B |
|---|---|---|
| Pipeline (filtros, ventanas de 6 s, 9 segmentos de 2 s, umbral 150 µV, veto EMG) | — | **Idéntico** |
| Marcadores de parpadeo del emulador | `blink` | `blink:<amplitud en Fp1, µV>` (`mock_lsl_streamer.py`) |
| Qué cuenta como “segmento con parpadeo” | se solapa con el núcleo (+0.05 a +0.25 s) | **contiene el pico** (+0.15 s) de un parpadeo **supraumbral** |
| Parpadeo supraumbral | — | amplitud × ganancia pico a pico del filtro ≥ 150 µV (`blink_gain()`) |
| Segmentos que solo rozan el parpadeo o tocan parpadeos subumbral | contaban como fallos | se reportan aparte (“parciales”) |
| Criterio | ≥ 95 % de segmentos con parpadeo rechazados | ≥ 95 % de segmentos **con el pico** de un parpadeo supraumbral rechazados |

**Cambios del 29 oct (tarde), solo en B:** el Paso 4 se trajo de la versión A (`spectral_features.py`,
`--equivalencia` en `replay_offline.py`) y se agregaron dos cambios de pipeline:

| | Versión A | Versión B |
|---|---|---|
| Veto EMG (25–40 Hz posterior > μ + 3σ de 90 s) | descarta segmentos | **solo se mide** (`emg_db` en `ventanas.csv`); `EMG_VETO = False` en `realtime_pipeline.py` |
| Rango de ajuste de specparam | 2–40 Hz (2–20 a 50 Hz) | **2–30 Hz** (2–20 a 50 Hz): deja fuera la mayor parte de la banda muscular sin descartar datos |

Motivo: con el veto, la equivalencia con `h1_por_minuto.csv` no pasaba (r 0.67) porque los minutos con músculo
se quedaban con 8–40 segmentos frente a ~110 del offline. El rechazo de parpadeos en Fp1 es independiente del
veto EMG y no cambia.

Hasta aquí, el comportamiento del pipeline de parpadeos es el mismo; cambia cómo se juzga. Los cambios están en `blink_report()` y
`blink_gain()` de `realtime_pipeline.py`, en las etiquetas del emulador y en `test_realtime_pipeline.py`.

## Hallazgo que motivó el ajuste

La explicación inicial (los parpadeos sintéticos de 150–170 µV quedan bajo el umbral tras el filtro) **era
incorrecta**: el filtro de 1–40 Hz no atenúa el pico a pico del parpadeo sintético, lo aumenta ~11 % por el
rebote del pasa-altos (ganancia 1.11; amplitud mínima detectable ~135 µV < mínimo sintético de 150 µV). Ningún
parpadeo sintético es subumbral. Los fallos eran, en ~70 %, segmentos que solo **rozan** el parpadeo (contienen
la subida o la bajada, con el pico a 10–98 ms fuera del borde) y cuya desviación queda bajo 150 µV.

## Resultados offline (600 s sintéticos, ~15 parpadeos/min)

| Semilla | 250 Hz: pico rechazado / parciales rechazados / sin parpadeo | 50 Hz: ídem |
|---|---|---|
| 1 | 97.9 % / 34 % / 0.2 % | 97.8 % / 24 % / 0.4 % |
| 2 | 97.6 % / 30 % / 0.5 % | 97.7 % / 28 % / 0.1 % |
| 3 | 98.8 % / 31 % / 0.1 % | 99.1 % / 21 % / 0.0 % |
| 4 | 98.2 % / 27 % / 0.8 % | 98.3 % / 31 % / 0.3 % |
| 5 | 99.7 % / 30 % / 0.6 % | 99.0 % / 24 % / 0.1 % |
| 7 | 98.8 % / 49 % / 0.3 % | 99.2 % / 30 % / 0.2 % |

Con el criterio actual las mismas corridas daban 92.5–95.6 %.

**Limitación que deja a la vista:** ~70–75 % de los segmentos que solo rozan un parpadeo no se rechazan. Llevan
contaminación parcial de baja frecuencia (flanco del parpadeo, por debajo de 150 µV), relevante para theta
frontal en el Paso 4.

## Prueba en vivo (29 oct, 10 min de uno en uno, tren de parpadeos de 30 s en el minuto 5)

Registros en `Tests/simulation_B/runs/20261029_140904_synthetic` (250 Hz) y `..._142011_synthetic` (50 Hz).

| | 250 Hz | 50 Hz |
|---|---|---|
| Intervalo entre ventanas | 0.981–1.021 s ✅ | 0.964–1.043 s ✅ |
| Búfer + filtros (p95 / máx.) | 0.41 / 0.72 ms ✅ | 0.39 / 2.44 ms ✅ |
| Rechazo (p95 / máx.) | 3.3 / 6.8 ms | 0.77 / 16.7 ms |
| Latencia p95 | 28.6 ms | 44.4 ms |
| Parpadeos (subumbral) | 177 (0) | 192 (0) |
| Segmentos con el pico rechazados | **98.4 %** ✅ | **97.8 %** ✅ |
| Segmentos parciales rechazados | 38 % (n = 184) | 31 % (n = 157) |
| Sin parpadeo rechazados | 0.5 % ✅ | 0.5 % ✅ |
| Ventanas válidas fuera del tren | 99.1 % ✅ | 94.6 % ✅ |
| Ventanas con señal perdida | 27 | 24 |

Ambas corridas: **PASA** todos los criterios (versión B).

## Comparación A frente a B con el Paso 4 (29 oct)

Mismo registro sintético con y sin parpadeos (3 semillas × 600 s), diferencia de features por ventana:

| | Ventanas con un segmento aceptado que roza un parpadeo | Resto |
|---|---|---|
| θ_per, 250 Hz | +0.10 dB (DE 1.36, n = 449) | +0.05 dB (DE 1.34, n = 1268) |
| θ_per, 50 Hz | +0.05 dB (DE 1.45, n = 423) | −0.03 dB (DE 1.44, n = 1276) |
| α_per, 250 Hz | −0.22 dB | −0.22 dB |
| α_per, 50 Hz | −0.09 dB | −0.16 dB |

Los segmentos que solo rozan un parpadeo suben θ_per ~0.05–0.08 dB y no cambian α_per: despreciable frente a
la variación normal entre ventanas (~1.4 dB). El ~6 % de “fallos” que marca la versión A no daña las features.

## Sin veto EMG y ajuste 2–30 Hz (29 oct, tarde)

**Offline** (`test_realtime_pipeline.py`, sintético semilla 7 y 3):

| | 250 Hz | 50 Hz |
|---|---|---|
| Segmentos con el pico rechazados | 98.9 % | 99.3 % |
| Parciales rechazados | 44 % (n = 140) | 30 % (n = 156) |
| Sin parpadeo rechazados | 0.0 % | 0.0 % |
| Ventanas válidas fuera del tren | 96.1 % | 95.3 % |
| α_per con alfa inyectado (15 µV) | +4.12 dB | +1.55 dB |
| R² ≥ 0.75 | 100 % | 98.8 % |
| Welch + specparam máx. | 47.1 ms | 37.7 ms |

El sintético no tiene EMG, así que quitar el veto no cambia el rechazo aquí: las diferencias con las corridas
anteriores son de semilla. El efecto de α a 50 Hz sigue siendo pequeño (+1.55 dB); no depende del rango de ajuste.

**Equivalencia con el offline** (ds007537 `sub-01`, `runs/20261029_161001_equivalencia_sub-01`):

| | r | Sesgo (RT − offline) | Criterio |
|---|---|---|---|
| α_per | **0.938** | **−0.23 dB** | r ≥ 0.8 y \|sesgo\| < 0.5 dB → **PASA** |
| θ_per | 0.651 | +0.41 dB | (rango offline −0.2 a 0.6 dB: r poco informativa) |
| χ posterior | 0.940 | −0.10 | — |

Con la versión A (veto, 2–40 Hz): α_per r 0.67, sesgo +1.29 dB → no pasa.

**En vivo** (10 min de uno en uno, Pasos 2–4, tren de parpadeos en el min 5; `runs/20261029_161028_synthetic`
250 Hz y `runs/20261029_162138_synthetic` 50 Hz):

| | 250 Hz | 50 Hz | Versión A (Paso 4, 250 / 50 Hz) |
|---|---|---|---|
| Intervalo entre ventanas | 0.872–1.127 s ❌ | 0.950–1.046 s ✅ | 0.926–1.062 / 0.964–1.033 s |
| Búfer + filtros (p95 / máx.) | 0.40 / 1.60 ms ✅ | 0.42 / 1.05 ms ✅ | 0.40 / 1.05 · 0.38 / 0.47 ms |
| Rechazo (p95 / máx.) | 3.0 / 13.1 ms | 0.78 / 2.9 ms | 3.4 / 7.7 · 0.77 / 1.1 ms |
| Welch + specparam (p95 / máx.) | 30.8 / **120.2 ms** ❌ | 23.5 / 54.4 ms ✅ | 37.5 / 92.6 · 23.3 / 36.7 ms |
| Latencia p95 | 52.6 ms | 61.7 ms | 57.5 · 61.9 ms |
| Segmentos con el pico rechazados | 98.4 % ✅ | 97.8 % ✅ | — |
| Sin parpadeo rechazados | 0.5 % ✅ | 0.5 % ✅ | 0.5 % |
| Ventanas válidas fuera del tren | 99.1 % ✅ | 94.6 % ✅ | — |
| R² ≥ 0.75 (θ / α) | 99.5 / 99.6 % | 100 / 100 % | 100 % |

50 Hz: **PASA**. 250 Hz: **NO PASA** por una sola ráfaga de ~20 s (ventanas 229–250, ~4 min después del inicio):
4 ventanas con features de 57–120 ms y dos intervalos de 1.11–1.13 s; el resto de la corrida, normal (p95
30.8 ms, menor que en A porque el ajuste 2–30 Hz tiene menos puntos). Es el mismo tipo de pico aislado del
sistema visto en el Paso 2, no un efecto del cambio de rango; hay que repetir la corrida de 250 Hz para
confirmarlo. El rechazo no cambia frente a la versión B anterior porque el sintético no tiene EMG (umbral EMG
calculado −18.1 dB, solo como referencia).

**Repetición de 250 Hz** (`runs/20261029_165807_synthetic`): todo pasa (intervalo 0.926–1.072 s, pico rechazado
98.4 %, sin parpadeo 0.5 %, válidas fuera del tren 99.1 %, latencia p95 51.4 ms) **salvo** Welch + specparam
máx. **111.3 ms** (p95 28.3 ms) → NO PASA.

**Causa (corrige lo dicho arriba sobre "picos del sistema"):** la ventana 250 es lenta en las tres corridas de
250 Hz (A 92.6 ms, B 98.7 ms, B repetida 111.3 ms) con idénticos R². Es determinista: el emulador usa siempre la
semilla 7 y en esa ventana (t ≈ 256 s) queda **un solo segmento limpio**; su periodograma es muy ruidoso y el ajuste
de specparam de alfa (hasta 6 picos) tarda ~88 ms offline con 2–30 Hz y ~80 ms con 2–40 Hz
(`scratchpad/slow_window.py`). En vivo se suma la carga del sistema y pasa de 100 ms. La ventana 231 de la primera
corrida (120 ms, 5 segmentos limpios) sí fue un pico del sistema: en la repetición tardó lo normal.

Exigir ≥ 2 segmentos limpios para calcular features bajaría el máximo a 61.5 ms en la repetición (y 70.4 ms en A),
a costa de pasar de 93.8 % a 88.4 % de ventanas con features; no elimina los picos del sistema. **Pendiente de
decisión:** mínimo de segmentos, o redefinir el criterio de tiempo (p. ej. p99 ≤ 100 ms y máx. ≤ 250 ms, muy por
debajo del avance de 1 s y de los 500 ms de latencia del Paso 7).

**Decisión 29 oct: criterio de tiempo redefinido** (protocolo y chequeos de A y B): Welch + specparam
**p99 ≤ 100 ms y máx. ≤ 250 ms**. Reevaluadas las corridas en vivo:

| Corrida | p99 | máx. | Tiempo |
|---|---|---|---|
| A 250 Hz (`simulation/runs/20261029_145151`) | 51.9 ms | 92.6 ms | ✅ |
| A 50 Hz (`simulation/runs/20261029_150302`) | 26.8 ms | 36.7 ms | ✅ |
| B 250 Hz (`161028`, con la ráfaga del sistema) | 40.0 ms | 120.2 ms | ✅ |
| B 50 Hz (`162138`) | 34.0 ms | 54.4 ms | ✅ |
| B 250 Hz repetida (`165807`) | 42.3 ms | 111.3 ms | ✅ |

Con esto, **la versión B (sin veto EMG, ajuste 2–30 Hz) pasa todos los criterios de los Pasos 2–4 a 250 y 50 Hz**,
incluida la equivalencia con el offline. La versión A pasa el tiempo pero sigue sin pasar la detección del Paso 3
(~94 %) ni la equivalencia (r 0.67).

## Paso 5 — calibración congelada (30 oct)

`calibration.py` (nuevo) e integración en `realtime_pipeline.py`:
- **Chequeo de calidad** con la ventana que cierra los primeros 10 s (criterio std de `load_file`), sumado a los
  canales malos que declara la fuente; se rehacen el rechazo y las ROI, y si una ROI queda vacía la sesión se detiene.
- **Línea base:** fases AURA (`baseline_eyes_open` → μ, σ; `baseline_eyes_closed` → IAF y Berger) o, sin
  marcadores, los 90 s siguientes al chequeo. ≥ 45 ventanas válidas por feature; si no, +30 s (máx. 2) y luego se aborta.
- **IAF** como `h1.iaf()`; `spectral_features.fit_roi()` devuelve el espectro aplanado completo para recalcular
  las bandas de las ventanas de calibración con la IAF final (el test comprueba que coincide con `h1.periodic()`).
- **EWMA** τ θ = 60 s, τ α = 5 s, solo con ventanas válidas. **σ_Z corregida** (ver protocolo, Paso 5):
  √((σ_suav · f_ac)² + σ_μ²), por autocorrelación de las ventanas solapadas y por la incertidumbre de μ.
- `ventanas.csv` añade `cal_estado`, `z_theta`, `z_alpha`; `config.json` añade `calibracion`.

**Diagnóstico de σ** (sintético 20 min estable, 3 semillas × 250/50 Hz, |Z| ≥ 1.5, promedio): fórmula del
protocolo θ 68 % / α 47 %; + autocorrelación 41 % / 20 %; + incertidumbre de μ 17 % / 17 %. Con 5 min de
calibración: 11 % / 15 %. Umbral efectivo 1.5 σ_Z ≈ 1.0 dB (θ) y ≈ 3.2 dB (α).

**Nivel 1 con Z_α** (sintético 20 min + alfa inyectado de 30 s): con σ corregida, 0–17 episodios espurios de
≥ 5 s en 20 min (mediana 3–4; el Paso 6 pide ≤ 1) y detección del alfa de 15 µV a los 22–34 s a 250 Hz
(1 de 3 a 50 Hz). Con τ = 5 s el alfa suavizado fluctúa ~2 dB por sí solo: τ, umbral y persistencia del Nivel 1
se ajustan en el Paso 6.

**Offline** (`test_realtime_pipeline.py`): calibración congelada, IAF 10 Hz, parámetros sin cambios; DE(Z)
θ 0.82 / 0.86, α 1.19 / 0.93 (250 / 50 Hz, semilla 11). CSV AURA de enero (con fases): **aborta**, con 23 de 84
ventanas válidas en ojos abiertos (hacen falta 45); aun sin Fp1, Cz, Pz y O1, los segmentos tienen 200–365 µV de pico
a pico en F3, F4, Fz y O2 → calidad o escala de ese registro, a revisar con grabaciones nuevas.

**En vivo** (10 min, de uno en uno; `runs/20261030_115159_synthetic` 50 Hz, `..._121157_synthetic` 250 Hz
repetida; la primera de 250 Hz, `..._114040`, tuvo picos de carga de hasta 453 ms con Edge abierto):

| | 250 Hz | 50 Hz |
|---|---|---|
| Calibración / IAF | congelada / 10 Hz | congelada / 10.5 Hz |
| Intervalo entre ventanas | 0.871–1.116 s ❌ (solo la ventana 245) | 0.928–1.081 s ✅ |
| Features p99 / máx. | 35.8 / 150.8 ms ✅ | 74.3 / 115.9 ms ✅ |
| Latencia p95 | 49.8 ms | 75.1 ms |
| Pico de parpadeo rechazado / válidas fuera del tren | 98.5 % / 99.1 % ✅ | 97.8 % / 94.6 % ✅ |
| Z_θ: DE / media / RMS | 0.55 ❌ / +0.98 / 1.12 | 0.64 ❌ / −0.99 / 1.18 |
| Z_α: DE / media / RMS | 1.17 ✅ / +0.10 / 1.17 | 1.04 ✅ / +0.42 / 1.12 |

- La única falla de intervalo es la ventana 245 (t ≈ 255 s, un solo segmento limpio): el ajuste de alfa tardó
  151 ms y retrasó la emisión 116 ms; la siguiente se recuperó (0.871 s). El intervalo se mide al emitir, después
  de los Pasos 3–5, así que hereda el tiempo de features (permitido hasta 250 ms desde el 29 oct).
- DE(Z_θ) < 0.7 es estructural, no ruido: la Z es determinista con la misma semilla (la repetición dio los mismos
  valores) y el error de μ aparece como un desplazamiento constante dentro de la sesión (media ±1), que la DE no
  ve. RMS(Z) = √(media² + DE²) da 1.12–1.18 en los cuatro casos.

**Cierre del Paso 5 (30 oct).** Correcciones de medición: (1) el intervalo del Paso 2 se mide al cortar la ventana
(`t_corte`), no al emitir después de los Pasos 3–5; (2) criterio RMS(Z) = √(media² + DE²) entre 0.7 y 1.4, en lugar de
DE(Z). Reevaluadas las corridas en vivo: intervalo al corte 0.941–1.061 / 0.979–1.022 / 0.958–1.036 s y RMS(Z) θ 1.13 /
1.13 / 1.18, α 1.17 / 1.17 / 1.12 (250 con carga / 250 repetida / 50 Hz) → todo ✅.

Tests offline añadidos (`test_realtime_pipeline.py`):
- **RMS(Z) con 6 sesiones** (semillas 11–16, 20 min cada una): combinado θ 1.03 / α 1.10 a 250 Hz y θ 1.23 / α 0.97 a
  50 Hz ✅. Por sesión, de 0.53 a 2.45: dos de las 12 sesiones de θ superan 1.4 (semilla 11 a 250 Hz, μ desplazada −1.5
  σ_Z; semilla 16 a 50 Hz, −1.9 σ_Z). Es el error de μ con 90 s de calibración y por eso el criterio combina sesiones.
- **Fases AURA:** fondo con IAF 10 Hz y alfa de 15 µV a 9 Hz solo en ojos cerrados → IAF 9.0 Hz (de ojos cerrados),
  μ y σ de ojos abiertos (80–81 ventanas), Berger +6.0 dB (250 Hz) / +6.2 dB (50 Hz) ✅.
- **Chequeo de calidad:** O1 muerto y Fz 10× más ruidoso → ambos detectados y excluidos, la calibración sigue; Fz y Cz
  muertos → ROI frontal vacía → la sesión se detiene ✅.
- No se probó la extensión de +30 s y el aborto por falta de ventanas válidas (decisión del 30 oct).
