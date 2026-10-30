# Graph Report - Project  (2026-10-30)

## Corpus Check
- 43 files · ~133,481 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 869 nodes · 1517 edges · 63 communities (49 shown, 14 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 119 edges (avg confidence: 0.86)
- Token cost: 729,283 input · 0 output

## Community Hubs (Navigation)
- Visor EEG Demo_processing
- Análisis del Scope v2
- Calibración Paso 5 (B)
- Pipeline tiempo real B
- Figuras de trayectorias H1/H1b
- Pipeline tiempo real A
- Pipeline offline ds007537
- Reporte H1 ds007537 (secciones)
- specparam offline y handoff
- Guía de exposición (diapositivas)
- Pipeline offline EEG-SVRec
- Datasets y deck de propuesta
- Features espectrales B
- Replay offline A
- Detección de streams LSL
- Pipeline offline Cao 2019
- Emulador LSL B
- Emulador LSL A
- Hipótesis H1-H3 y Jacquet
- Literatura theta tónico/fásico
- Configuración AURA
- Versión B: parpadeos y calibración
- Intervención JITAI y AR/VR
- Protocolo: filtros, EMG y equivalencia
- Fatiga tónica y ds007537
- Propuesta v1 (VR dopamina)
- Medidas conductuales Cao
- Replay offline B
- README del proyecto
- H4 y escenarios de resultados
- Reporte H1 ds007537 (conceptos)
- Reporte H1 EEG-SVRec
- Revisión de literatura
- Montaje AURA y datasets alternos
- Plan de avances
- Competidores y agencia
- Scope: dopamina y fatiga
- Alfa periódica y 1/f
- H2/H3 control inhibitorio
- Guía de canales (secciones)
- Resultados SVRec (secciones)
- Test pipeline A
- Guía de canales y FAA
- Guía AURA (secciones)
- Theta fásico Cao (figura)
- Reporte Cao 2019
- ds007537 y fatiga pasiva
- Features espectrales A
- Paso 7: latencia y Berger
- EMG y equivalencia B
- Épocas MNE
- Requisitos de simulación
- Config graphify

## God Nodes (most connected - your core abstractions)
1. `Análisis del Scope v2 y guía de cambios` - 24 edges
2. `Progress Report: Closed-Loop Neuroadaptive AR Platform for Scrolling` - 24 edges
3. `EEGViewer` - 23 edges
4. `Project Proposal v1: Closed-Loop Neuroadaptive VR Platform for Dopamine Scrolling` - 19 edges
5. `README: Plataforma Neuroadaptativa AR y procesamiento EEG` - 18 edges
6. `Reporte H1 ds007537` - 15 edges
7. `3. Explicación diapositiva por diapositiva` - 15 edges
8. `Resumen de sesión MIRAI 2026 (19-21 oct)` - 15 edges
9. `H1: Tonic Theta/Alpha Rise More with Scrolling than Documentary` - 15 edges
10. `main()` - 14 edges

## Surprising Connections (you probably didn't know these)
- `Closed-loop AR JITAI neuroadaptive platform` --semantically_similar_to--> `Closed-loop neuroadaptive VR platform (v1 general objective)`  [INFERRED] [semantically similar]
  README.md → Documentación/Project Proposal MIRAI Ricardo_Monrreal (1).pdf
- `Tonic posterior alpha (8-13 Hz, Pz/O1/O2)` --semantically_similar_to--> `Posterior alpha rises with accumulated fatigue (O1, O2, Pz)`  [INFERRED] [semantically similar]
  Documentación/Analisis_Scope_v2.md → Documentación/Scope_Dopamine_Scrolling.pdf
- `Tonic up / phasic down theta dissociation with time-on-task` --semantically_similar_to--> `Tonic theta baseline rise vs loss of phasic FM-theta bursts`  [INFERRED] [semantically similar]
  Documentación/Analisis_Scope_v2.md → Documentación/Scope_Dopamine_Scrolling.pdf
- `Project Proposal MIRAI v4 Deck (14 slides)` --semantically_similar_to--> `Progress Report: Closed-Loop Neuroadaptive AR Platform for Scrolling`  [INFERRED] [semantically similar]
  Tests/Guia_Exposicion.md → Tests/Progress Report MIRAI Ricardo_Monrreal.pdf
- `Frontal Alpha Asymmetry (FAA, exploratory approach-motivation index)` --semantically_similar_to--> `FAA as inferred gratification 'hook' (left < right frontal alpha)`  [INFERRED] [semantically similar]
  Documentación/Analisis_Scope_v2.md → Documentación/Scope_Dopamine_Scrolling.pdf

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Tonic/phasic hypothesis framework H1-H3** — documentaci_n_analisis_scope_v2_h1, documentaci_n_analisis_scope_v2_h2, documentaci_n_analisis_scope_v2_h3, documentaci_n_analisis_scope_v2_tonic_theta, documentaci_n_analisis_scope_v2_posterior_alpha, documentaci_n_analisis_scope_v2_phasic_fm_theta [EXTRACTED 1.00]
- **JITAI intervention mechanisms per detected state** — documentaci_n_analisis_scope_v2_intervention_ladder, documentaci_n_analisis_scope_v2_attention_restoration, documentaci_n_analisis_scope_v2_friction_nudge, documentaci_n_analisis_scope_v2_inhibitory_control_training, documentaci_n_analisis_scope_v2_jitai [EXTRACTED 1.00]
- **Public-dataset H1 validation (ds007537, EEG-SVRec, Cao 2019)** — documentaci_n_resumen_sesion_21_10_ds007537_h1_results, readme_svrec_result, readme_cao2019_result, documentaci_n_analisis_scope_v2_ds007537, documentaci_n_analisis_scope_v2_eeg_svrec, documentaci_n_analisis_scope_v2_cao_2019 [EXTRACTED 1.00]
- **Simulated Closed-Loop Pipeline (emulator -> pipeline -> features -> JITAI -> launcher)** — tests_protocolo_simulacion_pipeline_mock_lsl_streamer, tests_protocolo_simulacion_pipeline_realtime_pipeline, tests_protocolo_simulacion_pipeline_spectral_features, tests_protocolo_simulacion_pipeline_jitai_decision, tests_protocolo_simulacion_pipeline_run_simulation [EXTRACTED 1.00]
- **MIRAI Time-Based Hypothesis Set H1-H4** — tests_plan_avances_h1, tests_plan_avances_h1_state, tests_plan_avances_h2, tests_plan_avances_h3, tests_plan_avances_h4 [EXTRACTED 1.00]
- **Literature Supporting Tonic Theta/Alpha Rise with Time-on-Task** — tests_revision_literatura_hipotesis_tran2020, tests_revision_literatura_hipotesis_craig2012, tests_revision_literatura_hipotesis_boksem2005, tests_revision_literatura_hipotesis_wascher2014, tests_revision_literatura_hipotesis_benwell2019, tests_revision_literatura_hipotesis_borghini2014 [EXTRACTED 1.00]
- **Periodic alpha as disengagement marker across datasets** — tests_datasets_workflow_ds007537_reporte_h1_ds007537_periodic_alpha, tests_datasets_workflow_ds007537_reporte_h1_ds007537_cortical_disengagement, tests_datasets_workflow_eeg_svrec_reporte_h1_svrec_per_video_alpha_engagement, tests_datasets_workflow_eeg_svrec_reporte_h1_svrec_h1a_reformulation, tests_datasets_workflow_eeg_svrec_reporte_h1_svrec_jitai_trigger [INFERRED 0.85]
- **H1b frontal theta validation across ds007537, EEG-SVRec and Cao 2019** — tests_datasets_workflow_ds007537_reporte_h1_ds007537_h1b_frontal_theta, tests_datasets_workflow_eeg_svrec_reporte_h1_svrec_within_session_slopes, tests_datasets_workflow_cao2019_results_cao_reporte_h1b_positive_control, tests_datasets_workflow_cao2019_results_cao_reporte_theta_per_primary [INFERRED 0.85]
- **Version B Step 5 frozen calibration flow** — tests_simulation_b_version_b_quality_check, tests_simulation_b_version_b_aura_baseline_phases, tests_simulation_b_version_b_ewma_smoothing, tests_simulation_b_version_b_sigma_z_correction, tests_simulation_b_version_b_rms_z_criterion [EXTRACTED 1.00]
- **Tonic theta up, phasic theta preserved under fatigue** — tests_datasets_workflow_cao2019_results_cao_fasico_curso_phasic_theta, tests_datasets_workflow_cao2019_results_cao_fasico_curso_tonic_theta, tests_datasets_workflow_cao2019_results_cao_fasico_curso_fast_vs_slow_trials, tests_datasets_workflow_cao2019_results_cao_fasico_curso_baseline_normalization_artifact [INFERRED 0.85]
- **Early-peak fatigue markers (RT, lapses, tonic theta)** — tests_datasets_workflow_cao2019_results_cao_trayectorias_log_rt, tests_datasets_workflow_cao2019_results_cao_trayectorias_lapse_fraction, tests_datasets_workflow_eeg_svrec_results_svrec_trayectorias_tonic_theta [INFERRED 0.75]
- **Spectral parametrization: periodic alpha, periodic theta, aperiodic exponent** — tests_datasets_workflow_eeg_svrec_results_svrec_trayectorias_periodic_alpha, tests_datasets_workflow_eeg_svrec_results_svrec_trayectorias_periodic_theta, tests_datasets_workflow_eeg_svrec_results_svrec_trayectorias_aperiodic_exponent [INFERRED 0.85]
- **Artifact controls: EMG and blinks vs total alpha** — tests_datasets_workflow_eeg_svrec_results_svrec_trayectorias_emg_control, tests_datasets_workflow_eeg_svrec_results_svrec_trayectorias_blink_rate, tests_datasets_workflow_eeg_svrec_results_svrec_trayectorias_total_alpha [INFERRED 0.65]
- **Non-EEG and aperiodic arousal markers** — tests_datasets_workflow_ds007537_results_h1_trayectorias_blink_rate, tests_datasets_workflow_ds007537_results_h1_trayectorias_pupil_diameter, tests_datasets_workflow_eeg_svrec_results_svrec_trayectorias_aperiodic_exponent [INFERRED 0.75]

## Communities (63 total, 14 thin omitted)

### Community 0 - "Visor EEG Demo_processing"
Cohesion: 0.05
Nodes (22): alpha_channels(), band_filter(), band_powers(), bids_downloaded(), biomarker_summary(), cognitive_indices(), compute_psd(), draw_electrode_map() (+14 more)

### Community 1 - "Análisis del Scope v2"
Cohesion: 0.06
Nodes (33): 0. Estado actual de `/Tests`, 1. Objetivo central 1: datasets EEG de scrolling / video corto, 2.1 Veredicto general, 2.2 Qué está bien sustentado ✅, 2.3 Qué hay que corregir ⚠️, 2.4 Implicaciones para `Demo_processing.py`, 2. Objetivo central 2: revisión de la teoría, 3. Contenido nuevo de la presentación (v2) (+25 more)

### Community 2 - "Calibración Paso 5 (B)"
Cohesion: 0.08
Nodes (6): bad_channels(), Calibration, iaf_from(), rho_sum(), on(), run_step5()

### Community 3 - "Pipeline tiempo real B"
Cohesion: 0.10
Nodes (9): blink_gain(), blink_report(), CausalFilter, main(), on_window(), open_run(), Rejector, Windower (+1 more)

### Community 4 - "Figuras de trayectorias H1/H1b"
Cohesion: 0.13
Nodes (26): Cao 2019 sustained driving EEG dataset, H1b Cao 2019 Trajectories Figure (sustained driving, mean +- SE), H1b (inhibitory control / fatigue hypothesis), Lapse fraction (uncorrected drift time), log10 reaction time (behavioral fatigue), Periodic posterior alpha Pz/Oz/O1/O2, H1 ds007537 trajectories figure (tonic evolution and arousal markers, mean +/- SE), Blink rate (EEG Fp1 and eye-tracker) (+18 more)

### Community 5 - "Pipeline tiempo real A"
Cohesion: 0.11
Nodes (7): blink_report(), CausalFilter, main(), on_window(), open_run(), Rejector, Windower

### Community 6 - "Pipeline offline ds007537"
Cohesion: 0.13
Nodes (17): band_db(), clean(), detect_blinks(), et_window(), eyetrack(), is_downloaded(), main(), markers() (+9 more)

### Community 7 - "Reporte H1 ds007537 (secciones)"
Cohesion: 0.08
Nodes (25): 10. Próximos pasos, 11. Archivos, 1. Resumen, 2. Hipótesis evaluada, 3. Dataset, 4.1 Preprocesado (por sujeto), 4.2 Medidas espectrales (por minuto), 4.3 Marcadores de activación (control de somnolencia) (+17 more)

### Community 8 - "specparam offline y handoff"
Cohesion: 0.09
Nodes (22): iaf(), periodic(), 1. Contexto del proyecto, 2. Revisión del protocolo (problemas detectados, aún sin corregir en Pasos 2–7), 3. Paso 1 — HECHO, 4. Análisis del CSV real de AURA (`eeg_data_20260122_123839.csv`) — PRELIMINAR, interrumpido, 5. Herramientas, Handoff: sesión Cowork → Claude Code (MIRAI 2026, 28 oct 2026) (+14 more)

### Community 9 - "Guía de exposición (diapositivas)"
Cohesion: 0.09
Nodes (23): 0. La idea en 30 segundos (apréndela de memoria), 10 · System Pipeline, 11 · Robust to Negative Results — **la diapositiva más importante para defender el proyecto**, 12 · Gantt, 13 · Next Steps, 14 · References, 1. Conceptos clave (glosario para no confundirte), 1 · Portada — *Closed-Loop Neuroadaptive AR Platform for Dopamine Scrolling* (+15 more)

### Community 10 - "Pipeline offline EEG-SVRec"
Cohesion: 0.13
Nodes (12): across(), epochs_psd(), holm(), load_session(), main(), measures(), per_video(), plot() (+4 more)

### Community 11 - "Datasets y deck de propuesta"
Cohesion: 0.13
Nodes (17): Project Proposal MIRAI v4 Deck (14 slides), Cao 2019 Dataset (positive control, 60-90 min driving), EEG-SVRec Dataset (n=25, short video), OSF Preregistration, Own Experiment (scrolling vs documentary, 45-60 min, Go/NoGo), TOST / Bayes Factors, Progress Report: Closed-Loop Neuroadaptive AR Platform for Scrolling, Cao, Chuang, King & Lin 2019 (Scientific Data) (+9 more)

### Community 12 - "Features espectrales B"
Cohesion: 0.11
Nodes (12): band_per(), bands(), Features, fit_roi(), window_psd(), Comparación A frente a B con el Paso 4 (29 oct), Hallazgo que motivó el ajuste, Paso 5 — calibración congelada (30 oct) (+4 more)

### Community 13 - "Replay offline A"
Cohesion: 0.13
Nodes (6): eeg_blinks(), equivalence(), et_blinks(), main(), score(), Features

### Community 14 - "Detección de streams LSL"
Cohesion: 0.21
Nodes (8): channel_meta(), find_markers(), find_stream(), main(), channel_meta(), find_markers(), find_stream(), main()

### Community 15 - "Pipeline offline Cao 2019"
Cohesion: 0.17
Nodes (7): analyse(), main(), phasic(), phasic_report(), plot(), plot_curve(), report()

### Community 16 - "Emulador LSL B"
Cohesion: 0.20
Nodes (9): add_blink(), inject(), load_aura_csv(), load_file(), main(), make_outlet(), montage_1005(), stream() (+1 more)

### Community 17 - "Emulador LSL A"
Cohesion: 0.18
Nodes (9): add_blink(), inject(), load_aura_csv(), load_file(), main(), make_outlet(), montage_1005(), stream() (+1 more)

### Community 18 - "Hipótesis H1-H3 y Jacquet"
Cohesion: 0.12
Nodes (17): Jacquet et al. 2023 (45 min smartphone -> NoGo errors up), Tonic vs Phasic Theta Distinction, H1: Tonic Theta/Alpha Rise More with Scrolling than Documentary, H2: NoGo FM-Theta Falls and Commission Errors Rise After Scrolling, H3: Tonic Up / Phasic Down Dissociation, Sharpe & Spooner 2025 (Dopamine-scrolling public health), Arnau, Brummer, Liegel & Wascher 2021 (inverse time-on-task theta), Boksem, Meijman & Lorist 2005 (+9 more)

### Community 19 - "Literatura theta tónico/fásico"
Cohesion: 0.16
Nodes (16): Arnau et al. (2021) inverse time-on-task effects on theta, Cao et al. (2019) sustained-attention driving EEG dataset (Figshare 6427334), EEG-SVRec dataset (Zhang et al., SIGIR 2024), Tonic up / phasic down theta dissociation with time-on-task, Yu, Mückschel & Beste (2022) time-on-task theta, Pending: EEG-SVRec pilot, Cao 2019 positive control, pre-registration, own experiment, Real-time proof of concept via eyes-closed alpha (Berger effect), Cao 2019 positive control: tonic theta ~ log RT (rho=+0.50), phasic theta preserved (+8 more)

### Community 20 - "Configuración AURA"
Cohesion: 0.18
Nodes (14): AURA Channel Order Fp1,F3,Fz,F4,Cz,Pz,O1,O2, AURA EEG Headset (software v1.2.x), Aura.exe LSL Streams (AURA, AURA_Filtered, AURA_Power), AURA Test CSV eeg_data_20260122_123839, CSV 50 Hz Effective Sampling, LSL Stream Out Setting, MarkItDown (PDF/Office to Markdown), VRehab.py (StandardScaler + LogisticRegression, reads AURA_Power) (+6 more)

### Community 21 - "Versión B: parpadeos y calibración"
Cohesion: 0.16
Nodes (10): AURA baseline phases (eyes open mu/sigma, eyes closed IAF + Berger), Emulator markers blink:<amplitude uV>, blink_gain() filter peak-to-peak gain (~1.11), blink_report(), EWMA smoothing (tau theta 60 s, tau alpha 5 s), Grazing-blink segments raise theta_per ~0.05-0.08 dB (negligible), Level 1 detection with Z_alpha (tuned in Step 6), Calibration quality check (first 10 s window, ROI empty stops session) (+2 more)

### Community 22 - "Intervención JITAI y AR/VR"
Cohesion: 0.15
Nodes (16): Attention Restoration Theory restorative micro-break, Enriquez-Geppert et al. (2014) FM-theta neurofeedback, Inhibitory control training + FM-theta neurofeedback (VR Scroll-NoGo), Closed-loop intervention ladder (levels 0-3, refractory 5 min), Just-In-Time Adaptive Intervention (JITAI; Nahum-Shani 2018), Jones et al. (2016) inhibitory control training meta-analysis, Kim et al. (2018) VR craving in internet gaming disorder, Nahum-Shani et al. (2018) JITAI design principles (+8 more)

### Community 23 - "Protocolo: filtros, EMG y equivalencia"
Cohesion: 0.15
Nodes (13): Causal Stateful Filter (sosfilt with zi), Circular Buffer (6 s window, 1 s hop), EMG Veto (25-40 Hz posterior), Offline Equivalence Test (alpha_per r>=0.8, bias<0.5 dB), find_stream() Source Identification, results/h1_por_minuto.csv (offline reference), periodic() specparam (from h1_ds007537.py), realtime_pipeline.py (+5 more)

### Community 24 - "Fatiga tónica y ds007537"
Cohesion: 0.21
Nodes (16): Drowsiness control with KSS and time of day, OpenNeuro ds007537 (Mishra, Gandhi & Gandhi 2026) smartphone EEG dataset, H1 tonic fatigue hypothesis, Jensen & Mazaheri (2010) alpha gating by inhibition, Tonic posterior alpha (8-13 Hz, Pz/O1/O2), Tonic frontal theta (4-8 Hz, Fz) fatigue marker, Tran et al. (2020) mental fatigue meta-analysis, Wascher et al. (2014) frontal theta and mental fatigue (+8 more)

### Community 25 - "Propuesta v1 (VR dopamina)"
Cohesion: 0.15
Nodes (14): 12-week Gantt (F1-F8), Sharpe & Spooner (2025) Dopamine-scrolling public health, Ahmed (2019) Gen Z smartphone and social media survey, Four-phase development plan and 11-week Gantt, Project Proposal v1: Closed-Loop Neuroadaptive VR Platform for Dopamine Scrolling, Innovation factor v1: closed-loop therapeutic intervention in immersive VR, Digital mental health market ($45B by 2030; 83% Gen Z), Neuroadaptive VR with Focus Index EEG feedback (ISMAR NeuroXR) (+6 more)

### Community 26 - "Medidas conductuales Cao"
Cohesion: 0.16
Nodes (8): lapse_fraction(), measures(), reaction_times(), session(), download(), process_all(), fetch(), remote_files()

### Community 27 - "Replay offline B"
Cohesion: 0.17
Nodes (5): eeg_blinks(), equivalence(), et_blinks(), main(), score()

### Community 28 - "README del proyecto"
Cohesion: 0.13
Nodes (15): 1. Clonar el repositorio, 2. Configurar el entorno virtual de Python, 3. Ejecutar los pipelines de análisis, 4. Lanzar el Visor Interactivo de Señales, 🛠️ Arquitectura Tecnológica y Lazo Cerrado, 👤 Autor e Institución, 📊 Avances y Validación Empírica en Datasets Públicos, Brecha Identificada en el Estado del Arte (+7 more)

### Community 29 - "H4 y escenarios de resultados"
Cohesion: 0.18
Nodes (11): Existing Tools (Opal, Time2Stop, one sec) react to time/usage, AR Device/Engine Decision (Unity AR Foundation, Quest, WebXR), H4: EEG-Triggered AR Beats Timer-Triggered AR, Nahum-Shani et al. 2018 (JITAIs in mobile health), Orzikulova et al. 2024 (Time2Stop, CHI '24), EWMA Feature Smoothing (alpha tau 5 s, theta tau 60 s), jitai_decision.py, JITAI Intervention Ladder (Cue / Friction / Pause) (+3 more)

### Community 30 - "Reporte H1 ds007537 (conceptos)"
Cohesion: 0.23
Nodes (6): Reporte H1 ds007537, AURA montage (Pz, O1, O2), Periodic posterior alpha (dB over 1/f), Tran et al. 2020 - Mental fatigue meta-analysis, Wascher et al. 2014 - Frontal theta and mental fatigue, h1_reporte.txt (ds007537 statistics output)

### Community 31 - "Reporte H1 EEG-SVRec"
Cohesion: 0.22
Nodes (6): EEG-SVRec dataset (Zhang et al., SIGIR 2024), Periodic alpha ~ immersion/arousal per video (engagement state marker), Phase D (own experiment with control condition and AURA montage), Within-session slopes (primary, Holm): alpha down, theta up, both fragile, Zhang et al. 2024 (SIGIR) - EEG-SVRec, svrec_reporte.txt (EEG-SVRec statistics output)

### Community 32 - "Revisión de literatura"
Cohesion: 0.15
Nodes (11): H1-State (complementary, for JITAI), 1. Theta y alfa tónicos aumentan con el tiempo en tarea → **respaldado**, 2. Theta fásico ↓ con fatiga (control inhibitorio) → **respaldo moderado, literatura mixta**, 3. Matices que explican tus resultados (y que la teoría ya predecía), 4. ¿Aplica al scrolling? → **plausible, pero es el hueco de la literatura**, 5. Contraste con tus resultados, 6. Corrección a la reformulación v3, 7. Referencias (verificar páginas/DOI antes de citar en la propuesta) (+3 more)

### Community 33 - "Montaje AURA y datasets alternos"
Cohesion: 0.24
Nodes (11): Recommended AURA 8-channel montage (Fz FCz F3 F4 Pz O1 O2 Fp1), Baseline normalization (dB / % vs subject baseline), Cognitive Load EEG Dataset (Arithmetic/Stroop, Mendeley kt38js3jv7), Demo_processing.py offline EEG viewer, Análisis del Scope v2 y guía de cambios, Du et al. (2025) short-video polarized content EEG, Hamann & Carstengerdes (2023) simulated-flight mental fatigue EEG-fNIRS, Individual Alpha Frequency (IAF) band definition (+3 more)

### Community 34 - "Plan de avances"
Cohesion: 0.17
Nodes (12): 1. Estado actual, 2. Narrativa de la presentación, 3.1 Separar las dos contribuciones, 3.2 Escenarios y qué hacer en cada uno, 3.3 Recomendaciones para blindar el proyecto, 3. ¿Qué pasa si los resultados son negativos?, 4. Pasos a seguir, Fase 1 · Cerrar la validación ✅ casi completa (+4 more)

### Community 35 - "Competidores y agencia"
Cohesion: 0.20
Nodes (11): Competitor analysis v2 (app blockers, one sec, Muse), Friction / agency intervention (one sec), Grüning et al. (2023) one sec self-nudge app (PNAS), H4 EEG-triggered vs timer-triggered intervention, Kosmyna et al. (2021) AttentivU AR attention BCI, Lukoff et al. (2021) YouTube design and sense of agency, Nguyen et al. (2025) short-form video meta-analysis, Proposal presentation v2 structure (AR title) (+3 more)

### Community 36 - "Scope: dopamina y fatiga"
Cohesion: 0.25
Nodes (11): Ego depletion / resource-depletion model (failed replication, Hagger 2016), Frontal Alpha Asymmetry (FAA, exploratory approach-motivation index), Harmon-Jones & Gable (2018) frontal asymmetry motivation, Opportunity cost model of effort (Kurzban et al., 2013), Posterior alpha rises with accumulated fatigue (O1, O2, Pz), Scope Dopamine Scrolling: biomarcadores de fatiga cognitiva y control inhibitorio, FAA as inferred gratification 'hook' (left < right frontal alpha), Joint biomarker evolution and inhibitory-control collapse zone (+3 more)

### Community 37 - "Alfa periódica y 1/f"
Cohesion: 0.18
Nodes (8): Alternative explanations: fatigue, habituation, mind wandering, time-on-task, Posterior aperiodic 1/f exponent, Cortical disengagement (functional inhibition of visual cortex), Donoghue et al. 2020 - Parameterizing neural power spectra, Gao, Peterson & Voytek 2017 - E/I balance from field potentials, Jensen & Mazaheri 2010 - Gating by inhibition, Klimesch et al. 2007 - Alpha inhibition-timing hypothesis, Periodic frontal theta Fz/FCz (dB over 1/f)

### Community 38 - "H2/H3 control inhibitorio"
Cohesion: 0.22
Nodes (9): Cavanagh & Frank (2014) frontal theta cognitive control, Experimental validation plan (35 min scrolling vs documentary), H2 phasic inhibition hypothesis, H3 tonic-phasic dissociation hypothesis, Pre/post Go/NoGo or Stop-Signal inhibitory probe, Nigbur et al. (2011) theta and cognitive interference, Phasic frontal-midline theta (NoGo-evoked, Fz/FCz), Embedded Scroll-NoGo web feed with LSL markers (+1 more)

### Community 39 - "Guía de canales (secciones)"
Cohesion: 0.22
Nodes (9): 1. Canales Objetivo y su Función Neurocientífica, 2. Modulación Automática de Canales, 3. Representación Visual del Montaje 10-20 en la Interfaz, 4. Cómo Buscar y Limpiar Nuevos Datasets, A. Para los archivos actuales de Stroop (`raw_data/Stroop_Data`):, B. Para nuevos datasets limpios (6 canales o con encabezados):, Dónde buscar:, Guía de Uso: Nuevos Canales, Modulación Automática y Datasets EEG (+1 more)

### Community 40 - "Resultados SVRec (secciones)"
Cohesion: 0.22
Nodes (9): 1. Muestra, 2. Resultados, 3. Lectura frente a H1, 4. Implicaciones para MIRAI, 5. Limitaciones, A · Dentro de la sesión (pruebas primarias, Holm), B · Entre sesiones (exploratorio, confundido con el tipo de feed), C · Por video (exploratorio, 11 pruebas) (+1 more)

### Community 42 - "Guía de canales y FAA"
Cohesion: 0.38
Nodes (6): 10-20 electrode map tab in Demo_processing, Frontal Alpha Asymmetry FAA = ln(alpha_F4) - ln(alpha_F3), load_eeg automatic channel modulation, MNE script exporting 6-channel CSV at 250 Hz, 6 target channels (Fz, F3, F4, Pz, O1, O2), Stroop dataset (OpenBCI Cyton 8 channels)

### Community 43 - "Guía AURA (secciones)"
Cohesion: 0.33
Nodes (6): 1. Ajustes de la interfaz (de arriba a abajo), 2. Verificación del stream (antes de cada sesión), 3. Prueba rápida de calidad: efecto Berger (2 min), 4. Lo que muestra el CSV de prueba (enero 2026, configuración desconocida), 5. Replay del CSV con el emulador, Configuración de la AURA para MIRAI 2026

### Community 44 - "Theta fásico Cao (figura)"
Cohesion: 0.47
Nodes (6): Cao 2019 Phasic Theta Time Course (fast vs slow trials), Relative-baseline normalization artifact, Fast (alert) vs slow (fatigue) response trials, Phasic frontal-midline theta (Fz/FCz), Phasic window 0.1-0.5 s post-deviation, Tonic theta baseline elevation in slow trials

### Community 45 - "Reporte Cao 2019"
Cohesion: 0.53
Nodes (6): cao_reporte.txt (Cao 2019 positive control output), EEG-behavior coupling (Spearman rho per window), Uncorrected-deviation lapse fraction, log10 reaction time behavioral fatigue (primary, Holm p=0.86, null), Phasic theta ERSP at deviation onset, Periodic theta Fz/FCz rises (primary, Holm p=0.034)

### Community 46 - "ds007537 y fatiga pasiva"
Cohesion: 0.33
Nodes (6): ds007537 Dataset (n=27, 10 min smartphone), Mishra, Gandhi & Gandhi 2026 (OpenNeuro ds007537), Desmond & Hancock 2001, Differential Prediction (alpha up > theta up under passive fatigue), Active vs Passive Fatigue, Saxby et al. 2013

### Community 48 - "Paso 7: latencia y Berger"
Cohesion: 0.40
Nodes (5): Berger Effect Quality Test (EO/EC, >=3 dB O1/O2), Eyes-Closed Alpha Loop Demo, Latency Targets (processing <500 ms, total to AR <2 s), Offline Replay Mode (--offline, no LSL), run_simulation.py (Launcher & Benchmark)

### Community 49 - "EMG y equivalencia B"
Cohesion: 0.40
Nodes (4): OpenNeuro ds007537 (smartphone use, 64ch EEG + eye-tracking), Mishra, Gandhi & Gandhi 2026 - Multimodal smartphone dataset, Posterior EMG 25-40 Hz artifact control, Offline equivalence vs h1_por_minuto.csv (ds007537 sub-01): alpha_per r=0.938 PASA

### Community 51 - "Requisitos de simulación"
Cohesion: 0.83
Nodes (4): requirements.txt (simulation_B), requirements.txt (simulation), mne>=1.6, pylsl>=1.16

## Ambiguous Edges - Review These
- `Pilot Raw PSD Spectra (EEG-SVRec sub 07 & sub 02)` → `Posterior Broadband 20-45 Hz Elevation (sub 02)`  [AMBIGUOUS]
  Tests/datasets workflow/EEG-SVRec/results/piloto_espectros.png · relation: references
- `H1 EEG-SVRec Trajectories Figure (within/between sessions)` → `H1 (fatigue via theta/alpha)`  [AMBIGUOUS]
  Tests/datasets workflow/EEG-SVRec/results/svrec_trayectorias.png · relation: rationale_for

## Knowledge Gaps
- **204 isolated node(s):** `1. Clonar el repositorio`, `2. Configurar el entorno virtual de Python`, `3. Ejecutar los pipelines de análisis`, `4. Lanzar el Visor Interactivo de Señales`, `🛠️ Arquitectura Tecnológica y Lazo Cerrado` (+199 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 372 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **14 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `Pilot Raw PSD Spectra (EEG-SVRec sub 07 & sub 02)` and `Posterior Broadband 20-45 Hz Elevation (sub 02)`?**
  _Edge tagged AMBIGUOUS (relation: references) - confidence is low._
- **Why does `Reporte H1 ds007537` connect `Reporte H1 ds007537 (conceptos)` to `Alfa periódica y 1/f`, `Pipeline offline ds007537`, `Reporte H1 ds007537 (secciones)`, `EMG y equivalencia B`, `Versión B: parpadeos y calibración`, `Reporte H1 EEG-SVRec`?**
  _High betweenness centrality (0.078) - this node is a cross-community bridge._
- **What connects `1. Clonar el repositorio`, `2. Configurar el entorno virtual de Python`, `3. Ejecutar los pipelines de análisis` to the rest of the system?**
  _204 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Visor EEG Demo_processing` be split into smaller, more focused modules?**
  _Cohesion score 0.05136986301369863 - nodes in this community are weakly interconnected._
- **What is the exact relationship between `H1 EEG-SVRec Trajectories Figure (within/between sessions)` and `H1 (fatigue via theta/alpha)`?**
  _Edge tagged AMBIGUOUS (relation: rationale_for) - confidence is low._
- **Why does `ds007537 Dataset (n=27, 10 min smartphone)` connect `ds007537 y fatiga pasiva` to `Hipótesis H1-H3 y Jacquet`, `Datasets y deck de propuesta`, `Configuración AURA`, `Protocolo: filtros, EMG y equivalencia`?**
  _High betweenness centrality (0.046) - this node is a cross-community bridge._
- **Should `Análisis del Scope v2` be split into smaller, more focused modules?**
  _Cohesion score 0.05714285714285714 - nodes in this community are weakly interconnected._