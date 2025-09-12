import os
import random
import time
from datetime import datetime
from dotenv import load_dotenv
from seleniumwire import webdriver
from selenium.webdriver.chrome.options import Options
import json
import threading
import re
from urllib.parse import parse_qs
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import urllib.parse
from selenium.webdriver.chrome.service import Service
from fonctions_utils import (
    ajouter_relations,
    liker_publications,
    actions_humaines_random,
    check_notifications,
    actions_humaines_et_telecharger_profile,
    download_linkedin_profile_pdf,
    publish_post_from_profile,
    get_own_profile_url,
    ajouter_profils_cibles,
    enter_sms_code,
    detect_page_state,
    get_temp_number,
    get_sms_code,
    enter_phone_number
)
from resoudre_captcha import *
from webdriver_manager.chrome import ChromeDriverManager
from arkose_blob_extractor import get_blob_from_network
from playwright.sync_api import sync_playwright
from arkose_solver import solve_arkose_challenge_2captcha
from email_utils import envoyer_mail_captcha

# Charger variables d’environnement
load_dotenv()
USERNAME = os.getenv("LINKEDIN_USERNAME")
PASSWORD = os.getenv("LINKEDIN_PASSWORD")
PROMPT_PATH = "prompt.json"
API_KEY = "c0c15f74a9955364a43d1557773935a6"
CHROMEDRIVER_PATH = "/usr/local/bin/chromedriver"  

def setup_driver():
    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--no-sandbox")
    options.add_argument("--enable-features=NetworkServiceInProcess")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36")

    service = Service("/usr/local/bin/chromedriver")
    driver = webdriver.Chrome(service=service, options=options)

    driver.scopes = ['.*arkoselabs.com.*']  # <-- Ajout ici pour filtrer les requêtes pertinentes

    return driver

def login_linkedin(driver):
    driver.get("https://www.linkedin.com/login")
    time.sleep(2)
    driver.find_element("id", "username").send_keys(USERNAME)
    driver.find_element("id", "password").send_keys(PASSWORD)
    driver.find_element("id", "password").submit()
    time.sleep(3)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Connecté à LinkedIn")

def surveiller_prompt_et_exec(driver):
    if os.path.exists(PROMPT_PATH):
        try:
            with open(PROMPT_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            if "actions" in data:
                print(" Prompt reçu ! Exécution du plan d'action...")
                for action in data["actions"]:
                    fonction = action["fonction"]
                    params = action.get("params", {})
                    # Appel dynamique
                    globals()[fonction](driver, **params)
                os.remove(PROMPT_PATH)  # Reset une fois traité
        except Exception as e:
            print(f"[ERREUR] Pendant traitement du prompt : {e}")

def essayer_de_cliquer_sur_defi(driver, timeout=20):
    print("🔍 Recherche du bouton 'Commencer l’énigme'...")

    def trouver_et_cliquer_bouton(context):
        try:
            bouton = WebDriverWait(context, 2).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-theme='home.verifyButton']"))
            )
            bouton.click()
            print("🧩 Bouton 'Commencer l’énigme' cliqué ✅")
            time.sleep(2)
            return True
        except Exception:
            return False

    def scan_iframes(context, profondeur=0):
        try:
            if trouver_et_cliquer_bouton(context):
                return True

            iframes = context.find_elements(By.TAG_NAME, "iframe")
            for index, iframe in enumerate(iframes):
                try:
                    driver.switch_to.frame(iframe)
                    if scan_iframes(driver, profondeur + 1):
                        driver.switch_to.default_content()
                        return True
                    driver.switch_to.default_content()
                except Exception:
                    driver.switch_to.default_content()
                    continue
        except Exception as e:
            print(f"⚠️ Erreur lors du scan iframe : {e}")
        return False

    # Retry boucle sur plusieurs secondes
    fin = time.time() + timeout
    while time.time() < fin:
        if scan_iframes(driver):
            return True
        time.sleep(1)

    print("❌ Bouton 'Commencer l’énigme' introuvable après timeout.")
    return False

def get_arkose_blob(site_url):
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')

    service = Service("/usr/local/bin/chromedriver")
    driver = webdriver.Chrome(service=service, options=options)

    try:
        driver.get(site_url)

        iframe = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "iframe[src*='funCaptchaInternal']"))
        )
        driver.switch_to.frame(iframe)

        WebDriverWait(driver, 15).until(
            lambda d: d.execute_script("return window.sessionStorage.getItem('arkose_blob')") is not None
        )

        blob = driver.execute_script("return window.sessionStorage.getItem('arkose_blob')")
        return blob

    except Exception as e:
        print(f"❌ Erreur dans get_arkose_blob : {e}")
        return None

    finally:
        driver.quit()

def gerer_verifications(driver):
    etat = detect_page_state(driver)
    print(f" État de la page détecté : {etat}")

    if etat == "captcha":
        print("🔎 CAPTCHA détecté !")
        # Étape 1 : fallback sur image CAPTCHA classique si Arkose absent
        try:
            captcha_img = driver.find_element(By.CSS_SELECTOR, 'img.Captcha-Image')
            print("🖼️ CAPTCHA image détecté.")
            path = save_captcha_image(driver, captcha_img)
            if path:
                captcha_text = solve_captcha_2captcha(path)
                if captcha_text:
                    submit_captcha(driver, captcha_text)
        except Exception as e:
            print(f"⚠️ Aucun CAPTCHA image classique trouvé : {e}")
            print("🧩 CAPTCHA Arkose détecté !")
            try:
                # Pause brève pour laisser le temps au challenge d'apparaître
                print("⏳ Attente du chargement du challenge Arkose...")
                time.sleep(3)

                # Envoi d’un e-mail pour intervention humaine
                envoyer_mail_captcha(USERNAME, PASSWORD, driver.current_url)

                print("📨 Mail envoyé à l'humain pour résoudre le CAPTCHA Arkose.")
                print("⏸️ Mise en pause du bot en attendant une intervention humaine...")

                # le bot en pause 
                time.sleep(300)  

            except Exception as e:
                print(f"❌ Erreur lors du traitement du CAPTCHA Arkose : {e}")

    elif etat == "phone_number_required":
        logging.info("📲 Vérification par numéro de téléphone détectée !")

        try:
            activation_id, phone_number = get_temp_number()
            logging.info(f" Numéro temporaire obtenu : {phone_number}")

            enter_phone_number(driver, phone_number)

            # Attente que le champ code apparaisse
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.ID, "passp-field-phoneCode"))
            )

            sms_code = get_sms_code(activation_id)
            enter_sms_code(driver, sms_code)

        except Exception as e:
            logging.error(f"❌ Erreur lors de la vérification par téléphone : {e}")

    elif etat == "captcha_arkose":
        print("🧩 CAPTCHA Arkose détecté !")
        try:
            # Pause brève pour laisser le temps au challenge d'apparaître
            print("⏳ Attente du chargement du challenge Arkose...")
            time.sleep(3)

            # Envoi d’un e-mail pour intervention humaine
            envoyer_mail_captcha(USERNAME, PASSWORD, driver.current_url)

            print("📨 Mail envoyé à l'humain pour résoudre le CAPTCHA Arkose.")
            print("⏸️ Mise en pause du bot en attendant une intervention humaine...")

            # le bot en pause 
            time.sleep(300)  

        except Exception as e:
            print(f"❌ Erreur lors du traitement du CAPTCHA Arkose : {e}")

    elif etat == "phone_number_required":
        logging.info("📲 Vérification par numéro de téléphone détectée !")

        try:
            activation_id, phone_number = get_temp_number()
            logging.info(f" Numéro temporaire obtenu : {phone_number}")

            enter_phone_number(driver, phone_number)

            # Attente que le champ code apparaisse
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.ID, "passp-field-phoneCode"))
            )

            sms_code = get_sms_code(activation_id)
            enter_sms_code(driver, sms_code)

        except Exception as e:
            logging.error(f"❌ Erreur lors de la vérification par téléphone : {e}")

    elif etat == "sms_code":
        print("📱 SMS requis !")
        activation_id, numero = get_temp_number()
        print(f"Numéro temporaire obtenu : {numero}")
        code = get_sms_code(activation_id)
        enter_sms_code(driver, code)

    elif etat == "user_info":
        print("📝 Complément d'info requis. Remplissage automatique...")

    elif etat == "phone_call":
        logging.warning("📞 Vérification par appel vocal détectée.")
        envoyer_mail_verification("Vérification par appel vocal", USERNAME, PASSWORD)
        time.sleep(3600)  # pause longue pour intervention humaine

    elif etat == "unknown":
        print("❓ État inconnu détecté. Aucune action prise.")

def get_arkose_iframe_and_key(driver):
    try:
        # Récupérer l’iframe avec l’ID "captcha-internal"
        iframe = driver.find_element(By.ID, "captcha-internal")
        print(f"🔍 Iframe Arkose trouvé : {iframe.get_attribute('src')}")

        # Récupérer la clé publique Arkose depuis l’input
        public_key_input = driver.find_element(By.NAME, "captchaSiteKey")
        public_key = public_key_input.get_attribute("value")
        print(f"🔑 Clé publique Arkose trouvée : {public_key}")

        return iframe, public_key

    except Exception as e:
        print(f"⚠️ Erreur dans get_arkose_iframe_and_key : {e}")
        return None, None

def solve_arkose_captcha(driver, public_key, site_url):
    if not API_KEY:
        print("❌ API_KEY invalide")
        return None

    print(f"🌐 URL du site : {site_url}")
    print("🔍 Tentative de récupération automatique du blob...")

    blob = get_arkose_blob_from_driver(driver)
    if not blob:
        print("❌ Blob non trouvé, résolution impossible.")
        return None

    print("📤 Envoi de la requête à 2Captcha...")

    payload = {
        "key": API_KEY,
        "method": "funcaptcha",
        "publickey": public_key,
        "site": site_url,
        "blob": blob,
        "json": 1
    }

    try:
        response = requests.post("http://2captcha.com/in.php", data=payload)
        result = response.json()

        if result["status"] != 1:
            print(f"❌ Erreur de soumission : {result['request']}")
            return None

        captcha_id = result["request"]
        print(f"🕒 CAPTCHA envoyé. ID : {captcha_id}. Attente de la solution...")

        # Attente passive
        for i in range(20):
            time.sleep(5)
            res_check = requests.get(
                f"http://2captcha.com/res.php?key={API_KEY}&action=get&id={captcha_id}&json=1"
            )
            check_result = res_check.json()

            if check_result["status"] == 1:
                print("✅ CAPTCHA résolu !")
                return check_result["request"]
            else:
                print(f"⏳ Tentative {i+1}: {check_result['request']}")

        print("❌ Échec : délai dépassé sans solution.")
        return None

    except Exception as e:
        print(f"❌ Exception pendant la résolution ArkoseCaptcha : {e}")
        return None

def get_arkose_blob_from_driver(driver):
    print("📡 Recherche du blob Arkose dans les requêtes réseau...")
    try:
        time.sleep(10)  # attendre que les requêtes réseau soient envoyées

        for request in reversed(driver.requests):
            if request.method == 'POST' and 'arkoselabs.com' in request.url:
                try:
                    if request.body:
                        # Initialisation de la variable AVANT l'utilisation
                        body_str = request.body.decode('utf-8', errors='ignore')

                        # Vérification si c'est du JSON
                        if body_str.strip().startswith('{'):
                            try:
                                body_json = json.loads(body_str)
                                blob = body_json.get("blob")
                                if blob:
                                    print("✅ Blob Arkose trouvé dans le body JSON de la requête !")
                                    return blob
                            except Exception as e:
                                print(f"⚠️ Erreur de parsing JSON : {e}")
                        else:
                            # Cas x-www-form-urlencoded
                            try:
                                params = parse_qs(body_str)
                                if "blob" in params:
                                    blob = params["blob"][0]
                                    print("✅ Blob Arkose trouvé dans le body form-urlencoded !")
                                    return blob
                                else:
                                    print(f"⚠️ Pas de champ 'blob' trouvé dans : {body_str[:100]}...")
                            except Exception as e:
                                print(f"⚠️ Erreur de parsing form-urlencoded : {e}")

                        # Si aucun blob trouvé, tu peux logger l’URL et le body
                        print(f"📎 URL: {request.url}")
                        print(f"📦 Body: {body_str[:300]}")
                except Exception as e:
                    print(f"⚠️ Erreur d'analyse d'une requête Arkose : {e}")

    except Exception as e:
        print(f"❌ Erreur globale lors de l'extraction du blob : {e}")

    print("❌ Blob introuvable.")
    return None

def get_arkose_public_key(driver):
    try:
        # Récupère toutes les iframes de la page
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        for iframe in iframes:
            src = iframe.get_attribute("src")
            if src and "arkoselabs.com" in src:
                print(f"[🔎] Iframe Arkose détectée : {src}")
                
                # Match de la public_key dans l’URL
                match = re.search(r"/v2/([^/]+)/", src)
                if match:
                    public_key = match.group(1)
                    print(f"[✅] Public Key Arkose extraite : {public_key}")
                    return public_key
    except Exception as e:
        print(f"⚠️ Erreur lors de la récupération de la public_key Arkose : {e}")
    
    print("❌ Aucune iframe Arkose trouvée.")
    return None

# Fonction principale
def main():
    driver = setup_driver()
    etat_courant = None
    etat_bloquant = False  # Suivi d'un état bloquant actif

    try:
        login_linkedin(driver)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Bot LinkedIn lancé.")

        actions = [
            lambda: ajouter_relations(driver),
            # lambda: download_linkedin_profile_pdf(driver, "nour-eddine-yamouni-0163a5256"),
            lambda: liker_publications(driver),
            lambda: actions_humaines_random(driver),
            lambda: check_notifications(driver),
            # lambda: publish_post_from_profile(driver, script, profile_url)
            # lambda: ajouter_profils_cibles(driver, "data scientist paris", nombre_max=10)
        ]

        while True:
            nouvel_etat = detect_page_state(driver)

            # Si on était dans un état bloquant, on ne fait rien tant qu’il n’a pas changé
            if etat_bloquant:
                if nouvel_etat != etat_courant:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] État changé : {etat_courant} ➜ {nouvel_etat}")
                    etat_courant = nouvel_etat
                    etat_bloquant = False  # On suppose que l’utilisateur a résolu le défi
                else:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] État bloquant toujours actif : {nouvel_etat}")
                    time.sleep(5)
                    continue  # Attente de la résolution manuelle

            # Si l’état est bloquant, on appelle le gestionnaire
            if nouvel_etat in ["captcha", "captcha_arkose", "sms_code", "phone_number_required", "user_info", "phone_call"]:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] État bloquant détecté : {nouvel_etat}")
                etat_courant = nouvel_etat
                etat_bloquant = True
                gerer_verifications(driver)
                time.sleep(5)
                continue

            # État normal : exécution d’une action aléatoire
            action = random.choice(actions)
            try:
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Action aléatoire : {action.__name__}")
                action()
            except Exception as e:
                print(f"[ERREUR] Problème pendant {action.__name__} : {e}")

            pause = random.uniform(300, 900)
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Pause de {int(pause / 60)} min.")
            time.sleep(pause)

    finally:
        driver.quit()
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Fermeture du navigateur.")

if __name__ == "__main__":
    main()
