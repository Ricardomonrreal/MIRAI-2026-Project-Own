# Graph Report - Project  (2026-10-28)

## Corpus Check
- 19 files · ~108,316 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 8 file(s) not represented in the graph (top: (none) 2, .pptx 2, .bat 2)

## Summary
- 348 nodes · 595 edges · 15 communities (13 shown, 2 thin omitted)
- Extraction: 98% EXTRACTED · 2% INFERRED · 0% AMBIGUOUS · INFERRED: 13 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `a2fa0097`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- README del proyecto MIRAI
- 4. Pasos a seguir
- Reporte H1 · Validación en OpenNeuro ds007537
- Demo_processing.py
- EEGViewer
- load_eeg
- h1_ds007537.py
- numpy
- 3. Explicación diapositiva por diapositiva
- 🎧 Adaptación a la diadema AURA
- Reporte H1 · EEG-SVRec (Fase C)
- CLAUDE.md (instrucciones graphify)
- 3. Contenido nuevo de la presentación (v2)
- mock_lsl_streamer.py
- Configuración de la AURA para MIRAI 2026

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
- `[x] Paso 1: Emulador de Hardware y Transmisión LSL (`mock_lsl_streamer.py`) — implementado 28 oct 2026` --references--> `iaf()`  [INFERRED]
  Tests/Protocolo_Simulacion_Pipeline.md → Tests/datasets workflow/ds007537/h1_ds007537.py
- `1. Contexto del proyecto` --references--> `periodic()`  [INFERRED]
  Tests/HANDOFF_Claude_Code.md → Tests/datasets workflow/ds007537/h1_ds007537.py
- `2. Revisión del protocolo (problemas detectados, aún sin corregir en Pasos 2–7)` --references--> `periodic()`  [INFERRED]
  Tests/HANDOFF_Claude_Code.md → Tests/datasets workflow/ds007537/h1_ds007537.py
- `3. Paso 1 — HECHO` --references--> `synthetic()`  [INFERRED]
  Tests/HANDOFF_Claude_Code.md → Tests/simulation/mock_lsl_streamer.py
- `[x] Paso 1: Emulador de Hardware y Transmisión LSL (`mock_lsl_streamer.py`) — implementado 28 oct 2026` --references--> `synthetic()`  [INFERRED]
  Tests/Protocolo_Simulacion_Pipeline.md → Tests/simulation/mock_lsl_streamer.py

## Import Cycles
- None detected.

## Communities (15 total, 2 thin omitted)

### Community 0 - "README del proyecto MIRAI"
Cohesion: 0.67
Nodes (3): README del proyecto MIRAI, Módulo AURA (hardware y periféricos), Demo_processing.py (visor y analizador de señales EEG)

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
Nodes (25): band_db(), clean(), detect_blinks(), epoch_psd(), et_window(), iaf(), is_downloaded(), main() (+17 more)

### Community 7 - "numpy"
Cohesion: 0.08
Nodes (29): analyse(), epochs(), lapse_fraction(), main(), measures(), phasic(), phasic_report(), plot() (+21 more)

### Community 8 - "3. Explicación diapositiva por diapositiva"
Cohesion: 0.06
Nodes (31): 0. La idea en 30 segundos (apréndela de memoria), 10 · System Pipeline, 11 · Robust to Negative Results — **la diapositiva más importante para defender el proyecto**, 12 · Gantt, 13 · Next Steps, 14 · References, 1. Conceptos clave (glosario para no confundirte), 1 · Portada — *Closed-Loop Neuroadaptive AR Platform for Dopamine Scrolling* (+23 more)

### Community 9 - "🎧 Adaptación a la diadema AURA"
Cohesion: 0.15
Nodes (12): 🏗️ 1. Arquitectura del Lazo Cerrado Simulado, 📋 2. Pasos de Implementación y Validación Técnica, 📁 3. Estructura de Código a Implementar, 🎧 Adaptación a la diadema AURA, [ ] Paso 2: Búfer Circular Continuo y Filtrado Causal (`realtime_pipeline.py`), [ ] Paso 3: Veto de Artefactos Oculares en $Fp1$, [ ] Paso 4: Descomposición Espectral y Extracción con `specparam`, [ ] Paso 5: Calibración Individual Congelada (`StandardScaler`) (+4 more)

### Community 10 - "Reporte H1 · EEG-SVRec (Fase C)"
Cohesion: 0.20
Nodes (9): 1. Muestra, 2. Resultados, 3. Lectura frente a H1, 4. Implicaciones para MIRAI, 5. Limitaciones, A · Dentro de la sesión (pruebas primarias, Holm), B · Entre sesiones (exploratorio, confundido con el tipo de feed), C · Por video (exploratorio, 11 pruebas) (+1 more)

### Community 12 - "3. Contenido nuevo de la presentación (v2)"
Cohesion: 0.06
Nodes (33): 0. Estado actual de `/Tests`, 1. Objetivo central 1: datasets EEG de scrolling / video corto, 2.1 Veredicto general, 2.2 Qué está bien sustentado ✅, 2.3 Qué hay que corregir ⚠️, 2.4 Implicaciones para `Demo_processing.py`, 2. Objetivo central 2: revisión de la teoría, 3. Contenido nuevo de la presentación (v2) (+25 more)

### Community 13 - "mock_lsl_streamer.py"
Cohesion: 0.15
Nodes (11): channel_meta(), main(), add_blink(), inject(), load_aura_csv(), load_file(), main(), make_outlet() (+3 more)

### Community 14 - "Configuración de la AURA para MIRAI 2026"
Cohesion: 0.29
Nodes (6): 1. Ajustes de la interfaz (de arriba a abajo), 2. Verificación del stream (antes de cada sesión), 3. Prueba rápida de calidad: efecto Berger (2 min), 4. Lo que muestra el CSV de prueba (enero 2026, configuración desconocida), 5. Replay del CSV con el emulador, Configuración de la AURA para MIRAI 2026

## Knowledge Gaps
- **117 isolated node(s):** `0. Estado actual de `/Tests``, `1. Objetivo central 1: datasets EEG de scrolling / video corto`, `2.1 Veredicto general`, `2.2 Qué está bien sustentado ✅`, `2.3 Qué hay que corregir ⚠️` (+112 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 182 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **2 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `EEGViewer` connect `EEGViewer` to `Demo_processing.py`?**
  _High betweenness centrality (0.053) - this node is a cross-community bridge._
- **What connects `0. Estado actual de `/Tests``, `1. Objetivo central 1: datasets EEG de scrolling / video corto`, `2.1 Veredicto general` to the rest of the system?**
  _117 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Reporte H1 · Validación en OpenNeuro ds007537` be split into smaller, more focused modules?**
  _Cohesion score 0.07692307692307693 - nodes in this community are weakly interconnected._
- **Why does `[x] Paso 1: Emulador de Hardware y Transmisión LSL (`mock_lsl_streamer.py`) — implementado 28 oct 2026` connect `🎧 Adaptación a la diadema AURA` to `mock_lsl_streamer.py`, `h1_ds007537.py`?**
  _High betweenness centrality (0.041) - this node is a cross-community bridge._
- **Should `Demo_processing.py` be split into smaller, more focused modules?**
  _Cohesion score 0.06666666666666667 - nodes in this community are weakly interconnected._
- **Why does `load_eeg()` connect `load_eeg` to `Demo_processing.py`, `EEGViewer`, `numpy`?**
  _High betweenness centrality (0.041) - this node is a cross-community bridge._
- **Should `load_eeg` be split into smaller, more focused modules?**
  _Cohesion score 0.14285714285714285 - nodes in this community are weakly interconnected._