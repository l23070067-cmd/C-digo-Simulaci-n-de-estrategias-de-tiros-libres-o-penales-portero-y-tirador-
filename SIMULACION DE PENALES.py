import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
import random
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# --- 1. LÓGICA DE SIMULACIÓN Y DATOS ---

class SimuladorPenales:
    """
    Gestiona los datos de jugadores (Tiradores y Portero) y ejecuta la simulación
    basada en 18 zonas (3 filas x 6 columnas).
    """
    def __init__(self):
        self.columnas = ['Nombre', 'Rol'] + [f'Z{i}' for i in range(1, 19)]
        self.df_datos = pd.DataFrame(columns=self.columnas)
        self.resultados = []
        self.mapa_goles = {z: 0 for z in range(1, 19)}

    def limpiar_datos(self):
        self.df_datos = pd.DataFrame(columns=self.columnas)
        self.resultados = []

    def agregar_jugador_manual(self, nombre, rol, probabilidades):
        """Añade un jugador al DataFrame principal."""
        nuevo_dato = {'Nombre': nombre, 'Rol': rol}
        for i, prob in enumerate(probabilidades, start=1):
            nuevo_dato[f'Z{i}'] = prob
        nuevo_df = pd.DataFrame([nuevo_dato])
        self.df_datos = pd.concat([self.df_datos, nuevo_df], ignore_index=True)

    def cargar_desde_excel(self, ruta_archivo):
        """Carga datos desde un archivo Excel/CSV y realiza validaciones."""
        try:
            if ruta_archivo.endswith('.csv'):
                df_nuevo = pd.read_csv(ruta_archivo)
            else:
                df_nuevo = pd.read_excel(ruta_archivo)
            
            df_nuevo.columns = [c.strip() for c in df_nuevo.columns]
            
            if not all(col in df_nuevo.columns for col in self.columnas):
                return False, "El Excel debe tener: Nombre, Rol, y columnas de Z1 hasta Z18."
            
            for col in self.columnas[2:]:
                df_nuevo[col] = pd.to_numeric(df_nuevo[col], errors='coerce')
                if df_nuevo[col].isnull().any():
                     return False, f"La columna {col} contiene valores no numéricos o fuera de rango (0.0 a 1.0)."
            
            self.df_datos = df_nuevo
            return True, "Datos cargados correctamente."
        except Exception as e:
            return False, f"Error al cargar el archivo: {str(e)}"

    def validar_equipos(self):
        """
        Verifica que haya exactamente un portero y al menos un tirador antes de simular.
        """
        porteros = self.df_datos[self.df_datos['Rol'] == 'Portero']
        tiradores = self.df_datos[self.df_datos['Rol'] == 'Tirador']
        
        if len(porteros) != 1:
            return False, f"Debe haber EXACTAMENTE 1 Portero. Hay {len(porteros)}."
        if len(tiradores) == 0:
            return False, "Debe haber al menos 1 Tirador."
        return True, ""

    def ejecutar_simulacion(self, n_tiros):
        """Ejecuta N tiros para cada tirador contra el portero."""
        self.resultados = []
        self.mapa_goles = {z: 0 for z in range(1, 19)}
        
        datos_portero_df = self.df_datos[self.df_datos['Rol'] == 'Portero']
        if datos_portero_df.empty:
             messagebox.showerror("Error de Simulación", "No se encontró el Portero.")
             return [], "N/A"

        datos_portero = datos_portero_df.iloc[0]
        tiradores = self.df_datos[self.df_datos['Rol'] == 'Tirador']
        nombre_portero = datos_portero['Nombre']

        for _, tirador in tiradores.iterrows():
            goles = 0
            atajadas_o_fallos = 0
            
            for _ in range(n_tiros):
                zona = random.randint(1, 18) 
                col_zona = f'Z{zona}'
                
                prob_acierto_tirador = float(tirador[col_zona]) 
                prob_atajada_portero = float(datos_portero[col_zona])
                
                if random.random() < prob_acierto_tirador:
                    if random.random() < prob_atajada_portero:
                        atajadas_o_fallos += 1 # Atajada
                    else:
                        goles += 1 # GOL
                        self.mapa_goles[zona] += 1
                else:
                    atajadas_o_fallos += 1 # Tiro fuera

            self.resultados.append({
                "Tirador": tirador['Nombre'],
                "Goles": goles,
                "Fallos/Atajadas": atajadas_o_fallos,
                "Efectividad %": round((goles / n_tiros) * 100, 2)
            })
            
        return pd.DataFrame(self.resultados), nombre_portero

# --- 2. VENTANA POPUP PARA INGRESO MANUAL (Se mantiene igual) ---

class VentanaIngresoManual(tk.Toplevel):
    def __init__(self, parent, callback):
        super().__init__(parent)
        self.callback = callback
        self.title("Agregar Jugador (6 Columnas x 3 Filas)")
        self.geometry("1000x600") 
        
        frame_top = ttk.Frame(self, padding=10)
        frame_top.pack(fill='x')

        ttk.Label(frame_top, text="Nombre:").pack(side='left')
        self.ent_nombre = ttk.Entry(frame_top, width=20)
        self.ent_nombre.pack(side='left', padx=10)
        
        ttk.Label(frame_top, text="Rol:").pack(side='left')
        self.cb_rol = ttk.Combobox(frame_top, values=["Portero", "Tirador"], state="readonly", width=10)
        self.cb_rol.current(1) 
        self.cb_rol.pack(side='left', padx=10)
        self.cb_rol.bind("<<ComboboxSelected>>", self.al_cambiar_rol)
        
        self.lbl_instruccion = ttk.Label(self, text="...", font=('Arial', 10, 'bold'))
        self.lbl_instruccion.pack(pady=5)
        
        self.frame_porteria = ttk.LabelFrame(self, text=" Probabilidad de Éxito por Zona (0.0 a 1.0) ", padding=10)
        self.frame_porteria.pack(pady=5, padx=10)
        
        self.vars_zonas = {}
        
        self.mapa_indices = [
            [1, 2, 3, 4, 5, 6], 
            [7, 8, 9, 10, 11, 12],
            [13, 14, 15, 16, 17, 18]
        ]
        
        nombres_filas = ["Arriba", "Medio", "Abajo"]
        col_names = ["E.Izq", "Lat.Izq", "C.Izq", "C.Der", "Lat.Der", "E.Der"]
        
        for r in range(3): 
            for c in range(6): 
                cell_frame = ttk.Frame(self.frame_porteria, borderwidth=1, relief="solid")
                cell_frame.grid(row=r, column=c, padx=2, pady=2, ipadx=2, ipady=2, sticky="nsew")
                
                txt_label = f"Z{self.mapa_indices[r][c]}\n{nombres_filas[r]}\n{col_names[c]}"
                lbl = ttk.Label(cell_frame, text=txt_label, font=('Arial', 7), justify='center')
                lbl.pack()
                
                entry = ttk.Entry(cell_frame, width=5, justify='center')
                entry.insert(0, "0.5")
                entry.pack(pady=2)
                
                idx_zona = self.mapa_indices[r][c]
                self.vars_zonas[idx_zona] = entry

        btn_guardar = ttk.Button(self, text="Guardar Datos", command=self.guardar)
        btn_guardar.pack(pady=15)
        
        self.al_cambiar_rol() 

    def al_cambiar_rol(self, event=None):
        """Cambia textos y limpia/llena casillas según el rol."""
        rol = self.cb_rol.get()
        
        if rol == "Portero":
            self.lbl_instruccion.config(text="PORTERO: Ingrese prob. de ATAJAR (Vacío = debe llenar)", foreground="red")
            for key, entry in self.vars_zonas.items():
                entry.delete(0, tk.END) 
        else:
            self.lbl_instruccion.config(text="TIRADOR: Prob. de ACERTAR a la zona (0.5 por defecto)", foreground="green")
            for key, entry in self.vars_zonas.items():
                if entry.get() == "":
                    entry.insert(0, "0.5")

    def guardar(self):
        nombre = self.ent_nombre.get()
        rol = self.cb_rol.get()
        if not nombre:
            messagebox.showerror("Error", "Falta el nombre")
            return
            
        lista_probs = []
        try:
            for i in range(1, 19):
                raw_val = self.vars_zonas[i].get()
                if raw_val.strip() == "":
                    messagebox.showerror("Error", f"La zona Z{i} está vacía. Ingrese un número.")
                    return

                val = float(raw_val)
                if val < 0 or val > 1: raise ValueError
                lista_probs.append(val)
        except ValueError:
            messagebox.showerror("Error", "Revise que todos los valores sean números entre 0.0 y 1.0")
            return
            
        self.callback(nombre, rol, lista_probs)
        self.destroy()


# --- 3. INTERFAZ PRINCIPAL ---

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("⚽ Simulador Penales (Grid 6x3)")
        self.geometry("1250x850")
        self.sim = SimuladorPenales()
        
        pnl_top = ttk.Frame(self, padding=10)
        pnl_top.pack(fill='x')
        
        ttk.Button(pnl_top, text="📂 Cargar Excel (Z1-Z18)", command=self.cargar_excel).pack(side='left', padx=5)
        ttk.Button(pnl_top, text="✍️ Crear Manualmente", command=self.abrir_manual).pack(side='left', padx=5)
        ttk.Button(pnl_top, text="🗑️ Reset", command=self.limpiar).pack(side='left', padx=20)
        
        self.lbl_status = ttk.Label(pnl_top, text="Esperando datos...", font=('Arial', 10, 'bold'), foreground="orange")
        self.lbl_status.pack(side='left', padx=20)

        pnl_run = ttk.Frame(self, padding=10, relief='groove')
        pnl_run.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(pnl_run, text="Tiros por jugador:").pack(side='left')
        self.ent_tiros = ttk.Entry(pnl_run, width=8)
        self.ent_tiros.insert(0, "1000")
        self.ent_tiros.pack(side='left', padx=5)
        
        self.btn_run = ttk.Button(pnl_run, text="▶️ SIMULAR", command=self.ejecutar, state='disabled')
        self.btn_run.pack(side='left', padx=20)

        self.tree = ttk.Treeview(self, columns=("Jugador", "Goles", "Fallos", "Efectividad"), show='headings', height=6)
        for c in ["Jugador", "Goles", "Fallos", "Efectividad"]:
            self.tree.heading(c, text=c)
            self.tree.column(c, anchor='center')
        self.tree.pack(fill='x', padx=10)

        # La figura ahora será para una cuadrícula 2x2
        self.fig = Figure(figsize=(12, 8), dpi=100) # Se aumenta el alto para 2 filas de gráficas
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().pack(fill='both', expand=True, padx=10, pady=10)

    def abrir_manual(self):
        VentanaIngresoManual(self, self.callback_manual)

    def callback_manual(self, n, r, p):
        self.sim.agregar_jugador_manual(n, r, p)
        self.check_status()

    def cargar_excel(self):
        f = filedialog.askopenfilename(filetypes=[("Excel", "*.xlsx *.csv")])
        if f:
            ok, msg = self.sim.cargar_desde_excel(f)
            if ok: messagebox.showinfo("OK", msg)
            else: messagebox.showerror("Error", msg)
            self.check_status()

    def limpiar(self):
        self.sim.limpiar_datos()
        self.check_status()
        self.tree.delete(*self.tree.get_children())
        self.fig.clear()
        self.canvas.draw()

    def check_status(self):
        df = self.sim.df_datos
        nP = len(df[df['Rol']=='Portero'])
        nT = len(df[df['Rol']=='Tirador'])
        if nP == 1 and nT > 0:
            self.lbl_status.config(text=f"Listo: 1 Portero vs {nT} Tiradores", foreground="green")
            self.btn_run.config(state='normal')
        else:
            self.lbl_status.config(text=f"Falta: 1 Portero (Hay {nP}) o Tiradores (Hay {nT})", foreground="red")
            self.btn_run.config(state='disabled')

    def ejecutar(self):
        try: 
            n = int(self.ent_tiros.get())
            if n <= 0: raise ValueError
        except: 
            messagebox.showerror("Error", "Ingrese un número válido y positivo de tiros.")
            return

        ok, msg = self.sim.validar_equipos()
        if not ok:
            messagebox.showerror("Error de Validación", msg)
            self.check_status()
            return
            
        df_res, nom_port = self.sim.ejecutar_simulacion(n)
        
        self.tree.delete(*self.tree.get_children())
        for _, r in df_res.iterrows():
            self.tree.insert("", "end", values=(r['Tirador'], r['Goles'], r['Fallos/Atajadas'], f"{r['Efectividad %']}%"))
            
        self.dibujar_mapa(nom_port)

    def dibujar_mapa(self, nombre_portero):
        self.fig.clear()
        
        # Obtener datos para el cálculo teórico
        datos_portero = self.sim.df_datos[self.sim.df_datos['Rol'] == 'Portero'].iloc[0]
        tiradores_df = self.sim.df_datos[self.sim.df_datos['Rol'] == 'Tirador']
        
        # Definición de la cuadrícula
        matriz_indices = [
            [1, 2, 3, 4, 5, 6],
            [7, 8, 9, 10, 11, 12],
            [13, 14, 15, 16, 17, 18]
        ]
        
        col_labels = ["E.Izq", "Lat.I", "C.Izq", "C.Der", "Lat.D", "E.Der"]
        row_labels = ["Arriba", "Medio", "Abajo"]

        # --- CÁLCULO DE LA P(ATAJADA) DEL PORTERO (Matriz Base) ---
        prob_atajada_matrix = []
        for r in range(3):
            fila_data = []
            for c in range(6):
                z_id = matriz_indices[r][c]
                prob_atajada = float(datos_portero[f'Z{z_id}'])
                fila_data.append(prob_atajada)
            prob_atajada_matrix.append(fila_data)
        
        # --- PLOT 1: GRÁFICA DEL PORTERO ---
        # Posición 1 de 4 (Top Left)
        ax1 = self.fig.add_subplot(221)
        ax1.imshow(prob_atajada_matrix, cmap='Blues', aspect='auto', vmin=0, vmax=1)
        ax1.set_title(f"P. Atajada {nombre_portero}", fontsize=10)
        
        ax1.set_xticks(range(6))
        ax1.set_xticklabels(col_labels, rotation=45, ha='right')
        ax1.set_yticks(range(3))
        ax1.set_yticklabels(row_labels)
        
        # Anotaciones de texto para ax1
        for r in range(3):
            for c in range(6):
                prob = prob_atajada_matrix[r][c]
                text_color = 'white' if prob > 0.5 else 'black'
                ax1.text(c, r, f"{prob:.2f}", ha='center', va='center', 
                         color=text_color, fontsize=8, fontweight='bold')
        

        # --- PLOTS 2, 3, 4: GRÁFICAS DE CADA TIRADOR ---
        
        shooter_axes = [(222, 'Top Right'), (223, 'Bottom Left'), (224, 'Bottom Right')]
        
        for idx, (ax_pos, _) in enumerate(shooter_axes):
            
            if idx >= len(tiradores_df):
                # Si no hay más tiradores, llenamos el espacio vacío
                ax_empty = self.fig.add_subplot(ax_pos)
                ax_empty.set_title("No hay más tiradores para graficar", fontsize=10)
                ax_empty.axis('off')
                continue
            
            # Seleccionamos el tirador actual
            tirador = tiradores_df.iloc[idx]
            nombre_tirador = tirador['Nombre']
            
            ax_shooter = self.fig.add_subplot(ax_pos)
            prob_gol_matrix = []
            
            for r in range(3):
                fila_data = []
                for c in range(6):
                    z_id = matriz_indices[r][c]
                    
                    # P(Gol Esperado) = P(Acierto Tirador en Z) * (1 - P(Atajada Portero en Z))
                    p_acierto_tirador = float(tirador[f'Z{z_id}'])
                    p_atajada_portero = prob_atajada_matrix[r][c]
                    p_gol_zona = p_acierto_tirador * (1.0 - p_atajada_portero)
                    
                    fila_data.append(p_gol_zona)
                prob_gol_matrix.append(fila_data)

            # Ploteo de P(Gol Esperado) del Tirador
            ax_shooter.imshow(prob_gol_matrix, cmap='Reds', aspect='auto', vmin=0, vmax=1)
            ax_shooter.set_title(f"P. Gol Esperado: {nombre_tirador}", fontsize=10)
            
            ax_shooter.set_xticks(range(6))
            ax_shooter.set_xticklabels(col_labels, rotation=45, ha='right')
            ax_shooter.set_yticks(range(3))
            ax_shooter.set_yticklabels(row_labels)

            # Anotaciones de texto para el tirador
            for r in range(3):
                for c in range(6):
                    prob = prob_gol_matrix[r][c]
                    text_color = 'white' if prob > 0.5 else 'black'
                    ax_shooter.text(c, r, f"{prob:.2f}", ha='center', va='center', 
                             color=text_color, fontsize=8, fontweight='bold')

        self.fig.tight_layout()
        self.canvas.draw()

if __name__ == "__main__":
    app = App()
    app.mainloop()