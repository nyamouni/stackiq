import time
import random
from datetime import datetime
from fonctions_utils import (
    ajouter_relations,
    liker_publications,
    actions_humaines_random,
    check_notifications,
    detect_page_state
)
from fonctions_utils_talentIQ import gerer_verifications
from selenium.webdriver.chrome.options import Options
from seleniumwire import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import os 
from get_json_fromLLAMMA_talenIQ import executer_actions
import logging
import sys
import signal
import os

LOG_FILE = os.path.join(os.path.dirname(__file__), "logs.txt")
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
)

PID_FILE = "bot.pid"  

def ecrire_pid():
    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))

# 📌 Variable globale
lancer_prompt = False
USERNAME = os.getenv("LINKEDIN_USERNAME")
PASSWORD = os.getenv("LINKEDIN_PASSWORD")
driver = None

def log(message):
    print(message)
    logging.info(message)

def arreter(signum, frame):
    log("🛑 Signal reçu : arrêt du bot.")
    driver.quit()
    exit(0)

signal.signal(signal.SIGTERM, arreter)

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

    driver.scopes = ['.*arkoselabs.com.*']  

    return driver

def login_linkedin(driver, USERNAME, PASSWORD):
    driver.get("https://www.linkedin.com/login")
    time.sleep(2)
    driver.find_element("id", "username").send_keys(USERNAME)
    driver.find_element("id", "password").send_keys(PASSWORD)
    driver.find_element("id", "password").submit()
    time.sleep(3)
    log(f"[{datetime.now().strftime('%H:%M:%S')}] Connecté à LinkedIn")

def main(USERNAME, PASSWORD):
    ecrire_pid()  
    global lancer_prompt
    driver = setup_driver()
    etat_courant = None
    etat_bloquant = False

    try:
        login_linkedin(driver, USERNAME, PASSWORD)
        log(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Bot LinkedIn lancé.")

        actions = [
            lambda: ajouter_relations(driver),
            lambda: liker_publications(driver),
            lambda: actions_humaines_random(driver),
            lambda: check_notifications(driver),
        ]

        while True:
            nouvel_etat = detect_page_state(driver)

            if etat_bloquant:
                if nouvel_etat != etat_courant:
                    log(f"[{datetime.now().strftime('%H:%M:%S')}] 🔄 État changé : {etat_courant} ➜ {nouvel_etat}")
                    etat_courant = nouvel_etat
                    etat_bloquant = False
                else:
                    log(f"[{datetime.now().strftime('%H:%M:%S')}] 🛑 État bloquant toujours actif : {nouvel_etat}")
                    try:
                        gerer_verifications(driver)
                    except Exception as e:
                        logging.error(f"❌ Échec vérification téléphone : {e}")
                    time.sleep(5)
                    continue

            if nouvel_etat in ["captcha", "captcha_arkose", "sms_code", "phone_number_required", "user_info", "phone_call"]:
                log(f"[{datetime.now().strftime('%H:%M:%S')}] 🚨 État bloquant détecté : {nouvel_etat}")
                etat_courant = nouvel_etat
                etat_bloquant = True
                try:
                    gerer_verifications(driver)
                except Exception as e:
                    log(f"❌ Erreur dans gerer_verifications : {e}")

                time.sleep(5)
                continue

            # 🔍 Vérifie s'il y a un prompt en attente
            prompt_file = os.path.join(os.path.dirname(__file__), "pending_prompt.txt")
            if os.path.exists(prompt_file):
                with open(prompt_file, "r") as f:
                    prompt = f.read().strip()

                if prompt:
                    try:
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] 📩 Prompt reçu : {prompt}")
                        executer_actions(prompt, driver)
                    except Exception as e:
                        print(f"[ERREUR] lors de executer_actions : {e}")

                os.remove(prompt_file)  # Nettoyage

            # ✅ Action normale aléatoire
            action = random.choice(actions)
            try:
                log(f"\n[{datetime.now().strftime('%H:%M:%S')}] 🎲 Action aléatoire : {action.__name__}")
                action()
            except Exception as e:
                log(f"[ERREUR] Problème pendant {action.__name__} : {e}")

            pause = random.uniform(300, 900)
            log(f"[{datetime.now().strftime('%H:%M:%S')}] ⏸ Pause de {int(pause / 60)} min.")
            time.sleep(pause)

    finally:
        driver.quit()
        log(f"[{datetime.now().strftime('%H:%M:%S')}] 🔒 Fermeture du navigateur.")
main(USERNAME, PASSWORD)