# Graph Report - Project  (2026-11-26)

## Corpus Check
- 98 files · ~396,762 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 38 file(s) not represented in the graph (top: .log 29, .bat 3, (none) 2)

## Summary
- 1327 nodes · 2300 edges · 131 communities (74 shown, 57 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 134 edges (avg confidence: 0.86)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `5101f673`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- EEGViewer
- 3. Contenido nuevo de la presentación (v2)
- Análisis de las sesiones P01–P09 (19, 20, 25 y 26 nov 2026)
- calibration.py
- H1 ds007537 trajectories figure (tonic evolution and arousal markers, mean +/- SE)
- simulation_B/replay_offline.py
- pandas
- Reporte H1 · Validación en OpenNeuro ds007537
- main
- 3. Explicación diapositiva por diapositiva
- h1_svrec.py
- 2. Biomarcadores
- Análisis de las sesiones P01–P06 (19 y 20 nov 2026)
- Análisis de las sesiones P01–P07 (19, 20 y 25 nov 2026)
- SessionApp
- simulation_B/realtime_pipeline.py
- sys
- gonogo_db.py
- get
- README: Plataforma Neuroadaptativa AR y procesamiento EEG
- Protocolo_Simulacion_Pipeline.md
- VERSION_B.md
- Closed-loop neuroadaptive VR platform (v1 general objective)
- realtime_pipeline.py
- Resumen de sesión MIRAI 2026 (19-21 oct)
- Project Proposal v1: Closed-Loop Neuroadaptive VR Platform for Dopamine Scrolling
- BlinkCounter
- Session
- Plataforma Neuroadaptativa en Realidad Aumentada (AR) y Procesamiento de Señales EEG
- JITAI Intervention Ladder (Cue / Friction / Pause)
- Reporte H1 ds007537
- Reporte_H1_SVRec.md
- Plan de implementación · App móvil Go/NoGo + base de datos de sesiones
- Análisis del Scope v2 y guía de cambios
- 4. Pasos a seguir
- Proposal presentation v2 structure (AR title)
- Scope Dopamine Scrolling: biomarcadores de fatiga cognitiva y control inhibitorio
- Cortical disengagement (functional inhibition of visual cortex)
- Phasic frontal-midline theta (NoGo-evoked, Fz/FCz)
- Guía de Uso: Nuevos Canales, Modulación Automática y Datasets EEG
- Reporte H1 · EEG-SVRec (Fase C)
- Jitai
- Offline equivalence vs h1_por_minuto.csv (ds007537 sub-01): alpha_per r=0.938 PASA
- Script — 2nd Progress Report (7 min)
- Cao 2019 Phasic Theta Time Course (fast vs slow trials)
- cao_reporte.txt (Cao 2019 positive control output)
- CausalFilter
- sesion_aura_web.py
- Windower
- requirements.txt (simulation_B)
- CLAUDE.md
- simulation/realtime_pipeline.py
- OfflineInlet
- Progress Report: Closed-Loop Neuroadaptive AR Platform for Scrolling
- ds007537 Dataset (n=27, 10 min smartphone)
- OfflineMarkers
- Diagrama_Pipeline.md
- P07 (25 nov 2026): por qué solo 65.8 % de ventanas válidas
- Configuración de la AURA para MIRAI 2026
- h1b_cao2019.py
- Versión B — criterio de detección del Paso 3 precisado (29 oct 2026)
- MIRAI 2026 · Guía de estudio para la exposición de avances (22 oct 2026)
- gng
- MIRAI 2026 · ¿La literatura sostiene las hipótesis originales? (22 oct 2026)
- numpy
- replay_sesion.py
- os
- jitai.py
- simulation/replay_offline.py
- pylsl
- semaforo_canales.py
- Demo_processing.py
- tendencias.py
- window_biomarkers
- .refresh_biomarkers
- simulation_B/spectral_features.py
- json
- resumen
- CausalFilter
- Corrección de parpadeos antes del CAR — replay offline (26 nov 2026)
- Guia_Canales_y_Datasets.md
- EogRegression
- check_token
- P09 (26 nov 16:01): primera sesión en vivo con la corrección EOG
- preprocess
- Reporte rápido · 26 nov 2026 · n = 9
- replay_fp1.py
- init

## God Nodes (most connected - your core abstractions)
1. `Session` - 33 edges
2. `Progress Report: Closed-Loop Neuroadaptive AR Platform for Scrolling` - 24 edges
3. `Análisis del Scope v2 y guía de cambios` - 24 edges
4. `EEGViewer` - 23 edges
5. `Project Proposal v1: Closed-Loop Neuroadaptive VR Platform for Dopamine Scrolling` - 19 edges
6. `SessionApp` - 18 edges
7. `README: Plataforma Neuroadaptativa AR y procesamiento EEG` - 18 edges
8. `main()` - 17 edges
9. `Script — 2nd Progress Report (7 min)` - 15 edges
10. `Reporte H1 ds007537` - 15 edges

## Surprising Connections (you probably didn't know these)
- `Closed-loop AR JITAI neuroadaptive platform` --semantically_similar_to--> `Closed-loop neuroadaptive VR platform (v1 general objective)`  [INFERRED] [semantically similar]
  README.md → Documentación/Project Proposal MIRAI Ricardo_Monrreal (1).pdf
- `Project Proposal MIRAI v4 Deck (14 slides)` --semantically_similar_to--> `Progress Report: Closed-Loop Neuroadaptive AR Platform for Scrolling`  [INFERRED] [semantically similar]
  Tests/Guia_Exposicion.md → Tests/Progress Report MIRAI Ricardo_Monrreal.pdf
- `Tonic up / phasic down theta dissociation with time-on-task` --semantically_similar_to--> `Tonic theta baseline rise vs loss of phasic FM-theta bursts`  [INFERRED] [semantically similar]
  Documentación/Analisis_Scope_v2.md → Documentación/Scope_Dopamine_Scrolling.pdf
- `Tonic posterior alpha (8-13 Hz, Pz/O1/O2)` --semantically_similar_to--> `Posterior alpha rises with accumulated fatigue (O1, O2, Pz)`  [INFERRED] [semantically similar]
  Documentación/Analisis_Scope_v2.md → Documentación/Scope_Dopamine_Scrolling.pdf
- `Gantt Plan W1-W11 (Phases 1-4)` --conceptually_related_to--> `Own Experiment (scrolling vs documentary, 45-60 min, Go/NoGo)`  [INFERRED]
  Tests/Progress Report MIRAI Ricardo_Monrreal.pdf → Tests/Plan_Avances.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **JITAI intervention mechanisms per detected state** — documentaci_n_analisis_scope_v2_intervention_ladder, documentaci_n_analisis_scope_v2_attention_restoration, documentaci_n_analisis_scope_v2_friction_nudge, documentaci_n_analisis_scope_v2_inhibitory_control_training, documentaci_n_analisis_scope_v2_jitai [EXTRACTED 1.00]
- **MIRAI Time-Based Hypothesis Set H1-H4** — tests_plan_avances_h1, tests_plan_avances_h1_state, tests_plan_avances_h2, tests_plan_avances_h3, tests_plan_avances_h4 [EXTRACTED 1.00]
- **Public-dataset H1 validation (ds007537, EEG-SVRec, Cao 2019)** — documentaci_n_resumen_sesion_21_10_ds007537_h1_results, readme_svrec_result, readme_cao2019_result, documentaci_n_analisis_scope_v2_ds007537, documentaci_n_analisis_scope_v2_eeg_svrec, documentaci_n_analisis_scope_v2_cao_2019 [EXTRACTED 1.00]
- **Simulated Closed-Loop Pipeline (emulator -> pipeline -> features -> JITAI -> launcher)** — tests_protocolo_simulacion_pipeline_mock_lsl_streamer, tests_protocolo_simulacion_pipeline_realtime_pipeline, tests_protocolo_simulacion_pipeline_spectral_features, tests_protocolo_simulacion_pipeline_jitai_decision, tests_protocolo_simulacion_pipeline_run_simulation [EXTRACTED 1.00]
- **Tonic/phasic hypothesis framework H1-H3** — documentaci_n_analisis_scope_v2_h1, documentaci_n_analisis_scope_v2_h2, documentaci_n_analisis_scope_v2_h3, documentaci_n_analisis_scope_v2_tonic_theta, documentaci_n_analisis_scope_v2_posterior_alpha, documentaci_n_analisis_scope_v2_phasic_fm_theta [EXTRACTED 1.00]
- **Literature Supporting Tonic Theta/Alpha Rise with Time-on-Task** — tests_revision_literatura_hipotesis_tran2020, tests_revision_literatura_hipotesis_craig2012, tests_revision_literatura_hipotesis_boksem2005, tests_revision_literatura_hipotesis_wascher2014, tests_revision_literatura_hipotesis_benwell2019, tests_revision_literatura_hipotesis_borghini2014 [EXTRACTED 1.00]
- **Version B Step 5 frozen calibration flow** — tests_simulation_b_version_b_quality_check, tests_simulation_b_version_b_aura_baseline_phases, tests_simulation_b_version_b_ewma_smoothing, tests_simulation_b_version_b_sigma_z_correction, tests_simulation_b_version_b_rms_z_criterion [EXTRACTED 1.00]
- **Artifact controls: EMG and blinks vs total alpha** — tests_datasets_workflow_eeg_svrec_results_svrec_trayectorias_emg_control, tests_datasets_workflow_eeg_svrec_results_svrec_trayectorias_blink_rate, tests_datasets_workflow_eeg_svrec_results_svrec_trayectorias_total_alpha [INFERRED 0.65]
- **Early-peak fatigue markers (RT, lapses, tonic theta)** — tests_datasets_workflow_cao2019_results_cao_trayectorias_log_rt, tests_datasets_workflow_cao2019_results_cao_trayectorias_lapse_fraction, tests_datasets_workflow_eeg_svrec_results_svrec_trayectorias_tonic_theta [INFERRED 0.75]
- **Non-EEG and aperiodic arousal markers** — tests_datasets_workflow_ds007537_results_h1_trayectorias_blink_rate, tests_datasets_workflow_ds007537_results_h1_trayectorias_pupil_diameter, tests_datasets_workflow_eeg_svrec_results_svrec_trayectorias_aperiodic_exponent [INFERRED 0.75]
- **H1b frontal theta validation across ds007537, EEG-SVRec and Cao 2019** — tests_datasets_workflow_ds007537_reporte_h1_ds007537_h1b_frontal_theta, tests_datasets_workflow_eeg_svrec_reporte_h1_svrec_within_session_slopes, tests_datasets_workflow_cao2019_results_cao_reporte_h1b_positive_control, tests_datasets_workflow_cao2019_results_cao_reporte_theta_per_primary [INFERRED 0.85]
- **Periodic alpha as disengagement marker across datasets** — tests_datasets_workflow_ds007537_reporte_h1_ds007537_periodic_alpha, tests_datasets_workflow_ds007537_reporte_h1_ds007537_cortical_disengagement, tests_datasets_workflow_eeg_svrec_reporte_h1_svrec_per_video_alpha_engagement, tests_datasets_workflow_eeg_svrec_reporte_h1_svrec_h1a_reformulation, tests_datasets_workflow_eeg_svrec_reporte_h1_svrec_jitai_trigger [INFERRED 0.85]
- **Tonic theta up, phasic theta preserved under fatigue** — tests_datasets_workflow_cao2019_results_cao_fasico_curso_phasic_theta, tests_datasets_workflow_cao2019_results_cao_fasico_curso_tonic_theta, tests_datasets_workflow_cao2019_results_cao_fasico_curso_fast_vs_slow_trials, tests_datasets_workflow_cao2019_results_cao_fasico_curso_baseline_normalization_artifact [INFERRED 0.85]
- **Spectral parametrization: periodic alpha, periodic theta, aperiodic exponent** — tests_datasets_workflow_eeg_svrec_results_svrec_trayectorias_periodic_alpha, tests_datasets_workflow_eeg_svrec_results_svrec_trayectorias_periodic_theta, tests_datasets_workflow_eeg_svrec_results_svrec_trayectorias_aperiodic_exponent [INFERRED 0.85]

## Communities (131 total, 57 thin omitted)

### Community 0 - "EEGViewer"
Cohesion: 0.20
Nodes (3): EEGViewer, make_cmd(), on_window()

### Community 1 - "3. Contenido nuevo de la presentación (v2)"
Cohesion: 0.06
Nodes (33): 0. Estado actual de `/Tests`, 1. Objetivo central 1: datasets EEG de scrolling / video corto, 2.1 Veredicto general, 2.2 Qué está bien sustentado ✅, 2.3 Qué hay que corregir ⚠️, 2.4 Implicaciones para `Demo_processing.py`, 2. Objetivo central 2: revisión de la teoría, 3. Contenido nuevo de la presentación (v2) (+25 more)

### Community 2 - "Análisis de las sesiones P01–P09 (19, 20, 25 y 26 nov 2026)"
Cohesion: 0.14
Nodes (13): 1. Calidad de cada sesión, 2. Biomarcadores por bloque, 3. Hipótesis, 4. Parpadeos (nuevo), 5. Resumen de hipótesis, 6. Figuras, 7. Qué conviene revisar para las próximas sesiones, Análisis de las sesiones P01–P09 (19, 20, 25 y 26 nov 2026) (+5 more)

### Community 3 - "calibration.py"
Cohesion: 0.05
Nodes (26): iaf(), periodic(), 1. Contexto del proyecto, 2. Revisión del protocolo (problemas detectados, aún sin corregir en Pasos 2–7), 3. Paso 1 — HECHO, 4. Análisis del CSV real de AURA (`eeg_data_20260122_123839.csv`) — PRELIMINAR, interrumpido, 5. Herramientas, Handoff: sesión Cowork → Claude Code (MIRAI 2026, 28 oct 2026) (+18 more)

### Community 4 - "H1 ds007537 trajectories figure (tonic evolution and arousal markers, mean +/- SE)"
Cohesion: 0.13
Nodes (26): Cao 2019 sustained driving EEG dataset, H1b Cao 2019 Trajectories Figure (sustained driving, mean +- SE), H1b (inhibitory control / fatigue hypothesis), Lapse fraction (uncorrected drift time), log10 reaction time (behavioral fatigue), Periodic posterior alpha Pz/Oz/O1/O2, H1 ds007537 trajectories figure (tonic evolution and arousal markers, mean +/- SE), Blink rate (EEG Fp1 and eye-tracker) (+18 more)

### Community 5 - "simulation_B/replay_offline.py"
Cohesion: 0.17
Nodes (5): eeg_blinks(), equivalence(), et_blinks(), main(), score()

### Community 6 - "pandas"
Cohesion: 0.14
Nodes (18): band_db(), clean(), detect_blinks(), epoch_psd(), et_window(), eyetrack(), is_downloaded(), main() (+10 more)

### Community 7 - "Reporte H1 · Validación en OpenNeuro ds007537"
Cohesion: 0.08
Nodes (25): 10. Próximos pasos, 11. Archivos, 1. Resumen, 2. Hipótesis evaluada, 3. Dataset, 4.1 Preprocesado (por sujeto), 4.2 Medidas espectrales (por minuto), 4.3 Marcadores de activación (control de somnolencia) (+17 more)

### Community 8 - "main"
Cohesion: 0.18
Nodes (7): blink_match(), main(), emit_jitai(), on_window(), open_run(), Rejector, write_report_md()

### Community 9 - "3. Explicación diapositiva por diapositiva"
Cohesion: 0.13
Nodes (15): 10 · System Pipeline, 11 · Robust to Negative Results — **la diapositiva más importante para defender el proyecto**, 12 · Gantt, 13 · Next Steps, 14 · References, 1 · Portada — *Closed-Loop Neuroadaptive AR Platform for Dopamine Scrolling*, 2 · Objectives, 3. Explicación diapositiva por diapositiva (+7 more)

### Community 10 - "h1_svrec.py"
Cohesion: 0.11
Nodes (14): report(), across(), epochs_psd(), holm(), load_session(), main(), measures(), per_video() (+6 more)

### Community 11 - "2. Biomarcadores"
Cohesion: 0.11
Nodes (17): 1. Cómo se hicieron las gráficas, 2.1 θ periódica frontal (H1b) — `tend_theta.png`, 2.2 α periódica posterior (H1a) — `tend_alpha.png`, 2.3 Exponente aperiódico χ — `tend_chi_frontal.png`, `tend_chi_posterior.png`, 2.4 EMG (control de calidad) — `tend_emg.png`, 2.5 Ráfagas de ~4 Hz comunes a todos los canales (nuevo) — `tend_rafagas_4hz.png`, 2.6 Go/NoGo y θ evocada (H2/H3) — `tend_gonogo.png`, 2. Biomarcadores (+9 more)

### Community 12 - "Análisis de las sesiones P01–P06 (19 y 20 nov 2026)"
Cohesion: 0.15
Nodes (12): 1. Calidad de cada sesión, 2. Biomarcadores por bloque, 3. Hipótesis, 4. Resumen de hipótesis, 5. Figuras, 6. Qué conviene revisar para las próximas sesiones, Análisis de las sesiones P01–P06 (19 y 20 nov 2026), En pocas palabras (+4 more)

### Community 13 - "Análisis de las sesiones P01–P07 (19, 20 y 25 nov 2026)"
Cohesion: 0.15
Nodes (12): 1. Calidad de cada sesión, 2. Biomarcadores por bloque, 3. Hipótesis, 4. Resumen de hipótesis, 5. Figuras, 6. Qué conviene revisar para las próximas sesiones, Análisis de las sesiones P01–P07 (19, 20 y 25 nov 2026), En pocas palabras (+4 more)

### Community 15 - "simulation_B/realtime_pipeline.py"
Cohesion: 0.14
Nodes (3): blink_blocks(), blink_report(), mem_mb()

### Community 16 - "sys"
Cohesion: 0.16
Nodes (10): add_blink(), inject(), load_aura_csv(), load_file(), load_source(), main(), make_outlet(), montage_1005() (+2 more)

### Community 17 - "gonogo_db.py"
Cohesion: 0.13
Nodes (8): 4. Base de datos, bloque(), conn(), ensayos(), run_dir(), secuencia(), sesion(), sync()

### Community 18 - "get"
Cohesion: 0.12
Nodes (9): estado(), eventos(), gng_app(), gng_eventos(), gng_registros(), gng_resumen(), index(), reporte_ver() (+1 more)

### Community 19 - "README: Plataforma Neuroadaptativa AR y procesamiento EEG"
Cohesion: 0.16
Nodes (16): Arnau et al. (2021) inverse time-on-task effects on theta, Cao et al. (2019) sustained-attention driving EEG dataset (Figshare 6427334), EEG-SVRec dataset (Zhang et al., SIGIR 2024), Tonic up / phasic down theta dissociation with time-on-task, Yu, Mückschel & Beste (2022) time-on-task theta, Pending: EEG-SVRec pilot, Cao 2019 positive control, pre-registration, own experiment, Real-time proof of concept via eyes-closed alpha (Berger effect), Cao 2019 positive control: tonic theta ~ log RT (rho=+0.50), phasic theta preserved (+8 more)

### Community 20 - "Protocolo_Simulacion_Pipeline.md"
Cohesion: 0.18
Nodes (14): AURA Channel Order Fp1,F3,Fz,F4,Cz,Pz,O1,O2, AURA EEG Headset (software v1.2.x), Aura.exe LSL Streams (AURA, AURA_Filtered, AURA_Power), AURA Test CSV eeg_data_20260122_123839, CSV 50 Hz Effective Sampling, LSL Stream Out Setting, MarkItDown (PDF/Office to Markdown), VRehab.py (StandardScaler + LogisticRegression, reads AURA_Power) (+6 more)

### Community 21 - "VERSION_B.md"
Cohesion: 0.16
Nodes (10): AURA baseline phases (eyes open mu/sigma, eyes closed IAF + Berger), Emulator markers blink:<amplitude uV>, blink_gain() filter peak-to-peak gain (~1.11), blink_report(), EWMA smoothing (tau theta 60 s, tau alpha 5 s), Grazing-blink segments raise theta_per ~0.05-0.08 dB (negligible), Level 1 detection with Z_alpha (tuned in Step 6), Calibration quality check (first 10 s window, ROI empty stops session) (+2 more)

### Community 22 - "Closed-loop neuroadaptive VR platform (v1 general objective)"
Cohesion: 0.15
Nodes (16): Attention Restoration Theory restorative micro-break, Enriquez-Geppert et al. (2014) FM-theta neurofeedback, Inhibitory control training + FM-theta neurofeedback (VR Scroll-NoGo), Closed-loop intervention ladder (levels 0-3, refractory 5 min), Just-In-Time Adaptive Intervention (JITAI; Nahum-Shani 2018), Jones et al. (2016) inhibitory control training meta-analysis, Kim et al. (2018) VR craving in internet gaming disorder, Nahum-Shani et al. (2018) JITAI design principles (+8 more)

### Community 23 - "realtime_pipeline.py"
Cohesion: 0.13
Nodes (14): Berger Effect Quality Test (EO/EC, >=3 dB O1/O2), Eyes-Closed Alpha Loop Demo, Causal Stateful Filter (sosfilt with zi), Circular Buffer (6 s window, 1 s hop), find_stream() Source Identification, Frozen Individual Calibration (EO mu/sigma, EC IAF), IAF-Relative Bands (theta IAF-6..IAF-2, alpha IAF+-2), Latency Targets (processing <500 ms, total to AR <2 s) (+6 more)

### Community 24 - "Resumen de sesión MIRAI 2026 (19-21 oct)"
Cohesion: 0.21
Nodes (16): Drowsiness control with KSS and time of day, OpenNeuro ds007537 (Mishra, Gandhi & Gandhi 2026) smartphone EEG dataset, H1 tonic fatigue hypothesis, Jensen & Mazaheri (2010) alpha gating by inhibition, Tonic posterior alpha (8-13 Hz, Pz/O1/O2), Tonic frontal theta (4-8 Hz, Fz) fatigue marker, Tran et al. (2020) mental fatigue meta-analysis, Wascher et al. (2014) frontal theta and mental fatigue (+8 more)

### Community 25 - "Project Proposal v1: Closed-Loop Neuroadaptive VR Platform for Dopamine Scrolling"
Cohesion: 0.15
Nodes (14): 12-week Gantt (F1-F8), Sharpe & Spooner (2025) Dopamine-scrolling public health, Ahmed (2019) Gen Z smartphone and social media survey, Four-phase development plan and 11-week Gantt, Project Proposal v1: Closed-Loop Neuroadaptive VR Platform for Dopamine Scrolling, Innovation factor v1: closed-loop therapeutic intervention in immersive VR, Digital mental health market ($45B by 2030; 83% Gen Z), Neuroadaptive VR with Focus Index EEG feedback (ISMAR NeuroXR) (+6 more)

### Community 26 - "BlinkCounter"
Cohesion: 0.18
Nodes (3): 3.1 Qué fallaba en el contador del pipeline (corregido el 24 nov), blink_peaks(), BlinkCounter

### Community 28 - "Plataforma Neuroadaptativa en Realidad Aumentada (AR) y Procesamiento de Señales EEG"
Cohesion: 0.13
Nodes (15): 1. Clonar el repositorio, 2. Configurar el entorno virtual de Python, 3. Ejecutar los pipelines de análisis, 4. Lanzar el Visor Interactivo de Señales, 🛠️ Arquitectura Tecnológica y Lazo Cerrado, 👤 Autor e Institución, 📊 Avances y Validación Empírica en Datasets Públicos, Brecha Identificada en el Estado del Arte (+7 more)

### Community 29 - "JITAI Intervention Ladder (Cue / Friction / Pause)"
Cohesion: 0.17
Nodes (11): Existing Tools (Opal, Time2Stop, one sec) react to time/usage, AR Device/Engine Decision (Unity AR Foundation, Quest, WebXR), H4: EEG-Triggered AR Beats Timer-Triggered AR, Nahum-Shani et al. 2018 (JITAIs in mobile health), Orzikulova et al. 2024 (Time2Stop, CHI '24), EWMA Feature Smoothing (alpha tau 5 s, theta tau 60 s), jitai_decision.py, JITAI Intervention Ladder (Cue / Friction / Pause) (+3 more)

### Community 30 - "Reporte H1 ds007537"
Cohesion: 0.23
Nodes (6): Reporte H1 ds007537, AURA montage (Pz, O1, O2), Periodic posterior alpha (dB over 1/f), Tran et al. 2020 - Mental fatigue meta-analysis, Wascher et al. 2014 - Frontal theta and mental fatigue, h1_reporte.txt (ds007537 statistics output)

### Community 31 - "Reporte_H1_SVRec.md"
Cohesion: 0.20
Nodes (7): Alternative explanations: fatigue, habituation, mind wandering, time-on-task, EEG-SVRec dataset (Zhang et al., SIGIR 2024), Periodic alpha ~ immersion/arousal per video (engagement state marker), Phase D (own experiment with control condition and AURA montage), Within-session slopes (primary, Holm): alpha down, theta up, both fragile, Zhang et al. 2024 (SIGIR) - EEG-SVRec, svrec_reporte.txt (EEG-SVRec statistics output)

### Community 32 - "Plan de implementación · App móvil Go/NoGo + base de datos de sesiones"
Cohesion: 0.14
Nodes (13): 1. Qué se va a construir, 2. Cómo se logra la precisión de tiempo, 3.1 Qué dice la literatura de respaldo (revisado el 16 nov), 3. La tarea (valores definitivos), 5. Cambios en el dashboard, 6.1 Resultado de la Fase 2 (16 nov, navegador de la PC a 60 Hz), 6.2 Resultado de la Fase 3 (16 nov), 6.3 Fase 4: lo que hay hasta ahora (16 nov) (+5 more)

### Community 33 - "Análisis del Scope v2 y guía de cambios"
Cohesion: 0.24
Nodes (11): Recommended AURA 8-channel montage (Fz FCz F3 F4 Pz O1 O2 Fp1), Baseline normalization (dB / % vs subject baseline), Cognitive Load EEG Dataset (Arithmetic/Stroop, Mendeley kt38js3jv7), Demo_processing.py offline EEG viewer, Análisis del Scope v2 y guía de cambios, Du et al. (2025) short-video polarized content EEG, Hamann & Carstengerdes (2023) simulated-flight mental fatigue EEG-fNIRS, Individual Alpha Frequency (IAF) band definition (+3 more)

### Community 34 - "4. Pasos a seguir"
Cohesion: 0.17
Nodes (12): 1. Estado actual, 2. Narrativa de la presentación, 3.1 Separar las dos contribuciones, 3.2 Escenarios y qué hacer en cada uno, 3.3 Recomendaciones para blindar el proyecto, 3. ¿Qué pasa si los resultados son negativos?, 4. Pasos a seguir, Fase 1 · Cerrar la validación ✅ casi completa (+4 more)

### Community 35 - "Proposal presentation v2 structure (AR title)"
Cohesion: 0.20
Nodes (11): Competitor analysis v2 (app blockers, one sec, Muse), Friction / agency intervention (one sec), Grüning et al. (2023) one sec self-nudge app (PNAS), H4 EEG-triggered vs timer-triggered intervention, Kosmyna et al. (2021) AttentivU AR attention BCI, Lukoff et al. (2021) YouTube design and sense of agency, Nguyen et al. (2025) short-form video meta-analysis, Proposal presentation v2 structure (AR title) (+3 more)

### Community 36 - "Scope Dopamine Scrolling: biomarcadores de fatiga cognitiva y control inhibitorio"
Cohesion: 0.25
Nodes (11): Ego depletion / resource-depletion model (failed replication, Hagger 2016), Frontal Alpha Asymmetry (FAA, exploratory approach-motivation index), Harmon-Jones & Gable (2018) frontal asymmetry motivation, Opportunity cost model of effort (Kurzban et al., 2013), Posterior alpha rises with accumulated fatigue (O1, O2, Pz), Scope Dopamine Scrolling: biomarcadores de fatiga cognitiva y control inhibitorio, FAA as inferred gratification 'hook' (left < right frontal alpha), Joint biomarker evolution and inhibitory-control collapse zone (+3 more)

### Community 37 - "Cortical disengagement (functional inhibition of visual cortex)"
Cohesion: 0.25
Nodes (7): Posterior aperiodic 1/f exponent, Cortical disengagement (functional inhibition of visual cortex), Donoghue et al. 2020 - Parameterizing neural power spectra, Gao, Peterson & Voytek 2017 - E/I balance from field potentials, Jensen & Mazaheri 2010 - Gating by inhibition, Klimesch et al. 2007 - Alpha inhibition-timing hypothesis, Periodic frontal theta Fz/FCz (dB over 1/f)

### Community 38 - "Phasic frontal-midline theta (NoGo-evoked, Fz/FCz)"
Cohesion: 0.22
Nodes (9): Cavanagh & Frank (2014) frontal theta cognitive control, Experimental validation plan (35 min scrolling vs documentary), H2 phasic inhibition hypothesis, H3 tonic-phasic dissociation hypothesis, Pre/post Go/NoGo or Stop-Signal inhibitory probe, Nigbur et al. (2011) theta and cognitive interference, Phasic frontal-midline theta (NoGo-evoked, Fz/FCz), Embedded Scroll-NoGo web feed with LSL markers (+1 more)

### Community 39 - "Guía de Uso: Nuevos Canales, Modulación Automática y Datasets EEG"
Cohesion: 0.22
Nodes (9): 1. Canales Objetivo y su Función Neurocientífica, 2. Modulación Automática de Canales, 3. Representación Visual del Montaje 10-20 en la Interfaz, 4. Cómo Buscar y Limpiar Nuevos Datasets, A. Para los archivos actuales de Stroop (`raw_data/Stroop_Data`):, B. Para nuevos datasets limpios (6 canales o con encabezados):, Dónde buscar:, Guía de Uso: Nuevos Canales, Modulación Automática y Datasets EEG (+1 more)

### Community 40 - "Reporte H1 · EEG-SVRec (Fase C)"
Cohesion: 0.22
Nodes (9): 1. Muestra, 2. Resultados, 3. Lectura frente a H1, 4. Implicaciones para MIRAI, 5. Limitaciones, A · Dentro de la sesión (pruebas primarias, Holm), B · Entre sesiones (exploratorio, confundido con el tipo de feed), C · Por video (exploratorio, 11 pruebas) (+1 more)

### Community 42 - "Offline equivalence vs h1_por_minuto.csv (ds007537 sub-01): alpha_per r=0.938 PASA"
Cohesion: 0.29
Nodes (4): OpenNeuro ds007537 (smartphone use, 64ch EEG + eye-tracking), Mishra, Gandhi & Gandhi 2026 - Multimodal smartphone dataset, Posterior EMG 25-40 Hz artifact control, Offline equivalence vs h1_por_minuto.csv (ds007537 sub-01): alpha_per r=0.938 PASA

### Community 43 - "Script — 2nd Progress Report (7 min)"
Cohesion: 0.12
Nodes (16): 10 · Next Steps — 30 s (6:15 → 6:45), 11 · References + closing — 15 s (6:45 → 7:00), 1 · Cover — 15 s (0:00 → 0:15), 2 · Hypotheses — 35 s (0:15 → 0:50), 3 · Updated Gantt Diagram — 30 s (0:50 → 1:20), 4 · Real-Time Pipeline Design — 45 s (1:20 → 2:05), 5 · LSL Simulation Results — 60 s (2:05 → 3:05), 6 · Live AURA Recordings — 60 s (3:05 → 4:05) (+8 more)

### Community 44 - "Cao 2019 Phasic Theta Time Course (fast vs slow trials)"
Cohesion: 0.47
Nodes (6): Cao 2019 Phasic Theta Time Course (fast vs slow trials), Relative-baseline normalization artifact, Fast (alert) vs slow (fatigue) response trials, Phasic frontal-midline theta (Fz/FCz), Phasic window 0.1-0.5 s post-deviation, Tonic theta baseline elevation in slow trials

### Community 45 - "cao_reporte.txt (Cao 2019 positive control output)"
Cohesion: 0.53
Nodes (6): cao_reporte.txt (Cao 2019 positive control output), EEG-behavior coupling (Spearman rho per window), Uncorrected-deviation lapse fraction, log10 reaction time behavioral fatigue (primary, Holm p=0.86, null), Phasic theta ERSP at deviation onset, Periodic theta Fz/FCz rises (primary, Holm p=0.034)

### Community 47 - "CausalFilter"
Cohesion: 0.25
Nodes (3): blink_gain(), CausalFilter, Qué cambia

### Community 48 - "sesion_aura_web.py"
Cohesion: 0.15
Nodes (12): abortar(), act(), bloque_siguiente(), en(), gng_sync(), keep_token(), reporte_abrir(), semaforo_detener() (+4 more)

### Community 51 - "requirements.txt (simulation_B)"
Cohesion: 0.83
Nodes (4): requirements.txt (simulation_B), requirements.txt (simulation), mne>=1.6, pylsl>=1.16

### Community 64 - "simulation/realtime_pipeline.py"
Cohesion: 0.15
Nodes (5): blink_report(), main(), open_run(), Rejector, Windower

### Community 66 - "Progress Report: Closed-Loop Neuroadaptive AR Platform for Scrolling"
Cohesion: 0.09
Nodes (31): Jacquet et al. 2023 (45 min smartphone -> NoGo errors up), Tonic vs Phasic Theta Distinction, Cao 2019 Dataset (positive control, 60-90 min driving), EEG-SVRec Dataset (n=25, short video), H1: Tonic Theta/Alpha Rise More with Scrolling than Documentary, H2: NoGo FM-Theta Falls and Commission Errors Rise After Scrolling, H3: Tonic Up / Phasic Down Dissociation, OSF Preregistration (+23 more)

### Community 67 - "ds007537 Dataset (n=27, 10 min smartphone)"
Cohesion: 0.20
Nodes (11): ds007537 Dataset (n=27, 10 min smartphone), Mishra, Gandhi & Gandhi 2026 (OpenNeuro ds007537), EMG Veto (25-40 Hz posterior), Offline Equivalence Test (alpha_per r>=0.8, bias<0.5 dB), results/h1_por_minuto.csv (offline reference), replay_offline.py, Version B (Tests/simulation_B), Desmond & Hancock 2001 (+3 more)

### Community 76 - "P07 (25 nov 2026): por qué solo 65.8 % de ventanas válidas"
Cohesion: 0.29
Nodes (6): 1. El rechazo fue solo por Fp1, 2. Fp1 tuvo el doble de pico a pico que en P01–P06, 3. ¿Sudor por la bicicleta?, 4. Conclusión, 5. Reprocesado offline con otro umbral de Fp1, P07 (25 nov 2026): por qué solo 65.8 % de ventanas válidas

### Community 80 - "Configuración de la AURA para MIRAI 2026"
Cohesion: 0.33
Nodes (6): 1. Ajustes de la interfaz (de arriba a abajo), 2. Verificación del stream (antes de cada sesión), 3. Prueba rápida de calidad: efecto Berger (2 min), 4. Lo que muestra el CSV de prueba (enero 2026, configuración desconocida), 5. Replay del CSV con el emulador, Configuración de la AURA para MIRAI 2026

### Community 81 - "h1b_cao2019.py"
Cohesion: 0.11
Nodes (14): analyse(), epochs(), lapse_fraction(), main(), measures(), phasic(), phasic_report(), plot() (+6 more)

### Community 82 - "Versión B — criterio de detección del Paso 3 precisado (29 oct 2026)"
Cohesion: 0.12
Nodes (11): band_per(), bands(), Features, fit_roi(), Comparación A frente a B con el Paso 4 (29 oct), Hallazgo que motivó el ajuste, Paso 5 — calibración congelada (30 oct), Prueba en vivo (29 oct, 10 min de uno en uno, tren de parpadeos de 30 s en el minuto 5) (+3 more)

### Community 83 - "MIRAI 2026 · Guía de estudio para la exposición de avances (22 oct 2026)"
Cohesion: 0.25
Nodes (8): 0. La idea en 30 segundos (apréndela de memoria), 1. Conceptos clave (glosario para no confundirte), 2. Qué pasó en esta sesión (para que no te confundas con versiones viejas), 4. Cómo argumentar "mis exploraciones me dicen qué hacer" (el razonamiento completo), 5. Hoja de cifras (memorízalas), 6. Preguntas difíciles y respuestas cortas, 7. Pendientes antes de presentar, MIRAI 2026 · Guía de estudio para la exposición de avances (22 oct 2026)

### Community 84 - "gng"
Cohesion: 0.24
Nodes (5): gng(), gng_bloque_sync(), gng_ensayos(), gng_iniciar(), fn()

### Community 92 - "MIRAI 2026 · ¿La literatura sostiene las hipótesis originales? (22 oct 2026)"
Cohesion: 0.10
Nodes (17): 1. Cambios de la semana pasada (2–8 nov), 2. ¿Cuántas pruebas hacen falta?, 3. ¿Conviene usar regresión para dar más fuerza a la validación?, MIRAI 2026 · Análisis de la semana, tamaño de muestra y uso de regresión (9 nov 2026), Project Proposal MIRAI v4 Deck (14 slides), H1-State (complementary, for JITAI), 1. Theta y alfa tónicos aumentan con el tiempo en tarea → **respaldado**, 2. Theta fásico ↓ con fatiga (control inhibitorio) → **respaldo moderado, literatura mixta** (+9 more)

### Community 93 - "numpy"
Cohesion: 0.14
Nodes (9): add_blink(), inject(), load_aura_csv(), load_file(), main(), make_outlet(), montage_1005(), stream() (+1 more)

### Community 94 - "replay_sesion.py"
Cohesion: 0.19
Nodes (11): api(), control(), main(), mmss(), originales(), Stream, sync(), tel_bloque() (+3 more)

### Community 95 - "os"
Cohesion: 0.17
Nodes (5): main(), etiquetas(), main(), latest_report(), main()

### Community 98 - "simulation/replay_offline.py"
Cohesion: 0.17
Nodes (5): eeg_blinks(), equivalence(), et_blinks(), main(), score()

### Community 100 - "pylsl"
Cohesion: 0.21
Nodes (8): channel_meta(), find_markers(), find_stream(), main(), channel_meta(), find_markers(), find_stream(), main()

### Community 101 - "semaforo_canales.py"
Cohesion: 0.31
Nodes (3): main(), selftest(), semaforo()

### Community 102 - "Demo_processing.py"
Cohesion: 0.13
Nodes (8): bids_downloaded(), draw_electrode_map(), is_bids(), load_bids(), load_eeg(), main(), numeric_sort_key(), main()

### Community 107 - "tendencias.py"
Cohesion: 0.18
Nodes (12): bloques(), fig_gonogo(), fig_parpadeo_comparacion(), fig_parpadeo_qc(), fig_tendencia(), gonogo(), main(), parpadeos() (+4 more)

### Community 109 - "window_biomarkers"
Cohesion: 0.18
Nodes (7): alpha_channels(), band_powers(), biomarker_summary(), compute_psd(), _metrics_from_bp(), window_biomarkers(), [x] Paso 4: Descomposición Espectral y Extracción con `specparam` — cerrado 30 oct 2026 con la versión B

### Community 111 - ".refresh_biomarkers"
Cohesion: 0.19
Nodes (4): band_filter(), cognitive_indices(), PSDWindow, robust_limits()

### Community 112 - "simulation_B/spectral_features.py"
Cohesion: 0.15
Nodes (3): window_psd(), Features, window_psd()

### Community 116 - "json"
Cohesion: 0.19
Nodes (5): run(), blinks_fp1(), fit(), load(), load_source()

### Community 117 - "resumen"
Cohesion: 0.29
Nodes (4): _filtro(), registros(), resumen(), gng_exportar()

### Community 119 - "Corrección de parpadeos antes del CAR — replay offline (26 nov 2026)"
Cohesion: 0.50
Nodes (3): Corrección de parpadeos antes del CAR — replay offline (26 nov 2026), Lectura, Resultados

### Community 120 - "Guia_Canales_y_Datasets.md"
Cohesion: 0.38
Nodes (6): 10-20 electrode map tab in Demo_processing, Frontal Alpha Asymmetry FAA = ln(alpha_F4) - ln(alpha_F3), load_eeg automatic channel modulation, MNE script exporting 6-channel CSV at 250 Hz, 6 target channels (Fz, F3, F4, Pz, O1, O2), Stroop dataset (OpenBCI Cyton 8 channels)

### Community 124 - "P09 (26 nov 16:01): primera sesión en vivo con la corrección EOG"
Cohesion: 0.40
Nodes (4): Corrección EOG: quedó débil, Falsos positivos, P09 (26 nov 16:01): primera sesión en vivo con la corrección EOG, Señal

### Community 128 - "Reporte rápido · 26 nov 2026 · n = 9"
Cohesion: 0.33
Nodes (5): Calidad de datos, Hipótesis, Lo que falta para poder concluir, Parpadeos (recuento con umbral fijo por sesión), Reporte rápido · 26 nov 2026 · n = 9

### Community 130 - "init"
Cohesion: 0.50
Nodes (3): init(), guardado(), main()

## Ambiguous Edges - Review These
- `Posterior Broadband 20-45 Hz Elevation (sub 02)` → `Pilot Raw PSD Spectra (EEG-SVRec sub 07 & sub 02)`  [AMBIGUOUS]
  Tests/datasets workflow/EEG-SVRec/results/piloto_espectros.png · relation: references
- `H1 (fatigue via theta/alpha)` → `H1 EEG-SVRec Trajectories Figure (within/between sessions)`  [AMBIGUOUS]
  Tests/datasets workflow/EEG-SVRec/results/svrec_trayectorias.png · relation: rationale_for

## Knowledge Gaps
- **291 isolated node(s):** `graphify`, `Resultados`, `Lectura`, `Señal`, `Corrección EOG: quedó débil` (+286 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 626 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **57 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `Posterior Broadband 20-45 Hz Elevation (sub 02)` and `Pilot Raw PSD Spectra (EEG-SVRec sub 07 & sub 02)`?**
  _Edge tagged AMBIGUOUS (relation: references) - confidence is low._
- **Why does `Session` connect `Session` to `sesion_aura_web.py`?**
  _High betweenness centrality (0.044) - this node is a cross-community bridge._
- **What connects `graphify`, `Resultados`, `Lectura` to the rest of the system?**
  _291 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `3. Contenido nuevo de la presentación (v2)` be split into smaller, more focused modules?**
  _Cohesion score 0.05714285714285714 - nodes in this community are weakly interconnected._
- **What is the exact relationship between `H1 (fatigue via theta/alpha)` and `H1 EEG-SVRec Trajectories Figure (within/between sessions)`?**
  _Edge tagged AMBIGUOUS (relation: rationale_for) - confidence is low._
- **Why does `SessionApp` connect `SessionApp` to `Demo_processing.py`, `os`?**
  _High betweenness centrality (0.031) - this node is a cross-community bridge._
- **Should `Análisis de las sesiones P01–P09 (19, 20, 25 y 26 nov 2026)` be split into smaller, more focused modules?**
  _Cohesion score 0.14285714285714285 - nodes in this community are weakly interconnected._