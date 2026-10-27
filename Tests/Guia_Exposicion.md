# MIRAI 2026 · Guía de estudio para la exposición de avances (22 oct 2026)

Presentación: `Project Proposal MIRAI Ricardo_Monrreal (v4).pptx` (en Downloads). 14 diapositivas en inglés.
Fuentes de este resumen: [Plan_Avances.md](Plan_Avances.md) · [Revision_Literatura_Hipotesis.md](Revision_Literatura_Hipotesis.md) · reportes de [ds007537](datasets%20workflow/ds007537/Reporte_H1_ds007537.md), [EEG-SVRec](datasets%20workflow/EEG-SVRec/Reporte_H1_SVRec.md) y [Cao 2019](datasets%20workflow/Cao2019/results/cao_reporte.txt).

---

## 0. La idea en 30 segundos (apréndela de memoria)

> El scrolling de video corto debería producir **fatiga cognitiva**, que se ve como theta y alfa **tónicos** que suben con el tiempo. También debería producir **pérdida de control inhibitorio**, que se ve como una respuesta theta **fásica** al NoGo que baja.
> La literatura respalda las dos cosas en tareas largas.
> Probé la idea en tres datasets públicos. Ninguno podía confirmarla completa porque eran **demasiado cortos, pasivos o sin una sonda NoGo**. Aun así mostraron **piezas** del modelo: alfa como desenganche y theta tónico ligado al mal desempeño.
> Como ningún dataset reúne todas las condiciones, **hace falta mi propio experimento**.
> El sistema AR se diseña para funcionar **sea cual sea el resultado**: los resultados deciden **qué señal** dispara la intervención, no **si** el sistema funciona.

**El hilo de la exposición:** teoría → validación en la literatura → prueba en datasets → por qué no alcanzaron → brecha → mi estudio → sistema AR robusto.

---

## 1. Conceptos clave (glosario para no confundirte)

| Concepto | Qué es, en una frase | Por qué importa en mi proyecto |
|---|---|---|
| **Tónico** | Actividad de fondo, sostenida, medida en ventanas de segundos a minutos | Es el marcador de **fatiga**: sube lentamente con el tiempo |
| **Fásico** | Respuesta breve (0.1–0.5 s) **ligada a un evento**, por ejemplo un NoGo | Es el marcador de **control inhibitorio**: "¿el cerebro sigue reclutando control?" |
| **Theta frontal medial (FM-theta)** | Oscilación de 4–8 Hz en Fz/FCz, generada por el cíngulo anterior | Señal de "se necesita control" (Cavanagh & Frank, 2014) |
| **Alfa posterior** | Oscilación de 8–13 Hz en Pz/O1/O2 | Sube con el desenganche y la fatiga pasiva |
| **Periódico vs. aperiódico (1/f)** | El espectro EEG tiene un fondo 1/f (aperiódico) y "picos" encima (periódicos). Se separan con specparam/FOOOF | Parte de lo que parece "theta" es fondo 1/f o alfa enlentecida. Por eso uso **alfa_per / theta_per** y el **exponente 1/f** como covariable |
| **IAF** | Frecuencia pico individual de alfa (≈ 8–12 Hz, distinta en cada persona) | Con la fatiga, la IAF **baja** (Benwell 2019) e "invade" la banda theta. Por eso uso **bandas ajustadas a la IAF** |
| **Go/NoGo** | Tarea: responder a "Go" y **frenar** ante "NoGo" | Es la **sonda inhibitoria**. Sin NoGo no se puede medir H2/H3. Ningún dataset público la tenía |
| **Errores de comisión** | Responder ante un NoGo (no frenar) | Medida conductual de falla inhibitoria (H2) |
| **ERSP** | Cambio de potencia tras el evento respecto a una línea base pre-evento (en dB) | Es la medida del theta fásico. Ojo: puede ser **relativo** (respecto a la base del ensayo) o **absoluto** |
| **Fatiga activa vs. pasiva** | Activa = sobrecarga. Pasiva = tarea monótona y poco exigente (Desmond & Hancock, 2001) | El scrolling se parece más a la **pasiva** → se espera **alfa ↑ más que theta ↑** |
| **Condición control (documental)** | Un video neutro que **no fatiga** (Marcora 2009) | Separa el efecto del scrolling del simple paso del tiempo |
| **Contrabalanceo** | Mitad de los participantes hace primero scrolling y la otra mitad primero el documental | Evita confundir la condición con el orden (fue un problema de ds007537) |
| **Modelo mixto** | Regresión con el sujeto como efecto aleatorio | Analiza condición × tiempo respetando que cada persona tiene su propio nivel |
| **Holm** | Corrección por comparaciones múltiples | Evita falsos positivos al probar varias medidas |
| **TOST / factor de Bayes** | Pruebas que permiten afirmar "**no hay efecto mayor que X**" | Convierten un resultado nulo en información, no en "fracaso" |
| **Prerregistro (OSF)** | Publicar hipótesis y análisis **antes** de recolectar datos | Hace creíble cualquier resultado, incluido el nulo |
| **JITAI** | *Just-In-Time Adaptive Intervention*: intervenir en el momento justo según el estado del usuario | Mi AR es una JITAI cuya variable de adaptación es el **estado neural**, no el tiempo de pantalla |
| **LSL** | *Lab Streaming Layer*, protocolo para transmitir EEG y marcadores en tiempo real | AURA ya transmite por LSL (`AURA_Power` en `VRehab.py`) |
| **Simulador LSL** | Reproduce EEG grabado como si fuera en vivo | Permite probar todo el lazo **antes** de tener participantes |
| **Efecto Berger** | Al cerrar los ojos, el alfa occipital sube mucho | Es una señal **garantizada** para probar el lazo y hacer una demo segura |

---

## 2. Qué pasó en esta sesión (para que no te confundas con versiones viejas)

1. **Se reorganizó la presentación** en 14 diapositivas con tu orden (v3) y luego se hizo una versión visual con menos texto (**v4, la que vas a presentar**).
2. **Las hipótesis vigentes son las originales, basadas en el tiempo.** Hubo una versión "v3" que decía "la fatiga es un estado, no tiempo". **Quedó descartada**: fue una sobrecorrección, porque generalizaba a partir de datasets demasiado cortos y pasivos. Lo de "estado" se conserva solo como **H1-estado complementaria** (útil para la JITAI).
3. **El fásico de Cao se reinterpretó.** La primera lectura decía "los ensayos lentos tienen el pico fásico más bajo → apoyo a H3". **Era incorrecta**:
   - Al ver los **dB absolutos**, los ensayos lentos (fatigados) parten de **~1.1 dB más theta** antes del desvío y su pico también llega **más alto**.
   - La caída "relativa" se debía a normalizar cada ensayo contra su propia base, que en los lentos ya estaba inflada.
   - El −0.85 dB que se veía en la línea base de la figura vieja era un artefacto matemático (desigualdad de Jensen: promediar dB no es lo mismo que el dB del promedio), no un error de datos.
   - **Conclusión correcta:** en Cao la fatiga aparece como **theta tónico elevado** y la respuesta fásica **se conserva** (compensación). **H3 no se confirma en Cao**, pero Cao no tiene NoGo, así que H2/H3 siguen **sin probar**, no refutadas.
4. Las figuras de la v4 se generaron en inglés a partir de tus CSV de resultados (sin reprocesar datos) y coinciden con los reportes.

---

## 3. Explicación diapositiva por diapositiva

Para cada una: **mensaje** (la frase que debe quedar), **qué decir**, **datos clave** y **posibles preguntas**.

### 1 · Portada — *Closed-Loop Neuroadaptive AR Platform for Dopamine Scrolling*
- **Mensaje:** un sistema de lazo cerrado EEG + AR para el scrolling compulsivo.
- **Qué decir:** "dopamine scrolling" es el nombre popular del problema. Aclara desde el inicio que **no mido dopamina** (se explica en la diapositiva 3).
- **Pregunta posible:** "¿Por qué 'dopamine' si no la miden?" → Es el término con el que se conoce el fenómeno. Lo que mido es su **costo cognitivo**.

### 2 · Objectives
- **Mensaje:** detectar fatiga y pérdida de control inhibitorio durante el scrolling y responder con AR.
- **Los 5 objetivos específicos:** (1) intervención AR *just-in-time* comparada contra un temporizador · (2) validación offline en 3 datasets públicos · (3) protocolo propio, scrolling vs. documental + Go/NoGo · (4) pipeline en tiempo real (LSL → features → modelo individual) · (5) datos y documentación (BIDS).
- **Qué decir:** el objetivo 2 **ya está hecho** (es lo que presento hoy). Los demás son el plan.

### 3 · Scope & Framework
- **Mensaje:** mido el **costo cognitivo** del scrolling, no la dopamina.
- **Los 4 marcadores y su significado:**
  - **θ tónico ↑** (Fz, FCz, F3, F4) → fatiga.
  - **α periódica ↑** (Pz, O1, O2) → desenganche.
  - **θ NoGo ↓** (Fz/FCz, fásico) → pérdida de control.
  - **Fp1** → parpadeos, usados como veto de artefactos.
- **Qué decir:** la dopamina se libera en estructuras subcorticales (VTA, estriado) que el EEG de cuero cabelludo **no alcanza**.
- **Pregunta posible:** "¿Por qué theta y no otra banda?" → El theta frontal medial es la señal canónica de control cognitivo y el biomarcador de fatiga más robusto en el meta-análisis de Tran 2020.

### 4 · Hypotheses
- **Mensaje:** el modelo original, basado en el tiempo.
- **Las gráficas son ilustrativas** (predicciones, no datos):
  - **Izquierda (H1):** tras la línea base, la potencia tónica θ/α se separa de la línea base y sube a lo largo de 60 min de scrolling (Δ vs. baseline).
  - **Derecha (H2):** la respuesta theta tras el NoGo es más pequeña después del scrolling que en la línea base.
- **Las hipótesis:**
  - **H1:** θ/α tónicos suben **más con scrolling que con el documental** (con bandas IAF y 1/f como covariable). Complementaria, H1-estado: ambos covarían con los lapsos momentáneos.
  - **H2:** después del scrolling, la FM-θ evocada por NoGo baja y los errores de comisión suben.
  - **H3:** ambas cosas a la vez (tónico ↑ / fásico ↓). Antecedente directo: Arnau 2021.
  - **H4:** la AR disparada por el EEG supera a la misma intervención disparada por un temporizador.
- **Estado:** H1 tiene literatura ✓ y apoyo parcial en datasets. H2/H3 requieren el protocolo propio. H4 corresponde al Estudio 2.
- **Pregunta posible:** "¿Por qué comparar contra la línea base y contra el documental?" → La línea base controla las diferencias individuales y el documental controla el simple paso del tiempo.

### 5 · Theoretical Validation
- **Mensaje:** la literatura **sí** respalda el modelo.
- **Cifras clave:**
  - **g = 1.03** theta ↑ y **g = 0.85** alfa ↑ con fatiga (Tran 2020, meta-análisis de 21 estudios).
  - **~1 h:** el alfa llega a su máximo y el theta sigue subiendo (Wascher 2014).
  - **IAF ↓** con el tiempo en tarea (Benwell 2019).
  - **Tónico ↑ · fásico ↓:** precedente directo de H3 (Arnau 2021; Yu 2022).
  - **30 min** de redes sociales producen fatiga mental y 15 min no (Fortes 2019).
  - **NoGo errors ↑** (Jacquet et al., 2023, *Sci Rep*): 45 min de smartphone libre (sobre todo redes sociales) vs. documental, con Go/NoGo pre/post (n = 40 + 40). Los errores NoGo suben **solo** tras el smartphone (3.55 → 4.92; F = 5.23, p = .025). Es **apoyo conductual directo de H2** con un diseño casi igual al tuyo, pero **sin EEG** y sin video corto específico.
- **Condiciones que exige la teoría:** **≥ 30–60 min**, tarea exigente, ojos abiertos. **Nunca se ha probado con EEG + NoGo durante scrolling de video corto.**
- **Ojo:** el mismo grupo de Jacquet tiene un trabajo con EEG ("Electrophysiological changes associated with acute smartphone use and mental fatigue", proyecto ANR MENTALIST). Según su resumen, el theta frontal subió **tanto con smartphone como con documental**. No pudimos leer el texto completo. Es un riesgo conocido para H1, y justo lo que tu condición control y tu duración deben resolver.
- **Honestidad:** la literatura sobre inhibición (H2) es **mixta** (Kato 2009 sí; otros estudios no). Eso hace la pregunta más original, no más débil.
- **Pregunta posible:** "16 de los 21 estudios del meta-análisis eran conducción o vuelo, ¿aplica al scrolling?" → Es plausible, y justamente esa es la brecha que cubre mi estudio.

### 6 · Practical Validation
- **Mensaje:** los datasets mostraron **piezas** del modelo.
- **ds007537** (OpenNeuro, n = 27, 10 min de uso libre del smartphone):
  - En video corto, la **alfa periódica sube +0.43 dB** (minutos 9–10 vs. 1–2; 10 de 12 sujetos; p = 0.04, frágil).
  - El theta no cambia, **lo esperado** para solo 10 min.
  - Lectura: firma de desenganche / fatiga pasiva.
- **EEG-SVRec** (n = 25, sesiones de ≤ 15–30 min de video corto):
  - Las tendencias temporales son frágiles.
  - Por video: **más inmersión → menos alfa periódica** (20/25 sujetos; ρ mediana −0.10).
  - Lectura: la alfa sigue el (des)enganche momento a momento.
- **Cao 2019** (control positivo, n = 27, 62 sesiones, 60–90 min de conducción):
  - **Theta tónico ~ tiempo de reacción ρ = +0.50 (25/27)** y ~ lapsos +0.46 (23/27).
  - Alfa_per ~ TR +0.32 (24/27).
  - En 26 142 ensayos, el theta tónico previo al ensayo predice un TR más lento (**27/27**).
  - La respuesta fásica existe (+0.83 dB, 24/27) y **se conserva** bajo fatiga.
- **Qué decir sobre la figura de Cao:** los ensayos lentos (naranja) están **más arriba todo el tiempo**: la fatiga se ve en el nivel tónico, no en un pico más pequeño.
- **Pregunta posible:** "En Cao, ¿el TR empeora con el tiempo?" → No hay tendencia lineal del TR (ruidoso a escala de 5 min), pero el **acople** theta–TR dentro de cada sujeto es muy robusto. La fatiga fluctúa además de tener tendencia (Makeig & Inlow 1993).
- **Pregunta posible:** "¿Entonces Cao refuta H3?" → No. Cao mide desvío de carril, que no es un NoGo. Sin sonda inhibitoria no se puede probar la caída fásica.

### 7 · Why the Datasets Could Not Confirm It
- **Mensaje:** "**Ningún dataset público tiene las cinco condiciones.**"

| Requisito | ds007537 | EEG-SVRec | Cao 2019 | Mi estudio |
|---|---|---|---|---|
| Duración ≥ 45 min | ✗ 10 min | ✗ ≤ 30 min | ✓ 60–90 min | ✓ 45–60 min |
| Sonda NoGo | ✗ uso libre | ✗ pasivo | ✗ desvío de carril | ✓ en el feed + pre/post |
| Condición control | ✗ orden fijo | ✗ orden fijo | ✗ no hay | ✓ documental |
| Ancla de fatiga (TR / KSS) | ✗ | ✗ solo inmersión | ✓ TR, lapsos | ✓ KSS + TR |
| Paradigma de scrolling | ✓ smartphone | ✓ video corto | ✗ conducción | ✓ video corto |

- **También (no está en la diapositiva):** calidad de señal (ds007537: 3 sujetos ruidosos; SVRec: prefiltrado, meseta EMG 15–48 Hz y 3 archivos dañados; Cao: sin POz) y muestras pequeñas por condición (n = 12 en video corto).

### 8 · The Gap → A Unique Study
- **Mensaje:** scrolling + ≥ 45 min + NoGo + control = **mi estudio**, la primera prueba de tónico ↑ / fásico ↓ durante scrolling.
- **Evidencia de por qué el disparador debe ser cognitivo:**
  - **r = −.41:** más uso de video corto, peor control inhibitorio (Nguyen 2025, meta-análisis de 71 estudios).
  - **r = −.40:** más tendencia a la adicción, menos theta prefrontal (Yan 2024, EEG).
  - Son estudios correlacionales y de **rasgo**. Ninguno es agudo, pre/post, con EEG + Go/NoGo.
- **Herramientas actuales** (Opal, Time2Stop, one sec) reaccionan al **tiempo o al uso**, no al estado del cerebro.

### 9 · Experimental Plan
- **Sesión:** línea base de 3 min con ojos abiertos → Go/NoGo pre (5 min) → **scrolling o documental, 45–60 min**, con NoGo dentro del feed → Go/NoGo post (5 min) → KSS, VAS y NASA-TLX.
- **Diseño:** intra-sujeto, contrabalanceado, 2 días distintos, piloto n ≈ 10–15 + análisis de poder, prerregistro en OSF, modelos mixtos + TOST.
- **Montaje AURA:** Fz, FCz, F3, F4, Pz, O1, O2, Fp1.
- **Simulación primero:** el simulador LSL reproduce EEG grabado (ds007537 / Cao) a través del pipeline. Prueba features, latencia y el lazo AR **antes de tener participantes**. Después vienen la autoprueba con AURA y la prueba de ojos cerrados.
- **Pregunta posible:** "¿Por qué 45–60 min y no 35?" → Fortes encontró fatiga a los 30 min y no a los 15. Los efectos EEG tónicos más claros aparecen hacia ~1 h.

### 10 · System Pipeline
- **El lazo:** 1 scrolling (swipes + marcadores NoGo) → 2 EEG AURA por LSL → 3 preprocesamiento (filtros, artefactos, veto de parpadeo) → 4 features en ventanas de 2–4 s (θ, α periódica, 1/f) → 5 **modelo individual** (calibración por usuario, el patrón de `VRehab.py`: StandardScaler + LogisticRegression) → 6 AR (cue → fricción → pausa) → vuelve a 1.
- **Además:** almacenamiento BIDS, dashboard de sesión y modo offline con el simulador.
- **Pendiente de decidir:** dispositivo y motor de AR (Unity + AR Foundation, Quest en passthrough o WebXR).

### 11 · Robust to Negative Results — **la diapositiva más importante para defender el proyecto**
- **Mensaje:** "Las hipótesis deciden **qué** señal dispara la AR, no **si** el sistema funciona."
- **Dos aportes independientes:**
  - **Científico:** ¿hay disociación? Se evalúa con las pruebas prerregistradas de H1–H3.
  - **Ingenieril:** ¿el lazo detecta y responde a tiempo? Se evalúa con latencia < 2 s, AUC individual contra etiquetas conductuales, usabilidad (SUS) e intrusividad. **No depende de H1–H3.**
- **La matriz (cómo mis resultados me dicen qué hacer):**

| Resultado | Interpretación | Qué dispara la AR |
|---|---|---|
| **H1 ✓ H2 ✓** | Modelo completo | Escalera completa: cue → fricción → pausa |
| **H1 ✓ H2 ✗** | Hay fatiga pero el control se compensa (como en Cao y en Wascher 2014) | Solo marcadores tónicos → **pausa restaurativa**, sin fricción |
| **H1 ✗ H2 ✓** | Se pierde el control sin fatiga tónica | Desempeño en el NoGo del feed (errores, TR) → **fricción** |
| **H1 ✗ H2 ✗** | 45–60 min no producen fatiga medible: **hallazgo publicable** contra la narrativa de "brain rot" | Alfa periódica (desenganche) + conducta (velocidad de swipe, tiempo) → **cue de conciencia** |

- **Salvaguardas:** prerregistro en OSF · TOST / factores de Bayes · calibración individual (funciona aunque el efecto de grupo sea pequeño, porque el acople **dentro del sujeto** ya es robusto: 27/27 en Cao) · respaldo híbrido EEG + conducta · demo de ojos cerrados.

### 12 · Gantt
- 12 semanas. La validación offline (3 datasets) ya está **completada**. Después vienen: protocolo, OSF y ética → simulador LSL → calibración + prueba de ojos cerrados → autoprueba AURA + piloto → puente AR + condiciones H4 → análisis H1–H3 → integración + demo → reporte final.
- ⚠️ **Las semanas son relativas (W1–W12): ajústalas a tu calendario real antes de presentar.**

### 13 · Next Steps
1. Prerregistro en OSF + comité de ética de Ucaribe (iniciar ya).
2. Simulador LSL + prueba del lazo con ojos cerrados.
3. Autoprueba con AURA + piloto (n ≈ 10–15).

### 14 · References
- 19 referencias APA. ⚠️ Verifica antes de presentar: **Time2Stop (Orzikulova et al., 2024)**, **Fortes 2019** y **Wascher 2014** (algunos datos vienen de resúmenes).

---

## 4. Cómo argumentar "mis exploraciones me dicen qué hacer" (el razonamiento completo)

1. **Partí de una teoría** con respaldo: fatiga = tónico ↑, pérdida de control = fásico ↓.
2. **La probé barato y rápido** con datos públicos antes de gastar en un experimento. Eso es buena práctica, no una pérdida de tiempo.
3. **Los resultados se pueden leer a la luz de la teoría:**
   - Los datasets cortos y pasivos (ds007537, SVRec) dieron **alfa** pero no **theta**. Es justo lo que predice la teoría de fatiga pasiva con poca duración.
   - El único dataset largo (Cao) dio **theta tónico ligado al desempeño**. El pipeline funciona y detecta lo que debe.
   - El fásico en Cao **se conservó**, lo que demuestra que sin NoGo no se puede probar H2/H3.
4. **Cada limitación se convierte en una decisión de diseño:**

| Lo que faltó | Lo que haré |
|---|---|
| Duración corta | 45–60 min |
| Sin NoGo | Go/NoGo pre/post + NoGo dentro del feed |
| Sin control | Documental contrabalanceado |
| Sin ancla de fatiga | KSS / VAS / NASA-TLX + TR |
| "Theta" contaminado por alfa lenta y 1/f | Bandas IAF + specparam + exponente 1/f |
| Efectos frágiles de grupo | Prerregistro, modelos mixtos, TOST, calibración individual |

5. **Y el sistema no depende de un solo resultado:** la tabla de escenarios dice qué señal usar en cada caso.

**Frase de cierre sugerida:**
> "The public datasets could not test the full model, but each limitation told me exactly how to design my own study. And whatever the outcome, the closed-loop AR system is validated on its own criteria: the results decide which signal drives it, not whether it works."

---

## 5. Hoja de cifras (memorízalas)

| Cifra | Qué es |
|---|---|
| g = 1.03 / 0.85 | Theta / alfa ↑ con fatiga (Tran 2020) |
| r = −.41 | Uso de video corto ~ control inhibitorio (Nguyen 2025) |
| r = −.40 | Tendencia a la adicción ~ theta prefrontal (Yan 2024) |
| +0.43 dB, 10/12 | Alfa periódica en video corto, ds007537 |
| 20/25 | SVRec: más inmersión, menos alfa periódica |
| ρ = +0.50, 25/27 | Cao: theta tónico ~ TR |
| 27/27 | Cao: theta tónico previo al ensayo predice un TR más lento |
| +0.83 dB, 24/27 | Cao: la respuesta fásica existe |
| +1.16 dB | Cao: los ensayos lentos parten de más theta (por eso el fásico relativo "parecía" menor) |
| −0.22 dB, p = .09 | Cao: diferencia fásica relativa, no significativa → fásico conservado |
| 45–60 min | Duración de mi protocolo |
| n ≈ 10–15 | Piloto |
| < 2 s | Latencia objetivo del lazo |

---

## 6. Preguntas difíciles y respuestas cortas

- **"Sus datasets no confirmaron la hipótesis. ¿No será falsa?"** → No cumplían las condiciones que la teoría exige (duración, NoGo, control). Un resultado nulo en condiciones inadecuadas no refuta nada. Donde sí había duración (Cao), apareció el acople tónico.
- **"¿Por qué cree que el scrolling fatiga si es entretenido?"** → La recompensa puede **enmascarar** la fatiga mientras el usuario está dentro del feed (Hopstaken 2015). Por eso mido con una sonda NoGo y no solo con EEG pasivo.
- **"¿Y si theta sube por parpadeos o músculo?"** → Hay veto de parpadeos con Fp1, control de EMG, ICA y separación periódico/aperiódico.
- **"¿Por qué AR y no una app?"** → La AR funciona sobre **cualquier** app (TikTok, Reels, Shorts no permiten insertar contenido), el usuario sigue en su teléfono real, el diseño es no punitivo y el lazo es visible. La ruta de transferencia es la misma lógica en el teléfono o un wearable.
- **"¿Qué pasa si nada sale significativo?"** → Ver la diapositiva 11: es un hallazgo publicable, y el sistema usa alfa + conducta como disparador. Además, TOST permite afirmar la ausencia de efecto.
- **"¿El EEG realmente aporta algo frente a un temporizador?"** → Esa es exactamente la pregunta de H4 (EEG vs. temporizador vs. sin intervención). Si no lo supera, el EEG no se justifica, y esa es la prueba honesta.

---

## 7. Pendientes antes de presentar

- [ ] Ajustar las semanas del Gantt a tu calendario.
- [ ] Verificar las referencias marcadas (Time2Stop, Fortes 2019, Wascher 2014).
- [ ] Decidir si la portada mantiene "Dopamine Scrolling" (debes poder explicar por qué no mides dopamina).
- [ ] Opcional: el texto de H1 en la diapositiva 4 dice "than with a documentary", mientras que la gráfica muestra solo la comparación contra la línea base. Ambas son correctas (la línea base es el punto de partida y el documental es el control), pero prepárate para explicarlo.
