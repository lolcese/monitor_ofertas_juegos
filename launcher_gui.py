import tkinter as tk
from tkinter import scrolledtext, messagebox
import subprocess
import threading
import os
import sys

class ScraperLauncher:
    def __init__(self, root):
        self.root = root
        self.root.title("Monitor de Ofertas BGG - Panel de Control")
        self.root.geometry("800x750")
        self.root.configure(bg="#f0f2f5")

        # Estilos
        self.style_btn = {"font": ("Arial", 10, "bold"), "width": 20, "pady": 5}
        self.style_date = {"font": ("Arial", 8), "bg": "#f0f2f5", "fg": "#7f8c8d"}
        
        # UI
        main_frame = tk.Frame(root, bg="#f0f2f5")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Sección Philibert
        phili_frame = tk.LabelFrame(main_frame, text="🇫🇷 Philibert", bg="#f0f2f5", font=("Arial", 11, "bold"), padx=15, pady=10)
        phili_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        tk.Button(phili_frame, text="FLASH Sales", command=lambda: self.run_task("Philibert Flash", ["python", "scraper_philibert.py", "flash"]), bg="#f1c40f", **self.style_btn).grid(row=0, column=0, pady=3, sticky="w")
        self.lbl_flash = tk.Label(phili_frame, text="...", **self.style_date)
        self.lbl_flash.grid(row=0, column=1, padx=10, sticky="w")

        tk.Button(phili_frame, text="Occasions", command=lambda: self.run_task("Philibert Occasions", ["python", "scraper_philibert.py", "occasion"]), bg="#9b59b6", fg="white", **self.style_btn).grid(row=1, column=0, pady=3, sticky="w")
        self.lbl_occasion = tk.Label(phili_frame, text="...", **self.style_date)
        self.lbl_occasion.grid(row=1, column=1, padx=10, sticky="w")

        tk.Button(phili_frame, text="Ventes Privées", command=lambda: self.run_task("Philibert Privées", ["python", "scraper_philibert.py", "private"]), bg="#2c3e50", fg="white", **self.style_btn).grid(row=2, column=0, pady=3, sticky="w")
        self.lbl_private = tk.Label(phili_frame, text="...", **self.style_date)
        self.lbl_private.grid(row=2, column=1, padx=10, sticky="w")

        # Sección MM
        mm_frame = tk.LabelFrame(main_frame, text="🇺🇸 Miniature Market", bg="#f0f2f5", font=("Arial", 11, "bold"), padx=15, pady=10)
        mm_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        
        tk.Button(mm_frame, text="MM Daily Deal", command=lambda: self.run_task("MM Daily", ["python", "scraper_miniature_market.py", "daily"]), bg="#27ae60", fg="white", **self.style_btn).grid(row=0, column=0, pady=3, sticky="w")
        self.lbl_mm_daily = tk.Label(mm_frame, text="...", **self.style_date)
        self.lbl_mm_daily.grid(row=0, column=1, padx=10, sticky="w")

        tk.Button(mm_frame, text="MM All Sales", command=lambda: self.run_task("MM Sales", ["python", "scraper_miniature_market.py", "sales"]), bg="#2980b9", fg="white", **self.style_btn).grid(row=1, column=0, pady=3, sticky="w")
        self.lbl_mm_sales = tk.Label(mm_frame, text="...", **self.style_date)
        self.lbl_mm_sales.grid(row=1, column=1, padx=10, sticky="w")

        tk.Button(mm_frame, text="The Backrooms", command=lambda: self.run_task("The Backrooms", ["python", "scraper_miniature_market.py", "backrooms"]), bg="#e67e22", fg="white", **self.style_btn).grid(row=2, column=0, pady=3, sticky="w")
        self.lbl_mm_backrooms = tk.Label(mm_frame, text="...", **self.style_date)
        self.lbl_mm_backrooms.grid(row=2, column=1, padx=10, sticky="w")

        tk.Button(mm_frame, text="MM Clearance", command=lambda: self.run_task("MM Clearance", ["python", "scraper_miniature_market.py", "clearance"]), bg="#c0392b", fg="white", **self.style_btn).grid(row=3, column=0, pady=3, sticky="w")
        self.lbl_mm_clearance = tk.Label(mm_frame, text="...", **self.style_date)
        self.lbl_mm_clearance.grid(row=3, column=1, padx=10, sticky="w")

        tk.Button(mm_frame, text="Game On Weekend", command=lambda: self.run_task("Game On Weekend", ["python", "scraper_miniature_market.py", "gameon"]), bg="#34495e", fg="white", **self.style_btn).grid(row=4, column=0, pady=3, sticky="w")
        self.lbl_mm_gameon = tk.Label(mm_frame, text="...", **self.style_date)
        self.lbl_mm_gameon.grid(row=4, column=1, padx=10, sticky="w")

        tk.Button(mm_frame, text="MM Last Chance", command=lambda: self.run_task("MM Last Chance", ["python", "scraper_miniature_market.py", "lastchance"]), bg="#d35400", fg="white", **self.style_btn).grid(row=5, column=0, pady=3, sticky="w")
        self.lbl_mm_lastchance = tk.Label(mm_frame, text="...", **self.style_date)
        self.lbl_mm_lastchance.grid(row=5, column=1, padx=10, sticky="w")

        tk.Button(mm_frame, text="MM Markdown", command=lambda: self.run_task("MM Markdown", ["python", "scraper_miniature_market.py", "markdown"]), bg="#7f8c8d", fg="white", **self.style_btn).grid(row=6, column=0, pady=3, sticky="w")
        self.lbl_mm_markdown = tk.Label(mm_frame, text="...", **self.style_date)
        self.lbl_mm_markdown.grid(row=6, column=1, padx=10, sticky="w")

        tk.Button(mm_frame, text="Pre-orders Specials", command=lambda: self.run_task("Pre-orders", ["python", "scraper_miniature_market.py", "preorder"]), bg="#16a085", fg="white", **self.style_btn).grid(row=7, column=0, pady=3, sticky="w")
        self.lbl_mm_preorder = tk.Label(mm_frame, text="...", **self.style_date)
        self.lbl_mm_preorder.grid(row=7, column=1, padx=10, sticky="w")

        # Sección Tiendas Españolas (NUEVA)
        es_frame = tk.LabelFrame(main_frame, text="🇪🇸 Tiendas Españolas", bg="#f0f2f5", font=("Arial", 11, "bold"), padx=15, pady=10)
        es_frame.grid(row=0, column=2, sticky="nsew", padx=5)

        tk.Button(es_frame, text="Planeton Ofertas", command=lambda: self.run_task("Planeton Ofertas", ["python", "scraper_planeton.py"]), bg="#e74c3c", fg="white", **self.style_btn).grid(row=0, column=0, pady=3, sticky="w")
        self.lbl_planeton = tk.Label(es_frame, text="...", **self.style_date)
        self.lbl_planeton.grid(row=0, column=1, padx=10, sticky="w")

        tk.Button(es_frame, text="Planeton Próximamente", command=lambda: self.run_task("Planeton Próximamente", ["python", "scraper_planeton.py", "preorder"]), bg="#c0392b", fg="white", **self.style_btn).grid(row=1, column=0, pady=3, sticky="w")
        self.lbl_planeton_pre = tk.Label(es_frame, text="...", **self.style_date)
        self.lbl_planeton_pre.grid(row=1, column=1, padx=10, sticky="w")
        tools_frame = tk.LabelFrame(main_frame, text="📊 Herramientas y Reporte", bg="#f0f2f5", font=("Arial", 11, "bold"), padx=15, pady=10)
        tools_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=5, pady=10)

        tk.Button(tools_frame, text="GENERAR REPORTE HTML", command=lambda: self.run_task("Reporte", ["python", "report_generator.py"]), bg="#3498db", fg="white", font=("Arial", 11, "bold"), height=2, width=32).grid(row=0, column=0, padx=10, pady=10)
        tk.Button(tools_frame, text="REPORTE OFERTAS FINALIZADAS", command=lambda: self.run_task("Reporte Inactivo", ["python", "generate_inactive_report.py"]), bg="#95a5a6", fg="white", font=("Arial", 11, "bold"), height=2, width=32).grid(row=0, column=1, padx=10)
        tk.Button(tools_frame, text="GESTOR DE FALLOS BGG", command=lambda: self.run_task("Mapping", ["python", "manual_fix_gui.py"]), bg="#c0392b", fg="white", font=("Arial", 10, "bold"), width=32, height=1).grid(row=1, column=0, padx=10, pady=5)
        tk.Button(tools_frame, text="REINTENTAR COINCIDENCIAS FALLIDAS", command=lambda: self.run_task("Re-procesar", ["python", "reprocess_failed_matches.py"]), bg="#2c3e50", fg="white", font=("Arial", 10, "bold"), width=32, height=1).grid(row=1, column=1, padx=10, pady=5)

        # Consola Log
        self.log_area = scrolledtext.ScrolledText(main_frame, height=12, font=("Consolas", 9), bg="#1e1e1e", fg="#d4d4d4")
        self.log_area.grid(row=2, column=0, columnspan=2, sticky="nsew", pady=10)

        self.status_lbl = tk.Label(root, text="Listo.", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_lbl.pack(side=tk.BOTTOM, fill=tk.X)

        self.update_sync_labels()

    def update_sync_labels(self):
        try:
            from monitor_core import get_db_connection
            conn = get_db_connection()
            rows = conn.execute("SELECT deal_source, MAX(date_found) FROM deals GROUP BY deal_source").fetchall()
            conn.close()
            
            dates = {row[0]: row[1] for row in rows}
            
            self.lbl_flash.config(text=f"Último: {dates.get('flash', 'N/A')}")
            self.lbl_occasion.config(text=f"Último: {dates.get('occasion', 'N/A')}")
            self.lbl_private.config(text=f"Último: {dates.get('private', 'N/A')}")
            
            self.lbl_mm_daily.config(text=f"Último: {dates.get('mm_daily', 'N/A')}")
            self.lbl_mm_sales.config(text=f"Último: {dates.get('mm_sales', 'N/A')}")
            self.lbl_mm_backrooms.config(text=f"Último: {dates.get('mm_backrooms', 'N/A')}")
            self.lbl_mm_clearance.config(text=f"Último: {dates.get('mm_clearance', 'N/A')}")
            self.lbl_mm_gameon.config(text=f"Último: {dates.get('mm_gameon', 'N/A')}")
            self.lbl_mm_lastchance.config(text=f"Último: {dates.get('mm_lastchance', 'N/A')}")
            self.lbl_mm_markdown.config(text=f"Último: {dates.get('mm_markdown', 'N/A')}")
            self.lbl_mm_preorder.config(text=f"Último: {dates.get('mm_preorder', 'N/A')}")
            self.lbl_planeton.config(text=f"Último: {dates.get('planeton', 'N/A')}")
            self.lbl_planeton_pre.config(text=f"Último: {dates.get('planeton_preorder', 'N/A')}")
        except:
            pass

    def log(self, text):
        self.log_area.insert(tk.END, text + "\n")
        self.log_area.see(tk.END)

    def run_task(self, name, cmd):
        def worker():
            self.root.after(0, lambda: self.status_lbl.config(text=f"Ejecutando: {name}..."))
            self.log(f">>> Iniciando: {' '.join(cmd)}")
            try:
                if cmd[0] == "python": cmd.insert(1, "-u")
                process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors='replace', bufsize=1)
                for line in process.stdout:
                    self.root.after(0, lambda l=line: self.log(l.strip()))
                process.wait()
                if process.returncode == 0:
                    self.log(f"<<< Finalizado correctamente.")
                    self.root.after(0, lambda: self.status_lbl.config(text="Tarea completada."))
                else:
                    self.log(f"<<< Finalizado con errores (Code: {process.returncode})")
                    self.root.after(0, lambda: self.status_lbl.config(text="Error detectado."))
                
                # Actualizar etiquetas después de cualquier tarea
                self.root.after(0, self.update_sync_labels)
            except Exception as e:
                self.log(f"Error fatal: {str(e)}")
                self.root.after(0, lambda: self.status_lbl.config(text="Error de ejecución."))
        threading.Thread(target=worker, daemon=True).start()

if __name__ == "__main__":
    root = tk.Tk()
    app = ScraperLauncher(root)
    root.mainloop()
