import threading
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
from main import gerer_verifications
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from seleniumwire import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import os 
from get_json_fromLLAMMA_talenIQ import executer_actions
# 📌 Variable globale
lancer_prompt = False
USERNAME = os.getenv("LINKEDIN_USERNAME")
PASSWORD = os.getenv("LINKEDIN_PASSWORD")

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

#  Thread qui écoute clavier
def ecouter_clavier():
    global lancer_prompt
    while True:
        input("\n🔸 Appuie sur Entrée pour saisir un prompt...\n")
        lancer_prompt = True


def main():
    global lancer_prompt
    driver = setup_driver()
    etat_courant = None
    etat_bloquant = False

    # Lancer le thread d’écoute clavier
    thread = threading.Thread(target=ecouter_clavier, daemon=True)
    thread.start()

    try:
        login_linkedin(driver)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Bot LinkedIn lancé.")

        actions = [
            lambda: ajouter_relations(driver),
            lambda: liker_publications(driver),
            lambda: actions_humaines_random(driver),
            lambda: check_notifications(driver),
        ]

        while True:
            # 🔁 Si un prompt est déclenché par le clavier
            if lancer_prompt:
                lancer_prompt = False
                try:
                    prompt = input("\n📝 Entrez votre prompt pour executer_actions() : ")
                    executer_actions(prompt, driver=driver)
                except Exception as e:
                    print(f"[ERREUR] Problème pendant executer_actions : {e}")
                continue

            nouvel_etat = detect_page_state(driver)

            if etat_bloquant:
                if nouvel_etat != etat_courant:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔄 État changé : {etat_courant} ➜ {nouvel_etat}")
                    etat_courant = nouvel_etat
                    etat_bloquant = False
                else:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🛑 État bloquant toujours actif : {nouvel_etat}")
                    time.sleep(5)
                    continue

            if nouvel_etat in ["captcha", "captcha_arkose", "sms_code", "phone_number_required", "user_info", "phone_call"]:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 🚨 État bloquant détecté : {nouvel_etat}")
                etat_courant = nouvel_etat
                etat_bloquant = True
                gerer_verifications(driver)
                time.sleep(5)
                continue

            # ✅ Action normale aléatoire
            action = random.choice(actions)
            try:
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 🎲 Action aléatoire : {action.__name__}")
                action()
            except Exception as e:
                print(f"[ERREUR] Problème pendant {action.__name__} : {e}")

            pause = random.uniform(300, 900)
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ⏸ Pause de {int(pause / 60)} min.")
            time.sleep(pause)

    finally:
        driver.quit()
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔒 Fermeture du navigateur.")
