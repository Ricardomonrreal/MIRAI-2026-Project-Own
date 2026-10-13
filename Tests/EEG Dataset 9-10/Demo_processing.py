import os
import re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import tkinter as tk
from tkinter import ttk

# Directorio donde se encuentran los archivos de datos
directory_path = "raw_data/raw_data/Arithmetic_Data"

# Verificar si la ruta existe
if not os.path.exists(directory_path):
    print(f"Error: La ruta '{directory_path}' no existe. Verifica la ubicación de tus carpetas.")
else:
    all_files = [f for f in os.listdir(directory_path) if f.endswith('.txt')]
    
    # Función para extraer el número del archivo y ordenar numéricamente (ej: -2.txt antes que -10.txt)
    def numeric_sort_key(filename):
        match = re.search(r'(\d+)\.txt$', filename)
        return int(match.group(1)) if match else 0

    # Agrupar y ordenar numéricamente cada nivel
    levels_dict = {
        "Natural":    sorted([f for f in all_files if f.lower().startswith('n')], key=numeric_sort_key),
        "Low level":  sorted([f for f in all_files if f.lower().startswith('l')], key=numeric_sort_key),
        "Mid level":  sorted([f for f in all_files if f.lower().startswith('m')], key=numeric_sort_key),
        "High level": sorted([f for f in all_files if f.lower().startswith('h')], key=numeric_sort_key)
    }
    
    level_names = list(levels_dict.keys())
    
    # 2. Crear la ventana principal de la aplicación
    root = tk.Tk()
    root.title("Visualizador de Señales EEG - Orden Numérico")
    root.geometry("1400x850")
    
    # Panel izquierdo para los controles
    control_frame = ttk.Frame(root, padding=15)
    control_frame.pack(side=tk.LEFT, fill=tk.Y)
    
    # --- Primer menú desplegable: Seleccionar nivel ---
    label_level = ttk.Label(control_frame, text="Seleccionar nivel:", font=("Arial", 10, "bold"))
    label_level.pack(pady=(0, 5), anchor="w")
    
    level_var = tk.StringVar()
    level_combobox = ttk.Combobox(control_frame, textvariable=level_var, values=level_names, state="readonly", width=28)
    level_combobox.pack(pady=(0, 15))
    
    # --- Segundo menú desplegable: Seleccionar archivo ---
    label_file = ttk.Label(control_frame, text="Seleccionar archivo:", font=("Arial", 10, "bold"))
    label_file.pack(pady=(0, 5), anchor="w")
    
    file_var = tk.StringVar()
    file_combobox = ttk.Combobox(control_frame, textvariable=file_var, state="readonly", width=28)
    file_combobox.pack(pady=(0, 10))
    
    # Panel derecho para incrustar las gráficas de Matplotlib
    plot_frame = ttk.Frame(root)
    plot_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
    
    # 3. Configurar la figura y los 8 subplots de los canales EEG
    fig, axes = plt.subplots(8, 1, figsize=(10, 8), sharex=True)
    
    canvas = FigureCanvasTkAgg(fig, master=plot_frame)
    canvas_widget = canvas.get_tk_widget()
    canvas_widget.pack(fill=tk.BOTH, expand=True)
    
    # 4. Función para actualizar las gráficas del EEG
    def update_plot(event=None):
        selected_file = file_var.get()
        if not selected_file:
            return
            
        file_path = os.path.join(directory_path, selected_file)
        
        # Cargar y procesar datos del archivo seleccionado
        data_user1 = pd.read_csv(file_path, delimiter=",", header=None)
        eeg_channels = data_user1.iloc[:, 1:9]
        
        eeg_clean = eeg_channels.iloc[1:].copy()
        eeg_clean = eeg_clean - eeg_clean.mean()
        
        num_samples = len(eeg_clean)
        time_axis = range(num_samples)
        
        # Dibujar los 8 canales
        for i in range(8):
            axes[i].clear()
            axes[i].plot(time_axis, eeg_clean.iloc[:num_samples, i], color='b', linewidth=0.8)
            axes[i].set_ylabel(f'Canal {i+1}', fontsize=8)
            axes[i].grid(True, linestyle='--', alpha=0.5)
            
            if i < 7:
                axes[i].tick_params(labelbottom=False)
                
        axes[-1].set_xlabel('Índice de Muestra (Filas)', fontsize=10)
        fig.suptitle(f'Señales EEG - {selected_file}', fontsize=12, fontweight='bold')
        fig.tight_layout()
        canvas.draw()

    # 5. Función condicional que actualiza los archivos disponibles al cambiar de nivel
    def on_level_changed(event=None):
        selected_level = level_var.get()
        files_in_level = levels_dict.get(selected_level, [])
        
        # Actualizar las opciones del combobox de archivos
        file_combobox['values'] = files_in_level
        
        if files_in_level:
            file_combobox.set(files_in_level[0])  # Seleccionar el primer archivo por defecto
            update_plot()  # Actualizar la gráfica con el nuevo archivo
        else:
            file_var.set('')

    # Vincular los eventos de los menús desplegables
    level_combobox.bind("<<ComboboxSelected>>", on_level_changed)
    file_combobox.bind("<<ComboboxSelected>>", update_plot)
    
    # Inicializar la aplicación seleccionando por defecto el primer nivel ("Natural")
    level_combobox.set(level_names[0])
    on_level_changed()
    
    # Ejecutar la aplicación de escritorio
    root.mainloop()