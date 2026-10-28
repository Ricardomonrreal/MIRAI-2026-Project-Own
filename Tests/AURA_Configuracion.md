# Configuración de la AURA para MIRAI 2026

Guía para que la diadema AURA (software v1.2.x / instalador 2.0.1) entregue EEG utilizable para el pipeline del
`Protocolo_Simulacion_Pipeline.md` (theta periódico frontal y alfa periódico posterior). Basada en la interfaz
(captura del 28 oct 2026), el manual de `AURA/AURA_Software/README.md` y el CSV de prueba
`AURA/data/eeg_data_20260122_123839.csv`.

---

## 1. Ajustes de la interfaz (de arriba a abajo)

| Control | Valor en la captura | Valor recomendado | Motivo |
|---|---|---|---|
| **CONNECTION** | — | Puerto COM de la AURA → *Connect* | Sin conexión en vivo no hay stream LSL. |
| Pestaña de señal | EEG | **EEG** | ACC/AVCE son acelerómetro/giroscopio. |
| **File → Configure Electrodes** | (desconocido) | CH1…CH8 = **Fp1, F3, Fz, F4, Cz, Pz, O1, O2** → guardar | Es el orden que muestra la gráfica y el que usa el pipeline (`AURA_CHANNELS`). Hay que confirmar que coincide con la posición física de cada electrodo en el gorro. |
| **Contact quality** | CH1–CH8 y REF en **rojo (BAD)** | Todos en **azul (GOOD)** | Con REF en rojo, *todos* los canales quedan mal. Colocar primero REF (y tierra/bias), luego cada electrodo con gel hasta que se ponga azul. |
| **Notch Filter** | 60 Hz | **60 Hz** | Red eléctrica en México (Cancún). |
| **Bandpass Filter** | **15–50 Hz** | **La opción más amplia** (p. ej. 0.5–45, 1–50) **o sin filtro** | 15–50 Hz **elimina theta (4–7 Hz) y alfa (8–12 Hz)**, que son justo nuestros biomarcadores. El pipeline aplica su propio 1–40 Hz. |
| Scale | Autoscale | Indiferente | Solo afecta la visualización. |
| **LSL Stream Out** | **desmarcado** | **marcado** | Publica el stream LSL `AURA` (EEG crudo). Sin esto el pipeline no recibe nada. |
| FFT (Log, Smoothness) | — | Indiferente | Útil para ver el pico alfa con ojos cerrados (§3). |
| Grabación (botón rojo) | — | **Grabar siempre** como respaldo | CSV en `Documents\Aura EEG Records` (o la carpeta elegida con el icono de guardar). |
| **Event** (barra espaciadora) | — | Marcar inicio/fin de cada fase | Queda en el CSV; permite alinear fases si falla el stream. |

> El manual dice que *LSL Stream Out* envía “raw signals”, así que probablemente los filtros de la interfaz **no**
> se aplican al stream. Hay que comprobarlo (§2, paso 4): si se aplican, el bandpass 15–50 Hz arruinaría también
> los datos del pipeline.

## 2. Verificación del stream (antes de cada sesión)

Requiere `pip install -r Tests/simulation/requirements.txt` (incluye `pylsl`).

1. Conectar la AURA, contacto en azul (GOOD) en todos los canales y REF, marcar *LSL Stream Out*.
2. En otra terminal:
   ```bash
   python Tests/simulation/check_lsl_stream.py --name AURA --seconds 120
   ```
3. Anotar del reporte:
   - **`nominal ... Hz`**: la frecuencia real del stream. Esperado 250 Hz; el CSV de prueba está a **50 Hz** (ver §4).
   - **Canales/unidades**: etiquetas y si vienen en µV.
   - **Huecos / marcas monótonas / deriva**: deben pasar como con el emulador.
   - **RMS por canal**: 5–50 µV en canales buenos; ~0 = canal muerto; > 200 = mal contacto.
4. **¿Los filtros de la UI llegan al stream?** Repetir el paso 2 con el bandpass en 15–50 Hz y luego en la opción
   más amplia. Si el RMS de O1/O2 cambia mucho, los filtros sí se aplican al stream → usar siempre la opción más amplia.

**Lo que publica Aura.exe por LSL** (visto el 28 oct con el software abierto y *sin* diadema): `AURA` (EEG, 8 ch,
float32, **250 Hz nominal**, sin etiquetas de canal en los metadatos), `AURA_Filtered` (8 ch, 250 Hz; presumiblemente
con los filtros de la UI) y `AURA_Power` (40 ch, 100 Hz; el que lee `VRehab.py`). El pipeline debe leer **`AURA`**
(crudo) y asumir el orden CH1–CH8 de *Configure Electrodes*, porque el stream no trae etiquetas. Si otra PC de la red
tiene Aura abierto aparece un segundo `AURA`: `check_lsl_stream.py` lo detecta y pide `--source-id`.

> Que el stream sea de 250 Hz nominales hace pensar que los 50 Hz del CSV de enero vienen del script que lo grabó
> (diezmado), no del equipo. Confirmarlo con la diadema conectada (tasa efectiva en el reporte).

## 3. Prueba rápida de calidad: efecto Berger (2 min)

1 min ojos abiertos mirando un punto fijo, 1 min ojos cerrados, marcando cada cambio con la barra espaciadora.
En la FFT (o con el script de `AURA/data`), la potencia alfa 8–12 Hz en **O1/O2 debe subir ≥ 3 dB** con ojos cerrados.
Si no sube, revisar contacto de O1/O2 y REF antes de seguir: sin Berger no hay alfa confiable para H1.

## 4. Lo que muestra el CSV de prueba (enero 2026, configuración desconocida)

Columnas `timestamp, phase, label, channel_0..channel_7`; 30 738 muestras en 614.7 s. El formato (fases) no es el
CSV nativo de la AURA: lo generó un script de experimento que leía el stream (marcas de `pylsl.local_clock`).

- **Frecuencia: 50 Hz exactos** (4 500 muestras en cada fase de 90 s). Las marcas de tiempo tienen jitter y
  2 293 retrocesos: se asignaron al recibir, no son las de LSL → usar el índice de muestra, no la columna `timestamp`.
  Falta saber si 50 Hz es la tasa del equipo o si el script diezmó; `check_lsl_stream.py` lo resuelve (§2).
- **Filtro aplicado:** pasa-altos ~0.7 Hz y nada de 15–50 Hz (domina 1–4 Hz). No se ve una línea en 10 Hz,
  así que no hay indicio fuerte de que 60 Hz se haya plegado sobre alfa.
- **Fases:** setup 12 s · baseline_eyes_open 90 s · baseline_eyes_closed 90 s · pausa 17 s · low_load 180 s ·
  pausa 41 s · high_load 180 s · analysis 5 s.
- **Canales** (asumiendo orden por defecto):

| Canal | Electrodo | Estado | Berger (EC vs EO, 8–12 Hz) |
|---|---|---|---|
| channel_0 | Fp1 | saturado (máx 361 316 µV) | — |
| channel_1 | F3 | aceptable (σ 84 µV) | +0.4 dB |
| channel_2 | Fz | bueno (σ 41 µV) | +4.7 dB |
| channel_3 | F4 | regular (σ 210 µV) | +2.5 dB |
| channel_4 | Cz | **muerto** (≈ 0, cola de filtro) | — |
| channel_5 | Pz | **muerto** (idéntico a ch4) | — |
| channel_6 | O1 | mal contacto (σ 1 690 µV) | +5.8 dB |
| channel_7 | O2 | bueno (σ 42 µV) | **+7.2 dB** |

  El Berger más fuerte en ch6/ch7 respalda que ch6 = O1 y ch7 = O2 (orden por defecto). Cz y Pz muertos y
  idénticos sugieren electrodos desconectados o canales no asignados en *Configure Electrodes*.
- **Consecuencias para el pipeline:** a 50 Hz el espectro útil llega a 25 Hz: theta y alfa caben, pero no el
  rango 2–40 Hz de specparam offline ni un veto EMG en 25–40 Hz. Con Fp1 saturado no hay veto ocular; con Pz muerto
  y O1 ruidoso, el alfa posterior depende de O2. Ver la sección “Adaptación a AURA” del protocolo.

## 5. Replay del CSV con el emulador

```bash
python Tests/simulation/mock_lsl_streamer.py --source AURA/data/eeg_data_20260122_123839.csv          # 50 Hz nativos
python Tests/simulation/mock_lsl_streamer.py --source AURA/data/eeg_data_20260122_123839.csv --fs 250 # remuestreado
```

Las fases salen como marcadores `file:<fase>` en `AURA_Markers`. El remuestreo a 250 Hz solo sirve para probar el
código a 250 Hz: no recupera contenido por encima de 25 Hz.
