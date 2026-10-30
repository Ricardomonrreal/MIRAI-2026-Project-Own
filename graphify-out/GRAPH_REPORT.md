# Graph Report - Project  (2026-10-29)

## Corpus Check
- 30 files · ~129,381 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 10 file(s) not represented in the graph (top: (none) 2, .pptx 2, .bat 2)

## Summary
- 518 nodes · 929 edges · 29 communities (19 shown, 10 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 25 edges (avg confidence: 0.89)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `85c11795`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Plataforma Neuroadaptativa en Realidad Aumentada (AR) y Procesamiento de Señales EEG
- time
- Reporte H1 · Validación en OpenNeuro ds007537
- Demo_processing.py
- json
- load_eeg
- Rejector
- h1_svrec.py
- 3. Explicación diapositiva por diapositiva
- periodic
- Reporte H1 · EEG-SVRec (Fase C)
- CLAUDE.md
- 3. Contenido nuevo de la presentación (v2)
- numpy
- Configuración de la AURA para MIRAI 2026
- simulation/replay_offline.py
- Windower
- simulation_B/realtime_pipeline.py
- h1_ds007537.py
- blink_gain
- h1b_cao2019.py
- CausalFilter
- Rejector
- os
- Versión B — criterio de detección del Paso 3 precisado (29 oct 2026)

## God Nodes (most connected - your core abstractions)
1. `EEGViewer` - 23 edges
2. `main()` - 15 edges
3. `3. Explicación diapositiva por diapositiva` - 15 edges
4. `main()` - 14 edges
5. `subject()` - 13 edges
6. `Reporte H1 · Validación en OpenNeuro ds007537` - 13 edges
7. `session()` - 12 edges
8. `main()` - 11 edges
9. `subject()` - 11 edges
10. `main()` - 11 edges

## Surprising Connections (you probably didn't know these)
- `[x] Paso 1: Emulador de Hardware y Transmisión LSL (`mock_lsl_streamer.py`) — implementado 28 oct 2026` --references--> `download()`  [INFERRED]
  Protocolo_Simulacion_Pipeline.md → datasets workflow/EEG-SVRec/h1_svrec.py
- `3. Paso 1 — HECHO` --references--> `iaf()`  [INFERRED]
  HANDOFF_Claude_Code.md → datasets workflow/ds007537/h1_ds007537.py
- `[ ] Paso 5: Calibración Individual Congelada` --references--> `iaf()`  [INFERRED]
  Protocolo_Simulacion_Pipeline.md → datasets workflow/ds007537/h1_ds007537.py
- `1. Contexto del proyecto` --references--> `periodic()`  [INFERRED]
  HANDOFF_Claude_Code.md → datasets workflow/ds007537/h1_ds007537.py
- `2. Revisión del protocolo (problemas detectados, aún sin corregir en Pasos 2–7)` --references--> `periodic()`  [INFERRED]
  HANDOFF_Claude_Code.md → datasets workflow/ds007537/h1_ds007537.py

## Import Cycles
- None detected.

## Communities (29 total, 10 thin omitted)

### Community 0 - "Plataforma Neuroadaptativa en Realidad Aumentada (AR) y Procesamiento de Señales EEG"
Cohesion: 0.12
Nodes (15): 1. Clonar el repositorio, 2. Configurar el entorno virtual de Python, 3. Ejecutar los pipelines de análisis, 4. Lanzar el Visor Interactivo de Señales, 🛠️ Arquitectura Tecnológica y Lazo Cerrado, 👤 Autor e Institución, 📊 Avances y Validación Empírica en Datasets Públicos, Brecha Identificada en el Estado del Arte (+7 more)

### Community 1 - "time"
Cohesion: 0.08
Nodes (8): eeg_blinks(), equivalence(), et_blinks(), main(), score(), Features, on(), on()

### Community 2 - "Reporte H1 · Validación en OpenNeuro ds007537"
Cohesion: 0.08
Nodes (25): 10. Próximos pasos, 11. Archivos, 1. Resumen, 2. Hipótesis evaluada, 3. Dataset, 4.1 Preprocesado (por sujeto), 4.2 Medidas espectrales (por minuto), 4.3 Marcadores de activación (control de somnolencia) (+17 more)

### Community 3 - "Demo_processing.py"
Cohesion: 0.05
Nodes (20): alpha_channels(), band_filter(), band_powers(), bids_downloaded(), biomarker_summary(), cognitive_indices(), compute_psd(), draw_electrode_map() (+12 more)

### Community 4 - "json"
Cohesion: 0.25
Nodes (4): blink_report(), main(), on_window(), open_run()

### Community 5 - "load_eeg"
Cohesion: 0.14
Nodes (11): load_bids(), load_eeg(), 1. Canales Objetivo y su Función Neurocientífica, 2. Modulación Automática de Canales, 3. Representación Visual del Montaje 10-20 en la Interfaz, 4. Cómo Buscar y Limpiar Nuevos Datasets, A. Para los archivos actuales de Stroop (`raw_data/Stroop_Data`):, B. Para nuevos datasets limpios (6 canales o con encabezados): (+3 more)

### Community 7 - "h1_svrec.py"
Cohesion: 0.10
Nodes (16): across(), download(), epochs_psd(), holm(), load_session(), main(), measures(), per_video() (+8 more)

### Community 8 - "3. Explicación diapositiva por diapositiva"
Cohesion: 0.04
Nodes (43): 0. La idea en 30 segundos (apréndela de memoria), 10 · System Pipeline, 11 · Robust to Negative Results — **la diapositiva más importante para defender el proyecto**, 12 · Gantt, 13 · Next Steps, 14 · References, 1. Conceptos clave (glosario para no confundirte), 1 · Portada — *Closed-Loop Neuroadaptive AR Platform for Dopamine Scrolling* (+35 more)

### Community 9 - "periodic"
Cohesion: 0.09
Nodes (22): iaf(), periodic(), 1. Contexto del proyecto, 2. Revisión del protocolo (problemas detectados, aún sin corregir en Pasos 2–7), 3. Paso 1 — HECHO, 4. Análisis del CSV real de AURA (`eeg_data_20260122_123839.csv`) — PRELIMINAR, interrumpido, 5. Herramientas, Handoff: sesión Cowork → Claude Code (MIRAI 2026, 28 oct 2026) (+14 more)

### Community 10 - "Reporte H1 · EEG-SVRec (Fase C)"
Cohesion: 0.20
Nodes (9): 1. Muestra, 2. Resultados, 3. Lectura frente a H1, 4. Implicaciones para MIRAI, 5. Limitaciones, A · Dentro de la sesión (pruebas primarias, Holm), B · Entre sesiones (exploratorio, confundido con el tipo de feed), C · Por video (exploratorio, 11 pruebas) (+1 more)

### Community 12 - "3. Contenido nuevo de la presentación (v2)"
Cohesion: 0.06
Nodes (33): 0. Estado actual de `/Tests`, 1. Objetivo central 1: datasets EEG de scrolling / video corto, 2.1 Veredicto general, 2.2 Qué está bien sustentado ✅, 2.3 Qué hay que corregir ⚠️, 2.4 Implicaciones para `Demo_processing.py`, 2. Objetivo central 2: revisión de la teoría, 3. Contenido nuevo de la presentación (v2) (+25 more)

### Community 13 - "numpy"
Cohesion: 0.08
Nodes (27): channel_meta(), find_markers(), find_stream(), main(), add_blink(), inject(), load_aura_csv(), load_file() (+19 more)

### Community 14 - "Configuración de la AURA para MIRAI 2026"
Cohesion: 0.29
Nodes (6): 1. Ajustes de la interfaz (de arriba a abajo), 2. Verificación del stream (antes de cada sesión), 3. Prueba rápida de calidad: efecto Berger (2 min), 4. Lo que muestra el CSV de prueba (enero 2026, configuración desconocida), 5. Replay del CSV con el emulador, Configuración de la AURA para MIRAI 2026

### Community 15 - "simulation/replay_offline.py"
Cohesion: 0.13
Nodes (6): eeg_blinks(), equivalence(), et_blinks(), main(), score(), Features

### Community 17 - "simulation_B/realtime_pipeline.py"
Cohesion: 0.17
Nodes (5): blink_report(), main(), on_window(), open_run(), Windower

### Community 18 - "h1_ds007537.py"
Cohesion: 0.12
Nodes (18): band_db(), clean(), detect_blinks(), epoch_psd(), et_window(), eyetrack(), is_downloaded(), main() (+10 more)

### Community 20 - "blink_gain"
Cohesion: 0.25
Nodes (3): blink_gain(), CausalFilter, Qué cambia

### Community 22 - "h1b_cao2019.py"
Cohesion: 0.13
Nodes (12): analyse(), epochs(), lapse_fraction(), main(), measures(), phasic(), phasic_report(), plot() (+4 more)

### Community 28 - "Versión B — criterio de detección del Paso 3 precisado (29 oct 2026)"
Cohesion: 0.29
Nodes (6): Comparación A frente a B con el Paso 4 (29 oct), Hallazgo que motivó el ajuste, Prueba en vivo (29 oct, 10 min de uno en uno, tren de parpadeos de 30 s en el minuto 5), Resultados offline (600 s sintéticos, ~15 parpadeos/min), Sin veto EMG y ajuste 2–30 Hz (29 oct, tarde), Versión B — criterio de detección del Paso 3 precisado (29 oct 2026)

## Knowledge Gaps
- **130 isolated node(s):** `graphify`, `0. Estado actual de `/Tests``, `1. Objetivo central 1: datasets EEG de scrolling / video corto`, `2.1 Veredicto general`, `2.2 Qué está bien sustentado ✅` (+125 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 281 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **10 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `periodic()` connect `periodic` to `h1_ds007537.py`, `Demo_processing.py`, `numpy`?**
  _High betweenness centrality (0.033) - this node is a cross-community bridge._
- **What connects `graphify`, `0. Estado actual de `/Tests``, `1. Objetivo central 1: datasets EEG de scrolling / video corto` to the rest of the system?**
  _130 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Plataforma Neuroadaptativa en Realidad Aumentada (AR) y Procesamiento de Señales EEG` be split into smaller, more focused modules?**
  _Cohesion score 0.125 - nodes in this community are weakly interconnected._
- **Why does `load_eeg()` connect `load_eeg` to `Demo_processing.py`, `h1b_cao2019.py`?**
  _High betweenness centrality (0.031) - this node is a cross-community bridge._
- **Should `time` be split into smaller, more focused modules?**
  _Cohesion score 0.07765151515151515 - nodes in this community are weakly interconnected._
- **Should `Reporte H1 · Validación en OpenNeuro ds007537` be split into smaller, more focused modules?**
  _Cohesion score 0.07692307692307693 - nodes in this community are weakly interconnected._
- **Should `Demo_processing.py` be split into smaller, more focused modules?**
  _Cohesion score 0.054987212276214836 - nodes in this community are weakly interconnected._