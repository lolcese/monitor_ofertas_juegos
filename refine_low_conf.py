import sqlite3
import os
import datetime
import time
from monitor_core import fetch_bgg_id, fetch_details, get_db_connection

db_path = r'c:\Datos\Luis\bgg\monitor_ofertas_juegos\bgg_cache.db'
log_file = r'c:\Datos\Luis\bgg\monitor_ofertas_juegos\refine_results.log'

def log_to_file(msg):
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {msg}\n")
    print(msg)

def refine_low_confidence():
    conn = get_db_connection()
    try:
        # Abrir log limpio para esta sesión
        with open(log_file, "w", encoding="utf-8") as f:
            f.write(f"--- INICIO REFINAMIENTO (V4) {datetime.date.today()} ---\n")

        # FILTRO: Solo lo dudoso y QUE NO SEA IGNORADO
        wh = "(m.confidence < 95 OR m.bgg_id = 'WAITING' OR m.bgg_id = 'N/A' OR m.bgg_id IS NULL) AND (m.bgg_id IS NULL OR m.bgg_id != 'IGNORED')"
        q = f"SELECT DISTINCT m.item_name, m.confidence, m.bgg_id FROM bgg_mapping m WHERE {wh}"
        
        pending = conn.execute(q).fetchall()
        log_to_file(f"Mapeos reales a procesar: {len(pending)}")
        
        for name, old_conf, old_id in pending:
            log_to_file(f"🔍 Refinando: {name} (Anterior: {old_conf:.1f}%, ID: {old_id})")
            
            # fetch_bgg_id ahora usa SequenceMatcher para corregir errores como "Tesf"
            new_id, new_conf = fetch_bgg_id(name)
            
            if new_id and str(new_id).isdigit():
                # Si hemos conseguido un match mucho mejor o un candidato sólido (Umbral 90 para Validado)
                is_success = (new_conf >= 90)
                final_id = new_id if is_success else 'WAITING'
                cand_id = new_id if not is_success else None
                
                # Ojo: si ya tiene un ID SUCCESS y el nuevo es peor, no sobreescribimos
                if str(old_id).isdigit() and old_conf > new_conf:
                    log_to_file(f"   ⚠️ Manteniendo previo, no es mejor ({old_conf} > {new_conf}).")
                    continue
                
                log_to_file(f"   ✨ MEJORA: ID {new_id} ({new_conf:.1f}%)")
                with conn:
                    conn.execute("UPDATE bgg_mapping SET bgg_id = ?, confidence = ?, last_search = ?, candidate_id = ? WHERE item_name = ?", 
                                 (final_id, new_conf, datetime.date.today().isoformat(), cand_id, name))
                
                if new_conf >= 80:
                    fetch_details(new_id)
                
                time.sleep(1.0) # Pausa estratégica para Google
            else:
                log_to_file(f"   ❌ Sin match firme vía Google/BGG.")
                
        log_to_file("--- REPROCESO FINALIZADO ---")
        conn.commit()
    except Exception as e:
        log_to_file(f"ERROR CRÍTICO: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    refine_low_confidence()
