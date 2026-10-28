# Protocolo Técnico de Simulación y Pipeline en Tiempo Real (MIRAI 2026)

**Objetivo:** Validar el pipeline de procesamiento de señales EEG en tiempo real, el cálculo de biomarcadores periódicos libres de sesgo $1/f$, la calibración individual y la lógica de intervención neuroadaptativa (JITAI) mediante streaming LSL con datasets grabados (`ds007537` y `EEG-SVRec`), previo a las pruebas en vivo con la diadema AURA.

---

## 🏗️ 1. Arquitectura del Lazo Cerrado Simulado

El sistema se compone de dos procesos desacoplados que se comunican exclusivamente mediante **Lab Streaming Layer (LSL)**:

```mermaid
flowchart TD
    subgraph Proceso 1: Emulador de Hardware
        A["Datasets Grabados o fuente sintética\n(ds007537 / EEG-SVRec / CSV AURA / synthetic)"] --> B["mock_lsl_streamer.py\n(Control de tasa de muestreo)"]
        B -->|"Stream LSL: AURA (EEG crudo, µV) + AURA_Markers"| C["LSL Outlet\n(8 canales: Fp1, F3, Fz, F4, Cz, Pz, O1, O2)"]
    end

    subgraph Proceso 2: Pipeline Neuroadaptativo (Python)
        C -->|Stream LSL Inlet| D["realtime_pipeline.py\n(Búfer circular 3 s, hop 1 s)"]
        D --> E["Preprocesamiento y Veto Fp1\n(Filtro causal 1-40 Hz + Detección parpadeo)"]
        
        E --> F{"Estado de la Sesión"}
        
        F -->|t <= T_calib (90 s)| G["Módulo de Calibración\n(StandardScaler.fit)\n-> Congela mu y sigma"]
        F -->|t > T_calib| H["Extracción de Features\n(specparam: theta_per, alfa_per, 1/f)"]
        
        G -.->|Normalizador congelado| H
        H --> I["Cálculo de Score Z Individual\nZ = (x_t - mu) / sigma"]
        I --> J["Motor de Decisión JITAI\n(Persistencia temporal >= 3 s)"]
        J --> K["Salida Neuroadaptativa\n(Nivel 1 Cue / Nivel 2 Fricción / Nivel 3 Pausa)"]
    end
```

---

## 📋 2. Pasos de Implementación y Validación Técnica

Cada paso representa un hito técnico secuencial con entradas, acciones concretas y criterios de validación:

---

### [x] Paso 1: Emulador de Hardware y Transmisión LSL (`mock_lsl_streamer.py`) — implementado 28 oct 2026
* **Objetivo:** Reproducir EEG grabado (o sintético) muestra a muestra como si viniera de una diadema AURA física, de modo que el pipeline no distinga la simulación del hardware.
* **Archivos:** `Tests/simulation/mock_lsl_streamer.py` (emulador), `Tests/simulation/check_lsl_stream.py` (validador), `Tests/simulation/requirements.txt`.
* **Fuentes de datos:**
  - `synthetic` (por defecto): ruido 1/f (χ ≈ 1.5) + alfa posterior en la IAF + theta frontal (IAF − 4) + parpadeos de Poisson (~15/min, 150–300 µV en Fp1) + ruido de red. Permite tener el lazo vivo sin descargar datos.
  - **ds007537**: BrainVision (`sub-XX/eeg/sub-XX_task-phoneuse_eeg.vhdr`), referido a Cz en el registro.
  - **EEG-SVRec**: Neuroscan (`EEG/XX_data.cnt`, 62 canales, 1000 Hz, `data_format=int32`).
  - **CSV de AURA** (`timestamp, phase, label, channel_0..7`, µV, orden CH1–CH8): se transmite a su fs nativa (~50 Hz) o a `--fs`; cada cambio de `phase` sale como marcador `file:<fase>`. Prueba de enero 2026 en `AURA/data/` (ignorado por git).
  - Cualquier `.edf/.bdf/.set/.fif` legible por MNE.
  - ⚠️ En el proyecto solo están las cachés de features; hay que descargar los crudos (al menos `sub-01`) y apuntar `--source` a ellos.
* **Acciones completadas:**
  - [x] Lector MNE que recorta (`--start`, `--duration`), remuestrea a **250 Hz** con antialiasing y extrae los **8 electrodos AURA** en orden fijo: `Fp1, F3, Fz, F4, Cz, Pz, O1, O2` (orden por defecto CH1–CH8 del software AURA; Cz sustituye a FCz, que AURA no tiene; mapeo insensible a mayúsculas).
  - [x] `--fs` (250 por defecto) para emular la tasa real de la AURA (50 Hz en el CSV de prueba). En el sintético, la red se omite si cae por encima de Nyquist (se asume antialiasing del equipo).
  - [x] Re-referencia antes de seleccionar canales (`--ref average | none | M1,M2 | TP9,TP10`); detección MAD de canales rotos (excluidos del promedio e interpolados si son canales AURA).
  - [x] Conversión **V → µV** (sin ella el veto de 150 µV del Paso 3 nunca se activaría) y verificación de RMS por canal al arrancar.
  - [x] `pylsl.StreamOutlet` **`AURA`**, tipo `EEG`, 8 ch, `float32`, 250 Hz, con metadatos XDF (etiqueta, `microvolts`, tipo por canal) y `line_freq`, `reference`, `source`, `iaf`. *Nota:* `AURA_Power` de `VRehab.py` es un stream de potencias procesadas, no EEG crudo; el nombre `AURA` es el que publica el software real.
  - [x] Bucle de envío cada 10–20 ms (`--chunk-ms`) con marcas de tiempo calculadas desde el índice de muestra (`t0 + n/fs`, reloj `pylsl.local_clock`): el jitter de `sleep` en Windows (~15 ms) solo cambia el tamaño del bloque, no la tasa, y no hay deriva.
  - [x] Stream **`AURA_Markers`** con verdad de campo: parpadeos sintéticos (`blink`), inyecciones (`inject:<tipo>:on/off`) y anotaciones del archivo (`file:<etiqueta>`).
  - [x] Inyección de eventos (`--inject TIPO INICIO_S DUR_S AMP_µV`, repetible): `alpha` (IAF en Pz/O1/O2; prueba Berger), `theta` (IAF − 4 en Fz/Cz/F3/F4), `blink` (tren a 1 Hz en Fp1). Base para validar los Pasos 3, 6 y 7.
  - [x] `--line-freq` viaja en los metadatos para que el notch del Paso 2 use 50 Hz (SVRec) o 60 Hz (sintético, AURA en Cancún). `--loop` repite el registro con marcas continuas.
* **Uso:**
  ```bash
  pip install -r requirements.txt
  python mock_lsl_streamer.py                                   # sintético, 20 min
  python mock_lsl_streamer.py --inject alpha 120 20 15          # ojos cerrados simulados
  python mock_lsl_streamer.py --source "<ruta>/sub-01_task-phoneuse_eeg.vhdr" --start 60
  python mock_lsl_streamer.py --source "<ruta>/01_data.cnt" --ref M1,M2 --line-freq 50
  python mock_lsl_streamer.py --source ../../AURA/data/eeg_data_20260122_123839.csv   # replay AURA (50 Hz)
  python check_lsl_stream.py --seconds 120                      # en otra terminal
  ```
* **Criterio de Validación (`check_lsl_stream.py`):** tasa = fs nominal ± 0.1 % (marcas y reloj del receptor), 0 huecos, marcas monótonas, deriva acumulada < 5 ms, latencia de entrega p95 < 50 ms + 1 periodo de muestreo (54 ms a 250 Hz, 70 ms a 50 Hz: la marca de una muestra va hasta un periodo por detrás del envío), 8 canales, RMS en 1–200 µV (lista los canales fuera de rango).
  - ⚠️ **Colisión de nombres:** con **Aura.exe abierto** (aunque no haya diadema conectada) existen streams `AURA`, `AURA_Filtered` y `AURA_Power`, y otras PCs de la red con Aura publican los suyos (visto 28 oct: host `MSI`). Para simular con Aura abierto: `check_lsl_stream.py --source-id mirai-sim-AURA` o emulador con `--name AURA_SIM`. El verificador falla con la lista de candidatos si el nombre es ambiguo; el Paso 2 debe resolver igual (por `source_id`/host, nunca “el primero que responda”).
  - **Resultados 28 oct, máquina del proyecto** (Python 3.14, pylsl 1.18.6, 120 s cada uno):

    | Fuente | fs | Huecos | Deriva | Latencia p95 | Resultado |
    |---|---|---|---|---|---|
    | Sintético (+ `--inject alpha`) | 250 Hz | 0 | −1.53 ms | 27.5 ms | **PASA** (27 marcadores) |
    | Sintético `--fs 50` | 50 Hz | 0 | −1.04 ms | 54.7 ms | **PASA** |
    | ds007537 `sub-01` (`--start 60`, ref. promedio, 1000→250 Hz) | 250 Hz | 0 | +0.65 ms | 26.5 ms | **PASA** (0 canales rotos) |
    | CSV AURA enero 2026 (EO → EC) | 50 Hz | 0 | −1.89 ms | 54.7 ms | Transporte OK; **amplitud falla en Fp1, Cz, Pz** (calidad real del registro, esperado) |

    Antes (sesión Cowork): sintético 180 s con `--loop` y archivo de prueba a 1000 Hz con ref. promedio y M1/M2 → PASA. El lector del CSV reproduce las 8 fases y el Berger (O2 +7.2 dB, O1 +5.8 dB, Fz +4.7 dB).
  - Pendiente: un `.cnt` de EEG-SVRec (en `Datasets/MIRAI/EEG-SVRec` no hay crudos) y la AURA real con diadema conectada.

---

## 🎧 Adaptación a la diadema AURA

Configuración del equipo y análisis del CSV de prueba: **`Tests/AURA_Configuracion.md`**. Implicaciones para los Pasos 2–7:

| Tema | Situación AURA | Adaptación |
|---|---|---|
| **Montaje** | 8 canales, orden por defecto `Fp1, F3, Fz, F4, Cz, Pz, O1, O2`; sin FCz. | Theta frontal-medial = **Fz (+ Cz)**; alfa posterior = **Pz, O1, O2**; veto ocular en **Fp1**. Confirmar en *File → Configure Electrodes*. |
| **Frecuencia de muestreo** | Desconocida en vivo; el CSV de prueba está a **50 Hz**. | Todo el pipeline parametrizado por `fs = inlet.info().nominal_srate()` (ventanas en segundos, no en muestras). Si fs = 50: specparam hasta **min(40, 0.8·fs/2) = 20 Hz** (2–20 Hz; cubre theta y alfa con la IAF), pasa-banda 1–20 Hz, **sin notch** (60 Hz > Nyquist) y **sin veto EMG** 25–40 Hz. Si fs ≥ 250: parámetros offline (2–40 Hz) y veto EMG. |
| **Filtros del equipo** | La UI trae bandpass 15–50 Hz (borra theta/alfa); el CSV muestra solo un pasa-altos ~0.7 Hz. | Usar el bandpass más amplio en la UI y verificar si afecta al stream (guía §2.4). El pipeline filtra por su cuenta. |
| **Marcas de tiempo** | En el CSV, jitter y retrocesos (asignadas al recibir). | Usar las marcas de LSL del inlet (`proc_clocksync`) o el índice de muestra; nunca la columna `timestamp` del CSV. |
| **Canales rotos** | En la prueba: Fp1 saturado, Cz y Pz muertos, O1 con mal contacto. | Chequeo de calidad al inicio de la calibración (RMS / MAD por canal): un canal malo se excluye de su ROI (alfa = media de los canales posteriores válidos). Si **Fp1** está malo, el veto ocular pasa a F3/F4 con umbral propio. Si no queda ningún canal posterior válido, abortar la sesión. |
| **Calibración** | El protocolo de la prueba ya trae `baseline_eyes_open` 90 s + `baseline_eyes_closed` 90 s. | μ, σ del escalador sobre **ojos abiertos** (estado comparable a la tarea). Ojos cerrados se usa para estimar la **IAF** y como control de calidad (Berger ≥ 3 dB en O1/O2). |
| **Validación con datos reales** | CSV de enero 2026 con fases EO/EC/low_load/high_load. | Replay con `mock_lsl_streamer.py --source <csv>`: el Paso 7 comprueba que alfa_per sube en EC frente a EO y compara low_load vs high_load. |

---

### [ ] Paso 2: Búfer Circular Continuo y Filtrado Causal (`realtime_pipeline.py`)
* **Objetivo:** Capturar el flujo continuo de muestras desde LSL, acumularlas en memoria y aplicar filtrado digital en tiempo real sin distorsión de fase.
* **Acciones a completar:**
  - [ ] Conectar un `pylsl.StreamInlet` con resolución automática del stream.
  - [ ] Implementar una estructura FIFO (búfer circular) con:
    - Longitud de ventana: $W = 3.0\text{ s}$ ($750\text{ muestras}$ a 250 Hz).
    - Intervalo de evaluación (*hop size*): $S = 1.0\text{ s}$ ($250\text{ muestras}$), produciendo 1 salida cada segundo con 66% de solapamiento.
  - [ ] Aplicar filtrado causal rápido:
    - Pasa-banda: 1.0 – 40.0 Hz mediante `scipy.signal.sosfilt` con coeficientes Butterworth de segundo orden.
    - Filtro Notch centrado en la frecuencia de red (50/60 Hz).
* **Criterio de Validación:**
  - La ventana actualizada debe estar disponible cada segundo con un retraso de cálculo inferior a 10 ms.

---

### [ ] Paso 3: Veto de Artefactos Oculares en $Fp1$
* **Objetivo:** Impedir falsos positivos en la detección de fatiga causados por parpadeos o movimientos oculares.
* **Acciones a completar:**
  - [ ] Evaluar en cada ventana la señal del electrodo frontal ocular $Fp1$:
    - Calcular el rango pico a pico ($\max - \min$) y la desviación estándar local.
  - [ ] Si la amplitud supera el umbral de artefacto ($> 150\,\mu\text{V}$):
    - Marcar la ventana actual con el estado `ARTEFACTO_OCULAR = True`.
    - Omitir el envío de esta ventana hacia el motor de decisión de fatiga.
* **Criterio de Validación:**
  - Las ventanas con parpadeos evidentes se descartan automáticamente sin interrumpir el flujo continuo de las ventanas limpias.

---

### [ ] Paso 4: Descomposición Espectral y Extracción con `specparam`
* **Objetivo:** Descomponer el espectro de potencia en componentes aperiódicos ($1/f$) y periódicos libres de sesgo.
* **Acciones a completar:**
  - [ ] Estimar la densidad espectral de potencia (PSD) en la ventana limpia de 3 s mediante el método de Welch (`scipy.signal.welch`, ventanas de 1 s, solapamiento del 50%).
  - [ ] Ajustar el modelo `specparam.SpectralModel`:
    - Rango de frecuencia: 2 a 25 Hz.
    - Límites de ancho de pico: `[1.5, 8.0]`.
    - Altura mínima de pico: `0.1`.
  - [ ] Extraer el vector de características $\mathbf{x}_t$:
    - **$\theta_{\text{per}}$ (Theta periódico frontal):** Potencia en $Fz$ (+ $Cz$) sobre el fondo en banda 4–7 Hz (o adaptada a la IAF).
    - **$\alpha_{\text{per}}$ (Alfa periódico posterior):** Potencia en $Pz, O1, O2$ sobre el fondo en banda 8–12 Hz.
    - **Exponente $1/f$ ($\chi$):** Pendiente del fondo espectral aperiódico.
  - [ ] Respaldo de calidad: Si el ajuste produce $R^2 < 0.75$, utilizar la potencia espectral clásica como modo degradado de emergencia.
* **Criterio de Validación:**
  - El tiempo de cálculo de `specparam` en CPU para los canales clave debe ser $\le 100\text{ ms}$ por ventana.

---

### [ ] Paso 5: Calibración Individual Congelada (`StandardScaler`)
* **Objetivo:** Normalizar las señales a nivel intra-sujeto sin fuga de datos futuros (*no data leakage*), reproduciendo la arquitectura de `VRehab.py`.
* **Acciones a completar:**
  - [ ] **Fase 1: Calibración Basal ($t \le 90\text{ s}$):**
    - Acumular las features espectrales de los primeros 90 segundos de sesión (reposo / inicio del video).
    - Ajustar el escalador individual:
      ```python
      from sklearn.preprocessing import StandardScaler
      scaler = StandardScaler()
      scaler.fit(X_baseline)
      # Parámetros mu y sigma quedan CONGELADOS
      ```
  - [ ] **Fase 2: Inferencia en Tiempo Real ($t > 90\text{ s}$):**
    - Para cada nueva ventana entrante $\mathbf{x}_t$, calcular el puntaje Z individual respecto a su propia línea base:
      $$Z_t = \frac{\mathbf{x}_t - \mu_{\text{baseline}}}{\sigma_{\text{baseline}}}$$
* **Criterio de Validación:**
  - Las medias ($\mu$) y desviaciones ($\sigma$) no deben modificarse después de los 90 s iniciales (prohibido usar media móvil que anule la fatiga tónica).

---

### [ ] Paso 6: Motor de Decisión Neuroadaptativa JITAI (Escalera de Intervención)
* **Objetivo:** Disparar intervenciones graduales basadas en persistencia temporal del estado neurofisiológico.
* **Acciones a completar:**
  - [ ] Implementar un contador de persistencia temporal (exigir que el umbral se mantenga varias ventanas consecutivas para evitar disparos espurios).
  - [ ] Configurar las reglas de la escalera de intervención:

| Nivel de Intervención | Condición Neural | Persistencia Mínima | Acción Disparada (Simulación) |
|---|---|---|---|
| **Nivel 0 (Línea Base)** | $Z_{\theta} < 1.0$ y $Z_{\alpha} < 1.0$ | — | Estado neutro |
| **Nivel 1 (Cue Perceptual)** | $Z_{\alpha} \ge +1.5$ (Desenganche sostenido) | 3 s consecutivos (3 ventanas) | Log / Evento AR: *"Alerta visual sutil"* |
| **Nivel 2 (Fricción)** | $Z_{\theta} \ge +1.5$ (Fatiga tónica / sobreesfuerzo) | 5 s consecutivos (5 ventanas) | Log / Evento AR: *"Fricción de interacción"* |
| **Nivel 3 (Pausa Restaurativa)** | $Z_{\theta} \ge +2.0$ y $Z_{\alpha} \ge +2.0$ | 8 s consecutivos (8 ventanas) | Log / Evento AR: *"Pausa de recuperación"* |

  - [ ] Emitir la salida simulada mediante un paquete UDP/JSON local o impresión en consola con código de colores.
* **Criterio de Validación:**
  - Provocar deliberadamente tramos con alta potencia alfa/theta en el emulador y comprobar que los eventos Nivel 1, 2 y 3 se disparan únicamente tras cumplir la persistencia requerida.

---

### [ ] Paso 7: Benchmarking de Latencia y Validación Extremo a Extremo
* **Objetivo:** Verificar que el sistema completo cumple con las métricas de ingeniería requeridas para lazo cerrado.
* **Acciones a completar:**
  - [ ] Medir la **latencia total de procesamiento**:
    $$\text{Latencia} = t_{\text{evento\_emitido}} - t_{\text{última\_muestra\_ventana}} < 500\text{ ms}$$
  - [ ] Comprobar el uso de recursos: Uso de CPU $< 25\%$ en un núcleo estándar.
  - [ ] Prueba de resistencia: Ejecutar una simulación completa de 20 minutos sin desbordamiento de memoria ni desfase temporal respecto al reloj del sistema.
  - [ ] **Prueba de sensibilidad (Efecto Berger):** Simular un tramo de ojos cerrados y verificar que el Nivel 1 (alfa) reaccione con inmediatez.
* **Criterio de Validación:**
  - Generar un reporte final de métricas de desempeño técnico en consola y guardar el log de eventos.

---

## 📁 3. Estructura de Código a Implementar

Todo el código de la simulación se organizará en la carpeta `Tests/simulation/`:

```text
Tests/
├── simulation/
│   ├── mock_lsl_streamer.py      # Paso 1: Emulador de streaming LSL (+ AURA_Markers)
│   ├── check_lsl_stream.py       # Paso 1: Validador de tasa, huecos, deriva y latencia
│   ├── requirements.txt
│   ├── realtime_pipeline.py      # Pasos 2 y 3: Búfer circular, filtros y veto Fp1
│   ├── spectral_features.py      # Paso 4: Extracción Welch + specparam
│   ├── jitai_decision.py         # Pasos 5 y 6: Calibración StandardScaler y escalera JITAI
│   └── run_simulation.py         # Paso 7: Lanzador general y reporte de latencia
├── AURA_Configuracion.md         # Configuración del equipo y análisis del CSV de prueba
└── Protocolo_Simulacion_Pipeline.md # Este documento de seguimiento
```
