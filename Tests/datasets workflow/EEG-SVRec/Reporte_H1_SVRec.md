# Reporte H1 · EEG-SVRec (Fase C)

Datos: EEG-SVRec (Zhang et al., SIGIR 2024), scrolling de video corto en laboratorio, 62 canales a 1000 Hz.
Pipeline: [h1_svrec.py](h1_svrec.py), con el mismo preprocesado y las mismas medidas que ds007537.
Salidas: `results/svrec_reporte.txt`, `results/svrec_trayectorias.png`, `results/svrec_*.csv`.

## 1. Muestra

| | Sujetos |
|---|---|
| Analizados | **25** (84 sesiones válidas, ~1 200 min de EEG, ~1 900 videos) |
| Archivo dañado en el repositorio (cabecera en ceros) | 05, 16, 17 |
| Registro inutilizable por ruido (30–100× lo normal) | 19 (sin tramos limpios) y 15 (16 % de épocas válidas) |
| Parciales | 02 y 04 (archivo truncado); 11 (1 de 4 sesiones válida); 14 (4 de 5) |

Cambios respecto a ds007537, decididos por calidad de señal antes de ver resultados:
- specparam ajusta en **2–20 Hz**, porque los datos traen una meseta de ruido/EMG de 15–48 Hz que sesgaba el ajuste.
- Se agrega la medida de **EMG posterior (25–40 Hz)** como control de artefacto.

## 2. Resultados

### A · Dentro de la sesión (pruebas primarias, Holm)

| Medida | Pendiente | Sujetos ↑ | p Holm | Solo minutos con R² ≥ 0.8 | Solo sesiones ≥ 10 min |
|---|---|---|---|---|---|
| Alfa periódica (H1a) | **−0.021 dB/min** | 6/25 | **0.006** | −0.014, p = 0.17 | −0.007, p = 0.25 |
| Theta periódico (H1b) | **+0.016 dB/min** | 18/25 | **0.034** | +0.014, p = 0.23 | +0.016, p = 0.037 |

- Las dos pruebas primarias salen significativas con todos los datos, pero **ninguna es robusta**:
  - La bajada de alfa desaparece al quitar los minutos con mal ajuste y también al usar solo las sesiones largas.
  - La subida de theta desaparece con buen ajuste. Además, su Wilcoxon da p = 0.055.
- Magnitud: en 15 min equivale a unos −0.3 dB de alfa y +0.24 dB de theta. Son efectos pequeños.
- **Solo sesión 1** (lo más parecido a ds007537, n = 17): no hay cambio en nada.
- **Control de EMG:** el músculo no se relaciona con las pendientes (rho = −0.04 y −0.21).

### B · Entre sesiones (exploratorio, confundido con el tipo de feed)

- Alfa **total** ↑ +1.06 dB de la primera a la última sesión (16/22, p = 0.004). La alfa **periódica** no cambia (p = 0.30).
- El exponente 1/f se aplana (20/22, p < 0.001) y el EMG sube +2.2 dB (17/22, p < 0.001).
- Interpretación: es el patrón típico de **deterioro de la señal en un registro de ~2 h**: el gel se seca, sube la impedancia y aumenta el ruido de banda ancha. La alfa "total" sube por el fondo del espectro, no por el ritmo. Esto confirma por qué la medida primaria es la alfa periódica.

### C · Por video (exploratorio, 11 pruebas)

| Relación | rho medio | Sujetos con rho < 0 | p | Bonferroni ×11 |
|---|---|---|---|---|
| **Alfa periódica ~ inmersión** | −0.108 | 20/25 | 0.0025 | 0.028 |
| **Alfa periódica ~ arousal** | −0.106 | 18/25 | 0.0014 | 0.015 |
| Theta periódico ~ arousal | −0.074 | 20/25 | 0.0035 | 0.039 |
| EMG ~ inmersión (control) | −0.026 | — | 0.51 | — |
| Inmersión ~ orden del video | −0.012 | — | 0.78 | — |

- **Es el resultado más sólido:** con solo minutos de buen ajuste se fortalece (rho = −0.147, 18/25, p = 0.0003).
- Ni el músculo ni el paso del tiempo lo explican.
- Su tamaño es pequeño: explica ~1–2 % de la varianza por video.

## 3. Lectura frente a H1

| | ds007537 (10 min, uso libre) | EEG-SVRec (sesiones de 1–31 min, laboratorio) |
|---|---|---|
| Tendencia de alfa periódica | ↑ +0.04 dB/min (frágil) | ↓ −0.02 dB/min (frágil) |
| Tendencia de theta periódico | sin cambio | ↑ +0.016 dB/min (frágil) |
| Alfa periódica vs enganche | — | **menos alfa en los videos que más atrapan** (robusto) |

- **H1a, "la alfa sube con el tiempo de scrolling": no se sostiene.** Los dos datasets dan direcciones opuestas y ninguna es robusta. La tendencia temporal de alfa no es un marcador fiable de fatiga.
- **H1b, "theta sube": indicio débil.** Coincide con la idea de que se necesita más de 10 min, pero no resiste el filtro de calidad. Sigue pendiente el control positivo de la Fase B (Cao 2019).
- **Hallazgo nuevo:** la alfa periódica funciona como **marcador de estado de enganche, video a video**: más alfa cuando el contenido atrapa menos (menos inmersión y arousal). Es coherente con la lectura de "desenganche cortical" de ds007537, pero como **estado momentáneo**, no como acumulación con el tiempo.
- Nada de esto separa fatiga de habituación, porque no hay condición control. Eso sigue requiriendo la **Fase D**.

## 4. Implicaciones para MIRAI

1. **Reformular H1a:** de "alfa aumenta con el tiempo" a "la alfa periódica posterior indexa el desenganche momentáneo del contenido". La versión temporal queda para la Fase D, con control.
2. **Disparador del JITAI:** usar la alfa periódica respecto a la línea base de la persona, en ventanas cortas (de un video), como índice de desenganche. No usar el tiempo acumulado. El efecto es pequeño, así que conviene combinarlo con otras señales (theta, parpadeo, conducta de scroll).
3. **Fase D:** registrar inmersión o arousal por bloque para replicar la relación de C con el montaje AURA, y fijar desde antes un control de calidad de la señal (R² del ajuste, EMG).

## 5. Limitaciones

- La duración de las sesiones varía (1.4–31 min) y después del minuto 10 solo aportan las sesiones largas.
- El tipo de feed no está contrabalanceado, así que B queda confundido.
- Los datos vienen prefiltrados y con ruido de alta frecuencia; el 23 % de los minutos tiene un ajuste posterior con R² < 0.8.
- Los análisis B y C son exploratorios. Solo A tenía hipótesis y corrección previas.
- 5 de 30 sujetos se pierden por calidad de archivo o de señal.
