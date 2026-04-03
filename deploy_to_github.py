import subprocess
import sys

def run_git_command(command):
    print(f"> Ejecutando: {' '.join(command)}")
    result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='replace')
    if result.stdout: print(result.stdout)
    if result.stderr: print(result.stderr)
    return result.returncode

def deploy():
    print("--- INICIANDO DESPLIEGUE A GITHUB PAGES ---")
    
    # 1. Asegurar que todo esté añadido (respetando .gitignore)
    run_git_command(["git", "add", "."])
    
    # 2. Verificar si hay cambios antes de hacer commit (para evitar error)
    check_status = subprocess.run(["git", "diff", "--cached", "--quiet"], capture_output=False)
    if check_status.returncode == 0:
        print("--- NO HAY CAMBIOS NUEVOS PARA PUBLICAR ---")
        return
    
    # 3. Hacer el commit
    commit_rc = run_git_command(["git", "commit", "-m", "Actualización automática de reportes"])
    if commit_rc != 0:
        print("--- ERROR AL HACER COMMIT ---")
        return

    # 4. Hacer el push
    push_rc = run_git_command(["git", "push"])
    if push_rc == 0:
        print("--- (!) DESPLIEGUE COMPLETADO CON ÉXITO (!) ---")
        print("En unos minutos los cambios estarán vivos en tu GitHub Pages.")
    else:
        print("--- ERROR AL HACER PUSH ---")

if __name__ == "__main__":
    deploy()
