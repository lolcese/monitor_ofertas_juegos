import tkinter as tk
from tkinter import messagebox, ttk
import requests
import re
from bs4 import BeautifulSoup
import datetime
import sqlite3
import os

# Importamos las utilidades del núcleo para no repetir lógica
from philibert_core import fetch_details, get_db_connection

def run_fix():
    phili_url = entry_phili.get().strip()
    bgg_input = entry_bgg.get().strip()
    
    if not phili_url or not bgg_input:
        messagebox.showwarning("Faltan datos", "Por favor, introduce ambas URLs.")
        return

    try:
        # 0. Headers de navegador para evitar el 503
        PHILI_HEADERS = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        }
        
        lbl_status.config(text="🔍 Identificando producto...", foreground="#2980b9")
        root.update_idletasks()

        # 1. Extraer ID de BGG
        bgg_id = re.search(r'boardgame/(\d+)', bgg_input)
        bgg_id = bgg_id.group(1) if bgg_id else bgg_input
        
        # 2. Consultar Philibert
        res = requests.get(phili_url, headers=PHILI_HEADERS, timeout=10)
        res.raise_for_status()
        soup = BeautifulSoup(res.content, 'html.parser')
        
        title_tag = soup.find('h1', class_='item-title') or soup.find('h1')
        if not title_tag:
            messagebox.showerror("Error", "No se pudo encontrar el título en Philibert.")
            return
        
        p_name = title_tag.text.strip()
        
        # 3. Consultar BGG
        lbl_status.config(text=f"🌐 Consultando BGG para {bgg_id}...", foreground="#8e44ad")
        root.update_idletasks()
        
        rat, rnk, gt, l_dep, o_name, wgt, minp, maxp, bestp = fetch_details(bgg_id)
        
        # 4. Guardar en Base de Datos
        today = datetime.date.today().isoformat()
        db_path = r'c:\Datos\Luis\bgg\Phillibert\bgg_cache.db'
        conn = sqlite3.connect(db_path)
        
        # Mapeo
        conn.execute('INSERT OR REPLACE INTO bgg_mapping (philibert_name, bgg_id, confidence, last_search) VALUES (?, ?, ?, ?)',
                     (p_name, bgg_id, 100.0, today))
        
        # Juego
        conn.execute('''
            INSERT OR REPLACE INTO games (bgg_id, name, rating, rank, type, last_updated, language_dependency, original_name, weight, min_players, max_players, best_players)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (bgg_id, o_name, rat, rnk, gt, today, l_dep, o_name, wgt, minp, maxp, bestp))
        
        conn.commit()
        conn.close()
        
        lbl_status.config(text=f"✅ Mapeo completado: '{o_name}'", foreground="#27ae60")
        messagebox.showinfo("Éxito", f"'{p_name}' ahora está vinculado a '{o_name}'.\n\nRank: #{rnk}")
        
        # Limpiar campos
        entry_phili.delete(0, tk.END)
        entry_bgg.delete(0, tk.END)

    except Exception as e:
        lbl_status.config(text="❌ Error en el proceso", foreground="#c0392b")
        messagebox.showerror("Error inesperado", str(e))

# --- Interfaz Gráfica (Tkinter) ---
root = tk.Tk()
root.title("Monitor Philibert - Corrector de Mapeos")
root.geometry("600x320")
root.configure(bg="#f5f6f7")

# Estilos Elegant
style = ttk.Style()
style.configure("TButton", font=("Segoe UI", 10, "bold"), padding=10)
style.configure("TLabel", font=("Segoe UI", 10), background="#f5f6f7")

frame = ttk.Frame(root, padding="30")
frame.pack(fill=tk.BOTH, expand=True)

ttk.Label(frame, text="URL del Producto en Philibert:").pack(anchor=tk.W, pady=(0,5))
entry_phili = ttk.Entry(frame, width=70)
entry_phili.pack(fill=tk.X, pady=(0,15))

ttk.Label(frame, text="URL / ID de BGG:").pack(anchor=tk.W, pady=(0,5))
entry_bgg = ttk.Entry(frame, width=70)
entry_bgg.pack(fill=tk.X, pady=(0,20))

btn_fix = ttk.Button(frame, text="🔗 VINCULAR AHORA", command=run_fix)
btn_fix.pack(pady=5)

lbl_status = ttk.Label(frame, text="Listo para mapear", font=("Segoe UI", 9, "italic"))
lbl_status.pack(pady=10)

root.mainloop()
