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
        self.root.title("Gestor de Mapeo BGG - Ofertas Actuales")
        self.root.geometry("1100x750")
        self.root.configure(bg="#f4f6f9")
        
        init_db()
        self.setup_ui()
        self.show_ignored_var.set(False) # Por defecto ocultar ignorados
        self.load_data()

    def setup_ui(self):
        # Panel Superior (Filtros)
        filter_frame = tk.LabelFrame(self.root, text="🔍 Filtros de Búsqueda", bg="#f4f6f9", padx=10, pady=10)
        filter_frame.pack(fill=tk.X, padx=15, pady=10)

        tk.Label(filter_frame, text="Nombre:", bg="#f4f6f9").pack(side=tk.LEFT)
        self.filter_var = tk.StringVar()
        self.filter_var.trace_add("write", lambda *args: self.load_data())
        tk.Entry(filter_frame, textvariable=self.filter_var, width=35).pack(side=tk.LEFT, padx=10)

        self.only_failed_var = tk.BooleanVar(value=True)
        tk.Checkbutton(filter_frame, text="Solo Fallidos/Sin ID", 
                       variable=self.only_failed_var, command=self.load_data, bg="#f4f6f9").pack(side=tk.LEFT, padx=5)

        self.only_current_var = tk.BooleanVar(value=True)
        tk.Checkbutton(filter_frame, text="Ofertas Actuales", 
                       variable=self.only_current_var, command=self.load_data, bg="#f4f6f9", font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=5)

        self.show_ignored_var = tk.BooleanVar(value=False)
        tk.Checkbutton(filter_frame, text="Mostrar Ignorados", 
                       variable=self.show_ignored_var, command=self.load_data, bg="#f4f6f9").pack(side=tk.LEFT, padx=5)

        self.show_waiting_var = tk.BooleanVar(value=False)
        tk.Checkbutton(filter_frame, text="⏳ Mostrar en Espera", 
                       variable=self.show_waiting_var, command=self.load_data, bg="#f4f6f9").pack(side=tk.LEFT, padx=5)

        self.only_zero_rating_var = tk.BooleanVar(value=False)
        tk.Checkbutton(filter_frame, text="⭐ Rating 0/NA", 
                       variable=self.only_zero_rating_var, command=self.load_data, bg="#f4f6f9", fg="#e67e22").pack(side=tk.LEFT, padx=5)

        tk.Button(filter_frame, text="Refrescar", command=self.load_data, bg="#3498db", fg="white").pack(side=tk.RIGHT)

        # Panel Central
        main_mid_frame = tk.Frame(self.root, bg="#f4f6f9")
        main_mid_frame.pack(fill=tk.BOTH, expand=True, padx=15)

        table_frame = tk.Frame(main_mid_frame)
        table_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        cols = ("item_name", "bgg_id", "conf", "last")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", selectmode='extended')
        self.tree.heading("item_name", text="Nombre en Catálogo", command=lambda: self.treeview_sort_column("item_name", False))
        self.tree.heading("bgg_id", text="BGG ID", command=lambda: self.treeview_sort_column("bgg_id", False))
        self.tree.heading("conf", text="Confianza (%)", command=lambda: self.treeview_sort_column("conf", False))
        self.tree.heading("last", text="Última Búsqueda/Encontrado", command=lambda: self.treeview_sort_column("last", False))
        
        self.tree.column("item_name", width=400)
        self.tree.column("bgg_id", width=100, anchor=tk.CENTER)
        self.tree.column("conf", width=100, anchor=tk.CENTER)
        self.tree.column("last", width=120, anchor=tk.CENTER)
        
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        # Pre-visualización (Derecha)
        self.preview_frame = tk.LabelFrame(main_mid_frame, text="👀 Vista Previa", bg="#fff", padx=10, pady=10, width=300)
        self.preview_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        self.preview_frame.pack_propagate(False)

        self.img_label = tk.Label(self.preview_frame, bg="#eee", width=250, height=250)
        self.img_label.pack(pady=5)
        self.bgg_name_disp = tk.Label(self.preview_frame, text="BGG Name: -", bg="#fff", font=("Arial", 9, "bold"), wraplength=250)
        self.bgg_name_disp.pack(pady=5)
        self.link_store_btn = tk.Button(self.preview_frame, text="🛒 Ver en TIENDA", command=self.open_current_store_link, bg="#27ae60", fg="white", state='disabled', font=("Arial", 9, "bold"))
        self.link_store_btn.pack(pady=5, fill=tk.X)
        self.link_bgg_btn = tk.Button(self.preview_frame, text="🌐 Ver en BGG Site", command=self.open_current_bgg_site, bg="#e67e22", fg="white", state='disabled')
        self.link_bgg_btn.pack(pady=5, fill=tk.X)

        # Panel Inferior
        self.form_frame = tk.LabelFrame(self.root, text="🛠️ Acciones de Datos", bg="#f4f6f9", padx=15, pady=15)
        self.form_frame.pack(fill=tk.X, padx=15, pady=15)

        tk.Label(self.form_frame, text="Producto Seleccionado:", bg="#f4f6f9", font=("Arial", 9, "bold")).grid(row=0, column=0, sticky=tk.W)
        self.name_var = tk.StringVar()
        tk.Entry(self.form_frame, textvariable=self.name_var, state='readonly', width=70).grid(row=0, column=1, columnspan=3, padx=10, pady=5, sticky=tk.W)
        tk.Button(self.form_frame, text="📋 COPIAR NOMBRE", command=self.copy_name, bg="#95a5a6", fg="white", font=("Arial", 8, "bold")).grid(row=0, column=4, padx=5, sticky=tk.W)

        tk.Label(self.form_frame, text="Asignar BGG ID:", bg="#f4f6f9", font=("Arial", 9, "bold")).grid(row=1, column=0, sticky=tk.W)
        self.bgg_var = tk.StringVar()
        self.bgg_entry = tk.Entry(self.form_frame, textvariable=self.bgg_var, width=30, font=("Arial", 11))
        self.bgg_entry.grid(row=1, column=1, padx=10, pady=10, sticky=tk.W)

        tk.Button(self.form_frame, text="✅ GUARDAR MAPEO", command=self.save_mapping, bg="#27ae60", fg="white", font=("Arial", 10, "bold"), padx=15).grid(row=1, column=2, padx=5)
        tk.Button(self.form_frame, text="🔍 Buscar en BGG", command=self.open_bgg_search, bg="#3498db", fg="white").grid(row=1, column=3, padx=5)
        tk.Button(self.form_frame, text="🗑️ ELIMINAR DE DB", command=self.delete_from_db, bg="#c0392b", fg="white", font=("Arial", 9, "bold")).grid(row=1, column=4, padx=20)
        tk.Button(self.form_frame, text="🚫 NO INCLUIR (Ignorar)", command=self.ignore_mapping, bg="#95a5a6", fg="white", font=("Arial", 9, "bold"), height=2).grid(row=2, column=1, sticky=tk.W, padx=10, pady=10)
        tk.Button(self.form_frame, text="⏳ ESPERAR (Muy Nuevo)", command=self.wait_mapping, bg="#f39c12", fg="white", font=("Arial", 9, "bold"), height=2).grid(row=2, column=2, sticky=tk.W, padx=10, pady=10)

        self.current_store_url = ""

    def treeview_sort_column(self, col, reverse):
        l = [(self.tree.set(k, col), k) for k in self.tree.get_children('')]
        
        def convert(val):
            try:
                # Quitar %, €, $ para ordenar numéricamente
                clean_val = re.sub(r'[%€$]', '', val).strip()
                if not clean_val or clean_val == "N/A": return -999999 if not reverse else 999999
                return float(clean_val)
            except:
                return val.lower()

        l.sort(key=lambda t: convert(t[0]), reverse=reverse)

        for index, (val, k) in enumerate(l):
            self.tree.move(k, '', index)

        self.tree.heading(col, command=lambda: self.treeview_sort_column(col, not reverse))

    def load_data(self):
        for item in self.tree.get_children(): self.tree.delete(item)
        search_filter = f"%{self.filter_var.get()}%"
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            max_date = cursor.execute("SELECT MAX(date_found) FROM deals").fetchone()[0] or "1900-01-01"
            
            # Construimos la query usando LEFT JOIN desde deals para no perder productos sin bgg_mapping
            where_parts = ["d.item_name LIKE ?"]
            
            if self.only_failed_var.get():
                where_parts.append("(IFNULL(m.confidence,0) < 95 OR m.bgg_id IS NULL OR m.bgg_id = '')")
            
            if not self.show_ignored_var.get():
                where_parts.append("(m.bgg_id IS NULL OR m.bgg_id != 'IGNORED')")

            if not self.show_waiting_var.get():
                where_parts.append("(m.bgg_id IS NULL OR m.bgg_id != 'WAITING')")
            
            if self.only_current_var.get():
                where_parts.append("d.date_found = (SELECT MAX(date_found) FROM deals d2 WHERE d2.deal_source = d.deal_source)")
            
            if self.only_zero_rating_var.get():
                where_parts.append("(g.rating = '0' OR g.rating = '0.0' OR g.rating = 'N/A' OR g.rating IS NULL)")
            
            where_clause = " AND ".join(where_parts)
            
            query = f"""
                SELECT DISTINCT d.item_name, m.bgg_id, IFNULL(m.confidence,0), IFNULL(m.last_search, d.date_found)
                FROM deals d
                LEFT JOIN bgg_mapping m ON d.item_name = m.item_name
                LEFT JOIN games g ON m.bgg_id = g.bgg_id
                WHERE {where_clause}
                ORDER BY d.date_found DESC, m.last_search DESC LIMIT 400
            """
            
            cursor.execute(query, (search_filter,))
            for r in cursor.fetchall():
                # mostramos como "-" si es NULL
                v = list(r)
                v[1] = v[1] if v[1] else "-"
                v[2] = f"{int(v[2])}%" if v[2] else "0%"
                self.tree.insert("", tk.END, values=v)
        finally:
            conn.close()

    def on_select(self, event):
        selected = self.tree.selection()
        if not selected: return
        vals = self.tree.item(selected[0])['values']
        name = vals[0]
        # Si vals[1] es "-", el ID está vacío
        b_id = str(vals[1]) if (vals[1] and vals[1] != '-') else ""
        self.name_var.set(name); self.bgg_var.set(b_id)
        
        self.current_store_url = ""; img_local = ""; bgg_name = "-"
        conn = get_db_connection()
        try:
            c = conn.cursor()
            row_d = c.execute("SELECT url, image_local FROM deals WHERE item_name=? ORDER BY date_found DESC LIMIT 1", (name,)).fetchone()
            if row_d: self.current_store_url, img_local = row_d
            if b_id and b_id not in ['IGNORED', 'WAITING']:
                row_g = c.execute("SELECT original_name FROM games WHERE bgg_id=?", (b_id,)).fetchone()
                if row_g: bgg_name = row_g[0]
            elif b_id == 'WAITING':
                bgg_name = "⏳ EN ESPERA (Muy Nuevo)"
        finally:
            conn.close()
        self.bgg_name_disp.config(text=f"Nombre BGG:\n{bgg_name}")
        self.link_store_btn.config(state='normal' if self.current_store_url else 'disabled')
        self.link_bgg_btn.config(state='normal' if (b_id and b_id not in ['IGNORED', 'WAITING']) else 'disabled')
        self.img_label.config(image='')
        if img_local:
            ipath = os.path.join(IMG_DIR, img_local)
            if os.path.exists(ipath):
                try: pimg = Image.open(ipath); pimg.thumbnail((250, 250)); tkimg = ImageTk.PhotoImage(pimg); self.img_label.config(image=tkimg); self.img_label.image = tkimg
                except: pass

    def copy_name(self):
        name = self.name_var.get()
        if name:
            self.root.clipboard_clear()
            self.root.clipboard_append(name)
            self.status_bar_msg(f"'{name}' copiado.")

    def status_bar_msg(self, msg):
        # Usamos el título temporalmente o un messagebox discreto
        self.root.title(f"Gestor de Mapeo BGG - {msg}")
        self.root.after(3000, lambda: self.root.title("Gestor de Mapeo BGG - Ofertas Actuales"))

    def open_current_store_link(self):
        if self.current_store_url: webbrowser.open(self.current_store_url)
    def open_current_bgg_site(self):
        v = self.bgg_var.get().strip(); 
        if v and v not in ["IGNORED", "WAITING"]: webbrowser.open(f"https://boardgamegeek.com/boardgame/{v}")
    def open_bgg_search(self):
        n = self.name_var.get()
        if n:
            search_query = re.sub(r'\(.*?\)', '', n).strip().replace(' ', '+')
            webbrowser.open(f"https://boardgamegeek.com/search/boardgame?q={search_query}")

    def save_mapping(self):
        name = self.name_var.get(); new_id = self.bgg_var.get().strip()
        if not name: return
        
        # Manejar URL si se pega una entera (soporta boardgame y boardgameexpansion)
        if "boardgamegeek.com/" in new_id:
            match = re.search(r'/boardgame(?:expansion)?/(\d+)', new_id)
            if match:
                new_id = match.group(1)
                self.bgg_var.set(new_id)

        conn = get_db_connection()
        try:
            with conn:
                cursor = conn.cursor()
                cursor.execute("INSERT OR REPLACE INTO bgg_mapping (item_name, bgg_id, confidence, last_search) VALUES (?,?,?,?)", 
                              (name, new_id, 100.0, datetime.date.today().isoformat()))
                if new_id and new_id != "IGNORED":
                    details = fetch_details(new_id)
                    if details and details[4] != "Unknown":
                        rat, rnk, gt, l_dep, o_name, wgt, minp, maxp, bestp = details
                        cursor.execute('INSERT OR REPLACE INTO games (bgg_id, name, rating, rank, type, last_updated, language_dependency, original_name, weight, min_players, max_players, best_players) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)', (new_id, o_name, rat, rnk, gt, datetime.date.today().isoformat(), l_dep, o_name, wgt, minp, maxp, bestp))
        finally:
            conn.close()
        self.load_data(); messagebox.showinfo("Éxito", "Mapeo guardado.")

    def ignore_mapping(self):
        selected = self.tree.selection()
        if not selected: return
        
        conn = get_db_connection()
        try:
            with conn:
                for item in selected:
                    name = self.tree.item(item)['values'][0]
                    conn.execute("INSERT OR REPLACE INTO bgg_mapping (item_name, bgg_id, confidence, last_search) VALUES (?,?,?,?)", 
                                  (name, "IGNORED", 100.0, datetime.date.today().isoformat()))
        finally:
            conn.close()
        self.load_data()
        self.status_bar_msg(f"{len(selected)} items ignorados.")

    def wait_mapping(self):
        selected = self.tree.selection()
        if not selected: return
        
        conn = get_db_connection()
        try:
            with conn:
                for item in selected:
                    name = self.tree.item(item)['values'][0]
                    conn.execute("INSERT OR REPLACE INTO bgg_mapping (item_name, bgg_id, confidence, last_search) VALUES (?,?,?,?)", 
                                  (name, "WAITING", 100.0, datetime.date.today().isoformat()))
        finally:
            conn.close()
        self.load_data()
        self.status_bar_msg(f"{len(selected)} items marcados en espera.")

    def delete_from_db(self):
        selected = self.tree.selection()
        if not selected: return
        
        if messagebox.askyesno("Confirmar", f"¿Eliminar {len(selected)} items seleccionados de la base de datos?"):
            conn = get_db_connection()
            try:
                with conn:
                    for item in selected:
                        name = self.tree.item(item)['values'][0]
                        conn.execute("DELETE FROM bgg_mapping WHERE item_name = ?", (name,))
                        conn.execute("DELETE FROM deals WHERE item_name = ?", (name,))
            finally:
                conn.close()
            self.load_data()
            self.status_bar_msg(f"{len(selected)} items eliminados.")

if __name__ == "__main__":
    root = tk.Tk(); app = ManualFixGUI(root); root.mainloop()
