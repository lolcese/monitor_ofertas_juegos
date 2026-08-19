import json
import os
from dotenv import load_dotenv
from cryptography.fernet import Fernet

raw_cookies = [
    {"domain":".philibertnet.com","expirationDate":1818678657,"hostOnly":False,"httpOnly":False,"name":"rrpvid","path":"/","sameSite":"lax","secure":False,"session":False,"storeId":"0","value":"162558347670406"},
    {"domain":".www.philibertnet.com","expirationDate":1817380835,"hostOnly":False,"httpOnly":False,"name":"__stripe_mid","path":"/","sameSite":"strict","secure":True,"session":False,"storeId":"0","value":"8c4ad9a4-ba8c-43e7-8558-b51ea71afe2f77b806"},
    {"domain":".philibertnet.com","expirationDate":1790247481,"hostOnly":False,"httpOnly":False,"name":"didomi_token","path":"/","sameSite":"lax","secure":True,"session":False,"storeId":"0","value":"eyJ1c2VyX2lkIjoiMTk1OGEyYWEtOWM5Yy02MDMwLThhMmQtZWQyN2FiZmY1NjI3IiwiY3JlYXRlZCI6IjIwMjYtMDMtMjVUMTA6NTc6NTkuNDcyWiIsInVwZGF0ZWQiOiIyMDI2LTAzLTI1VDEwOjU4OjAxLjE4NloiLCJ2ZW5kb3JzIjp7ImVuYWJsZWQiOlsiZ29vZ2xlIiwic2FsZXNmb3JjZSIsImM6aG90amFyIiwiYzp5b3V0dWJlIiwiYzpkaWRvbWkiLCJjOmdvb2dsZWFuYS00VFhuSmlnUiIsImM6bmV0aWx1bWFmLWg4TmZGWmpDIiwiYzpwcmVzdGFzaG9wLW5MWTZyTEFuIiwiYzpjbG91ZGZsYXJlLUhUOGJ6UktmIiwiYzpnb29nbGVmYWMtUGRWZVpwTmoiLCJjOmdvb2dsZWZvbi1CVnhSVU1jaSIsImM6Z29vZ2xlbWFwLWhMblp5R216Il19LCJwdXJwb3NlcyI6eyJlbmFibGVkIjpbImZ1bmN0aW9uYWwtZlBOVkVhcFoiLCJkZXZpY2VfY2hhcmFjdGVyaXN0aWNzIl19LCJ2ZW5kb3JzX2xpIjp7ImVuYWJsZWQiOlsiZ29vZ2xlIl19LCJ2ZXJzaW9uIjoyLCJhYyI6IkM4R0FHQUZrRmt3THdRQUEuQzhHQUdBRmtGa3dMd1FBQSJ9"},
    {"domain":".philibertnet.com","expirationDate":1790247481,"hostOnly":False,"httpOnly":False,"name":"euconsent-v2","path":"/","sameSite":"lax","secure":True,"session":False,"storeId":"0","value":"CQhn3cAQhn3cAAHABBENCXFkAP_AAELAAAAAIzQAgF5gRmAvOACAvMAA.IIzQAgF5gRmA.f_gACFgAAAAA"},
    {"domain":".philibertnet.com","expirationDate":1818678571.000529,"hostOnly":False,"httpOnly":False,"name":"_abck","path":"/","sameSite":"unspecified","secure":True,"session":False,"storeId":"0","value":"A9BF3A576BBD6F623F2AA674E8EF464D~0~YAAQT+ocuFsoyPifAQAA4YP/GRC+lBO2ZMwTo9Q34A+cNzefehny6qE4dqwQWb1Vm8qNdtYFVQZW3bqfQpI6qJIWiVbMsLH5+Ilm159KF4fwe7NyJDjutBJtvofr6RdXTncJCWwktH6+hcm5wOKucsghH9EdmE/+xnJaYJUgBpXoI8/nimTkpN54F5kBZ6KR9f1mvy5hcWVZqWgqvekvTM3ENaqs6bHYgCB7jCXorKpif7AJPdZak1Jd6X+lRnTDLmWHjn3PrP8w7+JP2mcLqxIyeFoE2LSilUBDpr1FKvONpO7AAaFbuvVRIs+atNLrfnIUu3aibsbhgsm26BAqIEPZuViTwU5MwOI+33adv2GIIXvy3WBV3HNYg4s9BIHeYvID1GHN0zMBiErIPyEo3sGt7ueCQp3r5uhuqDFrpMtYXVe45dxh4m7LiF7JBM7pRY/otIb38VgMmgQrAeP7N6VvEy3rd+cdgH9iUJaaWqz4lUIcxXkR0Kad5MYxMGlYV8fd4mtpo/fbSi5vR+sZnE9yjJWccghZPPVUNYAGRQYlAPAbNy0DZ3y4LFDbR5pp83ZA5Edaudx2UhYEiW3vXQtpsN42fUzErobGFewPUFFRMhujl7vNkIDJ3Fj5b9ywM/m9rzposSKj58ECnJ6M7AJYBGDiwA==~-1~-1~-1~AAQAAAAG%2f%2f%2f%2f%2fzM%2fUT6iW0ET2qn6UQiSV675rDZqwjO1d+rzfX2WjoJBSPNW09g2PCJb4CUd1FMR0u4C%2f1L42joD1XlIytRvg8mxZOM6xTgMaSPD~-1"},
    {"domain":"www.philibertnet.com","expirationDate":1787747456.118851,"hostOnly":True,"httpOnly":True,"name":"REMEMBERME","path":"/","sameSite":"lax","secure":True,"session":False,"storeId":"0","value":"%3AMjQ3NjU4%3A1787747455%3As1cRzfAVat2qgaKdBatS9xKqQfWg3kYZY66wFZys5s4~56wHhmaOD_DwK2K9BPRf9jb9gttjsRBGAcl13ABfOmc~"},
    {"domain":"www.philibertnet.com","expirationDate":1789734656.119005,"hostOnly":True,"httpOnly":True,"name":"PHPSESSID","path":"/","sameSite":"lax","secure":True,"session":False,"storeId":"0","value":"cbb964a57fcc0165faa7a61b778528ce"},
    {"domain":"www.philibertnet.com","hostOnly":True,"httpOnly":False,"name":"SERVERID","path":"/","sameSite":"unspecified","secure":False,"session":True,"storeId":"0","value":"f2|aoWiB|aoWhr"},
    {"domain":".philibertnet.com","expirationDate":1787156970.295668,"hostOnly":False,"httpOnly":False,"name":"bm_sz","path":"/","sameSite":"unspecified","secure":False,"session":False,"storeId":"0","value":"CFD9A1FC1F03CB03F425314E150767F8~YAAQT+ocuOZJyPifAQAA+NQAGgBI3Qz3sQCSqipCjGgU15vfNAMnNLG1ZSwUpeEImZXtIS8qc3XKVWd8+egTOZlsT92YGIpwA5HAdqLn6RjX6QavDeTFxLuTfoxF7+3u0dhrJsZ3lddokXaZ7JY7nFQf5KweubTj/m81JdrReKeUFDQ71IydiCCEAlHJlnMCodCaJVbLGkoLtG4PYV6LZyrys4BgqRwXD5kBKz4zy2jkk592R/6VtU6mhmDGhZQroXDyWcyz8Hae+VovCqRE5GCcgnF5ZbCwR9RAjZvzD+f4lDxu+z4MiMn0AyxqWRUYPNh5rwH4z11vOVqUrAwQ4LKqyq4VpjQTyv9nM++Nj7hoKpWMyGU1iWx2cl3u3ZiJ6fH14culreWfUdbUzxnyO8ZCeeLx36TW49kFYeJXUkBudAsETZLTrXfWXwumBztlrR5AXw==~3158065~4473396"}
]

cookie_str = "; ".join([f"{item['name']}={item['value']}" for item in raw_cookies if isinstance(item, dict) and 'name' in item and 'value' in item])

base_dir = os.path.dirname(os.path.abspath(__file__))
env_file = os.path.join(base_dir, "..", ".env")
cookie_file = os.path.join(base_dir, "..", "philibert_cookie.txt")

load_dotenv(env_file)
key = os.getenv('PHILIBERT_COOKIE_KEY')

if key:
    fernet = Fernet(key.encode('utf-8'))
    encrypted = fernet.encrypt(cookie_str.encode('utf-8')).decode('utf-8')
    with open(cookie_file, 'w', encoding='utf-8') as f:
        f.write(encrypted)
    print(f"philibert_cookie.txt updated with encrypted cookie (length: {len(encrypted)}).")
else:
    with open(cookie_file, 'w', encoding='utf-8') as f:
        f.write(cookie_str)
    print(f"philibert_cookie.txt updated with plain cookie.")

# Update .env
if os.path.exists(env_file):
    with open(env_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    new_lines = []
    found = False
    for line in lines:
        if line.startswith('PHILIBERT_COOKIE='):
            new_lines.append(f'PHILIBERT_COOKIE="{cookie_str}"\n')
            found = True
        else:
            new_lines.append(line)
    if not found:
        new_lines.append(f'PHILIBERT_COOKIE="{cookie_str}"\n')
        
    with open(env_file, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    print(".env updated successfully.")
