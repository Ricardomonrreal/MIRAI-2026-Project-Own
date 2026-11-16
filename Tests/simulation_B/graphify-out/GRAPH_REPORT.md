# Graph Report - simulation_B  (2026-11-12)

## Corpus Check
- 14 files · ~34,474 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 2 file(s) not represented in the graph (top: .cfg 1, .bat 1)

## Summary
- 271 nodes · 583 edges · 11 communities (7 shown, 4 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 20 edges (avg confidence: 0.93)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `90e0cb0b`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- sesion_aura_web.py
- spectral_features.py
- test_realtime_pipeline.py
- realtime_pipeline.py
- replay_offline.py
- Versión B — criterio de detección del Paso 3 precisado (29 oct 2026)
- Session
- numpy
- SessionApp
- BlinkCounter
- Jitai

## God Nodes (most connected - your core abstractions)
1. `main()` - 23 edges
2. `Session` - 20 edges
3. `SessionApp` - 18 edges
4. `CausalFilter` - 16 edges
5. `main()` - 16 edges
6. `find_stream()` - 12 edges
7. `Rejector` - 12 edges
8. `equivalence()` - 12 edges
9. `load_source()` - 11 edges
10. `BlinkCounter` - 11 edges

## Surprising Connections (you probably didn't know these)
- `Contador de parpadeos en Fp1 (2 nov)` --references--> `find_stream()`  [INFERRED]
  VERSION_B.md → check_lsl_stream.py
- `Contador de parpadeos en Fp1 (2 nov)` --references--> `find_markers()`  [INFERRED]
  VERSION_B.md → check_lsl_stream.py
- `Paso 5 — calibración congelada (30 oct)` --references--> `load_file()`  [INFERRED]
  VERSION_B.md → mock_lsl_streamer.py
- `Paso 7 — benchmark y validación extremo a extremo (30 oct, en curso)` --references--> `load_source()`  [INFERRED]
  VERSION_B.md → mock_lsl_streamer.py
- `Contador de parpadeos en Fp1 (2 nov)` --references--> `BlinkCounter`  [INFERRED]
  VERSION_B.md → realtime_pipeline.py

## Import Cycles
- None detected.

## Communities (11 total, 4 thin omitted)

### Community 0 - "sesion_aura_web.py"
Cohesion: 0.08
Nodes (15): main(), abortar(), act(), check_token(), en(), estado(), eventos(), index() (+7 more)

### Community 1 - "spectral_features.py"
Cohesion: 0.09
Nodes (9): bad_channels(), Calibration, iaf_from(), rho_sum(), band_per(), bands(), Features, fit_roi() (+1 more)

### Community 2 - "test_realtime_pipeline.py"
Cohesion: 0.09
Nodes (15): chi_flat(), blink_blocks(), blink_match(), main(), emit_jitai(), on_window(), mem_mb(), open_run() (+7 more)

### Community 3 - "realtime_pipeline.py"
Cohesion: 0.16
Nodes (10): main(), channel_meta(), find_markers(), find_stream(), main(), latest_report(), main(), main() (+2 more)

### Community 4 - "replay_offline.py"
Cohesion: 0.12
Nodes (9): blink_peaks(), CausalFilter, Windower, eeg_blinks(), equivalence(), et_blinks(), main(), score() (+1 more)

### Community 5 - "Versión B — criterio de detección del Paso 3 precisado (29 oct 2026)"
Cohesion: 0.09
Nodes (13): blink_gain(), blink_report(), OfflineInlet, OfflineMarkers, Comparación A frente a B con el Paso 4 (29 oct), Hallazgo que motivó el ajuste, Paso 6 — motor JITAI (30 oct, cerrado con excepciones), Paso 7 — benchmark y validación extremo a extremo (30 oct, en curso) (+5 more)

### Community 7 - "numpy"
Cohesion: 0.18
Nodes (10): add_blink(), inject(), load_aura_csv(), load_file(), load_source(), main(), make_outlet(), montage_1005() (+2 more)

## Knowledge Gaps
- **6 isolated node(s):** `Hallazgo que motivó el ajuste`, `Resultados offline (600 s sintéticos, ~15 parpadeos/min)`, `Prueba en vivo (29 oct, 10 min de uno en uno, tren de parpadeos de 30 s en el minuto 5)`, `Comparación A frente a B con el Paso 4 (29 oct)`, `Sin veto EMG y ajuste 2–30 Hz (29 oct, tarde)` (+1 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 111 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **4 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Session` connect `Session` to `sesion_aura_web.py`?**
  _High betweenness centrality (0.145) - this node is a cross-community bridge._
- **What connects `Hallazgo que motivó el ajuste`, `Resultados offline (600 s sintéticos, ~15 parpadeos/min)`, `Prueba en vivo (29 oct, 10 min de uno en uno, tren de parpadeos de 30 s en el minuto 5)` to the rest of the system?**
  _6 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `sesion_aura_web.py` be split into smaller, more focused modules?**
  _Cohesion score 0.07957957957957958 - nodes in this community are weakly interconnected._
- **Why does `SessionApp` connect `SessionApp` to `sesion_aura_web.py`?**
  _High betweenness centrality (0.122) - this node is a cross-community bridge._
- **Should `spectral_features.py` be split into smaller, more focused modules?**
  _Cohesion score 0.0873440285204991 - nodes in this community are weakly interconnected._
- **Why does `BlinkCounter` connect `BlinkCounter` to `test_realtime_pipeline.py`, `realtime_pipeline.py`, `replay_offline.py`?**
  _High betweenness centrality (0.075) - this node is a cross-community bridge._
- **Should `test_realtime_pipeline.py` be split into smaller, more focused modules?**
  _Cohesion score 0.08901515151515152 - nodes in this community are weakly interconnected._