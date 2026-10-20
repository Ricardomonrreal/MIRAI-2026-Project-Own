# Guía de Uso: Nuevos Canales, Modulación Automática y Datasets EEG

Esta guía explica la arquitectura de los **6 canales objetivo** configurados en [Demo_processing.py](file:///c:/Users/ricar/Documents/Ucaribe/MIRAI%202026/Project/Tests/EEG%20Dataset%209-10/Demo_processing.py), la **modulación automática** ante datasets con menos canales (como el dataset Stroop actual) y la **representación visual del montaje 10-20** integrada en el programa.

---

## 1. Canales Objetivo y su Función Neurocientífica

El sistema está diseñado para investigar los siguientes **6 electrodos** del sistema estándar internacional 10-20:

```text
               (Nariz / Frente)
                     Fz         <- Theta tónico (Control ejecutivo / Fatiga mental)
               F3          F4   <- Asimetría Alfa Frontal: FAA = ln(α_F4) - ln(α_F3)
            
                     Pz         <- Alfa parietal (Atención visoespacial)
               O1          O2   <- Alfa occipital (Desactivación visual / Fatiga sensorial)
```

| Electrodo | Color en Visor | Región Cerebral | Rol en la Investigación | Métrica Principal |
| :--- | :--- | :--- | :--- | :--- |
| **Fz** | 🟣 Púrpura (`#7c62db`) | Frontal medial | Control cognitivo, esfuerzo atencional y fatiga tónica. | **Theta tónico (4–8 Hz)** |
| **F3** | 🔵 Azul (`#2a82e4`) | Frontal izquierdo | Corteza prefrontal dorsolateral izquierda (aproximación). | **FAA:** $\ln(\text{Alfa}_{F4}) - \ln(\text{Alfa}_{F3})$ |
| **F4** | 🔵 Azul (`#2a82e4`) | Frontal derecho | Corteza prefrontal dorsolateral derecha (evitación/alerta).| |
| **Pz** | 🟢 Verde (`#1ba06f`) | Parietal medial | Atención sostenida y consolidación atencional. | **Alfa posterior (8–13 Hz)** |
| **O1** | 🟢 Verde (`#1ba06f`) | Occipital izquierdo| Corteza visual primaria y somnolencia / fatiga perceptual.| (Promedio entre Pz, O1 y O2) |
| **O2** | 🟢 Verde (`#1ba06f`) | Occipital derecho | Procesamiento visual continuo. | |

---

## 2. Modulación Automática de Canales

El cargador de datos `load_eeg` ahora **modula y detecta dinámicamente** qué canales existen en cada archivo sin forzar errores ni mostrar señales erróneas:

### A. Para los archivos actuales de Stroop (`raw_data/Stroop_Data`):
- Los registros originales de Stroop provienen de un OpenBCI Cyton de 8 canales (`Fp1, Fp2, F7, F3, Fz, F4, F8, C2`).
- **Detección automática:** El programa identifica la estructura de columnas numéricas de OpenBCI y extrae automáticamente los canales objetivo disponibles: **`F3`** (col 4), **`F4`** (col 6) y **`Fz`** (col 5).
- **Adaptación:**
  - El visor crea 3 subplots para `F3`, `F4` y `Fz`.
  - La pestaña del mapa y la barra lateral indican que `Pz`, `O1` y `O2` no existen en este hardware.
  - Se calculan **Theta Fz** y **FAA (F3/F4)** con total precisión.
  - El alfa posterior se marca limpiamente como `No disponible (requiere Pz, O1 u O2)`.

### B. Para nuevos datasets limpios (6 canales o con encabezados):
- Si el archivo contiene encabezados (`F3, F4, Fz, Pz, O1, O2`): los lee automáticamente en orden.
- Si el archivo tiene 6 columnas numéricas (o 7 con columna índice de muestra): asume los 6 canales y los activa todos.
- Los 6 electrodos se iluminan en el mapa visual y se calculan los 3 biomarcadores simultáneamente.

---

## 3. Representación Visual del Montaje 10-20 en la Interfaz

Dentro de `Demo_processing.py`, se integró una pestaña gráfica dedicada: **`🧠 Mapa de Electrodos (10-20)`** (accesible también mediante el botón lateral *"🧠 Ver mapa de electrodos"*):

- **Vista superior de la cabeza:** Contorno craneal, nariz orientada al frente y orejas laterales ("Frente", "Izq.", "Der.").
- **Electrodos activos vs. ausentes:**
  - Los electrodos **presentes** en el archivo actual se iluminan con su color temático correspondiente (azul, púrpura o verde) en alta opacidad y con su etiqueta en negrita.
  - Los electrodos **ausentes** en el dataset actual se dibujan atenuados en gris claro con la marca `(n/d)`.
- **Panel de diagnóstico en vivo:** A la derecha del diagrama se describe detalladamente:
  - Nombre del archivo y frecuencia de muestreo.
  - Lista de canales activos y ausentes.
  - Diagnóstico de qué biomarcadores pueden calcularse con el registro actual.
- **Mini-mapa en la ventana PSD:** Al abrir *"Analizar PSD / biomarcadores"*, en la esquina inferior derecha también se renderiza el esquema anatómico activo para contextualizar los resultados numéricos.

---

## 4. Cómo Buscar y Limpiar Nuevos Datasets

### Dónde buscar:
1. **OpenNeuro (Recomendado):**
   - Dataset destacado: **`ds007537`** (*Mishra et al., 2026*): interacción natural con smartphones (Reels/Shorts vs. descanso), 64 canales incluyendo `F3, F4, Fz, Pz, O1, O2`.
2. **PhysioNet:** Datasets de fatiga cognitiva y atención prolongada.
3. **Zenodo / Mendeley Data:** Búsquedas tipo `EEG cognitive fatigue 32 channels`.

### Script para exportar solo los 6 canales listos:
```python
import mne
import pandas as pd

# 1. Cargar archivo original (ej. EDF, BDF, BrainVision)
raw = mne.io.read_raw_bdf("registro_original.bdf", preload=True)

# 2. Canales objetivo
target_channels = ['F3', 'F4', 'Fz', 'Pz', 'O1', 'O2']
raw.rename_channels(lambda s: s.strip().replace('.', ''))
raw.pick_channels([ch for ch in target_channels if ch in raw.ch_names], ordered=True)

# 3. Re-muestreo a 250 Hz (opcional para fluidez)
if raw.info['sfreq'] > 250:
    raw.resample(250.0)

# 4. Convertir a microvoltios (µV) y guardar con encabezado
data_uv = raw.get_data() * 1e6
df = pd.DataFrame(data_uv.T, columns=raw.ch_names)
df.to_csv("dataset_6canales_listo.csv", index=False)
print("Archivo listo para cargar en Demo_processing.py")
```
