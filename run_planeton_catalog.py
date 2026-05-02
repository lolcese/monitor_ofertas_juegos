import subprocess
import sys
import os
from datetime import datetime

# Tareas exclusivas de Catálogo Planeton
TASKS = [
    ("Planeton Catálogo Completo", [sys.executable, "scraper_planeton.py", "catalog"]),
    ("Generando Reporte", [sys.executable, "report_generator.py"]),
    ("Publicando en GitHub", [sys.executable, "deploy_to_github.py"])
]

def run():
    print(f"=== PLANETON CATALOG: INICIO ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) ===")
    
    # 0. Sincronizar cambios previos
    print("--- Sincronizando desde GitHub ---")
    subprocess.run(["git", "pull"])
    
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    for name, cmd in TASKS:
        print(f"\n--- {name} ---")
        subprocess.run([cmd[0], "-u"] + cmd[1:], env=env)
    print(f"\n=== FINALIZADO ({datetime.now().strftime('%H:%M:%S')}) ===")

if __name__ == "__main__":
    run()
