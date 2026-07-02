import os
import sys
import json
import shutil
import sqlite3
import base64
import ctypes
import subprocess
import time
from ctypes import wintypes

# ==================== CONFIGURACIÓN ====================
# Configura los datos de tu servidor Linux remoto:
SSH_USER = "usuario_servidor"
SSH_HOST = "ip_o_host_servidor"
REMOTE_PATH = "/ruta/a/tu/monitor_ofertas/philibert_cookie.txt"
IDENTITY_FILE = ""  # Opcional: Ruta a tu clave SSH (ej: "C:/Users/Profesor/.ssh/id_rsa")
# ========================================================
# Cargar variables de entorno del archivo .env local
try:
    from dotenv import load_dotenv
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    load_dotenv(os.path.join(BASE_DIR, '.env'))
except ImportError:
    pass

class DATA_BLOB(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

def decrypt_key_with_dpapi(encrypted_key):
    """Desencripta la clave usando la API de Windows DPAPI (sin requerir pywin32)"""
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    
    in_blob = DATA_BLOB(len(encrypted_key), ctypes.create_string_buffer(encrypted_key))
    out_blob = DATA_BLOB()
    
    if crypt32.CryptUnprotectData(ctypes.byref(in_blob), None, None, None, None, 0, ctypes.byref(out_blob)):
        decrypted = ctypes.string_at(out_blob.pbData, out_blob.cbData)
        kernel32.LocalFree(out_blob.pbData)
        return decrypted
    else:
        raise Exception("Error al desencriptar la clave maestra usando DPAPI.")

def get_aes_key(local_state_path):
    """Obtiene la clave AES desencriptada del archivo Local State"""
    with open(local_state_path, "r", encoding="utf-8") as f:
        local_state = json.loads(f.read())
    
    encrypted_key = base64.b64decode(local_state["os_crypt"]["encrypted_key"])
    # Las claves de Chrome/Edge en Windows empiezan con la marca "DPAPI" (5 bytes)
    encrypted_key = encrypted_key[5:]
    
    return decrypt_key_with_dpapi(encrypted_key)

def decrypt_cookie_value(encrypted_value, aes_key):
    """Desencripta el valor de la cookie usando AES-256-GCM"""
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except ImportError:
        print("[ERROR] Por favor, instala la librería de encriptación ejecutando: pip install cryptography")
        sys.exit(1)
        
    try:
        # Los valores encriptados empiezan con "v10" o "v11" (3 bytes)
        prefix = encrypted_value[:3]
        ciphertext = encrypted_value[3:]
        iv = ciphertext[:12]
        payload = ciphertext[12:]
        
        aesgcm = AESGCM(aes_key)
        decrypted = aesgcm.decrypt(payload, iv, None)
        return decrypted.decode("utf-8")
    except Exception as e:
        return f"Error decrypting: {e}"

def extract_philibert_cookies():
    """Busca y extrae las cookies de Philibert desde Chrome y Edge"""
    user_data_paths = {
        "Google Chrome": {
            "local_state": os.path.expandvars(r"%LocalAppData%\Google\Chrome\User Data\Local State"),
            "cookies": os.path.expandvars(r"%LocalAppData%\Google\Chrome\User Data\Default\Network\Cookies")
        },
        "Microsoft Edge": {
            "local_state": os.path.expandvars(r"%LocalAppData%\Microsoft\Edge\User Data\Local State"),
            "cookies": os.path.expandvars(r"%LocalAppData%\Microsoft\Edge\User Data\Default\Network\Cookies")
        }
    }
    
    philibert_cookies = {}
    
    for browser_name, paths in user_data_paths.items():
        local_state_path = paths["local_state"]
        cookies_path = paths["cookies"]
        
        if not os.path.exists(local_state_path) or not os.path.exists(cookies_path):
            continue
            
        print(f"\n[+] Buscando cookies en {browser_name}...")
        try:
            aes_key = get_aes_key(local_state_path)
            
            # Copiamos la base de datos temporalmente para evitar el error "database is locked"
            temp_db = "temp_cookies.db"
            try:
                shutil.copyfile(cookies_path, temp_db)
            except PermissionError:
                if "Edge" in browser_name:
                    # Edge suele dejar procesos zombi en segundo plano ("Impulso de inicio"). Los cerramos e intentamos de nuevo.
                    try:
                        print(f"[!] {browser_name} está bloqueado por procesos en segundo plano. Intentando cerrarlos automáticamente...")
                        subprocess.run(["taskkill", "/f", "/im", "msedge.exe"], capture_output=True)
                        time.sleep(0.5)
                        shutil.copyfile(cookies_path, temp_db)
                        print(f"[+] Procesos de Edge finalizados y base de datos copiada con éxito.")
                    except Exception:
                        print(f"[-] No se pudo liberar el archivo de cookies de {browser_name}.")
                        continue
                else:
                    print(f"[-] {browser_name} está abierto y Windows bloquea el acceso a sus cookies.")
                    print(f"    -> Soluciones: Cierra {browser_name} un instante al iniciar, o inicia sesión en el otro navegador (Chrome/Edge) y manténlo cerrado.")
                    continue
            
            conn = sqlite3.connect(temp_db)
            cursor = conn.cursor()
            
            # Buscamos cookies del dominio de Philibert
            cursor.execute(
                "SELECT name, encrypted_value FROM cookies WHERE host_key LIKE ?",
                ("%philibertnet.com%",)
            )
            
            rows = cursor.fetchall()
            conn.close()
            
            if os.path.exists(temp_db):
                os.remove(temp_db)
                
            for name, enc_val in rows:
                if enc_val:
                    dec_val = decrypt_cookie_value(enc_val, aes_key)
                    if dec_val and not dec_val.startswith("Error"):
                        philibert_cookies[name] = dec_val
            
            if philibert_cookies:
                print(f"[+] ¡Se encontraron {len(philibert_cookies)} cookies de Philibert en {browser_name}!")
                break  # Si encontramos en Chrome, no necesitamos sobreescribir con Edge a menos que falten
        except Exception as e:
            print(f"[-] Error leyendo {browser_name}: {e}")
            
    return philibert_cookies

def main():
    cookies = extract_philibert_cookies()
    if not cookies:
        print("[!] No se encontraron cookies de Philibert. Por favor, asegúrate de haber iniciado sesión en Philibert en tu navegador Chrome o Edge.")
        return
        
    # Construir la cookie en formato string cabecera
    cookie_str = "; ".join([f"{name}={value}" for name, value in cookies.items()])
    
    # Escribir localmente
    local_file = "philibert_cookie.txt"
    
    key = os.getenv('PHILIBERT_COOKIE_KEY')
    if not key:
        print("\n[!] ADVERTENCIA DE SEGURIDAD: No se encontró la variable PHILIBERT_COOKIE_KEY en tu archivo .env.")
        print("[!] Para subir la cookie encriptada a GitHub de forma 100% segura, copia la siguiente línea:")
        try:
            from cryptography.fernet import Fernet
            new_key = Fernet.generate_key().decode('utf-8')
            print(f"\n      >>>  PHILIBERT_COOKIE_KEY={new_key}  <<<\n")
            print("[!] Pega esa línea en el archivo .env de tu PC y también en el .env de tu servidor remoto.")
            print("[!] Por ahora, la cookie se guardará en texto plano.")
        except Exception:
            pass
        content_to_write = cookie_str
    else:
        try:
            from cryptography.fernet import Fernet
            fernet = Fernet(key.encode('utf-8'))
            encrypted = fernet.encrypt(cookie_str.encode('utf-8'))
            content_to_write = encrypted.decode('utf-8')
            print("[+] Cookie encriptada con éxito mediante AES-256 (Fernet) usando tu clave del .env.")
        except Exception as e:
            print(f"[-] Error al encriptar la cookie: {e}. Se guardará en texto plano.")
            content_to_write = cookie_str
            
    with open(local_file, "w", encoding="utf-8") as f:
        f.write(content_to_write)
    print(f"[+] Cookie guardada en: {local_file}")
    
    # Enviar al servidor remoto usando SCP
    if SSH_HOST == "ip_o_host_servidor" or SSH_USER == "usuario_servidor":
        print("\n[!] Configura las variables SSH_USER, SSH_HOST y REMOTE_PATH al principio de este script para subirla automáticamente al servidor.")
        return
        
    print(f"\n[+] Subiendo cookie al servidor remoto {SSH_USER}@{SSH_HOST}...")
    scp_cmd = ["scp"]
    if IDENTITY_FILE:
        scp_cmd.extend(["-i", IDENTITY_FILE])
    scp_cmd.extend([local_file, f"{SSH_USER}@{SSH_HOST}:{REMOTE_PATH}"])
    
    try:
        result = subprocess.run(scp_cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print("[🚀] ¡Cookie subida al servidor con éxito!")
        else:
            print(f"[[-] Error al subir por SCP:\n{result.stderr}")
    except Exception as e:
        print(f"[-] Error de conexión SSH/SCP: {e}")

if __name__ == "__main__":
    main()
