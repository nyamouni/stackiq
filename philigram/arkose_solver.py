# arkose_solver.py

import time
import requests
from playwright.sync_api import sync_playwright

API_KEY_2CAPTCHA = "c0c15f74a9955364a43d1557773935a6"

def solve_arkose_challenge_2captcha(page, public_key=None):
    """
    Résout automatiquement un captcha Arkose (FunCaptcha) sur la page donnée via Playwright.
    
    :param page: instance Playwright Page
    :param public_key: facultatif, si connu d'avance
    :return: token de résolution captcha ou lève une exception
    """

    print("🧩 Détection du challenge Arkose...")
    page.wait_for_selector("iframe[src*='arkoselabs']", timeout=20000)

    # Récupération de l'URL d'iframe
    frame = next(f for f in page.context.pages[0].frames if "arkoselabs" in f.url)

    # Récupération automatique de la clé publique si non fournie
    if not public_key:
        # La clé est souvent dans l'URL ou le JS du frame
        if "public_key" in frame.url:
            from urllib.parse import urlparse, parse_qs
            public_key = parse_qs(urlparse(frame.url).query).get("public_key", [None])[0]
        if not public_key:
            raise Exception("🔒 Impossible de trouver la public_key Arkose")

    site_url = page.url
    print(f"🔑 Public Key: {public_key}")
    print(f"🌐 Page URL: {site_url}")

    # Envoi à 2Captcha
    print("📡 Envoi du captcha à 2Captcha...")
    payload = {
        "key": API_KEY_2CAPTCHA,
        "method": "funcaptcha",
        "publickey": public_key,
        "pageurl": site_url,
        "json": 1
    }

    response = requests.get("http://2captcha.com/in.php", params=payload).json()
    if response["status"] != 1:
        raise Exception(f"❌ Erreur 2Captcha (in.php): {response}")

    captcha_id = response["request"]

    # Attente du résultat
    print("⏳ Attente de la résolution...")
    for _ in range(30):  # 30 * 5s = 150s
        time.sleep(5)
        res = requests.get("http://2captcha.com/res.php", params={
            "key": API_KEY_2CAPTCHA,
            "action": "get",
            "id": captcha_id,
            "json": 1
        }).json()

        if res["status"] == 1:
            print("✅ Captcha résolu avec succès !")
            return res["request"]
        elif res["request"] != "CAPCHA_NOT_READY":
            raise Exception(f"❌ Erreur 2Captcha (res.php): {res}")

    raise Exception("⌛ Timeout de résolution du captcha.")

