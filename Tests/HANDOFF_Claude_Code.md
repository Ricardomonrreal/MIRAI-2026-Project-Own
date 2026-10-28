# Handoff: sesión Cowork → Claude Code (MIRAI 2026, 28 oct 2026)

Este documento resume una sesión de trabajo para continuarla en Claude Code desde la raíz del proyecto
(`C:\Users\ricar\Documents\Ucaribe\MIRAI 2026\Project`). Léelo completo antes de actuar.

---

## 1. Contexto del proyecto

- Protocolo de trabajo: `Tests/Protocolo_Simulacion_Pipeline.md` (7 pasos: emulador LSL → búfer/filtros → veto Fp1 → specparam → calibración congelada → escalera JITAI → benchmarking).
- Plan general y escenarios: `Tests/Plan_Avances.md`.
- Pipeline offline ya validado: `Tests/datasets workflow/ds007537/h1_ds007537.py` y `EEG-SVRec/h1_svrec.py` (épocas de 2 s, Welch, IAF, `specparam` con `peak_width_limits=[1,8]`, `max_n_peaks=6`, `aperiodic_mode="fixed"`, rango 2–40 Hz, función `periodic()`).
- En el proyecto **solo están las cachés de features** de los datasets; los crudos (.vhdr de ds007537, .cnt de SVRec) hay que descargarlos.
- `AURA/AURA_Software/VRehab.py` lee el stream `AURA_Power` (potencias procesadas, **no** EEG crudo). El EEG crudo de AURA sale por LSL con el nombre `AURA`.

## 2. Revisión del protocolo (problemas detectados, aún sin corregir en Pasos 2–7)

**Críticos**
1. **Escala del efecto vs. umbrales:** los efectos tónicos son pequeños (ds007537: alfa_per +0.43 dB en 10 min; Cao: theta_per +0.007 dB/min), pero σ de la calibración es el ruido entre ventanas de 3 s (varios dB). Un Z ≥ 1.5 sostenido 5 s casi nunca vendrá de fatiga tónica. → Suavizar el **feature** (EWMA/promedio de 30–60 s) y calibrar μ, σ sobre el feature suavizado; la línea base sigue congelada.
2. **Veto Fp1 + persistencia:** con ~15–17 parpadeos/min, solo ~43 % de las ventanas de 3 s quedan limpias; los contadores de 3/5/8 ventanas se reiniciarían siempre. → Rechazar segmentos de 1 s dentro de la ventana, que una ventana vetada **mantenga** el contador, añadir veto EMG (25–40 Hz posterior).
3. Formatos/unidades/nombre de stream (resuelto en el Paso 1, ver §3).

**Inconsistencias con el pipeline offline:** specparam 2–25 Hz (offline 2–40), `peak_width_limits` [1.5,8] (offline [1,8]), theta 4–7 Hz (offline IAF−6 a IAF−2), Welch de 1 s → 1 Hz de resolución (offline 0.5 Hz). Recomendado: ventanas de 4 s o segmentos de 2 s, **importar `periodic()` del script offline**, calcular la IAF en la calibración. El respaldo R² < 0.75 cambia el tipo de feature y rompe el Z → marcar ventana inválida o usar un segundo escalador.

**JITAI:** estados sin definir entre 1.0 ≤ Z < 1.5; faltan histéresis, prioridad entre niveles y periodo refractario. Contradicción con `Plan_Avances.md` §3.2 (allí fricción = control inhibitorio/NoGo, pausa = tónico). χ (1/f) se calcula pero no se usa. Definir qué condición es la línea base (ojos abiertos vs. cerrados cambia alfa enormemente).

**Otros:** mantener el estado del filtro entre bloques (`sosfilt` con `zi`); un IIR causal sí distorsiona la fase (irrelevante para PSD). Notch según la red del registro (SVRec 50 Hz; Cancún 60 Hz); un Butterworth de orden 2 solo atenúa ~8 dB a 60 Hz. Unificar latencia objetivo (protocolo < 500 ms, Plan < 2 s). Añadir modo replay sin LSL para comparar features con `h1_por_minuto.csv`. MNE ≥ 1.14 elimina el montaje `standard_1005` (usar `colin27_1005`); afecta a `h1_*.py`.

## 3. Paso 1 — HECHO

Archivos en `Tests/simulation/`: `mock_lsl_streamer.py`, `check_lsl_stream.py`, `requirements.txt`. Protocolo actualizado (Paso 1 marcado `[x]`).

- Fuentes: `synthetic` (1/f + alfa en IAF + theta IAF−4 + parpadeos Poisson ~15/min en Fp1 + red), BrainVision, CNT (`data_format=int32`), EDF/BDF/SET/FIF.
- Remuestreo a 250 Hz, re-referencia (`--ref average|none|M1,M2`), detección MAD de canales rotos, V→µV.
- Stream `AURA` (EEG, 8 ch, float32, metadatos con `line_freq`, `reference`, `iaf`) + `AURA_Markers` (blink, `inject:<tipo>:on/off`, `file:<anotación>`).
- `--inject alpha|theta|blink INICIO DUR AMP`, `--loop`, `--wait`, `--chunk-ms`.
- Validación (sintético, 180 s): 250.0000 Hz, 0 huecos, deriva −0.38 ms, latencia p95 26 ms → PASA.
- Orden de canales actual en el emulador: `Fz, FCz, F3, F4, Pz, O1, O2, Fp1` → **debe cambiarse** al orden real de AURA (ver §4).

## 4. Análisis del CSV real de AURA (`eeg_data_20260122_123839.csv`) — PRELIMINAR, interrumpido

El usuario adjuntó dos capturas de la interfaz AURA y este CSV (configuración desconocida). Guardarlo en el proyecto antes de continuar (no está en la carpeta; pedirlo al usuario si hace falta).

**Interfaz AURA (capturas):** canales mostrados en orden `Fp1, F3, Fz, F4, Cz, Pz, O1, O2`; Notch 60 Hz; **Bandpass 15–50 Hz** (elimina theta y alfa: hay que cambiarlo); checkbox **LSL Stream Out** desmarcado; contact quality de CH1–CH8 y REF en rojo; posiciones del mapa 3D: F3, Fz, F4, C3, Cz, C4, P3, Pz, P4, P8, O1, O2 (no aparece **FCz**).

**CSV:** columnas `timestamp, phase, label, channel_0..channel_7`; 30 738 filas, 614.7 s.
- **Frecuencia efectiva ≈ 50 Hz, no 250 Hz.** Δt mediana 20 ms. Nyquist 25 Hz; si no hay antialiasing, **60 Hz se pliega exactamente a 10 Hz (alfa)**.
- Marcas de tiempo **no monótonas** (2 293 Δt negativos, mínimo −14.6 ms) y 9 huecos > 100 ms (máx 186 ms) → probablemente marcas asignadas por el receptor/script, no por LSL.
- Fases (protocolo de la prueba): setup 12 s · baseline_eyes_open 90 s · baseline_eyes_closed 90 s · baseline_completed · low_load 180 s · low_load_completed · high_load 180 s · analysis.
- **channel_4 y channel_5 muertos** (idénticos, ~0, colas de filtro) → con el orden por defecto serían **Cz y Pz**.
- channel_0 saturado/malo (|x| máx 361 316) → Fp1 (parpadeos/contacto). channel_6 con mal contacto (σ 1 690, 34 % de muestras > 150 µV; potencia enorme en high_load → artefacto). channel_3 regular (14 % > 150 µV).
- Correlaciones altas ch3–ch6 (0.89) y ch2–ch7 (0.84) → revisar referencia/puentes de gel.
- **Efecto Berger (alfa 8–12 Hz, ojos cerrados vs. abiertos):** ch7 +7.2 dB, ch6 +5.8 dB, ch2 +4.8 dB, ch3 +2.5 dB, ch0/ch1 ≈ 0 → consistente con **ch6 = O1, ch7 = O2** (orden por defecto `Fp1,F3,Fz,F4,Cz,Pz,O1,O2`). El mapeo parece ser el orden por defecto, pero confirmarlo en *File → Configure Electrodes*.
- Espectros sin pico alfa claro (máximo de 5–15 Hz cerca de 5.5 Hz); compatible con filtrado/decimación desconocidos. Falta revisar si el filtro 15–50 Hz se aplicó al CSV.

**Pendiente de este punto (lo que pidió el usuario):**
1. Guía de configuración de AURA: contacto (todos los CH y REF en "good", gel), Notch 60 Hz, bandpass lo más amplio posible o sin filtro (el pipeline filtra 1–40 Hz), activar *LSL Stream Out*, confirmar la frecuencia real del stream LSL (¿250 Hz?) y si los filtros de la UI se aplican al stream, mapeo de electrodos y grabación CSV de respaldo con *Event* (barra espaciadora).
2. Adaptar el protocolo a AURA: montaje recomendado = orden por defecto `Fp1, F3, Fz, F4, Cz, Pz, O1, O2` (Cz sustituye a FCz; theta frontal-medial con Fz [+Cz]); actualizar `AURA_CHANNELS` en `mock_lsl_streamer.py` a ese orden; soportar fs = 50 Hz si el stream real es así (theta y alfa caben, pero no la banda > 25 Hz ni el veto EMG 25–40 Hz); resolver el aliasing de 60 Hz; añadir un lector del CSV de AURA como `--source` (columnas `channel_0..7`, fases como marcadores) y usar este CSV para validar el lazo con el Berger real (fases EO/EC).
3. Verificar en vivo con `check_lsl_stream.py --name AURA` conectado a la diadema real.

## 5. Herramientas

- MarkItDown (`pip install 'markitdown[all]'`) para convertir PDFs/Office a Markdown antes de leerlos y ahorrar tokens.
