# Graph Report - Project  (2026-10-21)

## Corpus Check
- 11 files · ~124,993 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 7 file(s) not represented in the graph (top: (none) 2, .bat 2, .log 2)

## Summary
- 229 nodes · 458 edges · 9 communities (6 shown, 3 thin omitted)
- Extraction: 94% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 25 edges (avg confidence: 0.81)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `54ae03ea`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Análisis del scope v2 y guía de cambios a la propuesta
- load_bids
- EEGViewer
- Demo_processing.py
- H1 trajectories figure (ds007537)
- Reporte H1 · EEG-SVRec (Fase C)
- h1_ds007537.py
- h1_svrec.py
- CLAUDE.md (instrucciones graphify)

## God Nodes (most connected - your core abstractions)
1. `EEGViewer` - 23 edges
2. `subject()` - 13 edges
3. `session()` - 12 edges
4. `main()` - 11 edges
5. `subject()` - 11 edges
6. `main()` - 11 edges
7. `process_all()` - 10 edges
8. `main()` - 10 edges
9. `H1 trajectories figure (ds007537)` - 10 edges
10. `download()` - 9 edges

## Surprising Connections (you probably didn't know these)
- `Montaje AURA de 8 canales (Fz FCz F3 F4 Pz O1 O2 Fp1)` --conceptually_related_to--> `Módulo AURA (hardware y periféricos)`  [INFERRED]
  Tests/Analisis_Scope_v2.md → README.md
- `Modelo de costo de oportunidad (Kurzban et al., 2013)` --conceptually_related_to--> `Cascada: interfaz de scrolling a conducta automática`  [INFERRED]
  Tests/Analisis_Scope_v2.md → Tests/Scope_Dopamine_Scrolling.pdf
- `Modelo de ego depletion (cuestionado por Hagger et al., 2016)` --conceptually_related_to--> `Cascada: interfaz de scrolling a conducta automática`  [INFERRED]
  Tests/Analisis_Scope_v2.md → Tests/Scope_Dopamine_Scrolling.pdf
- `Alfa posterior tónica (Pz/O1/O2)` --conceptually_related_to--> `Alfa posterior como inhibición funcional`  [INFERRED]
  Tests/Analisis_Scope_v2.md → Tests/Scope_Dopamine_Scrolling.pdf
- `Asimetría alfa frontal (FAA, exploratoria)` --conceptually_related_to--> `FAA como índice inferido de búsqueda de recompensa`  [INFERRED]
  Tests/Analisis_Scope_v2.md → Tests/Scope_Dopamine_Scrolling.pdf

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Biomarcadores tónicos y fásicos del scope v2** — tests_analisis_scope_v2_theta_tonico, tests_analisis_scope_v2_theta_fasico, tests_analisis_scope_v2_alfa_posterior [EXTRACTED 1.00]
- **Intervención JITAI guiada por estado neural** — tests_analisis_scope_v2_jitai, tests_analisis_scope_v2_h4, tests_analisis_scope_v2_alfa_posterior [INFERRED 0.75]
- **EEG spectral markers tracked under H1** — tests_ds007537_results_h1_trayectorias_theta_tonico_fz_fcz, tests_ds007537_results_h1_trayectorias_alfa_posterior_total, tests_ds007537_results_h1_trayectorias_theta_periodico_fz_fcz, tests_ds007537_results_h1_trayectorias_alfa_posterior_periodica, tests_ds007537_results_h1_trayectorias_exponente_aperiodico_posterior [INFERRED 0.75]
- **Cadena de evidencia de H1 en ds007537** — tests_ds007537_reporte_h1_ds007537_alfa_periodica, tests_ds007537_reporte_h1_ds007537_exponente_1f, tests_ds007537_reporte_h1_ds007537_desenganche_cortical, tests_ds007537_reporte_h1_ds007537_parpadeo_eeg [INFERRED 0.85]

## Communities (9 total, 3 thin omitted)

### Community 0 - "Análisis del scope v2 y guía de cambios a la propuesta"
Cohesion: 0.07
Nodes (30): README del proyecto MIRAI, Módulo AURA (hardware y periféricos), Demo_processing.py (visor y analizador de señales EEG), Análisis del scope v2 y guía de cambios a la propuesta, Alfa posterior tónica (Pz/O1/O2), Asimetría alfa frontal (FAA, exploratoria), Probe Go/NoGo para medir theta fásico, H4: intervención disparada por EEG vs por temporizador (+22 more)

### Community 3 - "Demo_processing.py"
Cohesion: 0.07
Nodes (17): alpha_channels(), band_filter(), band_powers(), bids_downloaded(), biomarker_summary(), cognitive_indices(), compute_psd(), draw_electrode_map() (+9 more)

### Community 4 - "H1 trajectories figure (ds007537)"
Cohesion: 0.24
Nodes (11): H1 trajectories figure (ds007537), Periodic posterior alpha (1/f-corrected, dB change), Posterior alpha (total power, dB change), Pupil diameter (mm change), Posterior aperiodic exponent (a.u. change), Game group (n=13), Short video group (n=12), Blink rate (EEG Fp1, per min change) (+3 more)

### Community 5 - "Reporte H1 · EEG-SVRec (Fase C)"
Cohesion: 0.20
Nodes (9): 1. Muestra, 2. Resultados, 3. Lectura frente a H1, 4. Implicaciones para MIRAI, 5. Limitaciones, A · Dentro de la sesión (pruebas primarias, Holm), B · Entre sesiones (exploratorio, confundido con el tipo de feed), C · Por video (exploratorio, 11 pruebas) (+1 more)

### Community 6 - "h1_ds007537.py"
Cohesion: 0.09
Nodes (25): phasic(), band_db(), clean(), detect_blinks(), epoch_psd(), et_window(), eyetrack(), iaf() (+17 more)

### Community 7 - "h1_svrec.py"
Cohesion: 0.08
Nodes (23): analyse(), epochs(), lapse_fraction(), main(), measures(), phasic_report(), plot(), plot_curve() (+15 more)

## Ambiguous Edges - Review These
- `Periodic theta Fz/FCz (1/f-corrected, dB change)` → `H1: smartphone use modulates tonic/activation markers over minutes of use`  [AMBIGUOUS]
  Tests/ds007537/results/h1_trayectorias.png · relation: rationale_for

## Knowledge Gaps
- **17 isolated node(s):** `1. Muestra`, `A · Dentro de la sesión (pruebas primarias, Holm)`, `B · Entre sesiones (exploratorio, confundido con el tipo de feed)`, `C · Por video (exploratorio, 11 pruebas)`, `3. Lectura frente a H1` (+12 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 73 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **3 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `Periodic theta Fz/FCz (1/f-corrected, dB change)` and `H1: smartphone use modulates tonic/activation markers over minutes of use`?**
  _Edge tagged AMBIGUOUS (relation: rationale_for) - confidence is low._
- **Why does `EEGViewer` connect `EEGViewer` to `Demo_processing.py`?**
  _High betweenness centrality (0.095) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `session()` (e.g. with `main()` and `download()`) actually correct?**
  _`session()` has 2 INFERRED edges - model-reasoned connections that need verification._
- **What connects `1. Muestra`, `A · Dentro de la sesión (pruebas primarias, Holm)`, `B · Entre sesiones (exploratorio, confundido con el tipo de feed)` to the rest of the system?**
  _17 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Análisis del scope v2 y guía de cambios a la propuesta` be split into smaller, more focused modules?**
  _Cohesion score 0.06951219512195123 - nodes in this community are weakly interconnected._
- **Why does `window_biomarkers()` connect `Demo_processing.py` to `h1_ds007537.py`?**
  _High betweenness centrality (0.016) - this node is a cross-community bridge._
- **Should `Demo_processing.py` be split into smaller, more focused modules?**
  _Cohesion score 0.0708245243128964 - nodes in this community are weakly interconnected._