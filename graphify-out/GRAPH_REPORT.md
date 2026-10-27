# Graph Report - Project  (2026-10-27)

## Corpus Check
- 15 files · ~101,232 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 7 file(s) not represented in the graph (top: (none) 2, .bat 2, .log 2)

## Summary
- 302 nodes · 519 edges · 13 communities (10 shown, 3 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 16 edges (avg confidence: 0.86)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `3c10f43f`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Análisis del scope v2 y guía de cambios a la propuesta
- 4. Pasos a seguir
- Reporte H1 · Validación en OpenNeuro ds007537
- Demo_processing.py
- EEGViewer
- load_eeg
- h1_ds007537.py
- h1_svrec.py
- 3. Explicación diapositiva por diapositiva
- ⚙️ 3. Especificación Técnica Paso a Paso
- Reporte H1 · EEG-SVRec (Fase C)
- CLAUDE.md (instrucciones graphify)

## God Nodes (most connected - your core abstractions)
1. `EEGViewer` - 23 edges
2. `3. Explicación diapositiva por diapositiva` - 15 edges
3. `subject()` - 13 edges
4. `Reporte H1 · Validación en OpenNeuro ds007537` - 13 edges
5. `session()` - 12 edges
6. `main()` - 11 edges
7. `subject()` - 11 edges
8. `main()` - 11 edges
9. `process_all()` - 10 edges
10. `main()` - 10 edges

## Surprising Connections (you probably didn't know these)
- `Modelo de costo de oportunidad (Kurzban et al., 2013)` --conceptually_related_to--> `Cascada: interfaz de scrolling a conducta automática`  [INFERRED]
  Tests/Analisis_Scope_v2.md → Tests/Scope_Dopamine_Scrolling.pdf
- `Modelo de ego depletion (cuestionado por Hagger et al., 2016)` --conceptually_related_to--> `Cascada: interfaz de scrolling a conducta automática`  [INFERRED]
  Tests/Analisis_Scope_v2.md → Tests/Scope_Dopamine_Scrolling.pdf
- `2. Modulación Automática de Canales` --references--> `load_eeg()`  [INFERRED]
  Tests/datasets workflow/EEG Dataset 9-10/Guia_Canales_y_Datasets.md → Tests/datasets workflow/EEG Dataset 9-10/Demo_processing.py
- `Montaje AURA de 8 canales (Fz FCz F3 F4 Pz O1 O2 Fp1)` --conceptually_related_to--> `Módulo AURA (hardware y periféricos)`  [INFERRED]
  Tests/Analisis_Scope_v2.md → README.md
- `Alfa posterior tónica (Pz/O1/O2)` --conceptually_related_to--> `Alfa posterior como inhibición funcional`  [INFERRED]
  Tests/Analisis_Scope_v2.md → Tests/Scope_Dopamine_Scrolling.pdf

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Biomarcadores tónicos y fásicos del scope v2** — tests_analisis_scope_v2_theta_tonico, tests_analisis_scope_v2_theta_fasico, tests_analisis_scope_v2_alfa_posterior [EXTRACTED 1.00]
- **Intervención JITAI guiada por estado neural** — tests_analisis_scope_v2_jitai, tests_analisis_scope_v2_h4, tests_analisis_scope_v2_alfa_posterior [INFERRED 0.75]

## Communities (13 total, 3 thin omitted)

### Community 0 - "Análisis del scope v2 y guía de cambios a la propuesta"
Cohesion: 0.07
Nodes (28): README del proyecto MIRAI, Módulo AURA (hardware y periféricos), Demo_processing.py (visor y analizador de señales EEG), Análisis del scope v2 y guía de cambios a la propuesta, Alfa posterior tónica (Pz/O1/O2), Asimetría alfa frontal (FAA, exploratoria), Probe Go/NoGo para medir theta fásico, H4: intervención disparada por EEG vs por temporizador (+20 more)

### Community 1 - "4. Pasos a seguir"
Cohesion: 0.17
Nodes (12): 1. Estado actual, 2. Narrativa de la presentación, 3.1 Separar las dos contribuciones, 3.2 Escenarios y qué hacer en cada uno, 3.3 Recomendaciones para blindar el proyecto, 3. ¿Qué pasa si los resultados son negativos?, 4. Pasos a seguir, Fase 1 · Cerrar la validación ✅ casi completa (+4 more)

### Community 2 - "Reporte H1 · Validación en OpenNeuro ds007537"
Cohesion: 0.08
Nodes (25): 10. Próximos pasos, 11. Archivos, 1. Resumen, 2. Hipótesis evaluada, 3. Dataset, 4.1 Preprocesado (por sujeto), 4.2 Medidas espectrales (por minuto), 4.3 Marcadores de activación (control de somnolencia) (+17 more)

### Community 3 - "Demo_processing.py"
Cohesion: 0.07
Nodes (17): alpha_channels(), band_filter(), band_powers(), bids_downloaded(), biomarker_summary(), cognitive_indices(), compute_psd(), draw_electrode_map() (+9 more)

### Community 5 - "load_eeg"
Cohesion: 0.14
Nodes (11): load_bids(), load_eeg(), 1. Canales Objetivo y su Función Neurocientífica, 2. Modulación Automática de Canales, 3. Representación Visual del Montaje 10-20 en la Interfaz, 4. Cómo Buscar y Limpiar Nuevos Datasets, A. Para los archivos actuales de Stroop (`raw_data/Stroop_Data`):, B. Para nuevos datasets limpios (6 canales o con encabezados): (+3 more)

### Community 6 - "h1_ds007537.py"
Cohesion: 0.09
Nodes (25): epochs(), phasic(), band_db(), clean(), detect_blinks(), epoch_psd(), et_window(), eyetrack() (+17 more)

### Community 7 - "h1_svrec.py"
Cohesion: 0.08
Nodes (23): analyse(), lapse_fraction(), main(), measures(), phasic_report(), plot(), plot_curve(), reaction_times() (+15 more)

### Community 8 - "3. Explicación diapositiva por diapositiva"
Cohesion: 0.09
Nodes (23): 0. La idea en 30 segundos (apréndela de memoria), 10 · System Pipeline, 11 · Robust to Negative Results — **la diapositiva más importante para defender el proyecto**, 12 · Gantt, 13 · Next Steps, 14 · References, 1. Conceptos clave (glosario para no confundirte), 1 · Portada — *Closed-Loop Neuroadaptive AR Platform for Dopamine Scrolling* (+15 more)

### Community 9 - "⚙️ 3. Especificación Técnica Paso a Paso"
Cohesion: 0.14
Nodes (13): 🏗️ 1. Arquitectura del Entorno de Simulación, 1. Fase de Calibración Basal ($t \le 90\text{ s}$), 2. Fase de Inferencia Continua ($t > 90\text{ s}$), 📅 2. Hoja de Ruta de Implementación para la Semana, ⚙️ 3. Especificación Técnica Paso a Paso, 📂 4. Estructura de Archivos para la Simulación, 🎯 5. Checklist de Verificación para el Fin de Semana, Paso 1 (Día 1) · Emulador de Streaming LSL (`mock_lsl_streamer.py`) (+5 more)

### Community 10 - "Reporte H1 · EEG-SVRec (Fase C)"
Cohesion: 0.20
Nodes (9): 1. Muestra, 2. Resultados, 3. Lectura frente a H1, 4. Implicaciones para MIRAI, 5. Limitaciones, A · Dentro de la sesión (pruebas primarias, Holm), B · Entre sesiones (exploratorio, confundido con el tipo de feed), C · Por video (exploratorio, 11 pruebas) (+1 more)

## Knowledge Gaps
- **88 isolated node(s):** `0. La idea en 30 segundos (apréndela de memoria)`, `1. Conceptos clave (glosario para no confundirte)`, `2. Qué pasó en esta sesión (para que no te confundas con versiones viejas)`, `1 · Portada — *Closed-Loop Neuroadaptive AR Platform for Dopamine Scrolling*`, `2 · Objectives` (+83 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 147 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **3 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `EEGViewer` connect `EEGViewer` to `Demo_processing.py`?**
  _High betweenness centrality (0.057) - this node is a cross-community bridge._
- **What connects `0. La idea en 30 segundos (apréndela de memoria)`, `1. Conceptos clave (glosario para no confundirte)`, `2. Qué pasó en esta sesión (para que no te confundas con versiones viejas)` to the rest of the system?**
  _88 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Análisis del scope v2 y guía de cambios a la propuesta` be split into smaller, more focused modules?**
  _Cohesion score 0.06612685560053981 - nodes in this community are weakly interconnected._
- **Why does `load_eeg()` connect `load_eeg` to `Demo_processing.py`, `EEGViewer`, `h1_ds007537.py`?**
  _High betweenness centrality (0.044) - this node is a cross-community bridge._
- **Should `Reporte H1 · Validación en OpenNeuro ds007537` be split into smaller, more focused modules?**
  _Cohesion score 0.07692307692307693 - nodes in this community are weakly interconnected._
- **Should `Demo_processing.py` be split into smaller, more focused modules?**
  _Cohesion score 0.06868686868686869 - nodes in this community are weakly interconnected._
- **Should `load_eeg` be split into smaller, more focused modules?**
  _Cohesion score 0.14285714285714285 - nodes in this community are weakly interconnected._