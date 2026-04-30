import requests
from PIL import Image
from io import BytesIO
import os

url = "https://zatu.com/cdn/shop/files/zatu-logo-orange-white.webp?v=1748448404&width=200"
assets_dir = r"c:\Users\Profesor\Desktop\Personal\monitor_ofertas\assets"
target_path = os.path.join(assets_dir, "zatu_logo.png")

try:
    res = requests.get(url, timeout=10)
    if res.status_code == 200:
        img = Image.open(BytesIO(res.content))
        # Si es RGBA (como suelen ser los webp con transparencia), lo mantenemos o convertimos
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        
        # Redimensionar si es necesario (ya pedí width=200 en la URL pero por si acaso)
        img.thumbnail((200, 60), Image.Resampling.LANCZOS)
        
        img.save(target_path, "PNG")
        print(f"Logo guardado en {target_path}")
    else:
        print(f"Error bajando logo: {res.status_code}")
except Exception as e:
    print(f"Error: {e}")
