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
        self.root.geometry("750x650")
        self.root.configure(bg="#f0f2f5")

        # Estilos
        self.style_btn = {"font": ("Arial", 10, "bold"), "width": 18, "pady": 5}
        self.style_date = {"font": ("Arial", 8), "bg": "#f0f2f5", "fg": "#7f8c8d"}
        
        # UI
        main_frame = tk.Frame(root, bg="#f0f2f5")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Sección Philibert
        phili_frame = tk.LabelFrame(main_frame, text="🇫🇷 Philibert", bg="#f0f2f5", font=("Arial", 11, "bold"), padx=10, pady=10)
        phili_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        f1 = tk.Frame(phili_frame, bg="#f0f2f5")
        f1.pack(pady=3)
        tk.Button(f1, text="FLASH Sales", command=lambda: self.run_task("Philibert Flash", ["python", "scraper_philibert.py", "flash"]), bg="#f1c40f", **self.style_btn).pack(side=tk.LEFT)
        self.lbl_flash = tk.Label(f1, text="...", **self.style_date)
        self.lbl_flash.pack(side=tk.LEFT, padx=10)

        f2 = tk.Frame(phili_frame, bg="#f0f2f5")
        f2.pack(pady=3)
        tk.Button(f2, text="Occasions", command=lambda: self.run_task("Philibert Occasions", ["python", "scraper_philibert.py", "occasion"]), bg="#9b59b6", fg="white", **self.style_btn).pack(side=tk.LEFT)
        self.lbl_occasion = tk.Label(f2, text="...", **self.style_date)
        self.lbl_occasion.pack(side=tk.LEFT, padx=10)

        f3 = tk.Frame(phili_frame, bg="#f0f2f5")
        f3.pack(pady=3)
        tk.Button(f3, text="Ventes Privées", command=lambda: self.run_task("Philibert Privées", ["python", "scraper_philibert.py", "private"]), bg="#2c3e50", fg="white", **self.style_btn).pack(side=tk.LEFT)
        self.lbl_private = tk.Label(f3, text="...", **self.style_date)
        self.lbl_private.pack(side=tk.LEFT, padx=10)

        # Sección MM
        mm_frame = tk.LabelFrame(main_frame, text="🇺🇸 Miniature Market", bg="#f0f2f5", font=("Arial", 11, "bold"), padx=10, pady=10)
        mm_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        
        m1 = tk.Frame(mm_frame, bg="#f0f2f5")
        m1.pack(pady=3)
        tk.Button(m1, text="MM Deals", command=lambda: self.run_task("MM Deals", ["python", "scraper_miniature_market.py", "deals"]), bg="#27ae60", fg="white", **self.style_btn).pack(side=tk.LEFT)
        self.lbl_mm_deals = tk.Label(m1, text="...", **self.style_date)
        self.lbl_mm_deals.pack(side=tk.LEFT, padx=10)

        m2 = tk.Frame(mm_frame, bg="#f0f2f5")
        m2.pack(pady=3)
        tk.Button(m2, text="MM Backdoors", command=lambda: self.run_task("MM Backdoors", ["python", "scraper_miniature_market.py", "backdoor"]), bg="#e67e22", fg="white", **self.style_btn).pack(side=tk.LEFT)
        self.lbl_mm_backdoor = tk.Label(m2, text="...", **self.style_date)
        self.lbl_mm_backdoor.pack(side=tk.LEFT, padx=10)

        m3 = tk.Frame(mm_frame, bg="#f0f2f5")
        m3.pack(pady=3)
        tk.Button(m3, text="MM Clearance", command=lambda: self.run_task("MM Clearance", ["python", "scraper_miniature_market.py", "clearance"]), bg="#c0392b", fg="white", **self.style_btn).pack(side=tk.LEFT)
        self.lbl_mm_clearance = tk.Label(m3, text="...", **self.style_date)
        self.lbl_mm_clearance.pack(side=tk.LEFT, padx=10)

        # Sección Reporte y Otros
        tools_frame = tk.LabelFrame(main_frame, text="📊 Herramientas y Reporte", bg="#f0f2f5", font=("Arial", 11, "bold"), padx=10, pady=10)
        tools_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)

        tk.Button(tools_frame, text="GENERAR REPORTE HTML", command=lambda: self.run_task("Reporte", ["python", "report_generator.py"]), bg="#3498db", fg="white", font=("Arial", 11, "bold"), height=2, width=30).grid(row=0, column=0, padx=10, pady=10)
        tk.Button(tools_frame, text="GESTOR DE FALLOS BGG", command=lambda: self.run_task("Mapping", ["python", "manual_fix_gui.py"]), bg="#c0392b", fg="white", font=("Arial", 10, "bold"), width=30, height=2).grid(row=0, column=1, padx=10)
        tk.Button(tools_frame, text="REINTENTAR COINCIDENCIAS FALLIDAS", command=lambda: self.run_task("Re-procesar", ["python", "reprocess_failed_matches.py"]), bg="#2c3e50", fg="white", font=("Arial", 10, "bold"), width=62, height=1).grid(row=1, column=0, columnspan=2, padx=10, pady=5)

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
            
            self.lbl_mm_deals.config(text=f"Último: {dates.get('mm_deals', 'N/A')}")
            self.lbl_mm_backdoor.config(text=f"Último: {dates.get('mm_backdoor', 'N/A')}")
            self.lbl_mm_clearance.config(text=f"Último: {dates.get('mm_clearance', 'N/A')}")
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
