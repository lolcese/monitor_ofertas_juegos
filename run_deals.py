import subprocess
import sys
import os
from datetime import datetime

# Tareas de Ofertas y Preventas (Sin catálogo completo)
TASKS = [
    ("Phili Flash", [sys.executable, "scraper_philibert.py", "flash"]),
    ("Phili Occasions", [sys.executable, "scraper_philibert.py", "occasion"]),
    ("Phili Private", [sys.executable, "scraper_philibert.py", "private"]),
    ("Phili Preorder", [sys.executable, "scraper_philibert.py", "preorder"]),
    ("MM Daily", [sys.executable, "scraper_miniature_market.py", "daily"]),
    ("MM Sales", [sys.executable, "scraper_miniature_market.py", "sales"]),
    ("MM Backrooms", [sys.executable, "scraper_miniature_market.py", "backrooms"]),
    ("MM Clearance", [sys.executable, "scraper_miniature_market.py", "clearance"]),
    ("MM GameOn", [sys.executable, "scraper_miniature_market.py", "gameon"]),
    ("MM LastChance", [sys.executable, "scraper_miniature_market.py", "lastchance"]),
    ("MM Markdown", [sys.executable, "scraper_miniature_market.py", "markdown"]),
    ("MM Preorder", [sys.executable, "scraper_miniature_market.py", "preorder"]),
    ("Planeton Ofertas", [sys.executable, "scraper_planeton.py"]),
    ("Planeton Preorder", [sys.executable, "scraper_planeton.py", "preorder"]),
    ("Zatu Sale", [sys.executable, "scraper_zatu.py", "sale"]),
    ("Zatu Outlet", [sys.executable, "scraper_zatu.py", "outlet"]),
    ("Generando Reporte", [sys.executable, "report_generator.py"]),
    ("Publicando en GitHub", [sys.executable, "deploy_to_github.py"])
]

def run():
    print(f"=== MONITOR DEALS: INICIO ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) ===")
    
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
