import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk
from PIL import Image, ImageTk
import subprocess
import threading
import os
import sys
import webbrowser

class ScraperLauncher:
    def __init__(self, root):
        self.root = root
        self.root.title("BGG DEAL MONITOR - Dashboard (Light)")
        self.root.geometry("1150x750")
        self.root.configure(bg="#f8f9fa")

        # Configuración de colores (MODO CLARO)
        self.colors = {
            "bg": "#f8f9fa",
            "card": "#ffffff",
            "text": "#2c3e50",
            "accent": "#3498db",
            "success": "#27ae60",
            "warning": "#f39c12",
            "danger": "#e74c3c",
            "border": "#dee2e6",
            "web": "#dee2e6"
        }
        
        self.style_btn = {"font": ("Segoe UI", 9, "bold"), "width": 18, "pady": 4, "cursor": "hand2", "relief": "flat"}
        self.style_web = {"font": ("Segoe UI", 8, "bold"), "width": 5, "pady": 2, "cursor": "hand2", "relief": "flat", "bg": "#dee2e6", "fg": "#2c3e50"}
        self.style_date = {"font": ("Segoe UI", 8), "bg": "#ffffff", "fg": "#6c757d"}
        
        # Mapeo de URLs
        self.URLS = {
            'phili_flash': "https://www.philibertnet.com/fr/flash-sales",
            'phili_occasion': "https://www.philibertnet.com/fr/214-occasions",
            'phili_private': "https://www.philibertnet.com/fr/15007-ventes-privees",
            'phili_preorder': "https://www.philibertnet.com/fr/578-precommandes",
            'mm_daily': "https://www.miniaturemarket.com/dailydeal?properties=019262c7e0db711a97a94030d6103aa9",
            'mm_sales': "https://www.miniaturemarket.com/deals.html?properties=019262c7e0db711a97a94030d6103aa9",
            'mm_backrooms': "https://www.miniaturemarket.com/the-backrooms?properties=019262c7e0db711a97a94030d6103aa9",
            'mm_clearance': "https://www.miniaturemarket.com/deals/clearance.html?properties=019262c7e0db711a97a94030d6103aa9",
            'mm_gameon': "https://www.miniaturemarket.com/deals/game-on-weekend?properties=019262c7e0db711a97a94030d6103aa9",
            'mm_lastchance': "https://www.miniaturemarket.com/search?search=Last+Chance&properties=019262c7e0db711a97a94030d6103aa9",
            'mm_markdown': "https://www.miniaturemarket.com/search?search=Markdown&properties=019262c7e0db711a97a94030d6103aa9",
            'mm_preorder': "https://www.miniaturemarket.com/search?search=Pre-order&properties=019262c7e0db711a97a94030d6103aa9",
            'planeton': "https://www.planetongames.com/es/ofertas-195",
            'planeton_preorder': "https://www.planetongames.com/es/proximamente-192",
            'planeton_catalog': "https://www.planetongames.com/es/juegos-de-mesa-divertidos-10/s-1/idioma_del_juego-juegos_de_mesa_divertidos/en_stock-si"
        }
        
        self.load_logos()
        
        # --- UI LAYOUT ---
        main_frame = tk.Frame(root, bg=self.colors["bg"])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)

        # CABECERA
        header_frame = tk.Frame(main_frame, bg=self.colors["bg"])
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(header_frame, text="BGG MONITOR", font=("Segoe UI", 20, "bold"), bg=self.colors["bg"], fg=self.colors["text"]).pack(side=tk.LEFT)
        self.status_ball = tk.Label(header_frame, text="●", font=("Arial", 14), bg=self.colors["bg"], fg=self.colors["success"])
        self.status_ball.pack(side=tk.RIGHT, padx=5)
        self.status_lbl = tk.Label(header_frame, text="SISTEMA LISTO", font=("Segoe UI", 10, "bold"), bg=self.colors["bg"], fg=self.colors["text"])
        self.status_lbl.pack(side=tk.RIGHT)

        # ZONA DE TIENDAS
        shops_container = tk.Frame(main_frame, bg=self.colors["bg"])
        shops_container.pack(fill=tk.X, expand=False)
        
        col1 = tk.Frame(shops_container, bg=self.colors["bg"])
        col1.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        self.create_phili_card(col1)
        self.create_planeton_card(col1)

        col2 = tk.Frame(shops_container, bg=self.colors["bg"])
        col2.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.create_mm_card(col2)

        # ZONA INFERIOR
        bottom_frame = tk.Frame(main_frame, bg=self.colors["bg"])
        bottom_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        # HERRAMIENTAS
        tools_frame = tk.LabelFrame(bottom_frame, text=" ACCIONES ", bg=self.colors["bg"], fg=self.colors["accent"], font=("Segoe UI", 10, "bold"), padx=10, pady=10, relief="flat", highlightthickness=1, highlightbackground=self.colors["border"])
        tools_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        self.create_tools_panel(tools_frame)

        # CONSOLA LOG
        log_frame = tk.LabelFrame(bottom_frame, text=" REGISTRO ", bg=self.colors["bg"], fg=self.colors["text"], font=("Segoe UI", 10, "bold"), padx=5, pady=5)
        log_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.log_area = scrolledtext.ScrolledText(log_frame, height=5, font=("Consolas", 9), bg="#ffffff", fg="#495057", relief="flat", highlightthickness=1, highlightbackground="#dee2e6")
        self.log_area.pack(fill=tk.BOTH, expand=True)

        self.update_sync_labels()

    def load_logos(self):
        self.logos = {}
        assets_dir = os.path.join(os.path.dirname(__file__), "assets")
        logo_files = {"phili": "Logo_Philibert.png", "mm": "miniaturemarket_logo.jpeg", "planeton": "planeton_logo.jpg"}
        for key, name in logo_files.items():
            try:
                img = Image.open(os.path.join(assets_dir, name))
                img.thumbnail((100, 30), Image.Resampling.LANCZOS)
                self.logos[key] = ImageTk.PhotoImage(img)
            except: self.logos[key] = None

    def visit_url(self, key):
        url = self.URLS.get(key)
        if url: webbrowser.open(url)

    def create_phili_card(self, parent):
        card = tk.LabelFrame(parent, text=" 🇫🇷 PHILIBERT ", bg=self.colors["card"], fg=self.colors["text"], font=("Segoe UI", 10, "bold"), padx=10, pady=5, relief="flat", highlightthickness=1, highlightbackground=self.colors["border"])
        card.pack(fill=tk.X, pady=(0, 10))
        if self.logos["phili"]: tk.Label(card, image=self.logos["phili"], bg=self.colors["card"]).grid(row=0, column=0, columnspan=3, pady=(0,5))
        
        tasks = [("FLASH Sales", "flash", "#f1c40f", "black", "lbl_flash"), ("Occasions", "occasion", "#8e44ad", "white", "lbl_occasion"), 
                 ("Ventes Privées", "private", "#2c3e50", "white", "lbl_private"), ("Précommandes", "preorder", "#16a085", "white", "lbl_phili_pre")]
        
        for i, (txt, arg, bg, fg, lbl_attr) in enumerate(tasks):
            btn = tk.Button(card, text=txt, bg=bg, fg=fg, **self.style_btn, command=lambda a=arg, t=txt: self.run_task(f"Phili {t}", ["python", "scraper_philibert.py", a]))
            btn.grid(row=i+1, column=0, pady=2, sticky="w")
            tk.Button(card, text="WEB", **self.style_web, command=lambda a=f"phili_{arg}": self.visit_url(a)).grid(row=i+1, column=1, padx=5)
            lbl = tk.Label(card, text="...", **self.style_date)
            lbl.grid(row=i+1, column=2, padx=10, sticky="w")
            setattr(self, lbl_attr, lbl)

    def create_planeton_card(self, parent):
        card = tk.LabelFrame(parent, text=" 🇪🇸 PLANETON ", bg=self.colors["card"], fg=self.colors["text"], font=("Segoe UI", 10, "bold"), padx=10, pady=5, relief="flat", highlightthickness=1, highlightbackground=self.colors["border"])
        card.pack(fill=tk.X)
        if self.logos["planeton"]: tk.Label(card, image=self.logos["planeton"], bg=self.colors["card"]).grid(row=0, column=0, columnspan=3, pady=(0,5))
        
        tk.Button(card, text="Ofertas", bg="#e74c3c", fg="white", **self.style_btn, command=lambda: self.run_task("Planeton Ofertas", ["python", "scraper_planeton.py"])).grid(row=1, column=0, pady=2, sticky="w")
        tk.Button(card, text="WEB", **self.style_web, command=lambda: self.visit_url("planeton")).grid(row=1, column=1, padx=5)
        self.lbl_planeton = tk.Label(card, text="...", **self.style_date); self.lbl_planeton.grid(row=1, column=2, padx=10, sticky="w")
        
        tk.Button(card, text="Próximamente", bg="#c0392b", fg="white", **self.style_btn, command=lambda: self.run_task("Planeton Próximamente", ["python", "scraper_planeton.py", "preorder"])).grid(row=2, column=0, pady=2, sticky="w")
        tk.Button(card, text="WEB", **self.style_web, command=lambda: self.visit_url("planeton_preorder")).grid(row=2, column=1, padx=5)
        self.lbl_planeton_pre = tk.Label(card, text="...", **self.style_date); self.lbl_planeton_pre.grid(row=2, column=2, padx=10, sticky="w")

        tk.Button(card, text="Catálogo Completo", bg="#3498db", fg="white", **self.style_btn, command=lambda: self.run_task("Planeton Catálogo", ["python", "scraper_planeton.py", "catalog"])).grid(row=3, column=0, pady=2, sticky="w")
        tk.Button(card, text="WEB", **self.style_web, command=lambda: self.visit_url("planeton_catalog")).grid(row=3, column=1, padx=5)
        self.lbl_planeton_cat = tk.Label(card, text="...", **self.style_date); self.lbl_planeton_cat.grid(row=3, column=2, padx=10, sticky="w")

    def create_mm_card(self, parent):
        card = tk.LabelFrame(parent, text=" 🇺🇸 MINIATURE MARKET ", bg=self.colors["card"], fg=self.colors["text"], font=("Segoe UI", 10, "bold"), padx=10, pady=5, relief="flat", highlightthickness=1, highlightbackground=self.colors["border"])
        card.pack(fill=tk.BOTH, expand=True)
        if self.logos["mm"]: tk.Label(card, image=self.logos["mm"], bg=self.colors["card"]).grid(row=0, column=0, columnspan=6, pady=(0,5))
        
        mm_tasks = [("Daily Deal", "daily", "#27ae60", "lbl_mm_daily"), ("All Sales", "sales", "#2980b9", "lbl_mm_sales"), 
                    ("The Backrooms", "backrooms", "#e67e22", "lbl_mm_backrooms"), ("Clearance", "clearance", "#c0392b", "lbl_mm_clearance"),
                    ("Game On", "gameon", "#34495e", "lbl_mm_gameon"), ("Last Chance", "lastchance", "#d35400", "lbl_mm_lastchance"),
                    ("Markdown", "markdown", "#7f8c8d", "lbl_mm_markdown"), ("Pre-orders", "preorder", "#16a085", "lbl_mm_preorder")]
        for i, (txt, arg, bg, lbl_attr) in enumerate(mm_tasks):
            r, c = divmod(i, 2)
            btn = tk.Button(card, text=txt, bg=bg, fg="white", **self.style_btn, command=lambda a=arg, t=txt: self.run_task(f"MM {t}", ["python", "scraper_miniature_market.py", a]))
            btn.grid(row=r+1, column=c*3, pady=3, padx=5, sticky="w")
            tk.Button(card, text="WEB", **self.style_web, command=lambda a=f"mm_{arg}": self.visit_url(a)).grid(row=r+1, column=c*3+1, padx=2)
            lbl = tk.Label(card, text="...", **self.style_date)
            lbl.grid(row=r+1, column=c*3+2, padx=2, sticky="w")
            setattr(self, lbl_attr, lbl)

    def create_tools_panel(self, parent):
        tk.Button(parent, text="🚀 EJECUTAR TODO", bg=self.colors["success"], fg="white", font=("Segoe UI", 10, "bold"), relief="flat", height=2, cursor="hand2", command=self.run_all_scrapers).pack(fill=tk.X, pady=(0, 10))
        
        tool_row = tk.Frame(parent, bg=self.colors["bg"])
        tool_row.pack(fill=tk.X)
        tk.Button(tool_row, text="📊 REPORTE", bg=self.colors["accent"], fg="white", font=("Segoe UI", 8, "bold"), width=12, pady=6, relief="flat", command=lambda: self.run_task("Reporte", ["python", "report_generator.py"])).pack(side=tk.LEFT, expand=True, padx=1)
        tk.Button(tool_row, text="🔧 GESTOR", bg="#e67e22", fg="white", font=("Segoe UI", 8, "bold"), width=12, pady=6, relief="flat", command=lambda: self.run_task("Mapping", ["python", "manual_fix_gui.py"])).pack(side=tk.LEFT, expand=True, padx=1)
        tk.Button(tool_row, text="⌛ FIN", bg="#95a5a6", fg="white", font=("Segoe UI", 8, "bold"), width=10, pady=6, relief="flat", command=lambda: self.run_task("Reporte Inactivo", ["python", "generate_inactive_report.py"])).pack(side=tk.LEFT, expand=True, padx=1)

        tk.Button(parent, text="🔄 REINICIAR MATCHES", bg="#6c757d", fg="white", font=("Segoe UI", 8, "bold"), relief="flat", pady=4, command=lambda: self.run_task("Re-procesar", ["python", "reprocess_failed_matches.py"])).pack(fill=tk.X, pady=(10, 2))
        
        tk.Label(parent, text="", bg=self.colors["bg"]).pack(expand=True)
        tk.Button(parent, text="🌎 PUBLICAR GITHUB", bg="#10ac84", fg="white", font=("Segoe UI", 11, "bold"), height=2, relief="flat", cursor="hand2", command=lambda: self.run_task("GitHub Push", ["python", "deploy_to_github.py"])).pack(fill=tk.X)

    def update_sync_labels(self):
        try:
            from monitor_core import get_db_connection
            conn = get_db_connection()
            rows = conn.execute("SELECT deal_source, MAX(date_found) FROM deals GROUP BY deal_source").fetchall(); conn.close()
            dates = {row[0]: row[1] for row in rows}
            mapping = {'flash': self.lbl_flash, 'occasion': self.lbl_occasion, 'private': self.lbl_private, 'preorder': self.lbl_phili_pre,
                       'mm_daily': self.lbl_mm_daily, 'mm_sales': self.lbl_mm_sales, 'mm_backrooms': self.lbl_mm_backrooms, 'mm_clearance': self.lbl_mm_clearance, 
                       'mm_gameon': self.lbl_mm_gameon, 'mm_lastchance': self.lbl_mm_lastchance, 'mm_markdown': self.lbl_mm_markdown, 'mm_preorder': self.lbl_mm_preorder,
                       'planeton': self.lbl_planeton, 'planeton_preorder': self.lbl_planeton_pre, 'planeton_catalog': self.lbl_planeton_cat}
            for key, lbl in mapping.items(): lbl.config(text=f"S: {dates.get(key, 'N/A')}")
        except: pass

    def log(self, text, clear=False):
        if clear:
            self.log_area.delete('1.0', tk.END)
        self.log_area.insert(tk.END, text + "\n")
        self.log_area.see(tk.END)

    def run_task(self, name, cmd):
        def worker():
            from datetime import datetime
            self.root.after(0, lambda: self.status_lbl.config(text=f"TRABAJANDO...", fg=self.colors["warning"]))
            self.root.after(0, lambda: self.status_ball.config(fg=self.colors["warning"]))
            self.root.after(0, lambda: self.log(f"=== INICIO: {name.upper()} ({datetime.now().strftime('%H:%M:%S')}) ===", clear=True))
            try:
                cmd_run = list(cmd)
                if cmd_run[0] == "python": cmd_run.insert(1, "-u")
                
                # Forzar UTF-8 para evitar UnicodeEncodeError en Windows
                env = os.environ.copy()
                env["PYTHONIOENCODING"] = "utf-8"
                
                proc = subprocess.Popen(cmd_run, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors='replace', bufsize=1, env=env)
                for line in proc.stdout: self.root.after(0, lambda l=line: self.log(l.strip()))
                proc.wait()
                self.root.after(0, lambda: self.log(f"\n=== FINALIZADO: {name.upper()} ({datetime.now().strftime('%H:%M:%S')}) ==="))
                self.root.after(0, lambda: self.status_lbl.config(text="LISTO", fg=self.colors["text"]))
                self.root.after(0, lambda: self.status_ball.config(fg=self.colors["success"]))
                self.root.after(0, self.update_sync_labels)
            except Exception as e:
                self.root.after(0, lambda ex=e: self.log(f"ERROR EN TAREA: {ex}"))
        threading.Thread(target=worker, daemon=True).start()

    def run_all_scrapers(self):
        tasks = [
            ("Phili Flash", ["python", "scraper_philibert.py", "flash"]),
            ("Phili Occasions", ["python", "scraper_philibert.py", "occasion"]),
            ("Phili Private", ["python", "scraper_philibert.py", "private"]),
            ("Phili Preorder", ["python", "scraper_philibert.py", "preorder"]),
            ("MM Daily", ["python", "scraper_miniature_market.py", "daily"]),
            ("MM Sales", ["python", "scraper_miniature_market.py", "sales"]),
            ("MM Clearance", ["python", "scraper_miniature_market.py", "clearance"]),
            ("MM GameOn", ["python", "scraper_miniature_market.py", "gameon"]),
            ("MM LastChance", ["python", "scraper_miniature_market.py", "lastchance"]),
            ("MM Markdown", ["python", "scraper_miniature_market.py", "markdown"]),
            ("MM Preorder", ["python", "scraper_miniature_market.py", "preorder"]),
            ("Planeton Ofertas", ["python", "scraper_planeton.py"]),
            ("Planeton Preorder", ["python", "scraper_planeton.py", "preorder"]),
            ("Reporte Final", ["python", "report_generator.py"])
        ]
        def worker():
            from datetime import datetime
            self.root.after(0, lambda: self.status_lbl.config(text="SINCRO GLOBAL", fg=self.colors["warning"]))
            self.root.after(0, lambda: self.status_ball.config(fg=self.colors["warning"]))
            self.root.after(0, lambda: self.log(f"=== INICIANDO SINCRONIZACION TOTAL ({datetime.now().strftime('%H:%M:%S')}) ===", clear=True))
            
            for name, cmd in tasks:
                try:
                    self.root.after(0, lambda n=name: self.log(f"\n--- PROCESANDO: {n} ---"))
                    cmd_to_run = list(cmd)
                    if cmd_to_run[0] == "python": cmd_to_run.insert(1, "-u")
                    
                    # Forzar UTF-8
                    env = os.environ.copy()
                    env["PYTHONIOENCODING"] = "utf-8"
                    
                    proc = subprocess.Popen(cmd_to_run, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors='replace', bufsize=1, env=env)
                    for line in proc.stdout: self.root.after(0, lambda l=line: self.log(l.strip()))
                    proc.wait(); self.root.after(0, self.update_sync_labels)
                except Exception as e:
                    self.root.after(0, lambda ex=e: self.log(f"Error en {name}: {ex}"))
            
            self.root.after(0, lambda: self.log(f"\n=== SINCRONIZACION FINALIZADA ({datetime.now().strftime('%H:%M:%S')}) ==="))
            self.root.after(0, lambda: self.status_lbl.config(text="LISTO", fg=self.colors["text"]))
            self.root.after(0, lambda: self.status_ball.config(fg=self.colors["success"]))
        threading.Thread(target=worker, daemon=True).start()

if __name__ == "__main__":
    root = tk.Tk(); app = ScraperLauncher(root); root.mainloop()
