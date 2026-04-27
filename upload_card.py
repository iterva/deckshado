"""
Script para subir una carta nueva a PythonAnywhere:
1. Sube la imagen al servidor via Files API
2. Crea la carta en la DB de producción via Consoles API
"""

import os
import sys
import requests

# ── Config ──────────────────────────────────────────────────────────
PA_USER = "iterva"
PA_TOKEN = os.environ.get("PA_API_TOKEN", "")
PA_API = f"https://www.pythonanywhere.com/api/v0/user/{PA_USER}"
HEADERS = {"Authorization": f"Token {PA_TOKEN}"}

REMOTE_MEDIA = f"/home/{PA_USER}/deckshado/backend/media/extra_cards"
REMOTE_BACKEND = f"/home/{PA_USER}/deckshado/backend"

# ── Datos de la carta ───────────────────────────────────────────────
LOCAL_IMAGE = r"backend\media\extra_cards\tk26i_29.png"
REMOTE_FILENAME = "tk26i_29.png"

CARD_DATA = {
    "myl_id": "custom_tk26i_29",
    "edid": "29",
    "slug": "daga-ritual-tk26i",
    "name": "Daga Ritual",
    "edition_id": 75,  # custom_toolkit_26_imp
    "card_type_id": 3,  # Arma
    "cost": "1",
    "damage": "2",
    "ability": (
        "Exhumar.\\n"
        "El portador gana 2 de Fuerza, Furia y hace daño de combate al Destierro.\\n"
        "Cuando el portador haga daño de combate, pon un Oro del Destierro oponente "
        "en tu Oro Pagado o busca un Aliado y un Arma en tu Castillo y ponlos en tu mano."
    ),
    "flavour": (
        "Acero y runas brillan al fuego; la daga marca pactos y canaliza "
        "poder antiguo en manos ceremoniales."
    ),
    "custom_image_url": f"https://{PA_USER}.pythonanywhere.com/media/extra_cards/{REMOTE_FILENAME}",
}


def upload_image():
    """Sube la imagen al servidor via PythonAnywhere Files API."""
    remote_path = f"{REMOTE_MEDIA}/{REMOTE_FILENAME}"
    url = f"{PA_API}/files/path{remote_path}"

    with open(LOCAL_IMAGE, "rb") as f:
        resp = requests.post(url, headers=HEADERS, files={"content": f})

    if resp.status_code in (200, 201):
        print(f"[OK] Imagen subida: {remote_path}")
    else:
        print(f"[ERROR] Subir imagen: {resp.status_code} - {resp.text}")
        sys.exit(1)


def create_card_in_db():
    """Crea la carta en la DB de producción ejecutando un comando Django."""
    d = CARD_DATA
    python_code = f"""
import django, os
os.environ['DJANGO_SETTINGS_MODULE'] = 'backend.settings'
os.chdir('{REMOTE_BACKEND}')
import sys
sys.path.insert(0, '{REMOTE_BACKEND}')
django.setup()

from cards.models import Card, Edition, CardType

if Card.objects.filter(myl_id='{d["myl_id"]}').exists():
    print('Carta ya existe, saltando...')
else:
    card = Card.objects.create(
        myl_id='{d["myl_id"]}',
        edid='{d["edid"]}',
        slug='{d["slug"]}',
        name='{d["name"]}',
        edition_id={d["edition_id"]},
        card_type_id={d["card_type_id"]},
        cost='{d["cost"]}',
        damage='{d["damage"]}',
        ability='''{d["ability"]}''',
        flavour='''{d["flavour"]}''',
        custom_image_url='{d["custom_image_url"]}'
    )
    print(f'Carta creada: {{card.id}} | {{card.name}}')
"""

    # Obtener o crear consola bash
    console_url = f"{PA_API}/consoles/"
    resp = requests.get(console_url, headers=HEADERS)
    consoles = resp.json()

    # Buscar consola bash existente o crear una nueva
    bash_console = None
    for c in consoles:
        if c.get("executable") == "bash":
            bash_console = c
            break

    if not bash_console:
        resp = requests.post(console_url, headers=HEADERS, json={"executable": "bash"})
        if resp.status_code in (200, 201):
            bash_console = resp.json()
            print(f"[OK] Consola creada: {bash_console['id']}")
        else:
            print(f"[ERROR] Crear consola: {resp.status_code} - {resp.text}")
            sys.exit(1)

    console_id = bash_console["id"]

    # Enviar comando para crear la carta
    send_url = f"{PA_API}/consoles/{console_id}/send_input/"
    escaped_code = python_code.replace("'", "'\\''")
    command = (
        f"cd {REMOTE_BACKEND} && "
        f"source /home/{PA_USER}/.virtualenvs/myenv/bin/activate && "
        f"python -c \"{python_code.strip()}\"\n"
    )

    resp = requests.post(send_url, headers=HEADERS, json={"input": command})
    if resp.status_code in (200, 201):
        print(f"[OK] Comando enviado a consola {console_id}")
        print("     Revisa la consola en PythonAnywhere para confirmar.")
    else:
        print(f"[ERROR] Enviar comando: {resp.status_code} - {resp.text}")


def main():
    if not PA_TOKEN:
        print("ERROR: Setea la variable PA_API_TOKEN con tu token de PythonAnywhere")
        print("  PowerShell:  $env:PA_API_TOKEN = 'tu-token-aqui'")
        print("  Obtenerlo:   https://www.pythonanywhere.com/account/#api_token")
        sys.exit(1)

    print("=" * 50)
    print(f"Subiendo carta: {CARD_DATA['name']} (edid {CARD_DATA['edid']})")
    print("=" * 50)

    print("\n[1/2] Subiendo imagen...")
    upload_image()

    print("\n[2/2] Creando carta en DB de producción...")
    create_card_in_db()

    print("\n" + "=" * 50)
    print("¡Listo! La imagen debería estar disponible en:")
    print(f"  {CARD_DATA['custom_image_url']}")
    print("=" * 50)


if __name__ == "__main__":
    main()
