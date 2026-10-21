# Resumen de sesión · MIRAI 2026 (19–21 oct 2026)

Índice compacto de todo lo producido y decidido. El detalle está en los archivos enlazados.

---

## 1. Documentos y resultados generados

| Archivo | Qué contiene |
|---|---|
| [Analisis_Scope_v2.md](Analisis_Scope_v2.md) | Análisis de `/Tests`; búsqueda de datasets; revisión de la teoría (qué está sustentado y qué corregir); texto por diapositiva para la propuesta v2; pipeline; Gantt de 12 semanas; **§5 Intervención** (JITAI, por qué AR y no VR, escalera de intervención, Estudio 2 / H4); bibliografía APA |
| [Project Proposal MIRAI Ricardo_Monrreal.pptx](Project%20Proposal%20MIRAI%20Ricardo_Monrreal.pptx) | Propuesta v1 convertida de PDF a **PowerPoint editable** (13 diapositivas, 16:9, fuentes Cambria/Calibri) |
| [ds007537/Reporte_H1_ds007537.md](ds007537/Reporte_H1_ds007537.md) | **Reporte de validación de H1**: método, control de calidad, resultados y la interpretación de **alfa periódica vs total** |
| [ds007537/h1_ds007537.py](ds007537/h1_ds007537.py) | Pipeline de análisis de H1 (MNE + specparam + parpadeo + pupila) |
| [ds007537/results/h1_reporte.txt](ds007537/results/h1_reporte.txt) | Salida estadística completa |
| [ds007537/results/h1_trayectorias.png](ds007537/results/h1_trayectorias.png) | Figura con las 8 medidas por minuto |
| [ds007537/results/h1_por_minuto.csv](ds007537/results/h1_por_minuto.csv) · [h1_pendientes.csv](ds007537/results/h1_pendientes.csv) · [h1_calidad.csv](ds007537/results/h1_calidad.csv) | Datos por minuto, por sujeto y control de calidad |
| [EEG Dataset 9-10/Demo_processing.py](EEG%20Dataset%209-10/Demo_processing.py) | Visor: ahora también abre **ds007537** (montaje AURA, segmento de smartphone) |

Fuentes originales: [Project Proposal MIRAI Ricardo_Monrreal (1).pdf](Project%20Proposal%20MIRAI%20Ricardo_Monrreal%20(1).pdf) · [Scope_Dopamine_Scrolling.pdf](Scope_Dopamine_Scrolling.pdf)

---

## 2. Decisiones clave

- **Scope:** no se mide dopamina; se mide **fatiga cognitiva con pérdida del control inhibitorio**: theta y alfa **tónicos** (fatiga) y theta frontal medial **fásico** (inhibición).
- **H1 se divide** en **H1a (alfa posterior)** y **H1b (theta frontal)**.
- **El theta fásico** se mide con un *probe* inhibitorio (Go/NoGo antes y después, o NoGo dentro del feed, "Scroll-NoGo"), no contando ráfagas en la señal continua.
- **Medida alfa principal: alfa periódica** (sobre el fondo 1/f), no la potencia total.
- **Control de somnolencia: parpadeos desde Fp1/Fp2**, reproducible con AURA. Si se usa eye-tracking, es solo apoyo.
- **Montaje AURA recomendado:** `Fz, FCz, F3, F4, Pz, O1, O2, Fp1`.
- **Intervención:** JITAI guiado por el estado neural. **AR durante el scrolling** (independiente de la app, sin bloquear el teléfono) y **VR fuera de la sesión** (entrenamiento Scroll-NoGo). La prueba que justifica el sistema es **H4**: intervención disparada por EEG vs por temporizador.
- **Innovación** planteada como pregunta de investigación: medir la pérdida de control inhibitorio **durante** el scrolling y comprobar si intervenir según el estado neural supera a intervenir por tiempo.
- **Exclusiones en ds007537:** sub-22, sub-23 y sub-27 (registros ruidosos).

---

## 3. Resultados de H1 en ds007537 (27 sujetos, 10 min de smartphone)

| | Video corto (n = 12) | Juego (n = 13) |
|---|---|---|
| Alfa **total** | sin cambio (+0.12 dB, p = 0.30) | **↑ +0.47 dB, p = 0.013** |
| Alfa **periódica** | **↑ +0.43 dB, 10/12 sujetos, p = 0.04** (p = 0.064 sin los ajustes malos) | sin cambio |
| Exponente 1/f | **↑ (p = 0.02)**, distinto de juego (p = 0.02) | ↓ (n.s.) |
| Theta total y periódica | sin cambio | sin cambio |
| Parpadeo (EEG) / pupila | sin cambio | parpadeo **↑ +2.3/min, p = 0.007** |

**Conclusión:** en video corto el **ritmo alfa** sube mientras el fondo 1/f se inclina, y por eso la alfa total se ve plana. Sin señales de somnolencia, el patrón es compatible con **desenganche cortical**, pero **no prueba fatiga**: la habituación, la divagación mental y el efecto del tiempo no se pueden descartar sin condición control. **H1a: apoyo parcial y exploratorio. H1b: no detectado** (10 min es poco tiempo y el scrolling pasivo podría no exigir esfuerzo).

---

## 4. Entorno preparado

- **Dataset:** `C:\Users\ricar\Documents\Repositorios\Datasets\MIRAI\ds007537`. EEG real descargado de OpenNeuro para los 30 sujetos (~7.8 GB); `phenotype/` completo; eye-tracking `beh/*cyclopean*` descargado para 27 sujetos. Los demás archivos `annex` siguen siendo punteros.
- **Python del sistema:** se instalaron `mne` 1.13.2 y `specparam` 2.0.0rc7.
- **Ejecutar H1:**
  ```bash
  python "Tests/ds007537/h1_ds007537.py" "C:/Users/ricar/Documents/Repositorios/Datasets/MIRAI/ds007537"
  ```
  El caché se guarda en `results/cache_v2/`; bórralo si cambias el preprocesado.
- **Visor con ds007537:**
  ```bash
  python "Tests/EEG Dataset 9-10/Demo_processing.py" "C:/Users/ricar/Documents/Repositorios/Datasets/MIRAI/ds007537"
  ```

---

## 5. Pendientes

**Validación de H1 (en orden):**
1. **EEG-SVRec:** revisar el árbol de archivos (formato, montaje, marcas por video, licencia) → piloto con 2–3 sujetos → análisis dentro de cada sesión (15 min), entre sesiones (1 vs 4–5) y **alfa periódica por video vs inmersión reportada**.
2. **Control positivo con Cao 2019** (90 min, Figshare `6427334`): comprobar que el pipeline detecta theta al alza.
3. **Fijar las reglas de análisis** antes de los datos nuevos (medida principal, prueba, corrección).
4. **Experimento propio:** 35 min de scrolling vs 35 min de documental, contrabalanceado; KSS/VAS/NASA-TLX y Go/NoGo antes y después; montaje AURA; modelo mixto condición × tiempo; piloto n ≈ 10–15.

**Código:**
- En `Demo_processing.py`, la detección de ráfagas usa un umbral relativo a la mediana móvil, lo que sesga el conteo cuando sube el theta tónico. Hay que cambiarlo a una línea base fija.
- Opcional: ICLabel para quitar componentes musculares.

**Presentación v2** (texto en `Analisis_Scope_v2.md` §3 y §5.7): título VR → AR; nuevas diapositivas de Scope, Pipeline, Avances, Plan experimental e Intervención; state of the art con trabajos de scrolling; innovation factor; Gantt; referencias. Agregar los resultados de ds007537 como avance, con la frase de la §9 del reporte de H1.

**Verificar antes de citar:** Arnau 2021, valores de Nguyen 2025, Monge Roffarello & De Luca 2026, Kosmyna 2021, Haliburton 2024, InteractOut 2024, Kim 2018.
