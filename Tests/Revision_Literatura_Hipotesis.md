# MIRAI 2026 · ¿La literatura sostiene las hipótesis originales? (22 oct 2026)

Revisión dirigida a una pregunta concreta: **¿theta y alfa tónicos aumentan con el tiempo, el theta fásico disminuye, y eso aplica al scrolling?**
Contrasta la teoría original con los resultados de ds007537, EEG-SVRec y Cao 2019, y con la reformulación v3 de [Plan_Avances.md](Plan_Avances.md) §3.

> **Veredicto corto:** tu teoría original **sí está respaldada** por la literatura, y su núcleo (theta tónico ↑ mientras theta fásico ↓) tiene un estudio que lo muestra directamente (Arnau et al., 2021). Los datasets públicos no la refutan, porque **no cumplían sus condiciones** (pocos minutos, sin tarea exigente). La reformulación v3 ("la fatiga es un estado, no tiempo") **se pasó de la raya**: conviene conservar la hipótesis temporal original y añadir el acoplamiento de estado como hipótesis complementaria para la JITAI.

---

## 1. Theta y alfa tónicos aumentan con el tiempo en tarea → **respaldado**

| Estudio | Diseño | Hallazgo |
|---|---|---|
| **Tran et al. (2020)**, *Psychophysiology*, meta-análisis de 21 estudios | Tareas mentalmente fatigantes | **Theta ↑ grande (g = 1.03)** en sitios frontales, centrales y posteriores. **Alfa ↑ (g = 0.85)**, moderado en centrales y posteriores. Theta es el biomarcador robusto y alfa el de "segunda línea" por variabilidad individual. *Ojo:* 16 de 21 estudios eran conducción o vuelo |
| **Craig et al. (2012)**, *Psychophysiology* | 48 conductores, simulador hasta la fatiga | Theta y alfa 1/2 ↑ en toda la corteza |
| **Boksem, Meijman & Lorist (2005)**, *Cogn Brain Res* | Atención visual, **3 h sin pausa** | Theta y alfa baja ↑, junto con fatiga subjetiva, TR, omisiones y falsas alarmas |
| **Wascher et al. (2014)**, *Biol Psychol* | Tarea de estímulo-respuesta, ~4 h | **Alfa ↑ rápido y llega a su máximo en ~1 h.** **Theta frontal ↑ continuo** con el tiempo, interpretado como esfuerzo compensatorio |
| **Benwell et al. (2019)**, *NeuroImage* | Sesiones de ~1 h | **La potencia alfa ↑ y la frecuencia pico alfa ↓** con el tiempo en tarea |
| **Borghini et al. (2014)**, *Neurosci Biobehav Rev*, revisión | Pilotos y conductores | Carga alta: theta frontal ↑ y alfa ↓. **Paso a fatiga: theta, delta y alfa ↑.** Somnolencia: parpadeo ↑ |

**Conclusión:** la premisa "theta y alfa tónicos suben con el tiempo" es de lo mejor establecido en el campo. **Condiciones:** tareas exigentes, de **≥ 1 h** (alfa ~1 h, theta sigue subiendo después), con ojos abiertos.

## 2. Theta fásico ↓ con fatiga (control inhibitorio) → **respaldo moderado, literatura mixta**

| Estudio | Hallazgo | Dirección |
|---|---|---|
| **Arnau, Brümmer, Liegel & Wascher (2021)**, *Psychophysiology*, "Inverse effects of time-on-task in task-related and task-unrelated theta activity" | En los **intervalos entre ensayos, theta y alfa ↑**; el **theta ligado al estímulo ↓** (menor compromiso con la tarea) | ✅ **Es exactamente tu H3** |
| **Yu, Mückschel & Beste (2022)**, *Sci Rep* | Tarea de inhibición de respuesta modulada por memoria de trabajo: **theta evocado en giro frontal superior ↓**, desempeño ↓ y pupila fásica ↓. El acople theta–esfuerzo **desaparece** al final | ✅ |
| **Lorist, Boksem & Ridderinkhof (2005)**, *Cogn Brain Res* | Fatiga (2 h): monitoreo de errores y ajustes post-error comprometidos; menor actividad del cíngulo anterior | ✅ (el cíngulo anterior genera el theta frontal medial) |
| **Kato, Endo & Kizuka (2009)**, *Int J Psychophysiol* | Go/NoGo prolongado: **P3-NoGo ↓**, latencias de N2 y P3 ↑, amplitud de N2 sin cambio | ✅ parcial (ERP, no theta) |
| **Wascher et al. (2014)** | Theta frontal ↑ con el tiempo (compensación) | ⚠️ ambiguo: es sobre todo tónico |
| **Guo et al. (2018)** y otros, según cita secundaria | N2/P3 en Go/NoGo sin efecto de la fatiga; "los efectos sobre la inhibición son inconsistentes" | ❌ |

**Marco teórico:** Cavanagh & Frank (2014, *TiCS*) proponen que el theta frontal medial es la señal común de "se necesita control". Que caiga ante un NoGo bajo fatiga equivale a que el sistema deja de señalar o reclutar control.

**Conclusión:** H2 es defendible y H3 (disociación tónico ↑ / fásico ↓) tiene un **ancla directa en Arnau 2021**. Sigue siendo una pregunta abierta en la literatura de inhibición, lo cual es buena noticia para la originalidad: nadie lo ha probado durante scrolling.

## 3. Matices que explican tus resultados (y que la teoría ya predecía)

1. **Arnau (2021) advierte que el theta tónico ↑ podría ser un subproducto del alfa:** la frecuencia pico alfa baja con el tiempo (Benwell 2019) y "invade" la banda theta. Esto encaja con Cao: **theta total ~ TR sí, theta periódica no**. Parte de esa "theta" puede ser **alfa enlentecida o actividad aperiódica**.
   → **Acción:** usar bandas ajustadas a la IAF individual, reportar la frecuencia pico alfa como medida y separar periódico de aperiódico. No descartes theta: precísalo.
2. **Mucha "theta" de baja frecuencia es aperiódica.** Trabajos recientes con specparam/FOOOF en n-back y en theta post-estímulo muestran que cambios atribuidos a theta reflejan en buena parte el componente 1/f (PMC12611282, PMC13320869). Esto justifica tu control del exponente.
3. **La fatiga fluctúa minuto a minuto *además de* tener tendencia.** Makeig & Inlow (1993) muestran que errores y espectro EEG oscilan en ciclos de ~90 s y > 4 min, con relación estable dentro de cada sujeto. Esterman et al. (2013) describen estados "in the zone / out of the zone". **Las dos cosas son ciertas a la vez:** la tendencia temporal es el promedio de estados que fluctúan. Que Cao no muestre tendencia lineal en el TR **no anula** la hipótesis temporal; dice que el TR es ruidoso a escala de 5 min.
4. **Somnolencia ≠ fatiga en alfa.** Con ojos abiertos, alfa y theta ↑ con somnolencia. Con ojos cerrados, el alfa occipital ↓ al dormirse (Åkerstedt & Gillberg, 1990). Por eso el control con parpadeo/Fp1 sigue siendo obligatorio.
5. **La fatiga es reversible con motivación.** Hopstaken et al. (2015, *Psychophysiology*): tras 2 h, subir la recompensa restablece desempeño, P3 y pupila. El scrolling es muy recompensante, así que **puede mantener el enganche y ocultar la fatiga mientras el usuario está dentro del feed**. Esto justifica medir con una **sonda inhibitoria** (NoGo) y no solo con EEG pasivo.

## 4. ¿Aplica al scrolling? → **plausible, pero es el hueco de la literatura**

| Evidencia | Qué aporta |
|---|---|
| **Desmond & Hancock (2001); Saxby et al. (2013)**: fatiga **activa** (sobrecarga) vs. **pasiva** (tareas monótonas, poco estimulantes) | El scrolling encaja más con la **fatiga pasiva**: desenganche y baja inversión de esfuerzo, no sobrecarga. Predice alfa ↑ (desenganche) más que theta ↑ (esfuerzo) |
| **Fortes et al. (2019)** y **Gantois/Fortes et al. (2023)** (deportistas) | **30 min de redes sociales en el smartphone producen fatiga mental** (subjetiva) y empeoran la toma de decisiones. A los 15 min no hubo efecto. Solo conducta, sin EEG |
| **Marcora et al. (2009)**, *J Appl Physiol* | Un **documental emocionalmente neutro** es la condición control estándar *que no fatiga*. Respalda tu diseño scrolling vs. documental |
| **Nguyen et al. (2025)**, *Psychol Bull*, 71 estudios (N = 98 299) | El uso de video corto se asocia con peor atención (r = −.38) y **peor control inhibitorio (r = −.41)**. Correlacional y de rasgo |
| **Yan et al. (2024)**, *Front Hum Neurosci*, EEG, n = 48 | A mayor tendencia de adicción al video corto, **menor theta prefrontal durante el conflicto** (no en reposo). Correlacional y de rasgo |
| **Arnau et al. / revisión de mind-wandering** (42 estudios) | La divagación mental trae **alfa (y theta) ↑** con ojos abiertos. Respalda alfa_per ↑ = desenganche |
| Búsqueda de un estudio **agudo, pre/post, con EEG + Go/NoGo tras video corto** | **No existe** (lo más cercano son ERPs con *cues* de video o estudios de rasgo) → **es tu aporte original** |

## 5. Contraste con tus resultados

| Dataset | ¿Cumplía las condiciones de la teoría? | Lectura correcta |
|---|---|---|
| **ds007537** (10 min, pasivo) | ❌ Muy corto (la literatura pide ≥ 30–60 min) y sin tarea | El alfa_per ↑ es **coherente con la fatiga pasiva/desenganche**. Que theta no cambie es **lo esperado**, no una refutación |
| **EEG-SVRec** (sesiones ≤ 15–30 min, pasivo, sin sonda) | ❌ Corto, sin control, con degradación de señal | La tendencia temporal no es interpretable. El hallazgo por video (inmersión ↔ alfa_per ↓) **es compatible con la teoría del alfa como desenganche** |
| **Cao 2019** (60–90 min, tarea sostenida) | ✅ Es el único que se parece al paradigma clásico | Theta total ↔ TR (ρ = +0.50) y alfa_per ↔ TR **confirman la relación tónica**. El theta_per n.s. se explica con §3.1. La parte fásica sigue pendiente y es la prueba directa de H2/H3 |

## 6. Corrección a la reformulación v3

Lo que dije en `Plan_Avances.md` §3 ("dejar de definir la fatiga como minutos de scrolling") **fue una sobrecorrección**: generalicé a partir de datasets que no tenían ni la duración ni la tarea que la teoría exige. Propuesta revisada:

| | Propuesta revisada |
|---|---|
| **H1 (tónico, tiempo × condición)** — se **mantiene la original** | Theta frontal y alfa posterior (normalizados a la línea base, con bandas ajustadas a la IAF y exponente 1/f como covariable) **aumentan más con el tiempo de scrolling que con el documental**. Apoyo: Tran 2020, Wascher 2014, Benwell 2019, Fortes 2019 |
| **H1-estado (complementaria, para la JITAI)** | Dentro de la sesión, alfa_per y theta frontal **covarían con los momentos de peor desempeño o desenganche**. Apoyo: Makeig & Inlow 1993, Esterman 2013, Cao (tus datos), SVRec (tus datos) |
| **H2 (fásico)** — se mantiene | Tras el scrolling, el theta frontal medial evocado por NoGo ↓ y los errores de comisión ↑, frente al pre y al control. Apoyo: Arnau 2021, Yu 2022, Kato 2009 |
| **H3 (disociación)** — se mantiene y **gana peso** | Tónico ↑ y fásico ↓ ocurren a la vez. **Antecedente directo: Arnau et al. 2021** |
| **Predicción diferencial (nueva, opcional)** | Si el scrolling produce fatiga **pasiva** (Desmond & Hancock), se espera **alfa ↑ más fuerte que theta ↑**. Eso ya se vio en ds007537 y vale como hipótesis exploratoria |
| **H4** — sin cambio | La intervención por estado EEG supera a la intervención por temporizador |

**Implicación para el diseño:** 35 min queda en el límite. Fortes encontró fatiga a los 30 min (no a los 15), pero los efectos EEG tónicos más claros aparecen hacia ~1 h. Considera **45–60 min**, o mantener 35 min y declarar el tamaño de efecto esperado como pequeño.

**Mensaje para la diapositiva de avances:**
> Literature supports our core model: tonic theta/alpha rise with time-on-task (Tran 2020 meta-analysis, g ≈ 1.0) while task-evoked theta falls (Arnau 2021; Yu 2022). Public short-video datasets (10–15 min, passive) were too short to test it, yet they already showed the expected alpha disengagement signature. A positive-control dataset (Cao 2019, 60–90 min) reproduced the theta–performance coupling. No study has tested this dissociation during short-form video scrolling → our experiment fills that gap.

---

## 7. Referencias (verificar páginas/DOI antes de citar en la propuesta)

- Åkerstedt, T., & Gillberg, M. (1990). Subjective and objective sleepiness in the active individual. *International Journal of Neuroscience, 52*(1–2), 29–37.
- Arnau, S., Brümmer, T., Liegel, N., & Wascher, E. (2021). Inverse effects of time-on-task in task-related and task-unrelated theta activity. *Psychophysiology, 58*(6), e13805. https://doi.org/10.1111/psyp.13805
- Benwell, C. S. Y., et al. (2019). Frequency and power of human alpha oscillations drift systematically with time-on-task. *NeuroImage, 192*, 101–114. https://doi.org/10.1016/j.neuroimage.2019.02.067
- Boksem, M. A. S., Meijman, T. F., & Lorist, M. M. (2005). Effects of mental fatigue on attention: An ERP study. *Cognitive Brain Research, 25*(1), 107–116. https://doi.org/10.1016/j.cogbrainres.2005.04.011
- Borghini, G., Astolfi, L., Vecchiato, G., Mattia, D., & Babiloni, F. (2014). Measuring neurophysiological signals in aircraft pilots and car drivers for the assessment of mental workload, fatigue and drowsiness. *Neuroscience & Biobehavioral Reviews, 44*, 58–75. https://doi.org/10.1016/j.neubiorev.2012.10.003
- Cavanagh, J. F., & Frank, M. J. (2014). Frontal theta as a mechanism for cognitive control. *Trends in Cognitive Sciences, 18*(8), 414–421. https://doi.org/10.1016/j.tics.2014.04.012
- Craig, A., Tran, Y., Wijesuriya, N., & Nguyen, H. (2012). Regional brain wave activity changes associated with fatigue. *Psychophysiology, 49*(4), 574–582.
- Desmond, P. A., & Hancock, P. A. (2001). Active and passive fatigue states. In P. A. Hancock & P. A. Desmond (Eds.), *Stress, workload, and fatigue* (pp. 455–465). Erlbaum.
- Esterman, M., Noonan, S. K., Rosenberg, M., & DeGutis, J. (2013). In the zone or zoning out? Tracking behavioral and neural fluctuations during sustained attention. *Cerebral Cortex, 23*(11), 2712–2723.
- Fortes, L. S., et al. (2019). Effect of exposure time to smartphone apps on passing decision-making in male soccer athletes. *Psychology of Sport and Exercise, 44*, 35–41. **(verificar)**
- Hopstaken, J. F., van der Linden, D., Bakker, A. B., & Kompier, M. A. J. (2015). A multifaceted investigation of the link between mental fatigue and task disengagement. *Psychophysiology, 52*(3), 305–315.
- Kato, Y., Endo, H., & Kizuka, T. (2009). Mental fatigue and impaired response processes: Event-related brain potentials in a Go/NoGo task. *International Journal of Psychophysiology, 72*(2), 204–211.
- Lorist, M. M., Boksem, M. A. S., & Ridderinkhof, K. R. (2005). Impaired cognitive control and reduced cingulate activity during mental fatigue. *Cognitive Brain Research, 24*(2), 199–205.
- Makeig, S., & Inlow, M. (1993). Lapses in alertness: Coherence of fluctuations in performance and EEG spectrum. *Electroencephalography and Clinical Neurophysiology, 86*(1), 23–35.
- Marcora, S. M., Staiano, W., & Manning, V. (2009). Mental fatigue impairs physical performance in humans. *Journal of Applied Physiology, 106*(3), 857–864. https://doi.org/10.1152/japplphysiol.91324.2008
- Nguyen, L., et al. (2025). Feeds, feelings, and focus: A systematic review and meta-analysis examining the cognitive and mental health correlates of short-form video use. *Psychological Bulletin, 151*(9), 1125–1146. https://doi.org/10.1037/bul0000498
- Saxby, D. J., Matthews, G., Warm, J. S., Hitchcock, E. M., & Neubauer, C. (2013). Active and passive fatigue in simulated driving. *Journal of Experimental Psychology: Applied, 19*(4), 287–300. https://doi.org/10.1037/a0034386
- Tran, Y., Craig, A., Craig, R., Chai, R., & Nguyen, H. (2020). The influence of mental fatigue on brain activity: Evidence from a systematic review with meta-analyses. *Psychophysiology, 57*(5), e13554. https://doi.org/10.1111/psyp.13554
- Wascher, E., Rasch, B., Sänger, J., Hoffmann, S., Schneider, D., Rinkenauer, G., Heuer, H., & Gutberlet, I. (2014). Frontal theta activity reflects distinct aspects of mental fatigue. *Biological Psychology, 96*, 57–65. https://doi.org/10.1016/j.biopsycho.2013.11.010
- Yan, T.-T., Su, C.-H., Xue, W., Hu, Y.-Z., & Zhou, H. (2024). Mobile phone short video use negatively impacts attention functions: An EEG study. *Frontiers in Human Neuroscience, 18*. 
- Yu, S., Mückschel, M., & Beste, C. (2022). Superior frontal regions reflect the dynamics of task engagement and theta band-related control processes in time-on-task effects. *Scientific Reports, 12*, 846. https://doi.org/10.1038/s41598-022-04972-y

*Nota de método:* varios hallazgos (Wascher 2014, Kato 2009, Guo 2018) se tomaron de resúmenes o citas secundarias porque el texto completo es de pago. Lee el original antes de citar números exactos.
