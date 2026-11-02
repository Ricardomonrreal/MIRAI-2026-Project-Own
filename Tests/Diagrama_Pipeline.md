# Diagrama de flujo del pipeline (versión B, 2 nov 2026)

Estado del código en `Tests/simulation_B/` tras los Pasos 1–7 del protocolo. Línea discontinua = pendiente;
borde rojo = la sesión se detiene. Fuera del lazo quedan `test_realtime_pipeline.py` (chequeos offline) y
`replay_offline.py --equivalencia` (comparación con `results/h1_por_minuto.csv`).

```mermaid
flowchart TD
  RUN["run_simulation.py · lanzador<br/>live: emulador + conducta + pipeline<br/>offline: replay sin LSL"]

  subgraph S1["Paso 1 · Fuentes y emulación"]
    SRC["Sintético · ds007537 · SVRec · CSV AURA"]
    LS["load_source()<br/>recorte · 8 canales AURA · remuestreo<br/>canales rotos MAD · re-ref · V a µV<br/>--inject alpha / theta / blink"]
    EMU["mock_lsl_streamer.py<br/>push_chunk cada 20 ms · ts = t0 + n/fs<br/>LSL AURA + AURA_Markers"]
    SRC --> LS --> EMU
  end

  AURA["AURA real · Aura.exe<br/>LSL AURA · source_id AuraLSL-"]

  subgraph S2["Paso 2 · Entrada, filtro y búfer · realtime_pipeline.py"]
    FIND{"find_stream()<br/>nombre + esta PC<br/>+ prefijo source_id"}
    OFF["--offline · OfflineInlet<br/>bloques de 20 ms sin esperar"]
    PULL["pull_chunk timeout 0 + espera 5 ms<br/>marcadores → eventos.csv"]
    FILT["CausalFilter con estado<br/>1–40 Hz, 1–20 a 50 Hz · notch si cabe"]
    WIN["Windower<br/>ventana 6 s · avance 1 s"]
    FIND --> PULL
    OFF --> PULL
    PULL --> FILT --> WIN
  end

  subgraph S5A["Paso 5a · Chequeo de calidad a los 10 s"]
    QC["bad_channels: std sobre 5× o bajo 0.05×<br/>la mediana + malos de la fuente<br/>→ rehace rechazo y ROI"]
    ROI{"¿ROI θ y α<br/>con canales?"}
    QC --> ROI
  end

  subgraph S3["Paso 3 · Rechazo de artefactos"]
    REJ["9 segmentos de 2 s, paso 0.5 s<br/>fuera si PTP sobre 150 µV<br/>en Fp1 o F3/F4, o en la ROI<br/>EMG 25–40 Hz solo medido"]
    VAL{"¿≥ 1 segmento<br/>limpio?"}
    REJ --> VAL
  end

  subgraph S4["Paso 4 · Features · spectral_features.py"]
    PSD["Periodograma Hamming por segmento<br/>limpio · promedio por ROI<br/>θ: Fz+Cz · α: Pz, O1, O2"]
    FIT["fit_roi: specparam 2–30 Hz<br/>2–20 Hz a 50 Hz · como periodic()"]
    BAND["θ_per IAF−6 a IAF−2 · α_per IAF±2 · χ<br/>válida si R² ≥ 0.75"]
    PSD --> FIT --> BAND
  end

  subgraph S5B["Paso 5b · Calibración congelada · calibration.py"]
    CST{"¿Congelada?"}
    ACC["Acumula ventanas<br/>fases AURA: EO → μ, σ · EC → IAF<br/>sin fases: primeros 90 s"]
    ENO{"¿≥ 45 válidas<br/>por feature?"}
    EXT["+30 s<br/>máximo 2 veces"]
    FRZ["Congela IAF, μ, σ_Z<br/>autocorrelación + error de μ<br/>μ y σ de χ · Berger"]
    EW["EWMA solo con válidas<br/>θ τ 60 s · α τ 5 s<br/>Z = x̃ − μ entre σ_Z"]
    CST -->|no| ACC --> ENO
    ENO -->|no| EXT --> ACC
    ENO -->|sí| FRZ
    CST -->|sí| EW
  end

  subgraph S6["Paso 6 · Motor JITAI · jitai.py"]
    QB["Bloqueo de calidad<br/>χ bajo μ−3σ y EMG alto"]
    LVL["N3 pausa: Z_θ ≥ 1.5 por 30 s · refr. 300 s<br/>N1 cue: Z_α ≥ 1.5 por 5 s · refr. 60 s<br/>salen bajo 1.0 · inválidas mantienen contador"]
    N2["N2 fricción<br/>2 eventos nogo en 60 s<br/>sale tras 60 s · refr. 120 s"]
    PRI["Prioridad 3 > 2 > 1 · una activa<br/>el superior desplaza y bloquea"]
    QB --> LVL --> PRI
    N2 --> PRI
  end

  BEH["behavior_markers.py<br/>LSL MIRAI_Behavior"]
  NOGO["Tarea Scroll-NoGo<br/>pendiente"]

  OUT["Salidas: LSL MIRAI_JITAI · UDP/JSON 127.0.0.1:5005<br/>consola · runs/sesión/ ventanas.csv, eventos.csv"]
  REP["Paso 7 · reporte al cerrar<br/>latencia, CPU, memoria, rechazo, RMS de Z,<br/>disparos, Berger → reporte.md PASA / NO PASA"]
  AR["App AR · pendiente<br/>latencia total bajo 2 s"]

  STOP1(["Sale: 0 o más de 1 candidato"])
  STOP2(["Sesión detenida"])
  ABORT(["Calibración abortada"])
  INV["Ventana inválida<br/>más de 5 s seguidas: señal perdida"]

  RUN --> SRC
  RUN --> OFF
  LS --> OFF
  EMU --> FIND
  AURA --> FIND
  FIND --> STOP1
  WIN -->|"primera tras 10 s"| QC
  ROI -->|no| STOP2
  ROI -->|sí| REJ
  WIN -->|"siguientes"| REJ
  VAL -->|sí| PSD
  VAL -->|no| INV
  BAND --> CST
  INV --> CST
  EXT --> ABORT
  EW --> QB
  BEH --> N2
  NOGO -.-> N2
  PRI --> OUT --> REP
  OUT -.-> AR

  classDef pend stroke-dasharray:5 5
  classDef fin stroke:#A32D2D,stroke-width:1.5px
  class AR,NOGO pend
  class STOP1,STOP2,ABORT fin
```
