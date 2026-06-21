import json
import os
from cryptography.fernet import Fernet

# Datos de la cookie en formato JSON provistos por el usuario
cookies_json = """[
  {"domain":".www.philibertnet.com","expirationDate":1788311360,"hostOnly":false,"httpOnly":false,"name":"__stripe_mid","path":"/","sameSite":"strict","secure":true,"session":false,"storeId":"0","value":"0752c601-7752-4c22-a6cc-0f688f01976b1dfe51"},
  {"domain":".philibertnet.com","expirationDate":1809345885,"hostOnly":false,"httpOnly":false,"name":"rrpvid","path":"/","sameSite":"lax","secure":false,"session":false,"storeId":"0","value":"514878912827246"},
  {"domain":".philibertnet.com","expirationDate":1790028585,"hostOnly":false,"httpOnly":false,"name":"didomi_token","path":"/","sameSite":"lax","secure":true,"session":false,"storeId":"0","value":"eyJ1c2VyX2lkIjoiMTk1NWM4MGMtMTU1Ny02NDY4LThlNzUtMzExMGE1ZjA4N2Q0IiwiY3JlYXRlZCI6IjIwMjYtMDMtMjJUMjI6MDk6NDMuODQ4WiIsInVwZGF0ZWQiOiIyMDI2LTAzLTIyVDIyOjA5OjQ1Ljc4MVoiLCJ2ZW5kb3JzIjp7ImVuYWJsZWQiOlsiZ29vZ2xlIiwic2FsZXNmb3JjZSIsImM6aG90amFyIiwiYzp5b3V0dWJlIiwiYzpkaWRvbWkiLCJjOmdvb2dsZWFuYS00VFhuSmlnUiIsImM6bmV0aWx1bWFmLWg4TmZGWmpCIiwiYzpwcmVzdGFzaG9wLW5MWTZyTEFuIiwiYzpjbG91ZGZsYXJlLUhUOGJ6UktmIiwiYzpnb29nbGVmYWMtUGRWZVpwTmoiLCJjOmdvb2dsZWZvbi1CVnhSVU1jaSIsImM6Z29vZ2xlbWFwLWhMblp5R216Il19LCJwdXJwb3NlcyI6eyJlbmFibGVkIjpbImZ1bmN0aW9uYWwtZlBOVkVhcFoiLCJkZXZpY2VfY2hhcmFjdGVyaXN0aWNzIl19LCJ2ZW5kb3JzX2xpIjp7ImVuYWJsZWQiOlsiZ29vZ2xlIl19LCJ2ZXJzaW9uIjoyLCJhYyI6IkM4R0FHQUZrRmt3THdRQUEuQzhHQUdBRmtGa3dMd1FBQSJ9"},
  {"domain":".philibertnet.com","expirationDate":1790028585,"hostOnly":false,"httpOnly":false,"name":"euconsent-v2","path":"/","sameSite":"lax","secure":true,"session":false,"storeId":"0","value":"CQhd-oAQhd-oAAHABBENCWFkAP_AAELAAAAAIzQAgF5gRmAvOACAvMAA.IIzQAgF5gRmA.f_gACFgAAAAA"},
  {"domain":"www.philibertnet.com","expirationDate":1782651971.968821,"hostOnly":true,"httpOnly":true,"name":"REMEMBERME","path":"/","sameSite":"lax","secure":false,"session":false,"storeId":"0","value":"%3AMjQ3NjU4%3A1782651971%3Aa9abMWMFmlrXr_oVOBGRuG4VC5pO_iVaoQRc9-jYAtw~56wHhmaOD_DwK2K9BPRf9jb9gttjsRBGAcl13ABfOmc~"},
  {"domain":"www.philibertnet.com","expirationDate":1784639171.968998,"hostOnly":true,"httpOnly":true,"name":"PHPSESSID","path":"/","sameSite":"lax","secure":false,"session":false,"storeId":"0","value":"6e32dda9d9ec2e6d354de6046459b210"},
  {"domain":".philibertnet.com","expirationDate":1813583172.4549,"hostOnly":false,"httpOnly":false,"name":"_abck","path":"/","sameSite":"unspecified","secure":true,"session":false,"storeId":"0","value":"E4B340BB26ADBB4F5429D982AAE5259F~0~YAAQNyDUyfD1N9meAQAAnedJ6hAEQLbv1+hwZnqc9GGbo2KtxwytqStbWDHtI21AFmBxg+vM47xgwXxTbcGBLRWx5iv0vLiGlTWIuAsokBhRRxhnsJpKabu11HVc5S76GAipGxBS44wFRXCxUKbTpDj2eXVeWDsSgoKqFM1BCpS09FvY2U2cssaJLmbDB/xDpCSIwAVN4svdpNzFs6GeVHX+kTjpBrX1vlJZvgieTPc/FxQP7zm95LTww/zdTfx9u7NYp4HIyMKwRBHfa0/7KoqYmtYajRyZ8f4elWwGNaKn3c8Bb77UsRKd6ueOd6RN7ykYlbxQc7Om6kAvOTuQAoHWoCF7B3plEiPhnlOU400U61SeyPqfor9Xaps49oELJZYJPh61/8k8x7229kJnNIgSbanAiZzpEcwjjLfSSvUIywXYTcy+nrEDJIZzqEDhIJFPs/trQlusSgnxNm6gNnxL4eyO4EkWL0MYPa1apNlV02COLE07alEr4S+hg3HTjN9sI9DIZoLytp88GULKwMz9nGfy0H2YgTSZNiOL38A7B0+p/u5CZWDoh7rpYF4C7I5B2kyDNc7pP/i+7mDwFmu7XIf7FWcASjjlkCfPUdMeSrERjUKpTwUV9XRWITI7LMjxxX+ol1VExO7I7c7RcqSxR2VQEYbJTvzbH2EDFYo8pUsMkTcjkfLl6f5xKNxX~-1~-1~-1~AAQAAAAF%2f%2f%2f%2f%2fzRAjPvOWvsAt5wOBMC7FyF9arGnvyBfuFB5bhMsDIWTd6i+ePatjrmjXLEnWtQ104oz0pmYv12+y1UgS4pS52UciGPpsLKTVt8B~-1"},
  {"domain":".philibertnet.com","expirationDate":1782061465.423356,"hostOnly":false,"httpOnly":false,"name":"bm_sz","path":"/","sameSite":"unspecified","secure":false,"session":false,"storeId":"0","value":"D293C793E454DB09148989D5155815FB~YAAQNyDUyRP2N9meAQAAYOtJ6gA3CvwMSVGh0X7R3JHGd6Ukaf0hJC0cVvSvfr4xtAFa8Clbu0c3jnR/UCep6HV4poeOx1dPvz+M6Nds+f3zB+mqksx7UE8V+dYLrJtLCk6CbEAyXrRDbBa1mg2Qv+s22RpyezvZXee3dhndCZWJDMMUqZGl9c3fZ/0bQlAa/rf/7Ji3btv5rqrnIgEa4RfLNpymUFsEfwNl0R7B1M8P3IuFzMMlCQe+wMtQpmUM33QXD8qCqYe0UknjQZQmbR6slLxo0Lueg7t+FPuxDbvBL0v3SyxLMZdnRkgUJcwEMYuyDAh/ao5lTWtMtNluMVvxlgScOs74joO8CmCwx0cxPYQQo9jBWsDFNE+Grf2zwWWZLcSHfmYejK1RkUnlgTNFVibqHibHhLqSZ425C/opG/iWpWN/0XZBTx0kb7pKhYSCk9gxkoQCI1l+yA==~3752497~3752243"},
  {"domain":"www.philibertnet.com","hostOnly":true,"httpOnly":false,"name":"SERVERID","path":"/","sameSite":"unspecified","secure":false,"session":true,"storeId":"0","value":"f1|ajfhy|ajfhX"},
  {"domain":".philibertnet.com","expirationDate":1783603485.526655,"hostOnly":false,"httpOnly":true,"name":"cf_clearance","partitionKey":{"hasCrossSiteAncestor":false,"topLevelSite":"https://philibertnet.com"},"path":"/","sameSite":"no_restriction","secure":true,"session":false,"storeId":"0","value":"ioXeoN2eruFCq0wzd5u_wZ13EtQejY9yr7mQ4kHjcO4-1752067484-1.2.1.1-fqCqdztA3VgHPZh3N0Gb9rQDuOC2Kx.5OWMopAO7etJuVm4Mfm29HBFd85LSy1iG9RQgrtqgxt0ERwhpZz_qOFJ8qbZnGBXAlHUq5HAX3.AeoXu6mMtGQLlFc1m4C_cd2m_Z5i0IzQR_ZT9.buZs.LtzzfomcbczDVGyTzd8y07JhSMNBH.Md6WJr3.w58kJqMiej4UyJb.2TnhEf4jnrOjGLa34Q9uaw_2EIIYh4tY"}
]"""

# 1. Parsear cookies y formatear como string cabecera
cookies = json.loads(cookies_json)
cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies])
print(f"[+] Cookie formateada: {cookie_str[:60]}... ({len(cookie_str)} caracteres)")

# 2. Generar una nueva clave Fernet
key = Fernet.generate_key().decode('utf-8')
print(f"[+] Nueva clave Fernet generada: {key}")

# 3. Encriptar la cookie con la clave
fernet = Fernet(key.encode('utf-8'))
encrypted = fernet.encrypt(cookie_str.encode('utf-8'))
encrypted_str = encrypted.decode('utf-8')

# 4. Escribir la cookie encriptada en philibert_cookie.txt
with open("philibert_cookie.txt", "w", encoding="utf-8") as f:
    f.write(encrypted_str)
print("[+] Guardado encriptado en philibert_cookie.txt")

# 5. Escribir VALID en philibert_cookie_status.txt
with open("philibert_cookie_status.txt", "w", encoding="utf-8") as f:
    f.write("VALID")
print("[+] Guardada marca de cookie válida en philibert_cookie_status.txt")

# 6. Actualizar el archivo .env
env_lines = []
token_val = "dcfeaf75-d973-43b9-8d6d-baebdee39a00"
if os.path.exists(".env"):
    with open(".env", "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.startswith("token="):
                parts = line.split("=", 1)
                token_val = parts[1]
            elif line.startswith("PHILIBERT_COOKIE=") or line.startswith("PHILIBERT_COOKIE_KEY="):
                pass
            else:
                env_lines.append(line)

new_env_content = f"token={token_val}\nPHILIBERT_COOKIE={cookie_str}\nPHILIBERT_COOKIE_KEY={key}\n"
for l in env_lines:
    new_env_content += l + "\n"

with open(".env", "w", encoding="utf-8") as f:
    f.write(new_env_content)
print("[+] Archivo .env actualizado con la cookie en texto plano y la clave de encriptación.")
