import os
import sys
import json
import subprocess
import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Cargar variables de entorno del archivo .env local
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(BASE_DIR, '.env'))
except ImportError:
    pass

# ==================== CONFIGURACIÓN SSH ====================
SSH_USER = "usuario_servidor"
SSH_HOST = "ip_o_host_servidor"
REMOTE_PATH = "/ruta/a/tu/monitor_ofertas/philibert_cookie.txt"
IDENTITY_FILE = ""
# ==========================================================

def parse_cookie_input(user_input):
    user_input = user_input.strip()
    if not user_input:
        return ""
    
    # Intentar parsear como lista JSON
    if user_input.startswith('[') and user_input.endswith(']'):
        try:
            data = json.loads(user_input)
            if isinstance(data, list):
                cookie_str = "; ".join([f"{item['name']}={item['value']}" for item in data if isinstance(item, dict) and 'name' in item and 'value' in item])
                return cookie_str
        except Exception as e:
            print(f"[!] Error al parsear el JSON de la cookie: {e}. Se tratará como texto plano.")
            
    return user_input

def verify_philibert_session(cookie_str):
    if not cookie_str:
        return False, "No se proporcionó ninguna cookie."
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Cookie": cookie_str
    }
    try:
        res = requests.get("https://www.philibertnet.com/fr/mon-compte", headers=headers, timeout=12)
        if res.status_code == 200:
            if "deconnexion" in res.text.lower() or "déconnexion" in res.text.lower():
                return True, "Sesión activa y verificada con éxito en Philibert."
            else:
                return False, "La web respondió 200 OK pero no se detectó sesión iniciada en mon-compte."
        return False, f"La web de Philibert respondió con código HTTP {res.status_code}."
    except Exception as e:
        return False, f"Error de conexión con Philibert: {e}"

def update_env_cookie(cookie_str):
    env_path = os.path.join(BASE_DIR, '.env')
    try:
        lines = []
        if os.path.exists(env_path):
            with open(env_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        found = False
        new_lines = []
        for line in lines:
            if line.strip().startswith('PHILIBERT_COOKIE='):
                new_lines.append(f'PHILIBERT_COOKIE="{cookie_str}"\n')
                found = True
            else:
                new_lines.append(line)
        if not found:
            new_lines.append(f'PHILIBERT_COOKIE="{cookie_str}"\n')
        with open(env_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
    except Exception as e:
        print(f"Error actualizando .env: {e}")

def save_and_sync_cookie(cookie_input, push_to_github=False):
    cookie_str = parse_cookie_input(cookie_input)
    if not cookie_str:
        return False, "Entrada de cookie vacía o inválida."
    
    # 1. Verificar sesión
    is_valid, msg = verify_philibert_session(cookie_str)
    
    # 2. Guardar en .env local
    update_env_cookie(cookie_str)
    
    # 3. Encriptar y guardar philibert_cookie.txt
    local_file = os.path.join(BASE_DIR, "philibert_cookie.txt")
    key = os.getenv('PHILIBERT_COOKIE_KEY')
    content_to_write = cookie_str
    if key:
        try:
            from cryptography.fernet import Fernet
            fernet = Fernet(key.encode('utf-8'))
            encrypted = fernet.encrypt(cookie_str.encode('utf-8'))
            content_to_write = encrypted.decode('utf-8')
        except Exception as e:
            print(f"[-] Error al encriptar: {e}")
    else:
        print("[!] Advertencia: No se encontró PHILIBERT_COOKIE_KEY en tu .env. Guardando en texto plano.")
    
    with open(local_file, "w", encoding="utf-8") as f:
        f.write(content_to_write)
        
    # 4. Actualizar estado
    status_file = os.path.join(BASE_DIR, 'philibert_cookie_status.txt')
    try:
        with open(status_file, 'w', encoding='utf-8') as sf:
            sf.write("VALID" if is_valid else "INVALID")
    except Exception:
        pass
        
    # 5. Opcional: Subir a GitHub para crontab
    github_msg = ""
    if push_to_github:
        if is_valid:
            try:
                subprocess.run(["git", "add", "philibert_cookie.txt", "philibert_cookie_status.txt"], cwd=BASE_DIR, capture_output=True)
                subprocess.run(["git", "commit", "-m", "Actualizar cookie Philibert"], cwd=BASE_DIR, capture_output=True, text=True)
                push_res = subprocess.run(["git", "push"], cwd=BASE_DIR, capture_output=True, text=True)
                if push_res.returncode == 0:
                    github_msg = "\n[🚀] ¡Cookie subida a GitHub con éxito para sincronizar con el crontab!"
                else:
                    github_msg = f"\n[-] Error al hacer git push: {push_res.stderr.strip()}"
            except Exception as ge:
                github_msg = f"\n[-] Error ejecutando git: {ge}"
        else:
            github_msg = "\n[!] No se subió a GitHub porque la cookie no superó la verificación de sesión."
            
    # 6. Opcional: SCP si está configurado
    if SSH_HOST != "ip_o_host_servidor" and SSH_USER != "usuario_servidor":
        scp_cmd = ["scp"]
        if IDENTITY_FILE: scp_cmd.extend(["-i", IDENTITY_FILE])
        scp_cmd.extend([local_file, f"{SSH_USER}@{SSH_HOST}:{REMOTE_PATH}"])
        try:
            res_scp = subprocess.run(scp_cmd, capture_output=True, text=True)
            if res_scp.returncode == 0:
                github_msg += "\n[🚀] ¡Cookie subida al servidor remoto por SCP!"
        except Exception as se:
            github_msg += f"\n[-] Error SCP: {se}"
            
    return is_valid, f"{msg}{github_msg}"

def main():
    print("==========================================================")
    print("     ACTUALIZADOR DE COOKIE DE PHILIBERT (ENCRIPTADA)")
    print("==========================================================")
    print("Pega el JSON de las cookies de Philibert (Cookie-Editor / EditThisCookie)")
    print("o pega el string de la cookie directamente (name1=value1; name2=value2).")
    print("Si prefieres usar la cookie configurada en tu archivo .env local, presiona ENTER.")
    print("----------------------------------------------------------")
    
    try:
        user_input = input("Introduce la cookie: ").strip()
    except KeyboardInterrupt:
        print("\nSaliendo...")
        return
        
    if not user_input:
        user_input = os.getenv('PHILIBERT_COOKIE', '').strip()
        if not user_input:
            print("[!] ERROR: No se ingresó ninguna cookie y la variable PHILIBERT_COOKIE en tu .env está vacía.")
            return
            
    is_valid, msg = save_and_sync_cookie(user_input, push_to_github=True)
    print(f"\nResultado: {msg}")

if __name__ == "__main__":
    main()
