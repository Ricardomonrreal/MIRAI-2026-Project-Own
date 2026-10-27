# MIRAI 2026 · Plan para la presentación de avances (v2 · 22 oct 2026)

Documento de contexto: estado del proyecto, narrativa de la presentación, plan ante resultados negativos y pasos para terminar las diapositivas.
Antecedentes: [Revision_Literatura_Hipotesis.md](Revision_Literatura_Hipotesis.md) (hipótesis vigentes, §6) · [Resumen_Sesion_21_10.md](Resumen_Sesion_21_10.md) · [Analisis_Scope_v2.md](Analisis_Scope_v2.md) · [Reporte H1 ds007537](datasets%20workflow/ds007537/Reporte_H1_ds007537.md) · [Reporte H1 SVRec](datasets%20workflow/EEG-SVRec/Reporte_H1_SVRec.md) · [Reporte Cao](datasets%20workflow/Cao2019/results/cao_reporte.txt)

> **Historial:** la versión anterior proponía una reformulación v3 ("fatiga como estado, no como tiempo"). Quedó descartada tras la revisión de literatura por ser una sobrecorrección. Las hipótesis vigentes son las originales, con los ajustes de `Revision_Literatura_Hipotesis.md` §6.

---

## 1. Estado actual

| Bloque | Resultado | Lectura |
|---|---|---|
| **Literatura** | Theta y alfa tónicos ↑ con el tiempo en tarea (Tran 2020: g = 1.03 / 0.85). Theta ligado a la tarea ↓ mientras el tónico ↑ (**Arnau 2021**, Yu 2022) | **Hipótesis H1–H3 con validación teórica** |
| **ds007537** (n = 27, 10 min de smartphone) | Video corto: alfa periódica ↑ +0.43 dB (10/12, p = 0.04, frágil). Theta sin cambio | Firma de desenganche/fatiga pasiva. Theta nulo esperado por la corta duración |
| **EEG-SVRec** (n = 25, sesiones ≤ 15–30 min) | Tendencias temporales frágiles. Alfa_per ↓ con mayor inmersión por video (20/25) | Alfa como marcador de (des)enganche |
| **Cao 2019, tónico** (n = 27, 62 sesiones, 60–90 min) | Theta total ~ log TR **ρ = +0.50 (25/27)**, ~ lapsos +0.46 (23/27). Alfa_per ~ TR +0.32 (24/27). Theta_per: pendiente +0.007 dB/min (Holm p = 0.034), pero el TR no tiene tendencia lineal | El theta tónico **acompaña al desempeño**. El pipeline lo detecta |
| **Cao 2019, fásico** (26 142 ensayos; revisado el 22 oct) | Hay respuesta theta al desvío: **+0.83 dB, 24/27, p < 0.0001**. El theta tónico pre-ensayo predice un TR más lento: **ρ = +0.30, 27/27**. Ensayos lentos vs. rápidos: **base +1.16 dB (25/27)**, post absoluto +0.93 dB (20/27), ERSP relativo **−0.22 dB, n.s. (p = 0.09)**. Con TR ≥ 0.7 s (sin respuesta motora en la ventana): igual, ERSP −0.18, p = 0.16 | **El estado de fatiga es theta tónico elevado (robusto). La respuesta fásica se conserva**: parte de más arriba y llega más alto. **H3 (fásico ↓) no se confirma en Cao** (compatible con la compensación de Wascher 2014), pero la tarea no es NoGo |
| **Hardware** | AURA transmite por LSL (`AURA_Power` en `AURA/AURA_Software/VRehab.py`, que ya trae calibración con `StandardScaler` + `LogisticRegression`) | Base para el lazo en tiempo real |

**Revisión del fásico de Cao (22 oct):**
- **Figura corregida** (`cao_fasico_curso.png`, dos paneles). El −0.85 dB de la línea base venía de promediar dB de potencia instantánea contra la media lineal de la base (desigualdad de Jensen), no de un error en los datos. El panel relativo ahora está re-centrado en 0.
- **La lectura anterior era incorrecta:** "misma línea base" era un efecto de normalizar cada ensayo a su propia base. En dB absolutos, **los ensayos lentos tienen ~1.1 dB más theta antes del desvío** y su pico también es más alto. El incremento fásico es apenas menor y no es significativo.
- **Control de latencia:** solo el 1.9 % de los ensayos tiene TR < 0.5 s (mediana 0.97 s). Con TR ≥ 0.7 s el resultado no cambia, así que la respuesta motora no explica nada.
- **Lectura para la presentación:** en una tarea de 60–90 min, la fatiga aparece como **theta tónico elevado que predice peor desempeño (27/27)**, mientras la señal fásica de control se mantiene (compensación). La caída fásica de H2/H3 queda **sin probar**, porque Cao no tiene una sonda inhibitoria (NoGo). Esto refuerza la necesidad del experimento propio.

---

## 2. Narrativa de la presentación

**Hilo:** teoría → validación literaria → prueba en datasets → por qué no alcanzó → brecha → mi estudio → sistema AR robusto.

1. **Las hipótesis tienen validación literaria.** Tónico ↑ con el tiempo (Tran 2020, Wascher 2014, Benwell 2019). Disociación tónico ↑ / fásico ↓ (Arnau 2021, Yu 2022).
2. **En los datasets no tuvieron apoyo completo** por estas limitantes:

| Limitante | ds007537 | EEG-SVRec | Cao 2019 |
|---|---|---|---|
| **Duración insuficiente** (la literatura pide ≥ 30–60 min) | 10 min | ≤ 15–30 min por sesión | ✅ 60–90 min |
| **Sin tarea que exija control ni sonda inhibitoria** (sin NoGo no se puede medir el fásico) | Uso libre del teléfono | Visualización pasiva | Desvío de carril, no NoGo |
| **Sin condición control contrabalanceada** | El video siempre va después del teléfono | Modos en orden fijo | Sin control |
| **Sin medida conductual o subjetiva de fatiga** (TR, KSS) para anclar el EEG | ❌ | Solo ratings de inmersión | ✅ TR y lapsos |
| **Paradigma distinto al scrolling** | ✅ smartphone real | ✅ video corto | ❌ conducción |
| **Calidad de la señal** | 3 sujetos ruidosos | Prefiltrado, meseta EMG 15–48 Hz, 3 archivos corruptos | Sin POz |
| **Muestra por condición** | n = 12 en video corto | n = 25 | n = 27 |

   **Frase:** *"Ningún dataset público combina scrolling de video corto, duración suficiente, una sonda inhibitoria y una condición control."*
3. **Lo que sí mostraron:** la firma de alfa/desenganche en video corto. El acople theta tónico–desempeño en el control positivo (27/27). La respuesta fásica theta existe y se conserva bajo fatiga en conducción, así que la caída fásica requiere una sonda inhibitoria que ningún dataset tiene.
4. **La brecha:** no existen estudios ni datasets que prueben la disociación tónico/fásico durante el scrolling de video corto. Lo más cercano es correlacional y de rasgo (Nguyen 2025; Yan 2024). → **Estudio único.**
5. **Mi estudio:** scrolling vs. documental (control estándar no fatigante, Marcora 2009), 45–60 min, Go/NoGo antes y después, NoGo dentro del feed, KSS/NASA-TLX, montaje AURA.
6. **El sistema AR no depende de que todo salga positivo** (§3).

---

## 3. ¿Qué pasa si los resultados son negativos?

### 3.1 Separar las dos contribuciones
El proyecto tiene **dos aportes independientes**, y cada uno se evalúa con sus propios criterios:

| Aporte | Pregunta | Criterio de éxito | ¿Depende de H1–H3? |
|---|---|---|---|
| **Científico** | ¿El scrolling produce la disociación tónico ↑ / fásico ↓? | Pruebas prerregistradas de H1–H3 | — |
| **Ingenieril (AR en lazo cerrado)** | ¿El sistema detecta el estado de cada usuario y responde a tiempo? | Latencia < 2 s, precisión individual (AUC) contra etiquetas conductuales, usabilidad (SUS), intrusividad percibida | **No** |

Un resultado nulo en H1–H3 **no invalida el prototipo**: cambia qué señal lo dispara, no si funciona.

### 3.2 Escenarios y qué hacer en cada uno

| Escenario | Interpretación | Qué dispara la AR |
|---|---|---|
| **H1 ✅ H2 ✅ (H3 ✅)** | Modelo completo | Theta tónico ↑ + caída de la respuesta NoGo dentro del feed → escalera completa (cue → fricción → pausa) |
| **H1 ✅ H2 ❌** | Hay fatiga, pero el control inhibitorio se mantiene (compensación, como en Wascher 2014) | Solo marcadores tónicos → **pausa restaurativa** (contra la fatiga), sin fricción |
| **H1 ❌ H2 ✅** | Se pierde el control sin fatiga tónica | Desempeño en el NoGo dentro del feed (errores, TR) → **fricción** |
| **H1 ❌ H2 ❌** | 45–60 min de scrolling no producen fatiga medible. **Es un hallazgo publicable** que contradice la narrativa de "brain rot" | Alfa_per (desenganche, que ya tiene apoyo en 3 datasets) + conducta (velocidad de swipe, tiempo de sesión) → **cue de conciencia** |

### 3.3 Recomendaciones para blindar el proyecto
1. **Prerregistrar en OSF** las hipótesis, las medidas y el análisis. Así un nulo es un resultado informativo y no un fracaso.
2. **Poder estimar la ausencia de efecto:** además de p < 0.05, usar **pruebas de equivalencia (TOST) o factores de Bayes**. Permiten afirmar "no hay efecto mayor que X" en vez de "no se encontró".
3. **Disparador personalizado y no poblacional:** la AR usa un **modelo individual** calibrado al inicio de cada sesión. Las etiquetas salen del desempeño en el Go/NoGo o en el NoGo del feed, y las features EEG van normalizadas por usuario (el mismo patrón de `VRehab.py`). Funciona aunque el efecto promedio del grupo sea pequeño. Se apoya en el acople dentro del sujeto, que ya es robusto: en Cao, tónico ~ TR 27/27 y alfa_per ~ TR 24/27.
4. **Disparador híbrido como respaldo:** EEG + conducta (swipes, tiempo en video, errores NoGo). Si el EEG solo no basta, H4 se convierte en "híbrido vs. temporizador" y sigue siendo una JITAI.
5. **Validar el lazo con una señal garantizada:** ojos cerrados → alfa ↑ (efecto Berger). Demuestra latencia y funcionamiento del sistema sin depender de la fatiga, y sirve como **demo segura** en la presentación.
6. **Construir la AR en paralelo con el experimento**, no después. Simulador LSL con datos grabados → AURA en vivo → AR.

**Frase para la diapositiva:**
> *"Whatever the outcome of H1–H3, the closed-loop AR system is validated on its own engineering criteria and uses individually calibrated triggers; the hypotheses decide **which** signal drives the intervention, not **whether** the system works."*

---

## 4. Pasos a seguir

### Fase 1 · Cerrar la validación ✅ casi completa
1. ~~Pasada fásica de Cao~~ ✅ (22 oct).
2. ~~Revisar `cao_fasico_curso.png` y el control de latencia~~ ✅ (22 oct; ver §1).
3. **Figura resumen de los 3 datasets** (tabla de §2.2 + resultados de §1).

### Fase 2 · Diapositivas (orden definitivo, texto en inglés)
| # | Diapositiva | Contenido | Fuente |
|---|---|---|---|
| 1 | Portada | Título con AR | `Analisis_Scope_v2.md` §3 |
| 2 | **Objectives** | Objetivo general + específicos (científico e ingenieril, §3.1). Motivación: Nguyen 2025 (r = −.41 en control inhibitorio) | `Analisis_Scope_v2.md`, Revisión §4 |
| 3 | Scope y marco | Tónico (fatiga) vs. fásico (inhibición); no se mide dopamina | `Analisis_Scope_v2.md` slide 3 |
| 4 | Hypotheses H1–H4 | Versión vigente | Revisión §6 |
| 5 | **Theoretical validation** | Tabla de la literatura: Tran, Wascher, Benwell, Arnau, Yu, Kato | Revisión §1–2 |
| 6 | **Practical validation** | 3 datasets: qué se probó y el resultado. Control positivo Cao 2019: panel absoluto de `cao_fasico_curso.png` + acople tónico ~ TR (27/27). Mensaje: el tónico marca la fatiga y el fásico se compensa → hace falta una sonda NoGo | §1 |
| 7 | **Why they could not confirm it** | Tabla de limitantes | §2.2 |
| 8 | **The gap → unique study** | No existe un estudio de la disociación durante scrolling | §2.4 |
| 9 | Experimental plan | Protocolo de 45–60 min, medidas, modelo mixto, prerregistro. **Simulación:** simulador LSL con datos grabados (ds007537 / Cao) para probar el lazo antes del experimento | §4 Fase 3, Fase 4 paso 8 |
| 10 | System pipeline + AR | Lazo LSL → features → modelo individual → AR | `Analisis_Scope_v2.md` slide 7 y §5.7 |
| 11 | **Robust to negative results** | Tabla de escenarios §3.2 + frase | §3 |
| 12 | Gantt | Actualizado | `Analisis_Scope_v2.md` slide 12 |
| 13 | Next steps | Fases 3–4 pendientes | §4 |
| 14 | References | APA | Revisión §7 |

### Fase 3 · Experimento propio
4. **Prerregistro (OSF):** H1–H3, medidas principales (theta frontal en bandas ajustadas a la IAF con el exponente 1/f como covariable, alfa_per, ERSP theta NoGo absoluto **y** relativo, errores de comisión), modelos mixtos, Holm, TOST y exclusiones.
5. **Protocolo:** **45–60 min** de scrolling vs. documental, contrabalanceado, en días distintos. Go/NoGo antes y después + NoGo dentro del feed. KSS / VAS / NASA-TLX. Montaje AURA `Fz, FCz, F3, F4, Pz, O1, O2, Fp1`. Piloto n ≈ 10–15 + análisis de poder.
6. **Ética:** consentimiento y comité de Ucaribe (iniciar ya).
7. **Autoprueba** con AURA: Scroll-NoGo, calidad de electrodos y alineación de marcadores LSL.

### Fase 4 · Prototipo AR con retroalimentación EEG
8. **Simulador LSL** con datos grabados (ds007537 / Cao).
9. **Features en tiempo real** (ventanas de 2–4 s): theta frontal (banda ajustada a la IAF), alfa_per, exponente 1/f, parpadeo en Fp1.
10. **Calibración individual:** línea base + modelo personal (patrón de `VRehab.py`) con etiquetas conductuales; veto por parpadeo.
11. **Prueba de lazo con alfa de ojos cerrados** (demo segura).
12. **Puente a la AR** (UDP/WebSocket → estado → escalera de intervención). **Decisión pendiente:** dispositivo y motor (Unity + AR Foundation, Quest en passthrough o WebXR).
13. **Condiciones de H4** en el mismo código: EEG, temporizador e híbrido.

**Prioridad para la presentación:** 3 → diapositivas 5–8 y 11 (el núcleo nuevo) → resto de diapositivas → paso 11 de la Fase 4 (demo) si da tiempo. Las fases 3–4 restantes se presentan como plan.
