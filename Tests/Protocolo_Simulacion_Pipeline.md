# Protocolo Técnico de Simulación y Pipeline en Tiempo Real (MIRAI 2026)

**Objetivo:** Validar el pipeline de procesamiento de señales EEG en tiempo real, el cálculo de biomarcadores periódicos libres de sesgo $1/f$, la calibración individual y la lógica de intervención neuroadaptativa (JITAI) mediante streaming LSL con datasets grabados (`ds007537` y `EEG-SVRec`), previo a las pruebas en vivo con la diadema AURA.

---

## 🏗️ 1. Arquitectura del Lazo Cerrado Simulado

El sistema se compone de dos procesos desacoplados que se comunican exclusivamente mediante **Lab Streaming Layer (LSL)**:

```mermaid
flowchart TD
    subgraph Proceso 1: Emulador de Hardware
        A["Datasets Grabados\n(ds007537 / EEG-SVRec)"] --> B["mock_lsl_streamer.py\n(Control de tasa de muestreo)"]
        B -->|Stream LSL: 'AURA_Simulated'| C["LSL Outlet\n(8 canales: Fz, FCz, F3, F4, Pz, O1, O2, Fp1)"]
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

### [ ] Paso 1: Emulador de Hardware y Transmisión LSL (`mock_lsl_streamer.py`)
* **Objetivo:** Leer archivos EEG grabados y reproducirlos muestra a muestra como si provinieran de una diadema AURA física.
* **Archivos fuente:** `Tests/datasets workflow/ds007537/` (sujeto limpio `sub-01`) o `Tests/datasets workflow/EEG-SVRec/`.
* **Acciones a completar:**
  - [ ] Implementar lector de archivos (`.edf` o `.mat`) extrayendo únicamente los **8 electrodos AURA**:
    - Frontales: `Fz`, `FCz`, `F3`, `F4`, `Fp1`
    - Posteriores: `Pz`, `O1`, `O2`
  - [ ] Configurar un `pylsl.StreamOutlet`:
    - Nombre del Stream: `AURA_Power` (para paridad con `VRehab.py`) o `AURA_Simulated`.
    - Frecuencia nominal: $fs = 250\text{ Hz}$.
  - [ ] Implementar el bucle de envío temporizado con `time.perf_counter()` en bloques pequeños (10–20 ms) para garantizar sincronía exacta con el reloj real y evitar desbordamientos de búfer.
* **Criterio de Validación:**
  - Ejecutar el script y comprobar con una herramienta de prueba LSL o un simple receptor que se reciben exactamente 250 muestras por segundo sin deriva.

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
    - **$\theta_{\text{per}}$ (Theta periódico frontal):** Potencia en $Fz / FCz$ sobre el fondo en banda 4–7 Hz (o adaptada a la IAF).
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
│   ├── mock_lsl_streamer.py      # Paso 1: Emulador de streaming LSL
│   ├── realtime_pipeline.py      # Pasos 2 y 3: Búfer circular, filtros y veto Fp1
│   ├── spectral_features.py      # Paso 4: Extracción Welch + specparam
│   ├── jitai_decision.py         # Pasos 5 y 6: Calibración StandardScaler y escalera JITAI
│   └── run_simulation.py         # Paso 7: Lanzador general y reporte de latencia
└── Protocolo_Simulacion_Pipeline.md # Este documento de seguimiento
```
