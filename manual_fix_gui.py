import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import datetime
import webbrowser
import re
import os
from PIL import Image, ImageTk
from monitor_core import BGG_CACHE_DB, fetch_details, init_db, IMG_DIR, get_db_connection

class ManualFixGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("MAPEO BGG - Pro (Categorizado 📑)")
        self.root.geometry("1200x820")
        self.root.configure(bg="#f1f3f5")

        self.colors = {
            "bg": "#f1f3f5", "card": "#ffffff", "text": "#212529", "accent": "#339af0",
            "success": "#51cf66", "warning": "#fcc419", "danger": "#ff6b6b", "muted": "#868e96", "border": "#dee2e6"
        }
        self.style_btn = {"font": ("Segoe UI", 9, "bold"), "cursor": "hand2", "relief": "flat", "pady": 6}
        init_db()
        self.setup_styles()
        self.setup_ui()
        self.load_data()

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TNotebook", background=self.colors["bg"], borderwidth=0)
        style.configure("TNotebook.Tab", background="#e9ecef", foreground="#495057", font=("Segoe UI", 9, "bold"), padding=[20, 6])
        style.map("TNotebook.Tab", background=[('selected', '#ffffff')], foreground=[('selected', '#1c7ed6')])
        
        style.configure("Treeview", background="#ffffff", foreground="#212529", fieldbackground="#ffffff", borderwidth=0, font=("Segoe UI", 9), rowheight=30)
        style.map("Treeview", background=[('selected', '#339af0')], foreground=[('selected', 'white')])
        style.configure("Treeview.Heading", background="#f8f9fa", foreground="#495057", font=("Segoe UI", 9, "bold"), relief="flat")

    def setup_ui(self):
        main_frame = tk.Frame(self.root, bg=self.colors["bg"])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)

        # CABECERA
        header = tk.Frame(main_frame, bg=self.colors["bg"])
        header.pack(fill=tk.X, pady=(0, 15))
        tk.Label(header, text="🛡️ GESTOR DE MAPEO BGG", font=("Segoe UI", 20, "bold"), bg=self.colors["bg"], fg="#1c7ed6").pack(side=tk.LEFT)
        tk.Button(header, text="🔄 RECARGAR TODO", command=self.load_data, bg=self.colors["accent"], fg="white", **self.style_btn, width=15).pack(side=tk.RIGHT)

        # BARRA DE BUSQUEDA
        search_card = tk.Frame(main_frame, bg="white", highlightthickness=1, highlightbackground=self.colors["border"])
        search_card.pack(fill=tk.X, pady=(0, 15))
        tk.Label(search_card, text="🔍", font=("Segoe UI", 12), bg="white").pack(side=tk.LEFT, padx=10)
        self.filter_var = tk.StringVar()
        self.filter_var.trace_add("write", lambda *a: self.load_data())
        tk.Entry(search_card, textvariable=self.filter_var, font=("Segoe UI", 11), bg="white", borderwidth=0).pack(side=tk.LEFT, fill=tk.X, expand=True, pady=10)

        # LAYOUT
        panes = tk.Frame(main_frame, bg=self.colors["bg"])
        panes.pack(fill=tk.BOTH, expand=True)

        # IZQUIERDA: NOTEBOOK
        self.notebook = ttk.Notebook(panes)
        self.notebook.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.notebook.bind("<<NotebookTabChanged>>", lambda e: self.load_data())

        self.tabs = {}
        tab_configs = [
            ("wait", "⏳ ESPERANDO", "Juegos en espera"),
            ("mapped", "✅ YA MAPEADOS", "Confirmados (100%)"),
            ("ignored", "🚫 IGNORADOS", "Ignorados"),
            ("review", "🔍 REVISAR", "Pendientes de revisión")
        ]
        
        for key, label, tooltip in tab_configs:
            f = tk.Frame(self.notebook, bg="white")
            self.notebook.add(f, text=label)
            
            tree = ttk.Treeview(f, columns=("item_name", "bgg_id", "conf", "last", "cand"), show="headings", height=18)
            tree.heading("item_name", text="Nombre del Producto", anchor=tk.W)
            tree.heading("bgg_id", text="ID Sugerido"); tree.heading("conf", text="% Conf"); tree.heading("last", text="Fecha")
            tree.column("item_name", width=400, anchor=tk.W); tree.column("bgg_id", width=120, anchor=tk.CENTER)
            tree.column("conf", width=80, anchor=tk.CENTER); tree.column("last", width=100, anchor=tk.CENTER)
            tree.column("cand", width=0, stretch=tk.NO) # Invisible para almacenar el candidate_id crudo
            
            sc = ttk.Scrollbar(f, orient=tk.VERTICAL, command=tree.yview); tree.configure(yscroll=sc.set)
            sc.pack(side=tk.RIGHT, fill=tk.Y); tree.pack(fill=tk.BOTH, expand=True)
            tree.bind("<<TreeviewSelect>>", self.on_select)
            self.tabs[key] = tree

        # DERECHA: PANEL DE ACCION (Card)
        right_panel = tk.Frame(panes, bg=self.colors["bg"], width=320)
        right_panel.pack(side=tk.RIGHT, fill=tk.Y, padx=(20, 0)); right_panel.pack_propagate(False)

        detail_card = tk.LabelFrame(right_panel, text=" FICHA TÉCNICA ", bg="white", fg="#1c7ed6", font=("Segoe UI", 9, "bold"), padx=15, pady=15, relief="flat", highlightthickness=1, highlightbackground=self.colors["border"])
        detail_card.pack(fill=tk.BOTH, expand=True)

        self.img_label = tk.Label(detail_card, bg="#f8f9fa", width=260, height=220); self.img_label.pack(pady=(0, 10))
        self.bgg_name_disp = tk.Label(detail_card, text="-", bg="white", fg=self.colors["text"], font=("Segoe UI", 10, "bold"), wraplength=260, justify="center"); self.bgg_name_disp.pack(fill=tk.X)
        
        # Botón de búsqueda rápida por en Google (Pedido por usuario) - Para casos rebeldes
        tk.Button(detail_card, text="🔍 BUSCAR EN GOOGLE (BGG)", command=self.search_by_name, bg="#e9ecef", fg="#1c7ed6", font=("Segoe UI", 8, "bold"), relief="flat", cursor="hand2").pack(pady=5)

        self.lbl_cand_info = tk.Label(detail_card, text="", bg="white", fg="#e67e22", font=("Segoe UI", 9, "italic bold"), wraplength=260); self.lbl_cand_info.pack(fill=tk.X, pady=10)

        # Campos de entrada
        input_frame = tk.Frame(detail_card, bg="white")
        input_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(input_frame, text="NOMBRE PRODUCTO", bg="white", font=("Segoe UI", 7, "bold"), fg=self.colors["muted"]).pack(anchor=tk.W)
        self.name_var = tk.StringVar()
        self.name_ent = tk.Entry(input_frame, textvariable=self.name_var, state='readonly', font=("Segoe UI", 8), bg="#f8f9fa", borderwidth=0); self.name_ent.pack(fill=tk.X, pady=(0,10))

        tk.Label(input_frame, text="BGG ID", bg="white", font=("Segoe UI", 7, "bold"), fg=self.colors["muted"]).pack(anchor=tk.W)
        self.bgg_var = tk.StringVar()
        self.bgg_ent = tk.Entry(input_frame, textvariable=self.bgg_var, font=("Segoe UI", 14, "bold"), bg="#f1f3f5", relief="flat", justify="center"); self.bgg_ent.pack(fill=tk.X, pady=5)

        # Botonera
        tk.Button(detail_card, text="✅ VALIDAR Y GUARDAR", command=self.save, bg=self.colors["success"], fg="white", **self.style_btn).pack(fill=tk.X, pady=5)
        
        btn_row_1 = tk.Frame(detail_card, bg="white")
        btn_row_1.pack(fill=tk.X, pady=2)
        tk.Button(btn_row_1, text="🌐 ABRIR BGG", command=self.search, bg=self.colors["accent"], fg="white", **self.style_btn, width=12).pack(side=tk.LEFT, expand=True, padx=1)
        tk.Button(btn_row_1, text="🛒 EN TIENDA", command=self.open_store, bg="#37b24d", fg="white", **self.style_btn, width=12).pack(side=tk.LEFT, expand=True, padx=1)

        btn_row_2 = tk.Frame(detail_card, bg="white")
        btn_row_2.pack(fill=tk.X, pady=2)
        tk.Button(btn_row_2, text="📋 COPIAR NOM", command=self.copy_name, bg="#adb5bd", **self.style_btn, width=12).pack(side=tk.LEFT, expand=True, padx=1)
        tk.Button(btn_row_2, text="🚫 IGNORAR", command=self.ignore, bg="#adb5bd", **self.style_btn, width=12).pack(side=tk.LEFT, expand=True, padx=1)
        
        tk.Button(detail_card, text="⏳ ESPERAR (WAIT)", command=self.wait, bg=self.colors["warning"], fg="white", **self.style_btn).pack(fill=tk.X, pady=5)

    def load_data(self):
        try:
            tab_idx = self.notebook.index(self.notebook.select())
        except: return
        
        keys = ["wait", "mapped", "ignored", "review"]
        tab_names = ["⏳ ESPERANDO", "✅ YA MAPEADOS", "🚫 IGNORADOS", "🔍 REVISAR"]
        s = f"%{self.filter_var.get()}%"
        
        conn = get_db_connection()
        try:
            # 1. ACTUALIZAR CONTADORES DE PESTAÑAS
            for i, key in enumerate(keys):
                if key == "wait": wh_c = "m.bgg_id = 'WAITING'"
                elif key == "mapped": wh_c = "m.bgg_id GLOB '[0-9]*' AND m.confidence = 100"
                elif key == "ignored": wh_c = "m.bgg_id = 'IGNORED'"
                else: # review
                     wh_c = "(m.bgg_id IS NULL OR m.bgg_id NOT IN ('WAITING', 'IGNORED')) AND (m.confidence < 100 OR m.bgg_id NOT GLOB '[0-9]*')"
                
                count = conn.execute(f"SELECT COUNT(DISTINCT d.item_name) FROM deals d LEFT JOIN bgg_mapping m ON d.item_name=m.item_name WHERE d.item_name LIKE ? AND d.date_found >= date('now', '-15 days') AND {wh_c}", (s,)).fetchone()[0]
                self.notebook.tab(i, text=f"{tab_names[i]} ({count})")

            # 2. CARGAR DATA DE PESTAÑA ACTUAL
            current_key = keys[tab_idx]
            tree = self.tabs[current_key]
            for i in tree.get_children(): tree.delete(i)
            
            base_wh = "d.item_name LIKE ? AND d.date_found >= date('now', '-15 days')"
            if current_key == "wait": wh = f"{base_wh} AND m.bgg_id = 'WAITING'"
            elif current_key == "mapped": wh = f"{base_wh} AND m.bgg_id GLOB '[0-9]*' AND m.confidence = 100"
            elif current_key == "ignored": wh = f"{base_wh} AND m.bgg_id = 'IGNORED'"
            else: # review
                wh = f"{base_wh} AND (m.bgg_id IS NULL OR m.bgg_id NOT IN ('WAITING', 'IGNORED')) AND (m.confidence < 100 OR m.bgg_id NOT GLOB '[0-9]*')"

            q = f"SELECT DISTINCT d.item_name, m.bgg_id, IFNULL(m.confidence,0), MAX(d.date_found), m.candidate_id FROM deals d LEFT JOIN bgg_mapping m ON d.item_name=m.item_name WHERE {wh} GROUP BY d.item_name ORDER BY d.date_found DESC LIMIT 300"
            
            for r in conn.execute(q, (s,)).fetchall():
                v = list(r)
                real_id, conf, cand = v[1], v[2], v[4]
                if (not real_id or real_id in ['WAITING', 'N/A', '', '-']) and cand:
                    v[1] = f"{cand}?"
                elif not real_id or real_id == 'WAITING':
                    v[1] = "-"
                v[2] = f"{int(v[2])}%"
                tree.insert("", tk.END, values=v)
        finally: conn.close()

    def on_select(self, event):
        tree = event.widget
        sel = tree.selection()
        if not sel: return
        iid = sel[0]
        name = tree.set(iid, "item_name")
        bid_raw = tree.set(iid, "bgg_id")
        conf_str = tree.set(iid, "conf")
        cand = tree.set(iid, "cand")

        # Limpiar Sugerencia
        is_suggestion = False
        bid_str = str(bid_raw).strip()
        if bid_str.endswith('?'):
            bid = bid_str.replace('?', '')
            is_suggestion = True
        else:
            bid = bid_str if bid_str != "-" else ""
        
        self.name_var.set(name)
        mapping_list = ["WAITING", "N/A", "", "-", "None", "None?"]
        
        if is_suggestion or (bid in mapping_list and cand and str(cand) not in mapping_list):
            final_id = bid if is_suggestion else str(cand)
            self.bgg_var.set(final_id)
            self.lbl_cand_info.config(text=f"💡 Sugerencia: ID {final_id}\n(Confianza: {conf_str})", fg="#e67e22")
        else:
            self.bgg_var.set(bid if bid not in mapping_list else "")
            self.lbl_cand_info.config(text="", fg="#6c757d")

        # Cargar Imagen y Datos BGG
        self.img_label.config(image='')
        conn = get_db_connection()
        try:
            rd = conn.execute("SELECT url, image_local FROM deals WHERE item_name=? ORDER BY date_found DESC LIMIT 1", (name,)).fetchone()
            if rd:
                self.store_url, img_l = rd
                if img_l:
                    path = os.path.join(IMG_DIR, img_l)
                    if os.path.exists(path):
                        try:
                            pi = Image.open(path).convert("RGB").resize((260, 220), Image.Resampling.LANCZOS)
                            tki = ImageTk.PhotoImage(pi); self.img_label.config(image=tki); self.img_label.image = tki
                        except: pass
            
            curr_id = self.bgg_var.get()
            bn = "-"
            if curr_id and str(curr_id).isdigit():
                rg = conn.execute("SELECT original_name FROM games WHERE bgg_id=?", (curr_id,)).fetchone()
                if rg:
                    bn = rg[0]
                else:
                    # self.bgg_name_disp.config(text="⏳ Consultando BGG...")
                    # self.root.update_idletasks()
                    details = fetch_details(curr_id)
                    if details:
                        rat, rnk, gt, l_dep, o_name, wgt, minp, maxp, bestp = details
                        bn = o_name
                        with conn:
                            conn.execute('INSERT OR REPLACE INTO games (bgg_id, name, rating, rank, type, last_updated, language_dependency, original_name, weight, min_players, max_players, best_players) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)', (curr_id, name, rat, rnk, gt, datetime.date.today().isoformat(), l_dep, o_name, wgt, minp, maxp, bestp))
            self.bgg_name_disp.config(text=bn)
        finally: conn.close()

    def save(self):
        name = self.name_var.get()
        bid_raw = self.bgg_var.get().strip()
        if not name or not bid_raw: return
        
        # EXTRACTOR DE URL: Omnívoro para juegos, expansiones, etc.
        bid = bid_raw
        url_match = re.search(r'boardgame[^/]*/(\d+)', bid_raw)
        if url_match:
            bid = url_match.group(1)
            self.bgg_var.set(bid) # Mostrar solo el ID limpio en la interfaz

        if not str(bid).isdigit():
            messagebox.showwarning("Atención", "El BGG ID debe ser un número o una URL de juego válida.")
            return
        
        conn = get_db_connection()
        try:
            with conn:
                # Al guardar un mapeo manual, fijamos confianza 100 y borramos candidato
                conn.execute("INSERT OR REPLACE INTO bgg_mapping (item_name, bgg_id, confidence, last_search, candidate_id) VALUES (?,?,?,?,NULL)", (name, bid, 100, datetime.date.today().isoformat()))
                fetch_details(bid) # Aseguramos tener los datos en 'games'
            self.load_data()
            # Limpiar para el siguiente
            self.name_var.set(""); self.bgg_var.set(""); self.lbl_cand_info.config(text="")
        finally: conn.close()

    def search(self):
        bid = self.bgg_var.get()
        if bid and str(bid).isdigit():
            webbrowser.open(f"https://boardgamegeek.com/boardgame/{bid}")
        else:
            self.search_by_name()

    def search_by_name(self):
        name = self.name_var.get()
        if not name: return
        # Limpieza de nombre: quitar (EXP), [NUEVO], etc.
        clean_name = re.sub(r'\(.*?\)|\[.*?\]', '', name).strip()
        # Búsqueda en Google con el sufijo boardgamegeek (Muy potente para errores tipográficos)
        url = f"https://www.google.com/search?q={clean_name.replace(' ', '+')}+boardgamegeek"
        webbrowser.open(url)

    def ignore(self):
        # MODO MASIVO: Obtener todos los seleccionados
        keys = ["wait", "mapped", "ignored", "review"]
        tab_idx = self.notebook.index(self.notebook.select())
        current_tree = self.tabs[keys[tab_idx]]
        
        sel = current_tree.selection()
        if not sel: return
        
        conn = get_db_connection()
        try:
            with conn:
                for iid in sel:
                    name = current_tree.set(iid, "item_name")
                    conn.execute("INSERT OR REPLACE INTO bgg_mapping (item_name, bgg_id, confidence, last_search) VALUES (?,?,?,?)", (name, 'IGNORED', 100, datetime.date.today().isoformat()))
            self.load_data()
            self.name_var.set(""); self.bgg_var.set("")
        finally: conn.close()

    def wait(self):
        # MODO MASIVO
        keys = ["wait", "mapped", "ignored", "review"]
        tab_idx = self.notebook.index(self.notebook.select())
        current_tree = self.tabs[keys[tab_idx]]
        
        sel = current_tree.selection()
        if not sel: return
        
        conn = get_db_connection()
        try:
            with conn:
                for iid in sel:
                    name = current_tree.set(iid, "item_name")
                    conn.execute("INSERT OR REPLACE INTO bgg_mapping (item_name, bgg_id, confidence, last_search) VALUES (?,?,?,?)", (name, 'WAITING', 0, datetime.date.today().isoformat()))
            self.load_data()
            self.name_var.set(""); self.bgg_var.set("")
        finally: conn.close()

    def open_store(self):
        if hasattr(self, 'store_url') and self.store_url:
            webbrowser.open(self.store_url)
        else:
            messagebox.showinfo("INFO", "No hay URL de tienda disponible para este producto.")

    def copy_name(self):
        name = self.name_var.get()
        if name:
            self.root.clipboard_clear()
            self.root.clipboard_append(name)
            self.root.update() # Refrescar portapapeles

if __name__ == "__main__":
    root = tk.Tk()
    app = ManualFixGUI(root)
    root.mainloop()
