# MIRAI 2026 · Análisis del scope v2 y guía de cambios a la propuesta

> Base: `Project Proposal MIRAI Ricardo_Monrreal (1).pdf` (v1, 13 diapositivas) + `Scope_Dopamine_Scrolling.pdf` (research de scope) + `EEG Dataset 9-10/Demo_processing.py`.
> Fecha: 2026-10-19. Las referencias marcadas con **(verificar)** solo se confirmaron por resumen o metadatos, no por el texto completo.

---

## 0. Estado actual de `/Tests`

| Elemento | Qué es | Observación |
|---|---|---|
| `raw_data/Stroop_Data`, `raw_data/Arithmetic_Data` | 60 + 60 registros `.txt` (natural/low/mid/high × 15 sujetos) | Es el dataset **"Cognitive Load Assessment Through EEG: A Dataset from Arithmetic and Stroop Tasks"** (Mendeley `kt38js3jv7`; *Data in Brief* 2025, doi:10.1016/j.dib.2025.111477). OpenBCI Cyton, 8 canales, 250 Hz, ~112 s por archivo. |
| `Demo_processing.py` | Visor Tkinter: trim 3 s, pasa-banda 1–40 Hz, notch, reparación de artefactos, PSD de Welch, theta Fz tónico, detección de ráfagas theta, alfa, FAA, comparación entre niveles | Buena base. Ya implementa los biomarcadores del scope (ver §2.4 para sus limitaciones). |
| `Demo_processing_copy.py` | Versión antigua (127 líneas) | Ya no se usa; se puede borrar. |

**Qué puede validar este dataset y qué no:**
- ✅ Sirve como *sanity check* del pipeline: theta Fz debería subir con la carga (natural → high).
- ❌ No sirve para la teoría de fatiga: los registros duran ~2 min (sin *time-on-task*), no hay scrolling y **no hay electrodos parieto-occipitales** (Pz/O1/O2). El montaje es Fp1, Fp2, F7, F3, Fz, F4, F8, C2. En el código, `C2` funciona como "proxy" de alfa posterior, **y eso no es válido**: el alfa en C2 refleja el ritmo mu sensoriomotor, no el alfa posterior.

---

## 1. Objetivo central 1: datasets EEG de scrolling / video corto

**Hasta hoy no existe un dataset público de "dopamine scrolling" con una tarea de control inhibitorio.** Lo que sí existe, ordenado por utilidad para tu teoría:

| # | Dataset | Contenido | Utilidad para la teoría | Acceso |
|---|---|---|---|---|
| **1** | **Mishra, Gandhi & Gandhi (2026). Multimodal dataset of EEG, eye-tracking and physiological signals during naturalistic smartphone interactions** | 23 sujetos (14 en video corto: Reels/Shorts, 7 en juegos). **10 min de uso libre del smartphone** seguidos de 5 min de video de naturaleza (línea base). 64 canales (ActiCHamp, 1000 Hz, ref. Cz), eye-tracking (pupila), PPG, GSR. Cuestionarios **SAS** y **MPPUS**. | ⭐ **La mejor opción para el componente tónico.** Tiene Fz, Pz, O1 y O2. Permite medir la tendencia de theta y alfa minuto a minuto, comparar video corto vs. juego vs. línea base y correlacionar con la escala de adicción. | **OpenNeuro `ds007537`**, BIDS (BrainVision). Licencia CC-BY-NC 4.0. Se lee directo con `mne_bids`. |
| **2** | **EEG-SVRec (Zhang et al., SIGIR 2024)** | 30 sujetos, **4–5 sesiones de ~15 min navegando videos cortos** con *like*/*swipe* reales. 64 canales, 1000 Hz. Etiquetas de *engagement* afectivo, *likes* y % visto. 3,657 interacciones. | ⭐ **Tiene más *time-on-task* (hasta ~75 min por sujeto) y eventos de swipe** con marca de tiempo. Útil para ver cómo cambia theta/alfa a lo largo de las sesiones y alrededor de cada swipe. | Repositorio anónimo `anonymous.4open.science/r/Z-SV-CFB1` (~62 GB). Hay que confirmar la licencia; conviene escribir a los autores (Tsinghua, grupo de Yiqun Liu). |
| 3 | Du et al. (2025), *Sci. Reports*: EEG y contenido polarizado en video corto | 24 sujetos navegando video corto (TikTok/Bilibili). | Secundaria: el foco es la polarización, no la fatiga. | Datos aparentemente en Figshare **(verificar)**. |
| 4 | Rahman et al. (AMIA 2024/25): detección de adicción a video corto con wearables | 10 sujetos, Muse S (TP9/AF7/AF8/TP10) + EDA, 15 min de TikTok/Shorts/Reels. | Referencia de *state of the art*. No sirve para validar: no tiene Fz ni electrodos occipitales y los datos no son públicos. | No público. |

**Datasets de apoyo (fatiga e inhibición, sin scrolling):** sirven para calibrar el detector tónico/fásico con una verdad conocida.

| Dataset | Para qué |
|---|---|
| **Cao et al. (2019), *Sci. Data*:** 27 sujetos, 62 sesiones de 90 min de conducción con atención sostenida, 32 canales, en Figshare (`6427334`) | Validar que theta/alfa tónicos suben con el *time-on-task* y que se relacionan con el tiempo de reacción. |
| **Hamann & Carstengerdes (2023), *Sci. Reports*:** fatiga mental en 90 min de vuelo simulado, EEG+fNIRS, 31 sujetos, en PsychArchives | Igual que el anterior, con medidas subjetivas de fatiga. |
| **Cognitive Load (el que ya tienes)** | *Sanity check* de theta Fz contra la carga. |

**Recomendación práctica:** usa **ds007537** como dataset principal de validación offline (es BIDS y se puede descargar ya) y **EEG-SVRec** como segundo dataset si consigues acceso. La teoría completa (pérdida de theta **fásico**) **no se puede validar con ningún dataset público**: ninguno incluye una tarea inhibitoria antes y después del scrolling. Por eso necesitas un experimento propio (§2.3).

---

## 2. Objetivo central 2: revisión de la teoría

### 2.1 Veredicto general

**La dirección es correcta y defendible**, sobre todo el cambio de "medir dopamina" a "medir el costo cognitivo". La separación entre theta **tónico** (fatiga) y theta **fásico** (control inhibitorio) es la parte más fuerte y original. Hay cinco puntos que corregir para que la teoría resista una revisión académica.

### 2.2 Qué está bien sustentado ✅

| Afirmación del scope | Evidencia |
|---|---|
| La dopamina no se mide con EEG de superficie | Correcto. Los centros de recompensa (VTA, estriado) son subcorticales. Su et al. (2021) vieron activación de la VTA con videos personalizados de TikTok **con fMRI**, no con EEG. |
| Theta ↑ es el biomarcador más robusto de fatiga mental | Correcto. El meta-análisis de Tran et al. (2020; 21 estudios) encontró incrementos grandes de theta (g > 1) en zonas frontales, centrales y posteriores, y alfa como marcador de segunda línea. |
| Alfa posterior ↑ con la fatiga | Correcto en tareas largas: Wascher et al. (2014) reportan más alfa al final de 4 h de tarea. Tran et al. (2020) encuentran cambios moderados en alfa central y posterior. |
| Theta frontal medial (Fz/FCz) es la firma del control cognitivo/inhibitorio | Correcto. Cavanagh & Frank (2014) lo describen como un mecanismo común del cíngulo anterior para conflicto, error e inhibición. Nigbur et al. (2011) lo muestran en Go/NoGo, Stroop y Flanker. |
| El uso de video corto se asocia a peor control ejecutivo, también en el EEG | Yan et al. (2024, n = 48): la tendencia a la adicción a video corto se **correlaciona negativamente con la theta prefrontal en la condición de conflicto** del ANT (r = −0.395), no en reposo. **Es el antecedente más directo para tu hipótesis fásica.** El meta-análisis de Nguyen et al. (2025; 71 estudios, N = 98,299) encuentra r ≈ −.41 con el control inhibitorio y r ≈ −.38 con la atención **(verificar los valores)**. |
| Disociación tónico ↑ / fásico ↓ con el *time-on-task* | Tiene apoyo: Yu, Mückschel & Beste (2022) muestran que la theta **evocada por la tarea** en la corteza frontal superior **disminuye** con el *time-on-task*. Wascher (2014) muestra que la theta frontal **de fondo** **aumenta**. Arnau et al. (2021) titulan su trabajo "*Inverse effects of time-on-task in task-related and task-unrelated theta*" **(verificar el resumen)**. |

### 2.3 Qué hay que corregir ⚠️

**1. Las "ráfagas de theta fásico" necesitan un evento inhibitorio que las provoque.**
La FM-theta de control inhibitorio es una respuesta **ligada a un evento** (un estímulo NoGo, un conflicto o un error). Durante el scrolling libre no hay momentos marcados en los que el usuario "frene un impulso", así que contar ráfagas de theta en la señal continua (lo que hace hoy `detect_theta_bursts`) mide **theta espontáneo**, no control inhibitorio. Esa ráfaga podría deberse a carga de memoria, a una sorpresa, a parpadeos residuales o a un movimiento.
→ **Corrección:** mide el componente fásico con un *probe* inhibitorio. Hay dos opciones:
- **(A) Pre/post (más simple):** Go/NoGo o Stop-Signal antes y después de 30–40 min de scrolling, comparado contra una condición control (por ejemplo, un documental largo del mismo tiempo). Variables: potencia theta Fz/FCz relacionada al evento en los ensayos NoGo (200–500 ms), N2/P3 de NoGo y errores de comisión.
- **(B) Embebido (más original, recomendado):** un *feed* web propio tipo Reels donde algunos videos llevan una señal (por ejemplo, un borde rojo) que indica **"no deslizar durante X s"**. Esto convierte el scrolling en una tarea Go/NoGo ecológica: cada swipe y cada señal se envían como marcadores LSL, y se puede medir la theta fásica en NoGo **durante** la sesión, minuto a minuto. Así validas directamente la curva "pérdida de ráfagas" de la Figura 6.

**2. El alfa posterior no necesariamente "sube" mientras ves video.**
El estímulo visual activo **suprime** el alfa occipital (Jensen & Mazaheri, 2010). Varios estudios sobre smartphones reportan supresión de alfa durante el uso. Un aumento absoluto contra el reposo no es lo que debes esperar.
→ **Corrección:** formula la hipótesis como **tendencia dentro de la misma condición** (minutos finales vs. iniciales del scrolling, normalizados a la línea base del sujeto) y compárala contra la condición control. Separa también la fatiga de la **somnolencia** (que también sube theta y alfa) con la escala KSS (Karolinska) y controla la hora del día.

**3. "La corteza prefrontal agota su reserva energética" es un modelo cuestionado.**
El modelo de agotamiento de recursos (*ego depletion*) falló en una réplica multilaboratorio preregistrada (Hagger et al., 2016).
→ **Corrección:** habla de **"efectos de time-on-task / fatiga cognitiva"** y presenta como marco explicativo el **modelo de costo de oportunidad** (Kurzban et al., 2013): el cerebro reduce el esfuerzo de control cuando la tarea deja de compensar. Encaja muy bien con el scrolling, donde la recompensa inmediata del siguiente video compite con el esfuerzo de detenerse. Evita "reserva energética".

**4. Términos no científicos.**
| Evitar | Usar |
|---|---|
| "trance", "estado hipnótico", "hijack dopaminergic pathways" | "estado de fatiga cognitiva con pérdida del control inhibitorio", "desacoplamiento atencional", "reducción del sentido de agencia" (Lukoff et al., 2021) |
| "Dopamine scrolling" como diagnóstico | Úsalo como término divulgativo (Sharpe & Spooner, 2025); el constructo medible es "uso compulsivo de video corto" (escalas SAS, MPPUS o SVAS) |
| "medir la dopamina" | "medir el costo cognitivo del ciclo de gratificación" |
| "FAA = enganche clínico en la búsqueda de gratificación" | "FAA = índice de motivación de aproximación" (Harmon-Jones & Gable, 2018). Es una variable **exploratoria**: su fiabilidad es baja en ventanas cortas y depende de la referencia. |

**5. Las hipótesis tienen que ser falsables.** Propuesta:
- **H1 (fatiga, tónico):** la potencia theta en Fz y alfa en Pz/O1/O2, normalizadas a la línea base, aumentan con el tiempo de scrolling más que en la condición control.
- **H2 (inhibición, fásico):** después del scrolling (o en los últimos bloques del *feed* embebido) **disminuye la theta FM evocada por NoGo** y **aumentan los errores de comisión**, en relación con el pre y con el control.
- **H3 (disociación):** H1 y H2 ocurren a la vez (theta tónico ↑ y theta fásico ↓), y su magnitud se correlaciona con SAS/MPPUS.

### 2.4 Implicaciones para `Demo_processing.py`

1. **Línea base de las ráfagas (sesgo importante):** el umbral es `2.5 × mediana móvil de 10 s`. Si la theta tónica sube, el umbral sube con ella y **las ráfagas "desaparecen" por construcción**. Esto acopla H1 y H2 artificialmente. Usa una línea base **fija**, calculada en la calibración inicial de cada sujeto.
2. **Alfa posterior con C2:** no es válido (ver §0). Necesitas Pz/O1/O2.
3. **Ojos:** Fp1/Fp2 y la banda theta están muy contaminadas por parpadeos y movimientos oculares, que son constantes al ver una pantalla. La interpolación con umbral de ±150 µV no basta: usa ICA (MNE) con Fp1 como canal EOG de referencia.
4. **Bandas fijas:** calcula la **frecuencia alfa individual (IAF)** en la línea base y define theta como IAF−6 a IAF−2 y alfa como IAF−2 a IAF+2.
5. **Normalización:** reporta los cambios como dB o % contra la línea base del sujeto, no como µV² absolutos (la impedancia varía entre sesiones).

**Montaje recomendado para el AURA (8 canales):** `Fz, FCz, F3, F4, Pz, O1, O2, Fp1 (EOG)`. Así cubres theta FM, FAA, alfa posterior y artefactos oculares.

---

## 3. Contenido nuevo de la presentación (v2)

Título nuevo: **"Closed-Loop Neuroadaptive AR Platform for Dopamine Scrolling: EEG Detection of Cognitive Fatigue and Inhibitory-Control Loss"**

Estructura propuesta (11–12 diapositivas, con más peso en los avances):

| # | Diapositiva | Acción |
|---|---|---|
| 1 | Portada | Cambiar VR → AR y añadir subtítulo |
| 2 | Problem | Mantener; cambiar la fuente de estadísticas comerciales (ScrollGuard) por Nguyen et al. (2025) |
| 3 | **Scope v2: qué medimos y qué NO** | Nueva |
| 4 | **Marco neurofisiológico (theta tónico/fásico + alfa)** | Nueva (usar Fig. 4 y 6 del research) |
| 5 | Objectives | Reescribir |
| 6 | State of the Art + Competitors | Reescribir |
| 7 | **System Pipeline** | Nueva |
| 8 | **Avances (Progress)** | Nueva: la más importante |
| 9 | Experimental validation plan | Nueva |
| 10 | Technologies | Reescribir |
| 11 | Innovation factor | Reescribir |
| 12 | Gantt + Next steps | Actualizar |
| 13 | References | Ampliar (§4) |

Target Market (slide 10 de v1) puede quedar como respaldo o eliminarse para ganar espacio para los avances.

---

### Slide 3 · Scope v2

**We do NOT measure dopamine.** Reward release occurs in subcortical structures (VTA/striatum) that scalp EEG cannot reach.

**We measure its cognitive cost:** the user's transition into **cognitive fatigue with loss of inhibitory control** during short-form video scrolling.

| Marker | Band / site | Expected with prolonged scrolling | Meaning |
|---|---|---|---|
| Tonic theta power | 4–8 Hz, Fz | ↑ | Cognitive fatigue |
| Tonic posterior alpha | 8–13 Hz, Pz/O1/O2 | ↑ (relative to session start) | Cognitive fatigue / disengagement |
| Phasic FM-theta (NoGo-evoked) | 4–8 Hz, Fz/FCz | ↓ | Loss of inhibitory control |
| FAA (exploratory) | alpha F4 vs F3 | — | Approach motivation |

> Focus: degradation of sustained attention and depletion of the executive control network.

### Slide 5 · Objectives

**General:** Develop and validate a closed-loop EEG platform with AR feedback that detects, during short-form video scrolling, the user's transition into cognitive fatigue with loss of inhibitory control, using tonic/phasic theta and posterior alpha dynamics.

**Specific:**
1. Validate tonic theta/alpha biomarkers offline on public smartphone/short-video EEG datasets (OpenNeuro ds007537, EEG-SVRec).
2. Design and run an experimental protocol (scrolling vs. control, with an embedded or pre/post Go/NoGo probe) to measure phasic FM-theta.
3. Build a real-time processing pipeline (acquisition → preprocessing → per-window features → individually calibrated fatigue/inhibition index) for the 8-channel AURA device.
4. Implement standardized storage (BIDS) and a session dashboard.
5. Design and evaluate a just-in-time AR intervention (awareness cue → friction → restorative micro-break) triggered by the detected state, and compare it against a time-based (open-loop) intervention.
6. Prototype an off-session VR inhibitory-control training module (Scroll-NoGo + FM-theta neurofeedback).
7. Document architecture, protocol and data standards.

### Slide 6 · State of the Art + Competitor analysis

**Scrolling research (behavioral / HCI):**
- **Nguyen et al. (2025), Psychological Bulletin:** meta-analysis of 71 studies (N = 98,299). Heavier short-form video use is associated with poorer attention and inhibitory control.
- **Chiossi et al. (2023), CHI:** only TikTok-style short videos (vs. Twitter, YouTube) impaired prospective memory, which the authors attribute to rapid context switching.
- **Lukoff et al. (2021), CHI:** autoplay and recommendations reduce the user's sense of agency; **Monge Roffarello & De Luca (2026), CHI** examine infinite scroll and autoplay on TikTok **(verificar)**.
- **Grüning et al. (2023), PNAS (one sec app):** a friction nudge led to 36% of attempted app openings being abandoned and 37% fewer opening attempts after 6 weeks (n = 280).

**Neurophysiology of short video:**
- **Su et al. (2021), NeuroImage (fMRI):** personalized TikTok videos activate the default mode network and VTA.
- **Yan et al. (2024), Front. Hum. Neurosci. (EEG, n = 48):** short-video addiction tendency correlates negatively with prefrontal theta during conflict.
- **Rahman et al. (2025), AMIA:** detection of short-form video addiction from Muse S EEG + EDA.
- **Mishra et al. (2026), OpenNeuro ds007537:** EEG + eye-tracking during naturalistic smartphone use.

**Closed-loop EEG + XR:**
- **Kosmyna et al. (2021), AttentivU (MIT):** HoloLens 2 that adapts to EEG-measured attention.
- **Closed-loop VR Attention Restoration (Sensors, 2020):** uses FM-theta and P3b.

**Competitors:**
| | Strength | Weakness |
|---|---|---|
| App blockers (Opal, Freedom) | Hard blocking | Punitive; ignore the user's internal state |
| Friction nudges (one sec) | Evidence-based | Time/opening-based, blind to cognitive state |
| EEG wearables (Muse) | Consumer EEG | Meditation focus, no scrolling model |
| **Ours** | **State-based trigger (fatigue + inhibition loss), non-punitive AR feedback** | Requires EEG headset |

### Slide 7 · System Pipeline

```
[1] Scrolling session          [2] EEG acquisition        [3] Preprocessing
 custom web feed / app  ──►     AURA 8 ch (Fz FCz F3 F4    trim → 1–40 Hz band-pass → notch 60 Hz
 swipe + NoGo markers (LSL)     Pz O1 O2 Fp1) via LSL      → ICA/EOG → artifact rejection
        │                                                         │
        ▼                                                         ▼
[6] User feedback (AR)   ◄──  [5] Storage & presentation  ◄──  [4] Transformation pipeline
 non-punitive overlay:         BIDS / Parquet session         sliding windows (4 s, 50%): Welch PSD
 "you've reached fatigue        logs + Streamlit/Flask         tonic θ Fz, α Pz/O1/O2 (IAF bands)
 threshold — pause?"            dashboard                      NoGo-locked FM-θ (phasic)
                                                               → baseline-normalized index → state
```

(Hacerlo como diagrama de 6 bloques; la flecha 6 → 1 cierra el lazo.)

### Slide 8 · Progress (avances)

- **Done:** offline EEG viewer/analyzer (`Demo_processing.py`): 3 s trim, band-pass/notch, artifact repair, Welch PSD, band powers, cognitive-load indices (θ/α, β/α, engagement), tonic θ Fz, θ-burst detection, FAA, level comparisons.
- **Done:** pipeline tested on the Cognitive Load dataset (Stroop/Arithmetic, 15 subjects × 4 levels, OpenBCI 8 ch). *Incluye 1–2 capturas: el PSD y la pestaña "Biomarcadores".*
- **Done:** scope redefinition (dopamine → cognitive fatigue + inhibitory control) with literature review.
- **Identified:** validation datasets (ds007537, EEG-SVRec) and pipeline limitations (missing posterior channels, adaptive-threshold bias, ocular artifacts).
- **Next:** run the pipeline on ds007537 (MNE-BIDS) and test H1.

### Slide 9 · Experimental validation plan

- **Design:** within-subject, two sessions on separate days, order counterbalanced: **short-form scrolling (35 min)** vs. **control (long-form documentary, 35 min)**.
- **Per session:** 3 min eyes-open baseline → Go/NoGo (5 min) → condition → Go/NoGo (5 min) → KSS + NASA-TLX + VAS fatigue. Optional: embedded NoGo cues inside the feed.
- **Measures:** tonic θ Fz and α Pz/O1/O2 trend; NoGo FM-θ ERS, N2/P3, commission errors, RT; SAS/MPPUS.
- **Analysis:** linear mixed models (condition × time), with the subject as a random effect.
- **Pilot sample:** n ≈ 10–15 (feasibility), with informed consent and an ethics committee review.
- **Study 2 (intervention, see §5):** three conditions (no intervention / time-based friction / EEG-triggered AR intervention) to test H4.

### Slide 10 · Technologies

| Layer | Tools |
|---|---|
| Acquisition | AURA (8 ch), BrainFlow / Lab Streaming Layer (pylsl), LabRecorder |
| Stimulus / experiment | PsychoPy (Go/NoGo) + custom web feed (HTML/JS) with LSL markers |
| Processing | Python: MNE-Python, MNE-BIDS, SciPy, NumPy, pandas |
| Storage | BIDS (offline), Parquet/SQLite (session telemetry) |
| Visualization | Streamlit or Flask dashboard; Matplotlib |
| AR feedback | Unity + AR Foundation / OpenXR (passthrough MR headset or AR glasses) |
| Stats | statsmodels (mixed models), pingouin |
| Versioning | Git / GitHub |

**Nota práctica sobre AR:** la correa del visor presiona Pz/O1/O2 y genera artefactos. Por eso, valida el feedback primero en pantalla (fase 1) y migra a AR después. Elige un visor con correa frontal o lentes AR ligeros. HoloLens 2 ya se descontinuó, así que no es buena opción.

### Slide 11 · Innovation factor

**A closed-loop, state-based (not time-based) intervention for compulsive scrolling.**
To our knowledge, the first system that detects in real time the user's transition into cognitive fatigue with loss of inhibitory control during short-form video scrolling. It uses the dissociation between tonic theta/posterior alpha (rising fatigue) and phasic frontal-midline theta (falling inhibitory control), and returns non-punitive AR feedback without blocking the device.

It is a **just-in-time adaptive intervention (JITAI)** whose tailoring variable is a neural state rather than screen time. Each intervention targets one mechanism: friction restores agency when inhibitory control drops, and a restorative break counters fatigue. The system checks its own effect by tracking whether the biomarkers recover. AR keeps the user on their real phone and works with any app (TikTok, Reels, Shorts) without needing access to the platform.

### Slide 12 · Gantt (12 semanas; ajusta las fechas a tu calendario)

| Fase / proceso | S1 | S2 | S3 | S4 | S5 | S6 | S7 | S8 | S9 | S10 | S11 | S12 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **F1** Validación offline (ds007537, EEG-SVRec) + corrección del pipeline | ■ | ■ | ■ | | | | | | | | | |
| **F2** Diseño del protocolo, montaje AURA, feed web + Go/NoGo, ética | | ■ | ■ | ■ | | | | | | | | |
| **F3** Pipeline en tiempo real (LSL) + almacenamiento BIDS | | | | ■ | ■ | ■ | | | | | | |
| **F4** Piloto experimental (adquisición, n ≈ 10–15) | | | | | | ■ | ■ | ■ | | | | |
| **F5** Análisis estadístico (H1–H3) + calibración del índice | | | | | | | | ■ | ■ | ■ | | |
| **F6** Intervención JITAI: pantalla → AR (cue/fricción/pausa) + piloto de H4 | | | | | | | ■ | ■ | ■ | ■ | | |
| **F7** Integración end-to-end + demo | | | | | | | | | | ■ | ■ | |
| **F8** Reporte final y documentación | | | | | | | | | | | ■ | ■ |

**Next steps:** (1) descargar ds007537 y probar H1; (2) corregir la línea base fija de las ráfagas y añadir ICA; (3) definir el montaje AURA y construir el feed con NoGo embebido.

> El módulo VR de entrenamiento (objetivo 6) queda como trabajo futuro si las 12 semanas no alcanzan. Lo prioritario es demostrar H4.

---

## 5. Intervención: cómo justificar AR/VR (y otras tecnologías) para regular el scrolling

### 5.1 La idea clave: el EEG justifica la tecnología, no al revés

Si solo mides el EEG, el proyecto es un estudio observacional. Para justificar una tecnología de intervención necesitas tres cosas:
1. **Un marco reconocido** que diga *cuándo* intervenir: **JITAI** (*Just-In-Time Adaptive Intervention*; Nahum-Shani et al., 2018). Un JITAI da "el tipo y la cantidad de apoyo adecuados, en el momento adecuado", adaptándose al estado interno del usuario. Tu EEG es justo la **variable de adaptación** (*tailoring variable*) que les falta a los JITAI de smartphone. Esos sistemas solo conocen el tiempo de pantalla y no saben si el usuario está fatigado o en automático.
2. **Un mecanismo con evidencia para cada evento** que detectas: cada evento neural dispara una intervención distinta (§5.2).
3. **Una comparación que demuestre el valor del lazo cerrado:** intervención disparada por el EEG **vs.** la misma intervención disparada por tiempo, como hace one sec (§5.5). Si el lazo cerrado no supera al temporizador, el EEG no se justifica. Esa es la prueba honesta.

### 5.2 Cada evento detectado activa un mecanismo distinto

| Estado detectado | Mecanismo de la intervención | Evidencia |
|---|---|---|
| **Fatiga cognitiva** (theta tónico ↑, alfa posterior ↑) | **Restauración:** micro-pausa de 2–3 min con naturaleza o respiración lenta, para recuperar la atención dirigida (*Attention Restoration Theory*) | Dillon & Cai (2022, n = 120): la naturaleza en VR restauró mejor la atención dirigida que otras condiciones. ⚠️ **Evidencia mixta:** un estudio preregistrado de 2023 no encontró efecto con videos de naturaleza. Por eso **verificas la recuperación con el EEG** en lugar de darla por hecha. |
| **Pérdida del control inhibitorio** (theta FM fásico ↓) | **Fricción y agencia:** interrumpir la conducta automática con una pausa breve que exige una decisión deliberada | Grüning et al. (2023, PNAS): la fricción hizo que se abandonara el 36% de las aperturas. Haliburton et al. (CHI 2024): efecto sostenido en campo. InteractOut (CHI 2024, N = 42): −15.6% de tiempo frente a un bloqueo por temporizador. Lukoff (2021): el diseño que devuelve agencia es preferido. |
| **Déficit crónico de inhibición** (fuera de la sesión) | **Entrenamiento:** Go/NoGo con estímulos de scrolling + neurofeedback de theta FM | Jones et al. (2016, meta-análisis): el entrenamiento de control inhibitorio reduce la conducta apetitiva (SMD = 0.36, mejor con Go/NoGo). Enriquez-Geppert et al. (2014): 8 sesiones de neurofeedback de theta FM mejoraron el control **proactivo**, pero ⚠️ no la inhibición motora. Es una hipótesis exploratoria. |

### 5.3 Por qué AR para la intervención en el momento (y no VR)

| Argumento | Explicación |
|---|---|
| **Validez ecológica** | En AR el usuario sigue usando **su propio teléfono y su app real**. La VR reemplazaría la conducta que quieres regular. El passthrough de Quest 3 permite leer la pantalla del teléfono (mejorado en la actualización v64). |
| **Independiente de la app** | TikTok, Reels y Shorts no permiten insertar contenido dentro de su interfaz (sobre todo en iOS). Un overlay AR funciona **sobre cualquier app**, sin API ni permisos de la plataforma. |
| **No punitivo y graduable** | La señal puede vivir en la visión periférica (un viñeteado suave) y escalar solo si hace falta. Bloquear la app genera abandono, como ya señalaba tu análisis de competidores. |
| **Lazo cerrado visible** | Durante la pausa el usuario ve su propio indicador de recuperación (theta y alfa volviendo a la línea base). Eso convierte la pausa en *biofeedback*. |

**Por qué VR sí tiene lugar, pero fuera de la sesión:** el entrenamiento necesita estímulos controlados y repetibles (*cue exposure*). La VR provoca *craving* de forma fiable en adicciones conductuales: un cibercafé virtual lo indujo en jugadores con trastorno por videojuegos, proporcional a la severidad (Kim et al., 2018, PLOS ONE). Un **"feed Scroll-NoGo" en VR** con neurofeedback de theta FM es el módulo de entrenamiento.

### 5.4 Escalera de intervención en lazo cerrado

```
Línea base (3 min) → índice_fatiga = z(θ Fz) + z(α Pz/O1/O2)     índice_inhibición = Δ FM-θ en NoGo del feed
                                                                   (+ proxy conductual: swipes cada vez más rápidos y regulares)

NIVEL 0  normal ──────────────────────────────────────────────► sin intervención
NIVEL 1  fatiga > umbral durante ≥ 60 s ──────────────────────► señal ambiental AR periférica (conciencia, no interrumpe)
NIVEL 2  fatiga + caída de inhibición ≥ 60 s ─────────────────► tarjeta AR de fricción: "¿Sigues por decisión?"
                                                                 mantener un gesto/mirada 3 s → [Continuar] / [Pausa 2 min]
NIVEL 3  eligió pausa ────────────────────────────────────────► micro-pausa restaurativa AR (portal de naturaleza / respiración
                                                                 a 6 rpm) con indicador EEG de recuperación → vuelve al nivel 0
Periodo refractario: 5 min entre intervenciones (evita la fatiga de alertas; los usuarios abandonan las fricciones demasiado frecuentes).
```

Nota: los umbrales son z > 1.5 sobre la línea base individual. Es una heurística inicial; se recalibran con los datos del piloto (F5).

### 5.5 El experimento que justifica la tecnología (Estudio 2)

- **Diseño:** intra-sujeto, 3 sesiones contrabalanceadas de 35 min de scrolling:
  **(a)** sin intervención · **(b)** fricción por **tiempo** (cada 10 min, estilo one sec) · **(c)** fricción y pausa **disparadas por el EEG** (AR).
- **H4:** (c) supera a (b) en: % de veces que el usuario se detiene después de la intervención, recuperación de la theta FM fásica y del alfa tras la pausa, errores de comisión en el Go/NoGo post-sesión, sentido de agencia y percepción de intrusividad (cuestionario breve).
- **Por qué importa:** si (c) ≈ (b), el EEG no aporta nada a la regulación. Si (c) > (b), queda demostrado que **el momento elegido por el estado neural** es el ingrediente activo. Esto es lo que diferencia tu proyecto de one sec, Opal y los demás.

### 5.6 Alternativas sin XR (válidas para presentar)

| Canal | Ventaja | Cuándo usarlo |
|---|---|---|
| **Overlay en el propio teléfono** (app Android con permiso de superposición) | Sin visor; ruta realista a producto | Fase 1 de validación y como versión "transferible" |
| **Háptico en smartwatch** | Discreto; nada visual compite con el video | Nivel 1 (conciencia) |
| **Iluminación ambiental (bombilla smart)** | Cero interrupción | Demo y señal de nivel 1 |

**Mensaje para la presentación:** la AR es la plataforma de **investigación y entrenamiento** porque es independiente de la app, ecológica y visible. La **ruta de transferencia** es la misma lógica JITAI en el teléfono o un wearable con EEG de consumo (diadema o audífonos).

### 5.7 Diapositiva nueva · "Neuroadaptive Intervention"

**From measuring to regulating: a just-in-time adaptive intervention (JITAI) driven by brain state.**

| Detected state | AR response | Mechanism |
|---|---|---|
| Fatigue rising | Peripheral ambient cue | Awareness |
| Fatigue + inhibition loss | Friction card: "Still scrolling by choice?" (hold 3 s) | Restores agency (one sec, PNAS 2023) |
| Break accepted | 2-min restorative AR micro-break with live EEG recovery meter | Attention restoration + biofeedback |
| Off-session | VR Scroll-NoGo training + FM-theta neurofeedback | Inhibitory control training (Jones 2016) |

**Validation:** EEG-triggered vs. time-triggered vs. no intervention (H4).

---

## 6. Bibliografía (APA 7)

**Fatiga mental y bandas EEG**
- Tran, Y., Craig, A., Craig, R., Chai, R., & Nguyen, H. (2020). The influence of mental fatigue on brain activity: Evidence from a systematic review with meta-analyses. *Psychophysiology, 57*(5), e13554. https://doi.org/10.1111/psyp.13554
- Wascher, E., Rasch, B., Sänger, J., Hoffmann, S., Schneider, D., Rinkenauer, G., Heuer, H., & Gutberlet, I. (2014). Frontal theta activity reflects distinct aspects of mental fatigue. *Biological Psychology, 96*, 57–65. https://doi.org/10.1016/j.biopsycho.2013.11.010
- Arnau, S., et al. (2021). Inverse effects of time-on-task in task-related and task-unrelated theta activity. *Psychophysiology*, e13805. https://doi.org/10.1111/psyp.13805 **(verificar)**
- Yu, S., Mückschel, M., & Beste, C. (2022). Superior frontal regions reflect the dynamics of task engagement and theta band-related control processes in time-on task effects. *Scientific Reports, 12*. https://doi.org/10.1038/s41598-022-04972-y
- Boksem, M. A. S., Meijman, T. F., & Lorist, M. M. (2005). Effects of mental fatigue on attention: An ERP study. *Cognitive Brain Research, 25*(1), 107–116. https://doi.org/10.1016/j.cogbrainres.2005.04.011

**Theta frontal medial y control inhibitorio**
- Cavanagh, J. F., & Frank, M. J. (2014). Frontal theta as a mechanism for cognitive control. *Trends in Cognitive Sciences, 18*(8), 414–421. https://doi.org/10.1016/j.tics.2014.04.012
- Nigbur, R., Ivanova, G., & Stürmer, B. (2011). Theta power as a marker for cognitive interference. *Clinical Neurophysiology, 122*(11), 2185–2194. https://doi.org/10.1016/j.clinph.2011.03.030

**Alfa e inhibición funcional**
- Klimesch, W., Sauseng, P., & Hanslmayr, S. (2007). EEG alpha oscillations: The inhibition–timing hypothesis. *Brain Research Reviews, 53*(1), 63–88. https://doi.org/10.1016/j.brainresrev.2006.06.003
- Jensen, O., & Mazaheri, A. (2010). Shaping functional architecture by oscillatory alpha activity: Gating by inhibition. *Frontiers in Human Neuroscience, 4*, 186. https://doi.org/10.3389/fnhum.2010.00186

**Motivación, FAA y modelos de esfuerzo**
- Harmon-Jones, E., & Gable, P. A. (2018). On the role of asymmetric frontal cortical activity in approach and withdrawal motivation: An updated review of the evidence. *Psychophysiology, 55*(1), e12879. https://doi.org/10.1111/psyp.12879
- Kurzban, R., Duckworth, A., Kable, J. W., & Myers, J. (2013). An opportunity cost model of subjective effort and task performance. *Behavioral and Brain Sciences, 36*(6), 661–679. https://doi.org/10.1017/S0140525X12003196
- Hagger, M. S., et al. (2016). A multilab preregistered replication of the ego-depletion effect. *Perspectives on Psychological Science, 11*(4), 546–573. https://doi.org/10.1177/1745691616652873

**Video corto / scrolling**
- Nguyen, L., et al. (2025). Feeds, feelings, and focus: A systematic review and meta-analysis examining the cognitive and mental health correlates of short-form video use. *Psychological Bulletin, 151*(9), 1125–1146. https://doi.org/10.1037/bul0000498
- Yan, T., Su, C., Xue, W., Hu, Y., & Zhou, H. (2024). Mobile phone short video use negatively impacts attention functions: An EEG study. *Frontiers in Human Neuroscience, 18*, 1383913. https://doi.org/10.3389/fnhum.2024.1383913
- Su, C., Zhou, H., Gong, L., Teng, B., Geng, F., & Hu, Y. (2021). Viewing personalized video clips recommended by TikTok activates default mode network and ventral tegmental area. *NeuroImage, 237*, 118136. https://doi.org/10.1016/j.neuroimage.2021.118136
- Chiossi, F., Haliburton, L., Ou, C., Butz, A., & Schmidt, A. (2023). Short-form videos degrade our capacity to retain intentions: Effect of context switching on prospective memory. *CHI '23*. https://doi.org/10.1145/3544548.3580778
- Lukoff, K., Lyngs, U., Zade, H., Liao, J. V., Choi, J., Fan, K., Munson, S. A., & Hiniker, A. (2021). How the design of YouTube influences user sense of agency. *CHI '21*. https://doi.org/10.1145/3411764.3445467
- Grüning, D. J., Riedel, F., & Lorenz-Spreen, P. (2023). Directing smartphone use through the self-nudge app one sec. *PNAS, 120*(8), e2213114120. https://doi.org/10.1073/pnas.2213114120
- Sharpe, B. T., & Spooner, R. A. (2025). Dopamine-scrolling: A modern public health challenge requiring urgent attention. *Perspectives in Public Health, 145*(4), 190–191. https://doi.org/10.1177/17579139251331914
- Sharpe, A. T. R., Tyndall, I., Poulus, D. R., Obine, E. A. C., & Sharpe, B. T. (2026). The influence of doomscrolling on mental health: A scoping review. *Mental Health and Digital Technologies, 3*(3), 290–342.
- Rahman, M., Mahi, A. M., Sultana, S., Churpek, M. M., & Alam, M. A. U. (2025). Detection of short-form video addiction with wearable sensors via temporally-coherent domain adaptation. *AMIA Annual Symposium Proceedings, 2024*, 940–949.

**Datasets**
- Mishra, P., Gandhi, T. K., & Gandhi, S. R. (2026). A multimodal dataset of EEG, eye-tracking, and physiological signals during naturalistic smartphone interactions. *bioRxiv*. https://doi.org/10.64898/2026.04.21.719334 · OpenNeuro **ds007537**
- Zhang, S., He, Z., Ye, Z., Sun, P., Ai, Q., Zhang, M., & Liu, Y. (2024). EEG-SVRec: An EEG dataset with user multidimensional affective engagement labels in short video recommendation. *SIGIR '24*. https://arxiv.org/abs/2404.01008
- Cao, Z., Chuang, C.-H., King, J.-K., & Lin, C.-T. (2019). Multi-channel EEG recordings during a sustained-attention driving task. *Scientific Data, 6*, 19. https://doi.org/10.1038/s41597-019-0027-4
- Hamann, A., & Carstengerdes, N. (2023). Assessing the development of mental fatigue during simulated flights with concurrent EEG-fNIRS measurement. *Scientific Reports, 13*. https://doi.org/10.1038/s41598-023-31264-w
- Cognitive load assessment through EEG: A dataset from arithmetic and Stroop tasks. (2025). *Data in Brief*, 111477. https://doi.org/10.1016/j.dib.2025.111477

**Intervención (JITAI, fricción, restauración, entrenamiento)**
- Nahum-Shani, I., Smith, S. N., Spring, B. J., Collins, L. M., Witkiewitz, K., Tewari, A., & Murphy, S. A. (2018). Just-in-time adaptive interventions (JITAIs) in mobile health: Key components and design principles for ongoing health behavior support. *Annals of Behavioral Medicine, 52*(6), 446–462. https://doi.org/10.1007/s12160-016-9830-8
- Haliburton, L., Grüning, D. J., Riedel, F., Schmidt, A., & Terzimehić, N. (2024). A longitudinal in-the-wild investigation of design frictions to prevent smartphone overuse. *CHI '24* **(verificar autores)**
- Xu, T., et al. (2024). InteractOut: Leveraging interaction proxies as input manipulation strategies for reducing smartphone overuse. *CHI '24*. https://doi.org/10.1145/3613904.3642747 **(verificar)**
- Jones, A., Di Lemma, L. C. G., Robinson, E., Christiansen, P., Nolan, S., Tudur-Smith, C., & Field, M. (2016). Inhibitory control training for appetitive behaviour change: A meta-analytic investigation of mechanisms of action and moderators of effectiveness. *Appetite, 97*, 16–28. https://doi.org/10.1016/j.appet.2015.11.013
- Enriquez-Geppert, S., Huster, R. J., Figge, C., & Herrmann, C. S. (2014). Self-regulation of frontal-midline theta facilitates memory updating and mental set shifting. *Frontiers in Behavioral Neuroscience, 8*, 420. https://doi.org/10.3389/fnbeh.2014.00420
- Kaplan, S. (1995). The restorative benefits of nature: Toward an integrative framework. *Journal of Environmental Psychology, 15*(3), 169–182. https://doi.org/10.1016/0272-4944(95)90001-2
- Dillon, D., & Cai, J. (2022). Virtual reality greenspaces: Does level of immersion affect directed attention restoration in VR environments? *J, 5*(3), 334–357. https://doi.org/10.3390/j5030023
- Kim, D. Y., Lee, J. H., et al. (2018). Development of an effective virtual environment in eliciting craving in adolescents and young adults with internet gaming disorder. *PLOS ONE, 13*(4), e0195677. https://doi.org/10.1371/journal.pone.0195677 **(verificar autores)**

**EEG + XR en lazo cerrado**
- Kosmyna, N., et al. (2021). Assessing internal and external attention in AR using brain computer interfaces: A pilot study. *IEEE BSN 2021* (MIT Media Lab, AttentivU) **(verificar)**
- Closed-loop attention restoration theory for virtual reality-based attentional engagement enhancement. (2020). *Sensors, 20*(8), 2208. https://doi.org/10.3390/s20082208
