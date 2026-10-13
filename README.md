# Neuroadaptive VR Platform & EEG Signal Processing (MIRAI Project)

Plataforma de investigación orientada al procesamiento en tiempo real de señales electroencefalográficas (EEG) —como conjuntos de datos de pruebas tipo *Stroop*— y al desarrollo de sistemas cerrados de neuroadaptación para mitigar la fatiga atencional digital.

---

## 🚀 Descripción del Proyecto
Este repositorio forma parte del desarrollo de investigación tecnológica enfocado en interfaces cerebro-computadora (BCI) y entornos virtuales adaptativos. El sistema procesa y analiza telemetría EEG para evaluar la carga cognitiva y los estados atencionales, integrando herramientas de procesamiento de datos en Python y entornos interactivos.

---

## 📂 Estructura del Repositorio

```text
Project/
│
├── AURA/                    # Módulos de integración y control de hardware/periféricos
├── Benkyokai-oct/           # Módulos de desarrollo y experimentación
├── Tests/                   # Pruebas y datasets experimentales
│   └── EEG Dataset 9-10/    # Registros y conjuntos de datos de EEG (ej. pruebas Stroop)
│       └── raw_data/        # Archivos de datos crudos (excluidos del control de versiones por peso)
├── Demo_processing.py       # Script principal de procesamiento y análisis de señales
├── .gitignore               # Configuración de exclusiones de Git
└── README.md                # Documentación del proyecto
```

---

## 🛠️ Tecnologías y Herramientas Utilizadas
* **Lenguaje:** Python
* **Procesamiento de Datos:** Análisis de señales EEG, filtrado y modelado de conjuntos de datos experimentales.
* **Entornos y Simulación:** Integración orientada a entornos virtuales y arquitecturas de retroalimentación en tiempo real.
* **Control de Versiones:** Git y GitHub.

---

## ⚙️ Configuración e Instalación

1. Clona el repositorio:
   ```bash
   git clone https://github.com/Ricardomonrreal/MIRAI-2026-Project-Own.git
   cd Project
   ```

2. Configura tu entorno virtual e instala las dependencias necesarias para la ejecución de los scripts de procesamiento (`Demo_processing.py`).

3. **Nota sobre los datos (`raw_data`):** 
   La carpeta de datos crudos (`raw_data`) se encuentra excluida en el archivo `.gitignore` debido al volumen de los registros EEG. Asegúrate de colocar tus fuentes de datos localmente en la ruta correspondiente dentro de `Tests/EEG Dataset 9-10/` para la correcta ejecución de los scripts de análisis.

---

## 👤 Autor
**Ricardo Monrreal Pool**  
*Ingeniería en Datos e Inteligencia Organizacional — Universidad del Caribe*  
*Participante del MIRAI Innovation Training Program (Japón)*