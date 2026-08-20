import os
import sys
import json
import subprocess

# ==================== CONFIGURACIÓN ====================
# Configura los datos de tu servidor Linux remoto (si deseas usar SCP):
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

def main():
    print("==========================================================")
    print("     ACTUALIZADOR DE COOKIE DE PHILIBERT (ENCRIPTADA)")
    print("==========================================================")
    print("Pega el JSON de las cookies de Philibert (exportado con Cookie-Editor/EditThisCookie)")
    print("o pega el string de la cookie directamente (name1=value1; name2=value2).")
    print("Si prefieres usar la cookie configurada en tu archivo .env local, presiona ENTER sin pegar nada.")
    print("----------------------------------------------------------")
    
    try:
        user_input = input("Introduce la cookie: ").strip()
    except KeyboardInterrupt:
        print("\nSaliendo...")
        return
        
    cookie_str = ""
    if user_input:
        cookie_str = parse_cookie_input(user_input)
        if cookie_str:
            print("[+] Cookie procesada correctamente desde la entrada del usuario.")
    else:
        # Fallback a la cookie en .env
        cookie_str = os.getenv('PHILIBERT_COOKIE', '').strip()
        if cookie_str:
            print("[+] Usando cookie desde la variable PHILIBERT_COOKIE de tu archivo .env.")
        else:
            print("[!] ERROR: No se ingresó ninguna cookie y la variable PHILIBERT_COOKIE en tu .env está vacía.")
            return

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
    print(f"[+] Cookie guardada localmente en: {local_file}")
    
    # Actualizar estado de la cookie a VALID
    status_file = os.path.join(BASE_DIR, 'philibert_cookie_status.txt')
    try:
        with open(status_file, 'w', encoding='utf-8') as sf:
            sf.write("VALID")
    except Exception:
        pass
    
    # Enviar al servidor remoto usando SCP
    if SSH_HOST == "ip_o_host_servidor" or SSH_USER == "usuario_servidor":
        print("\n[i] Nota: Si deseas subirla automáticamente al servidor remoto sin pasar por GitHub,")
        print("    configura las variables SSH_USER, SSH_HOST y REMOTE_PATH en este script.")
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
            print(f"[-] Error al subir por SCP:\n{result.stderr}")
    except Exception as e:
        print(f"[-] Error de conexión SSH/SCP: {e}")

if __name__ == "__main__":
    main()
