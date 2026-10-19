"""
Tareas Express - Aplicación de gestión de tareas
Lenguaje: Python (tkinter incluido, no necesita instalar nada)

Ejecutar:
    python tareas_express.py

Funcionalidades:
    - Agregar, editar y eliminar tareas
    - Marcar como completada / pendiente
    - Filtrar: Todas, Pendientes, Completadas
    - Guarda automáticamente en archivo tareas.json
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import json
import os
from datetime import datetime

# Colores de la app (estilo teal, limpio y moderno)
TEAL = "#2a9d8f"
TEAL_DARK = "#21867a"
BG = "#f0fdfa"
CARD_BG = "#ffffff"
TEXT = "#374151"
MUTED = "#6b7280"
LIGHT_TEAL = "#e9f5f2"
AMBER = "#f59e0b"
VERDE = "#22c55e"
ROJO = "#ef4444"

ARCHIVO_DATOS = "tareas.json"


class Tarea:
    """Representa una tarea individual."""
    def __init__(self, titulo, materia="", fecha="", descripcion="",
                 presupuesto=0, estado="pendiente", id_=None):
        self.id = id_ or str(int(datetime.now().timestamp() * 1000))
        self.titulo = titulo
        self.materia = materia
        self.fecha = fecha
        self.descripcion = descripcion
        self.presupuesto = presupuesto
        self.estado = estado  # pendiente | completada
        self.creado = datetime.now().strftime("%Y-%m-%d %H:%M")

    def a_diccionario(self):
        return {
            "id": self.id,
            "titulo": self.titulo,
            "materia": self.materia,
            "fecha": self.fecha,
            "descripcion": self.descripcion,
            "presupuesto": self.presupuesto,
            "estado": self.estado,
            "creado": self.creado,
        }

    @staticmethod
    def desde_diccionario(d):
        t = Tarea(
            titulo=d.get("titulo", ""),
            materia=d.get("materia", ""),
            fecha=d.get("fecha", ""),
            descripcion=d.get("descripcion", ""),
            presupuesto=d.get("presupuesto", 0),
            estado=d.get("estado", "pendiente"),
            id_=d.get("id"),
        )
        t.creado = d.get("creado", t.creado)
        return t


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Tarea Express - Gestión de Tareas")
        self.geometry("450x750")
        self.configure(bg=BG)
        self.resizable(False, False)

        self.tareas = []
        self.filtro_actual = "todas"  # todas | pendientes | completadas

        self.cargar_tareas()
        self.construir_ui()
        self.renderizar_lista()

    # ---------------------- Persistencia ----------------------
    def cargar_tareas(self):
        if os.path.exists(ARCHIVO_DATOS):
            try:
                with open(ARCHIVO_DATOS, "r", encoding="utf-8") as f:
                    datos = json.load(f)
                self.tareas = [Tarea.desde_diccionario(d) for d in datos]
            except Exception:
                self.tareas = []
        else:
            self.tareas = []

    def guardar_tareas(self):
        try:
            with open(ARCHIVO_DATOS, "w", encoding="utf-8") as f:
                json.dump([t.a_diccionario() for t in self.tareas],
                          f, indent=2, ensure_ascii=False)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudieron guardar las tareas:\n{e}")

    # ---------------------- Interfaz ----------------------
    def construir_ui(self):
        # Header
        header = tk.Frame(self, bg=TEAL, height=60)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(header, text="TAREA EXPRESS", bg=TEAL, fg="white",
                 font=("Segoe UI", 13, "bold")).pack(pady=18)

        # Botón nueva tarea
        btn_nueva = tk.Button(header, text="+ Nueva", bg=TEAL_DARK, fg="white",
                              font=("Segoe UI", 10, "bold"), relief="flat",
                              cursor="hand2", command=self.abrir_modal_nueva)
        btn_nueva.place(relx=1.0, y=30, anchor="e", x=-15)

        # Filtros
        frame_filtros = tk.Frame(self, bg=CARD_BG)
        frame_filtros.pack(fill="x", padx=20, pady=(10, 0))

        tk.Label(frame_filtros, text="Filtrar:", bg=CARD_BG, fg=MUTED,
                 font=("Segoe UI", 9)).pack(side="left")

        for texto, valor in [("Todas", "todas"), ("Pendientes", "pendientes"),
                             ("Completadas", "completadas")]:
            b = tk.Button(frame_filtros, text=texto, bg="#f8fafc",
                          fg=TEXT if self.filtro_actual != valor else TEAL_DARK,
                          font=("Segoe UI", 9, "bold"),
                          relief="flat", bd=1, cursor="hand2",
                          command=lambda v=valor: self.cambiar_filtro(v))
            b.pack(side="left", padx=4)
            setattr(self, f"btn_filtro_{valor}", b)

        # Contador
        self.lbl_contador = tk.Label(frame_filtros, text="0 tareas",
                                     bg=CARD_BG, fg=TEAL_DARK,
                                     font=("Segoe UI", 9, "bold"))
        self.lbl_contador.pack(side="right")

        # Lista con scroll
        contenedor = tk.Frame(self, bg=BG)
        contenedor.pack(fill="both", expand=True, padx=20, pady=10)

        self.canvas = tk.Canvas(contenedor, bg=BG, highlightthickness=0)
        scroll = ttk.Scrollbar(contenedor, orient="vertical",
                               command=self.canvas.yview)
        self.frame_lista = tk.Frame(self.canvas, bg=BG)

        self.frame_lista.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self.canvas.create_window((0, 0), window=self.frame_lista, anchor="nw")
        self.canvas.configure(yscrollcommand=scroll.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        # Barra inferior (navegación simple)
        nav = tk.Frame(self, bg=CARD_BG, height=50)
        nav.pack(side="bottom", fill="x")
        nav.pack_propagate(False)

        btn_salir = tk.Button(nav, text="Salir", bg=CARD_BG, fg=MUTED,
                              font=("Segoe UI", 10), relief="flat",
                              cursor="hand2", command=self.quit)
        btn_salir.pack(side="right", padx=20, pady=12)

    def cambiar_filtro(self, valor):
        self.filtro_actual = valor
        # Actualizar estilos de botones de filtro
        for v in ["todas", "pendientes", "completadas"]:
            btn = getattr(self, f"btn_filtro_{v}")
            if v == valor:
                btn.configure(bg="#d1fae5", fg=TEAL_DARK)
            else:
                btn.configure(bg="#f8fafc", fg=TEXT)
        self.renderizar_lista()

    def renderizar_lista(self):
        # Limpiar lista actual
        for widget in self.frame_lista.winfo_children():
            widget.destroy()

        # Filtrar tareas
        if self.filtro_actual == "pendientes":
            filtradas = [t for t in self.tareas if t.estado == "pendiente"]
        elif self.filtro_actual == "completadas":
            filtradas = [t for t in self.tareas if t.estado == "completada"]
        else:
            filtradas = list(self.tareas)

        # Actualizar contador
        self.lbl_contador.configure(text=f"{len(self.tareas)} tareas")

        if not filtradas:
            lbl = tk.Label(self.frame_lista, bg=BG, fg=MUTED,
                           font=("Segoe UI", 11))
            if self.filtro_actual == "pendientes":
                lbl.configure(text="¡No hay tareas pendientes! 🎉")
            elif self.filtro_actual == "completadas":
                lbl.configure(text="Sin tareas completadas aún")
            else:
                lbl.configure(text="No hay tareas registradas")
            lbl.pack(pady=40)
            return

        for tarea in filtradas:
            self.crear_fila_tarea(tarea)

    def crear_fila_tarea(self, tarea):
        card = tk.Frame(self.frame_lista, bg=CARD_BG, relief="flat")
        card.pack(fill="x", pady=6, padx=2)
        card.configure(highlightbackground="#e2e8f0", highlightthickness=1)

        # Fila principal
        fila = tk.Frame(card, bg=CARD_BG)
        fila.pack(fill="x", padx=14, pady=10)

        # Checkbox completado
        var = tk.BooleanVar(value=(tarea.estado == "completada"))
        chk = tk.Checkbutton(fila, variable=var, bg=CARD_BG,
                             activebackground=CARD_BG,
                             command=lambda: self.toggle_completada(tarea.id, var))
        chk.pack(side="left")

        # Info de la tarea
        info = tk.Frame(fila, bg=CARD_BG)
        info.pack(side="left", fill="x", expand=True, padx=10)

        lbl_titulo = tk.Label(info, text=tarea.titulo, bg=CARD_BG, fg=TEXT,
                              font=("Segoe UI", 10, "bold"),
                              anchor="w")
        lbl_titulo.pack(fill="x")

        meta_partes = []
        if tarea.materia:
            meta_partes.append(tarea.materia)
        if tarea.fecha:
            meta_partes.append(tarea.fecha)
        if tarea.presupuesto:
            meta_partes.append(f"${tarea.presupuesto:,.0f} COP")

        lbl_meta = tk.Label(info, text=" · ".join(meta_partes), bg=CARD_BG,
                            fg=MUTED, font=("Segoe UI", 8), anchor="w")
        lbl_meta.pack(fill="x", pady=(2, 0))

        if tarea.estado == "completada":
            lbl_titulo.configure(fg=MUTED)

        # Estado y acciones
        acciones = tk.Frame(fila, bg=CARD_BG)
        acciones.pack(side="right")

        lbl_estado = tk.Label(acciones, text="✓" if tarea.estado == "completada" else "○",
                              bg=CARD_BG,
                              fg=VERDE if tarea.estado == "completada" else AMBER,
                              font=("Segoe UI", 11, "bold"))
        lbl_estado.pack(side="right", padx=4)

        btn_editar = tk.Button(acciones, text="✎", bg="#f1f5f9", fg=TEAL_DARK,
                               font=("Segoe UI", 10), relief="flat", bd=0,
                               cursor="hand2", width=2,
                               command=lambda: self.abrir_modal_editar(tarea))
        btn_editar.pack(side="right", padx=2)

        btn_eliminar = tk.Button(acciones, text="×", bg="#f1f5f9", fg=ROJO,
                                 font=("Segoe UI", 10, "bold"), relief="flat",
                                 bd=0, cursor="hand2", width=2,
                                 command=lambda: self.eliminar_tarea(tarea.id))
        btn_eliminar.pack(side="right", padx=2)

        # Línea divisoria sutil
        tk.Frame(card, height=1, bg="#f1f5f9").pack(fill="x", padx=14)

    # ---------------------- Acciones ----------------------
    def toggle_completada(self, id_tarea, var):
        for t in self.tareas:
            if t.id == id_tarea:
                t.estado = "completada" if var.get() else "pendiente"
                break
        self.guardar_tareas()
        self.renderizar_lista()
        estado_txt = "completada" if var.get() else "pendiente"
        messagebox.showinfo("Tarea", f"Tarea marcada como {estado_txt}.")

    def eliminar_tarea(self, id_tarea):
        if not messagebox.askyesno("Eliminar", "¿Estás seguro de eliminar esta tarea?"):
            return
        self.tareas = [t for t in self.tareas if t.id != id_tarea]
        self.guardar_tareas()
        self.renderizar_lista()

    def abrir_modal_nueva(self):
        self.abrir_modal(tarea=None)

    def abrir_modal_editar(self, tarea):
        self.abrir_modal(tarea=tarea)

    def abrir_modal(self, tarea):
        modal = tk.Toplevel(self)
        modal.title("Tarea" if tarea else "Nueva tarea")
        modal.geometry("380x560")
        modal.configure(bg=CARD_BG)
        modal.resizable(False, False)
        modal.transient(self)
        modal.grab_set()

        # Centrar modal
        modal.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - 380) // 2
        y = self.winfo_y() + (self.winfo_height() - 560) // 2
        modal.geometry(f"380x560+{x}+{y}")

        # Título modal
        lbl_modal_titulo = tk.Label(modal, text="Editar tarea" if tarea else "Nueva tarea",
                                    bg=TEAL, fg="white", font=("Segoe UI", 12, "bold"))
        lbl_modal_titulo.pack(fill="x", pady=(0, 10))

        # Formulario con scroll
        canvas = tk.Canvas(modal, bg=CARD_BG, highlightthickness=0)
        scroll = ttk.Scrollbar(modal, orient="vertical", command=canvas.yview)
        frame_form = tk.Frame(canvas, bg=CARD_BG)

        frame_form.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=frame_form, anchor="nw")
        canvas.configure(yscrollcommand=scroll.set)

        canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        # Campos
        def campo(etiqueta, valor="", tipo="entry"):
            tk.Label(frame_form, text=etiqueta, bg=CARD_BG, fg=MUTED,
                     font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(8, 2), padx=20)
            if tipo == "text":
                widget = tk.Text(frame_form, height=3, bg="#f8fafc", fg=TEXT,
                                 font=("Segoe UI", 10), relief="flat", bd=0,
                                 padx=8, pady=8)
                widget.insert("1.0", valor)
                widget.pack(fill="x", padx=20, pady=(0, 4))
            elif tipo == "number":
                widget = tk.Entry(frame_form, bg="#f8fafc", fg=TEXT,
                                  font=("Segoe UI", 10), relief="flat", bd=0)
                widget.insert(0, str(valor) if valor else "")
                widget.pack(fill="x", padx=20, pady=(0, 4))
            else:
                widget = tk.Entry(frame_form, bg="#f8fafc", fg=TEXT,
                                  font=("Segoe UI", 10), relief="flat", bd=0)
                widget.insert(0, valor)
                widget.pack(fill="x", padx=20, pady=(0, 4))
            return widget

        ent_titulo = campo("Título *", tarea.titulo if tarea else "")
        ent_materia = campo("Materia", tarea.materia if tarea else "")
        ent_fecha = campo("Fecha límite (YYYY-MM-DD)", tarea.fecha if tarea else "")
        txt_descripcion = campo("Descripción", tarea.descripcion if tarea else "", "text")
        ent_presupuesto = campo("Presupuesto (COP)",
                                tarea.presupuesto if tarea and tarea.presupuesto else "", "number")

        # Estado
        tk.Label(frame_form, text="Estado", bg=CARD_BG, fg=MUTED,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(12, 2), padx=20)
        var_estado = tk.StringVar(value=tarea.estado if tarea else "pendiente")
        frame_estado = tk.Frame(frame_form, bg=CARD_BG)
        frame_estado.pack(fill="x", padx=20, pady=(0, 10))
        tk.Radiobutton(frame_estado, text="Pendiente", variable=var_estado,
                       value="pendiente", bg=CARD_BG, fg=TEXT,
                       font=("Segoe UI", 10), activebackground=CARD_BG).pack(side="left")
        tk.Radiobutton(frame_estado, text="Completada", variable=var_estado,
                       value="completada", bg=CARD_BG, fg=TEXT,
                       font=("Segoe UI", 10), activebackground=CARD_BG).pack(side="left", padx=15)

        # Botones
        frame_botones = tk.Frame(modal, bg=CARD_BG)
        frame_botones.pack(fill="x", pady=15)

        def guardar():
            titulo = ent_titulo.get().strip()
            if not titulo:
                messagebox.showwarning("Validación", "El título es obligatorio.")
                ent_titulo.focus()
                return

            try:
                presupuesto = int(ent_presupuesto.get()) if ent_presupuesto.get().strip() else 0
            except ValueError:
                messagebox.showwarning("Validación", "El presupuesto debe ser un número.")
                ent_presupuesto.focus()
                return

            datos = {
                "titulo": titulo,
                "materia": ent_materia.get().strip(),
                "fecha": ent_fecha.get().strip(),
                "descripcion": txt_descripcion.get("1.0", "end-1c").strip(),
                "presupuesto": presupuesto,
                "estado": var_estado.get(),
            }

            if tarea:
                for t in self.tareas:
                    if t.id == tarea.id:
                        t.titulo = datos["titulo"]
                        t.materia = datos["materia"]
                        t.fecha = datos["fecha"]
                        t.descripcion = datos["descripcion"]
                        t.presupuesto = datos["presupuesto"]
                        t.estado = datos["estado"]
                        break
                messagebox.showinfo("Éxito", "Tarea actualizada.")
            else:
                nueva = Tarea(**datos)
                self.tareas.append(nueva)
                messagebox.showinfo("Éxito", "Tarea creada.")

            self.guardar_tareas()
            self.renderizar_lista()
            modal.destroy()

        btn_cancelar = tk.Button(frame_botones, text="Cancelar", bg=CARD_BG,
                                 fg=MUTED, font=("Segoe UI", 10), relief="flat",
                                 bd=1, cursor="hand2", width=12,
                                 command=modal.destroy)
        btn_cancelar.pack(side="right", padx=10)

        btn_guardar = tk.Button(frame_botones, text="Guardar", bg=TEAL,
                                fg="white", font=("Segoe UI", 10, "bold"),
                                relief="flat", cursor="hand2", width=12,
                                command=guardar)
        btn_guardar.pack(side="right")

        if tarea:
            btn_eliminar_modal = tk.Button(frame_botones, text="Eliminar", bg=ROJO,
                                           fg="white", font=("Segoe UI", 10, "bold"),
                                           relief="flat", cursor="hand2", width=12,
                                           command=lambda: self.eliminar_desde_modal(tarea.id, modal))
            btn_eliminar_modal.pack(side="right", padx=10)

    def eliminar_desde_modal(self, id_tarea, modal):
        if not messagebox.askyesno("Eliminar", "¿Estás seguro de eliminar esta tarea?"):
            return
        self.tareas = [t for t in self.tareas if t.id != id_tarea]
        self.guardar_tareas()
        self.renderizar_lista()
        modal.destroy()


if __name__ == "__main__":
    App().mainloop()
