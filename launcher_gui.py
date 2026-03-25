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
        self.root.geometry("700x550")
        self.root.configure(bg="#f0f2f5")

        # Estilos
        self.style_btn = {"font": ("Arial", 10, "bold"), "width": 20, "pady": 5}
        
        # UI
        main_frame = tk.Frame(root, bg="#f0f2f5")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Sección Philibert
        phili_frame = tk.LabelFrame(main_frame, text="🇫🇷 Philibert", bg="#f0f2f5", font=("Arial", 11, "bold"), padx=10, pady=10)
        phili_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        tk.Button(phili_frame, text="FLASH Sales", command=lambda: self.run_task("Philibert Flash", ["python", "scraper_philibert.py", "flash"]), bg="#f1c40f", **self.style_btn).pack(pady=3)
        tk.Button(phili_frame, text="Occasions", command=lambda: self.run_task("Philibert Occasions", ["python", "scraper_philibert.py", "occasion"]), bg="#9b59b6", fg="white", **self.style_btn).pack(pady=3)
        tk.Button(phili_frame, text="Ventes Privées", command=lambda: self.run_task("Philibert Privées", ["python", "scraper_philibert.py", "private"]), bg="#2c3e50", fg="white", **self.style_btn).pack(pady=3)

        # Sección MM
        mm_frame = tk.LabelFrame(main_frame, text="🇺🇸 Miniature Market", bg="#f0f2f5", font=("Arial", 11, "bold"), padx=10, pady=10)
        mm_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        
        tk.Button(mm_frame, text="MM Deals", command=lambda: self.run_task("MM Deals", ["python", "scraper_miniature_market.py", "deals"]), bg="#27ae60", fg="white", **self.style_btn).pack(pady=3)
        tk.Button(mm_frame, text="MM Backdoors", command=lambda: self.run_task("MM Backdoors", ["python", "scraper_miniature_market.py", "backdoor"]), bg="#e67e22", fg="white", **self.style_btn).pack(pady=3)
        tk.Button(mm_frame, text="MM Clearance", command=lambda: self.run_task("MM Clearance", ["python", "scraper_miniature_market.py", "clearance"]), bg="#c0392b", fg="white", **self.style_btn).pack(pady=3)

        # Sección Reporte y Otros
        tools_frame = tk.LabelFrame(main_frame, text="📊 Herramientas y Reporte", bg="#f0f2f5", font=("Arial", 11, "bold"), padx=10, pady=10)
        tools_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)

        tk.Button(tools_frame, text="GENERAR REPORTE HTML", command=lambda: self.run_task("Reporte", ["python", "report_generator.py"]), bg="#3498db", fg="white", font=("Arial", 11, "bold"), height=2, width=30).grid(row=0, column=0, padx=10, pady=10)
        tk.Button(tools_frame, text="GESTOR DE FALLOS BGG", command=lambda: self.run_task("Mapping", ["python", "manual_fix_gui.py"]), bg="#c0392b", fg="white", font=("Arial", 10, "bold"), width=30, height=2).grid(row=0, column=1, padx=10)

        # Consola Log
        self.log_area = scrolledtext.ScrolledText(main_frame, height=12, font=("Consolas", 9), bg="#1e1e1e", fg="#d4d4d4")
        self.log_area.grid(row=2, column=0, columnspan=2, sticky="nsew", pady=10)

        self.status_lbl = tk.Label(root, text="Listo.", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_lbl.pack(side=tk.BOTTOM, fill=tk.X)

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
            except Exception as e:
                self.log(f"Error fatal: {str(e)}")
                self.root.after(0, lambda: self.status_lbl.config(text="Error de ejecución."))
        threading.Thread(target=worker, daemon=True).start()

if __name__ == "__main__":
    root = tk.Tk()
    app = ScraperLauncher(root)
    root.mainloop()
