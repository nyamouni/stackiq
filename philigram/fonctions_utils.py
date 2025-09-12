from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
import os
from datetime import datetime, timedelta
import undetected_chromedriver as uc
from twocaptcha import TwoCaptcha
import imaplib
import email
import re
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
import fitz 
import time, random, requests, logging
from faker import Faker
from resoudre_captcha import save_captcha_image, solve_captcha_2captcha, submit_captcha
from email_utils import send_personalize_email
from dotenv import load_dotenv

API_KEY = "c0c15f74a9955364a43d1557773935a6"

def ajouter_relations(driver):
    ajout_total_journalier = random.randint(40, 50)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Objectif du jour : {ajout_total_journalier} invitations.")
    
    deja_ajoutes = 0
    prochain_reset = datetime.now() + timedelta(days=1)

    while True:
        maintenant = datetime.now()

        # Si on a dépassé les 24h -> réinitialiser
        if maintenant >= prochain_reset:
            ajout_total_journalier = random.randint(40, 50)
            deja_ajoutes = 0
            prochain_reset = maintenant + timedelta(days=1)
            print(f"\n[{maintenant.strftime('%H:%M:%S')}] Nouveau cycle : {ajout_total_journalier} relations à ajouter.")

        # Si on a atteint la limite du jour, attendre le prochain cycle
        if deja_ajoutes >= ajout_total_journalier:
            print(f"[{maintenant.strftime('%H:%M:%S')}] Limite quotidienne atteinte. Attente du prochain cycle...")
            time.sleep(60 * 10)  # Attendre 10 minutes avant de revérifier
            continue

        # Aller à la page "People You May Know" (ou autre URL ciblée)
        driver.get("https://www.linkedin.com/mynetwork/")

        try:
            # Attendre que la section soit visible
            WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.XPATH, "//button[contains(@aria-label, 'Inviter')]"))
            )

            boutons = driver.find_elements(By.XPATH, "//button[contains(@aria-label, 'Inviter')]")
            random.shuffle(boutons)  # Mélanger les suggestions

            batch_size = random.choice([3, 4])
            ajoutés_ce_batch = 0

            for bouton in boutons:
                if deja_ajoutes >= ajout_total_journalier or ajoutés_ce_batch >= batch_size:
                    break
                try:
                    bouton.click()
                    time.sleep(random.uniform(1.5, 4.0))  # Pause entre clics
                    deja_ajoutes += 1
                    ajoutés_ce_batch += 1
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Invitation envoyée ({deja_ajoutes}/{ajout_total_journalier})")
                except Exception as e:
                    print(f"[!] Erreur clic : {e}")
                    continue

            pause_batch = random.uniform(300, 900)  # Pause entre 5 et 15 minutes
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Pause de {int(pause_batch)} sec avant le prochain batch.")
            time.sleep(pause_batch)

        except Exception as e:
            print(f"[!] Erreur récupération boutons : {e}")
            time.sleep(120)  # Pause de 2 minutes en cas de problème

def liker_publications(driver):
    from datetime import datetime, timedelta
    import time
    import random
    from selenium.webdriver.common.by import By

    likes_du_jour = random.randint(30, 50)
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Objectif j’aime du jour : {likes_du_jour}")
    deja_aime = 0
    prochain_reset = datetime.now() + timedelta(days=1)

    while True:
        maintenant = datetime.now()

        if maintenant >= prochain_reset:
            likes_du_jour = random.randint(30, 50)
            deja_aime = 0
            prochain_reset = maintenant + timedelta(days=1)
            print(f"\n[{maintenant.strftime('%H:%M:%S')}] Nouveau cycle de likes : {likes_du_jour}")

        if deja_aime >= likes_du_jour:
            print(f"[{maintenant.strftime('%H:%M:%S')}] Limite atteinte. Pause...")
            time.sleep(60 * 10)
            continue

        # Aller au feed
        driver.get("https://www.linkedin.com/feed/")
        time.sleep(random.uniform(5, 8))

        scrolls = 0
        while deja_aime < likes_du_jour and scrolls < 10:
            driver.execute_script("window.scrollBy(0, window.innerHeight);")
            time.sleep(random.uniform(3, 5))

            try:
                boutons_like = driver.find_elements(By.XPATH, "//button[contains(@aria-label, 'J’aime') and contains(@class, 'react-button__trigger') and @aria-pressed='false']")
                print(f"[DEBUG] Boutons J’aime détectés : {len(boutons_like)}")

                random.shuffle(boutons_like)

                for bouton in boutons_like:
                    if deja_aime >= likes_du_jour:
                        break
                    try:
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", bouton)
                        time.sleep(random.uniform(1.5, 3))
                        bouton.click()
                        deja_aime += 1
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] J’aime envoyé ({deja_aime}/{likes_du_jour})")
                        time.sleep(random.uniform(2, 4))
                    except Exception as e:
                        print(f"[!] Erreur clic bouton J’aime : {e}")
                        continue

            except Exception as e:
                print(f"[!] Erreur récupération des boutons : {e}")

            scrolls += 1
            time.sleep(random.uniform(3, 6))

        pause = random.uniform(600, 1200)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Pause de {int(pause/60)} minutes avant la prochaine session de likes.")
        time.sleep(pause)

def actions_humaines_random(driver):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Début des actions humaines simulées.")
    
    driver.get("https://www.linkedin.com/feed/")
    time.sleep(random.uniform(5, 8))

    scroll_count = 0
    max_scrolls = random.randint(10, 20)

    while scroll_count < max_scrolls:
        # Scroller un peu
        scroll_distance = random.randint(300, 1000)
        driver.execute_script(f"window.scrollBy(0, {scroll_distance});")
        time.sleep(random.uniform(2, 5))

        action_type = random.choice(["click_description", "click_profil", "scroll_only"])

        if action_type == "click_description":
            try:
                descriptions = driver.find_elements(By.XPATH, "//span[contains(text(), '...voir plus')]")
                if descriptions:
                    elem = random.choice(descriptions)
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", elem)
                    time.sleep(random.uniform(1.5, 3))
                    elem.click()
                    print("[+] Click sur description.")
                    time.sleep(random.uniform(4, 7))
                    driver.back()
                    time.sleep(random.uniform(2, 4))
            except Exception:
                pass

        elif action_type == "click_profil":
            try:
                profils = driver.find_elements(By.XPATH, "//a[contains(@href, '/in/') and not(contains(@href, 'miniProfile'))]")
                profils = [p for p in profils if p.is_displayed()]
                if profils:
                    elem = random.choice(profils)
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", elem)
                    time.sleep(random.uniform(1.5, 3))
                    elem.click()
                    print("[+] Click sur un profil.")
                    time.sleep(random.uniform(5, 9))
                    driver.back()
                    time.sleep(random.uniform(2, 4))
            except Exception:
                pass

        else:
            print("[-] Juste un scroll cette fois.")
            time.sleep(random.uniform(3, 5))

        scroll_count += 1

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Fin des actions humaines.")

def check_notifications(driver):
    try:
        # Accès direct à la page des notifications
        driver.get("https://www.linkedin.com/notifications/?filter=all")
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "nt-card"))
        )
        print("[INFO] Notifications chargées.")

        # Scrolling aléatoire pour simuler une activité humaine
        for _ in range(random.randint(2, 5)):
            driver.execute_script("window.scrollBy(0, 400);")
            time.sleep(random.uniform(1, 3))

        # Récupérer les cartes de notification
        notifications = driver.find_elements(By.CLASS_NAME, "nt-card")
        print(f"[DEBUG] {len(notifications)} notifications détectées.")

        if notifications:
            notif = random.choice(notifications[:3])  # Choix parmi les 3 premières
            try:
                notif_link = notif.find_element(By.TAG_NAME, "a")
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", notif_link)
                time.sleep(random.uniform(1.5, 3))
                notif_link.click()
                print("[INFO] Notification ouverte.")
                time.sleep(random.uniform(4, 7))
                driver.back()
                print("[INFO] Retour arrière.")
            except Exception as e:
                print(f"[WARN] Erreur lors du clic sur une notification : {e}")
        else:
            print("[INFO] Aucune notification trouvée.")

    except Exception as e:
        print(f"[ERROR] Erreur dans la fonction check_notifications: {e}")
        with open("debug_notifications.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        print("[DEBUG] HTML sauvegardé dans debug_notifications.html")

def publish_post_from_profile(driver, prompt_text, profil_url):
    try:
        # Aller à l'éditeur de post via le profil
        create_post_url = profil_url + "/overlay/create-post"
        driver.get(create_post_url)
        time.sleep(3)

        # Attendre que le champ de texte soit prêt
        textarea = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "ql-editor"))
        )
        textarea.click()
        time.sleep(0.5)
        textarea.send_keys(prompt_text)
        print("[INFO] Texte inséré dans l'éditeur de post.")

        time.sleep(2)

        # Bouton "Publier"
        post_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Publier')]"))
        )
        driver.execute_script("arguments[0].click();", post_button)
        print("[SUCCESS] Post publié via profil.")

    except Exception as e:
        print(f"[ERROR] Erreur lors de la publication via profil : {e}")
        with open("debug_post_from_profile.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        print("[DEBUG] HTML sauvegardé dans debug_post_from_profile.html")

def get_own_profile_url(driver):
    try:
        # 1. On charge le feed (ou toute autre page où la sidebar apparaît)
        driver.get("https://www.linkedin.com/feed/")
        time.sleep(3)

        # 2. On attend que la sidebar soit présente
        sidebar = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "aside.scaffold-layout__sidebar"))
        )

        # 3. Dans cette sidebar, on cherche le lien vers son propre profil
        profile_link = sidebar.find_element(
            By.CSS_SELECTOR,
            "a.profile-card-profile-link"
        )
        href = profile_link.get_attribute("href")
        # Ajoute le domaine si nécessaire
        if href.startswith("/"):
            href = "https://www.linkedin.com" + href

        print(f"[INFO] URL du profil détectée : {href}")
        return href

    except Exception as e:
        print(f"[ERROR] Impossible de récupérer l'URL du profil : {e}")
        # Enregistrer le HTML pour debug
        with open("debug_sidebar.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        print("[DEBUG] HTML de la sidebar sauvé dans debug_sidebar.html")
        return None

def is_captcha_present(driver):
    try:
        # 1. CAPTCHA image Yandex classique
        if driver.find_elements(By.CSS_SELECTOR, 'img.Captcha-Image'):
            logging.info(" CAPTCHA image détecté (Captcha-Image)")
            return True

        # 2. CAPTCHA dans une iframe (type reCAPTCHA ou autre widget)
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        for iframe in iframes:
            src = iframe.get_attribute("src")
            if src and ("captcha" in src.lower() or "verify" in src.lower()):
                logging.info(" CAPTCHA iframe détecté avec src:", src)
                return True

        # 3. Divs typiques utilisées par Yandex pour CAPTCHA challenge
        if driver.find_elements(By.CLASS_NAME, "Captcha"):
            logging.info(" CAPTCHA div (class='Captcha') détectée")
            return True

        # 4. Placeholder ou label qui demande de résoudre un CAPTCHA
        body_text = driver.page_source.lower()
        if "captcha" in body_text or "prove you're not a robot" in body_text:
            logging.info(" CAPTCHA détecté dans le texte de la page")
            return True

    except Exception as e:
        logging.warning(f" Erreur lors de la détection de CAPTCHA: {e}")

    return False

def creer_compte_linkedin(email, password, prenom, nom, email_password=None):
    # Configuration pour utiliser Bright Data Browser API comme WebDriver distant
    remote_url = "https://brd-customer-hl_345c0977-zone-scraping_browser1:zx157nv8pr22@brd.superproxy.io:9515"

    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Remote(
        command_executor=remote_url,
        options=chrome_options
    )

    try:
        driver.get("https://www.linkedin.com/signup")
        time.sleep(3)

        driver.find_element(By.ID, "email-address").send_keys(email)
        driver.find_element(By.ID, "password").send_keys(password)
        driver.find_element(By.XPATH, "//button[contains(text(),'S’inscrire')]").click()

        time.sleep(3)

        if is_captcha_present(driver):
            handle_captcha(driver)

        driver.find_element(By.ID, "first-name").send_keys(prenom)
        driver.find_element(By.ID, "last-name").send_keys(nom)
        driver.find_element(By.XPATH, "//button[contains(text(),'Continuer')]").click()

        if is_captcha_present(driver):
            handle_captcha(driver)

        # Vérification email (via ta boîte email)
        confirmation_link = get_confirmation_link_from_email(email, email_password)
        if confirmation_link:
            print("[INFO] Lien de confirmation trouvé.")
            driver.get(confirmation_link)
        else:
            print("[ERREUR] Aucun lien trouvé.")

        # Continuer le profil ici
        time.sleep(10)

    except Exception as e:
        print(f"[!] Erreur pendant création : {e}")
    finally:
        driver.quit()

def get_confirmation_link_from_email(email_address, email_password, subject_filter="LinkedIn"):
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(email_address, email_password)
    mail.select("inbox")

    result, data = mail.search(None, 'UNSEEN')
    mail_ids = data[0].split()

    for num in reversed(mail_ids):
        result, data = mail.fetch(num, "(RFC822)")
        raw_email = data[0][1]
        msg = email.message_from_bytes(raw_email)

        if subject_filter.lower() in msg["subject"].lower():
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/html":
                        html = part.get_payload(decode=True).decode()

                        # Cas : lien
                        match = re.search(r'https://www\.linkedin\.com/e/[^"\']+', html)
                        if match:
                            return match.group(0)

                        # Cas : code à 6 chiffres
                        code_match = re.search(r'(\d{6})', html)
                        if code_match:
                            return code_match.group(1)

    return None

def entrer_code_verification(driver, code):
    try:
        input_field = driver.find_element(By.XPATH, "//input[@name='pin']")
        input_field.send_keys(code)
        driver.find_element(By.XPATH, "//button[contains(text(),'Valider')]").click()
        print("[INFO] Code de vérification soumis.")
    except Exception as e:
        print(f"[ERREUR] Impossible de soumettre le code : {e}")

def setup_driver():
    chrome_options = Options()

    # Met à jour ce chemin selon où tu veux stocker les PDF
    download_dir = os.path.abspath("downloads")
    os.makedirs(download_dir, exist_ok=True)

    prefs = {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "plugins.always_open_pdf_externally": True,  # évite ouverture dans Chrome
        "profile.default_content_setting_values.automatic_downloads": 1
    }
    chrome_options.add_experimental_option("prefs", {
    "download.default_directory": download_dir,
    "download.prompt_for_download": False,
    "download.directory_upgrade": True,
    "plugins.always_open_pdf_externally": True,  
    "profile.default_content_setting_values.automatic_downloads": 1
    })

    chrome_options.add_experimental_option("prefs", prefs)
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    # Pour réduire les risques de détection
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36")

    driver = webdriver.Chrome(options=chrome_options)
    driver.set_window_size(1200, 900)

    return driver

def download_linkedin_profile_pdf(driver, username):
    try:
        profile_url = f"https://www.linkedin.com/in/{username}/"
        print(f"[DEBUG] Accès au profil : {profile_url}")
        driver.get(profile_url)
        time.sleep(random.uniform(4, 6))

        print("[DEBUG] Recherche du bouton 'Plus d’actions' (SVG)...")
        
        # Attente du bouton par ID ou aria-label
        more_button = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((
                By.XPATH,
                "//button[contains(@aria-label, 'Plus d’actions') or contains(@id, 'profile-overflow-action')]"
            ))
        )
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", more_button)
        time.sleep(1)

        # Supprimer les overlays (LinkedIn en utilise parfois)
        driver.execute_script("""
            const overlay = document.querySelector('.artdeco-modal-overlay, .artdeco-toasts');
            if (overlay) { overlay.remove(); }
        """)
        time.sleep(0.5)

        # Utilisation de JavaScript pour éviter les erreurs "element not clickable"
        driver.execute_script("arguments[0].click();", more_button)
        time.sleep(2)

        print("[DEBUG] Recherche du bouton 'Enregistrer au format PDF'...")
        pdf_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((
                By.XPATH,
                "//span[contains(text(), 'Enregistrer au format PDF') or contains(text(), 'Save to PDF')]"
            ))
        )
        driver.execute_script("arguments[0].click();", pdf_button)
        print(f"[✓] Téléchargement PDF lancé pour : {username}")
        time.sleep(5)

    except Exception as e:
        print(f"[ERROR] Impossible de télécharger le PDF du profil : {e}")

        # Capture HTML pour debug si besoin
        try:
            html = driver.page_source
            print("[DEBUG] HTML actuel (extrait) :")
            print(html[:1500])
        except Exception as html_error:
            print(f"[DEBUG] Impossible de capturer le HTML : {html_error}")

def actions_humaines_et_telecharger_profile(driver):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Début des actions humaines simulées.")
    
    driver.get("https://www.linkedin.com/feed/")
    time.sleep(random.uniform(5, 8))

    scroll_count = 0
    max_scrolls = random.randint(10, 20)

    while scroll_count < max_scrolls:
        scroll_distance = random.randint(300, 1000)
        driver.execute_script(f"window.scrollBy(0, {scroll_distance});")
        time.sleep(random.uniform(2, 5))

        action_type = random.choice(["click_description", "click_profil", "scroll_only"])

        if action_type == "click_description":
            try:
                descriptions = driver.find_elements(By.XPATH, "//span[contains(text(), '...voir plus')]")
                if descriptions:
                    elem = random.choice(descriptions)
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", elem)
                    time.sleep(random.uniform(1.5, 3))
                    elem.click()
                    print("[+] Click sur description.")
                    time.sleep(random.uniform(4, 7))
                    driver.back()
                    time.sleep(random.uniform(2, 4))
            except Exception:
                pass

        elif action_type == "click_profil":
            try:
                profils = driver.find_elements(By.XPATH, "//a[contains(@href, '/in/') and not(contains(@href, 'miniProfile'))]")
                profils = [p for p in profils if p.is_displayed()]
                if profils:
                    elem = random.choice(profils)
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", elem)
                    time.sleep(random.uniform(1.5, 3))
                    elem.click()
                    print("[+] Click sur un profil.")
                    time.sleep(random.uniform(5, 8))

                    # Récupérer le slug du profil depuis l’URL
                    current_url = driver.current_url
                    if "/in/" in current_url:
                        username = current_url.split("/in/")[1].split("/")[0]
                        print(f"[INFO] Profil visité : {username}")

                        # Appel à ta fonction de téléchargement PDF
                        try:
                            download_linkedin_profile_pdf(driver, username)
                        except Exception as e:
                            print(f"[ERROR] Erreur téléchargement PDF : {e}")
                    
                    driver.back()
                    time.sleep(random.uniform(2, 4))
            except Exception:
                pass

        else:
            print("[-] Juste un scroll cette fois.")
            time.sleep(random.uniform(3, 5))

        scroll_count += 1

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Fin des actions humaines.")

def ajouter_profils_cibles(driver, mots_cles, nombre_max=10):

    recherche = mots_cles.replace(" ", "%20")
    url_recherche = f"https://www.linkedin.com/search/results/people/?keywords={recherche}&origin=GLOBAL_SEARCH_HEADER"
    driver.get(url_recherche)
    time.sleep(random.uniform(3, 6))

    demandes_envoyees = 0
    scroll_count = 0

    while demandes_envoyees < nombre_max and scroll_count < 6:
        boutons_connecter = driver.find_elements(By.XPATH, "//button[contains(@aria-label, 'Invitez')]")
        print(f"[INFO] Boutons 'Se connecter' trouvés : {len(boutons_connecter)}")

        for bouton in boutons_connecter:
            if demandes_envoyees >= nombre_max:
                break
            try:
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", bouton)
                time.sleep(random.uniform(1.5, 3))
                bouton.click()
                time.sleep(random.uniform(2, 4))

                try:
                    # Essayer de cliquer sur "Envoyer sans note"
                    envoyer_sans_note_btn = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, "//button//span[text()='Envoyer sans note']/.."))
                    )
                    envoyer_sans_note_btn.click()
                    print(f"[✓] Demande envoyée sans note ({demandes_envoyees+1})")
                    demandes_envoyees += 1
                    time.sleep(random.uniform(1, 2))

                except:
                    # Sinon, essayer "Envoyer maintenant"
                    try:
                        envoyer_btn = WebDriverWait(driver, 3).until(
                            EC.element_to_be_clickable((By.XPATH, "//button[@aria-label='Envoyer maintenant']"))
                        )
                        envoyer_btn.click()
                        print(f"[✓] Demande envoyée avec 'Envoyer maintenant' ({demandes_envoyees+1})")
                        demandes_envoyees += 1
                        time.sleep(random.uniform(1, 2))
                    except:
                        print("[INFO] Aucun bouton 'Envoyer' trouvé, tentative de fermeture du pop-up.")
                        try:
                            fermer_btn = driver.find_element(By.XPATH, "//button[@aria-label='Fermer']")
                            fermer_btn.click()
                        except:
                            pass

            except Exception as e:
                print(f"[!] Erreur : {e}")

        # Scroll pour charger plus de résultats
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(random.uniform(4, 6))
        scroll_count += 1

    print(f"[✓] Total de demandes envoyées : {demandes_envoyees}")

def extraire_infos_depuis_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()

    nom = re.search(r"([A-Z][a-z]+(?: [A-Z][a-z]+)+)", text)
    entreprise = re.search(r"(?i)(chez|at)\s([A-Z][\w& ]+)", text)
    titre = re.search(r"(?i)(Data|AI|CTO|Science)[\w\s]+", text)

    return {
        "nom": nom.group(1) if nom else "là",
        "entreprise": entreprise.group(2) if entreprise else "",
        "titre": titre.group(0) if titre else ""
    }

def envoyer_un_message(driver, url_profil, message_modele):
    # Étape 1 : aller au profil
    driver.get(url_profil)
    time.sleep(3)

    # Étape 2 : télécharger le PDF
    pdf_path = download_linkedin_profile_pdf(driver, url_profil)
    if not pdf_path:
        print("Erreur : impossible de télécharger le profil.")
        return

    # Étape 3 : extraire les infos
    infos = extraire_infos_depuis_pdf(pdf_path)

    # Étape 4 : personnaliser le message
    message_final = message_modele
    message_final = message_final.replace("[nom]", infos["nom"])
    message_final = message_final.replace("[entreprise]", infos["entreprise"])
    message_final = message_final.replace("[titre]", infos["titre"])

    # Étape 5 : cliquer sur "Message"
    try:
        bouton_message = driver.find_element(By.XPATH, "//button[contains(@aria-label, 'Message')]")
        bouton_message.click()
        time.sleep(2)

        zone_message = driver.find_element(By.XPATH, "//div[contains(@class, 'msg-form__contenteditable')]")
        zone_message.send_keys(message_final)

        bouton_envoyer = driver.find_element(By.XPATH, "//button[contains(@aria-label, 'Envoyer')]")
        bouton_envoyer.click()

        print(f"Message envoyé à {infos['nom']}")
    except Exception as e:
        print(f"Échec de l'envoi du message : {e}")

def is_captcha_present(driver):
    try:
        # 1. CAPTCHA image Yandex classique
        if driver.find_elements(By.CSS_SELECTOR, 'img.Captcha-Image'):
            logging.info(" CAPTCHA image détecté (Captcha-Image)")
            return True

        # 2. CAPTCHA dans une iframe (type reCAPTCHA ou autre widget)
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        for iframe in iframes:
            src = iframe.get_attribute("src")
            if src and ("captcha" in src.lower() or "verify" in src.lower()):
                logging.info(" CAPTCHA iframe détecté avec src:", src)
                return True

        # 3. Divs typiques utilisées par Yandex pour CAPTCHA challenge
        if driver.find_elements(By.CLASS_NAME, "Captcha"):
            logging.info(" CAPTCHA div (class='Captcha') détectée")
            return True

        # 4. Placeholder ou label qui demande de résoudre un CAPTCHA
        body_text = driver.page_source.lower()
        if "captcha" in body_text or "prove you're not a robot" in body_text:
            logging.info(" CAPTCHA détecté dans le texte de la page")
            return True

    except Exception as e:
        logging.warning(f" Erreur lors de la détection de CAPTCHA: {e}")

    return False

def detecter_et_cliquer_captcha_arkose(driver, timeout=5):
    def trouver_et_cliquer_bouton(context):
        try:
            bouton = WebDriverWait(context, 2).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-theme='home.verifyButton']"))
            )
            bouton.click()
            logging.info("🧩 CAPTCHA Arkose détecté et bouton cliqué.")
            time.sleep(2)
            return True
        except:
            return False

    def scan_iframes(context):
        if trouver_et_cliquer_bouton(context):
            return True

        iframes = context.find_elements(By.TAG_NAME, "iframe")
        for iframe in iframes:
            try:
                context.switch_to.frame(iframe)
                if scan_iframes(driver):
                    context.switch_to.default_content()
                    return True
                context.switch_to.default_content()
            except:
                context.switch_to.default_content()
                continue
        return False

    fin = time.time() + timeout
    while time.time() < fin:
        if scan_iframes(driver):
            return True
        time.sleep(1)

    return False

def detect_page_state(driver):

    try:
        # Vérification des pages LinkedIn normales
        url = driver.current_url.lower()
        if any(x in url for x in [
            "linkedin.com/feed", 
            "linkedin.com/in/", 
            "linkedin.com/search", 
            "linkedin.com/jobs", 
            "linkedin.com/messaging", 
            "linkedin.com/notifications"
        ]):
            logging.info("Page LinkedIn normale détectée.")
            return "ok"
    except:
        pass
    
    try:
        if detecter_et_cliquer_captcha_arkose(driver):
            return "captcha_arkose"
    except Exception as e:
        logging.warning(f"Erreur détection Arkose via interaction : {e}")

    try:
        # Vérifie si le champ du code SMS est présent
        if driver.find_element(By.ID, "passp-field-phoneCode"):
            logging.info("Champ code SMS détecté.")
            return "sms_code"
    except:
        pass

    try:
        # Recherche un message indiquant un appel vocal
        page_text = driver.page_source.lower()
        if "appel" in page_text or "you will receive a call" in page_text or "мы вам позвоним" in page_text:
            return "phone_call"
    except:
        pass

    try:
        # Vérifie s’il y a un champ pour entrer le numéro de téléphone
        if driver.find_element(By.NAME, "phoneNumber") or driver.find_element(By.ID, "phoneNumber"):
            logging.info("Demande d'un numéro de téléphone détectée.")
            return "phone_number_required"
    except:
        pass

    try:
        # CAPTCHA présent ?
        #driver.find_element(By.CSS_SELECTOR, 'img.Captcha-Image')
        if is_captcha_present(driver) :
            logging.info("CAPTCHA détecté.")
            return "captcha"
    except:
        pass

    try:
        # Champs prénom / nom pour compléter l'inscription
        if driver.find_element(By.ID, "passp-field-firstname"):
            return "user_info"
    except:
        pass

    try:
        # Vérifie si on est déjà sur un compte ou dashboard
        if "account" in driver.current_url or "passport.yandex.ru/profile" in driver.current_url:
            return "account_ready"
    except:
        pass
    
    try:
        current_url = driver.current_url
        if "checkpoint/lg/login-challenge-submit" in current_url:
            # Charger variables d’environnement
            load_dotenv()
            USERNAME = os.getenv("LINKEDIN_USERNAME")
            PASSWORD = os.getenv("LINKEDIN_PASSWORD")
            print("🔒 LinkedIn demande une vérification d'identité.")
            send_personalize_email(USERNAME, PASSWORD, "https://www.linkedin.com/", "🔒 LinkedIn demande une vérification d'identité.", "Action humaine requise linkedin demande une verification d'identité")
            return "identity_verification"
    except Exception as e:
        logging.warning(f"Erreur lors de la détection de la vérification d'identité : {e}")


    return "unknown"

def enter_phone_number(driver, phone_number):
    try:
        input_field = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.NAME, "phoneNumber"))
        )
        input_field.clear()
        input_field.send_keys(phone_number)
        logging.info(f" Numéro de téléphone {phone_number} saisi.")

        # Clique sur le bouton de validation
        try:
            driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
            logging.info(" Bouton de confirmation du numéro cliqué.")
        except:
            logging.warning(" Bouton non trouvé ou déjà cliqué.")
    except Exception as e:
        logging.error(f" Erreur lors de la saisie du numéro de téléphone : {e}")

def enter_sms_code(driver, code_sms):
    try:
        # Attente explicite que le champ soit présent et interactif
        input_code = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "passp-field-phoneCode"))
        )
        input_code.clear()
        input_code.send_keys(code_sms)
        logging.info(f" Code SMS {code_sms} saisi avec succès.")

        # si un bouton "Continuer" existe :
        try:
            submit_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            submit_btn.click()
            logging.info(" Bouton de confirmation cliqué.")
        except:
            logging.warning(" Bouton de confirmation non trouvé ou déjà validé.")

    except Exception as e:
        logging.error(f" Erreur lors de la saisie du code : {e}")

def get_temp_number():
    url = f"https://sms-activate.org/stubs/handler_api.php?api_key={API_KEY}&action=getNumber&service=ya&country=0"
    r = requests.get(url)
    if r.text.startswith('ACCESS_NUMBER'):
        parts = r.text.split(':')
        return parts[1], parts[2]
    raise Exception(f"Erreur get_temp_number(): {r.text}")

def get_sms_code(activation_id):

    logging.info(" Attente de réception du code SMS...")
    for i in range(60):
        r = requests.get(
            f"https://sms-activate.org/stubs/handler_api.php?api_key={API_KEY}&action=getStatus&id={activation_id}"
        )
        logging.debug(f"Réponse API SMS : {r.text}")
        if "STATUS_OK" in r.text:
            code = r.text.split(":")[1]
            logging.info(f" Code SMS reçu : {code}")
            return code
        time.sleep(3)
    raise Exception(" Code non reçu dans le délai imparti")

def handle_captcha(driver):
    try:
        logging.info("↪ Début du traitement du CAPTCHA...")

        # Détecter l'image CAPTCHA
        captcha_img = driver.find_element(By.CSS_SELECTOR, 'img.Captcha-Image')
        if not captcha_img:
            logging.warning(" Aucune image CAPTCHA détectée.")
            return False

        # Télécharger l’image localement
        image_path = save_captcha_image(driver, captcha_img)
        if not image_path:
            logging.error(" Échec du téléchargement de l’image CAPTCHA.")
            return False

        # Envoyer à 2Captcha et récupérer le texte
        captcha_text = solve_captcha_2captcha(image_path)
        if not captcha_text:
            logging.error(" Résolution du CAPTCHA échouée.")
            return False

        # Soumettre la réponse sur la page
        submit_captcha(driver, captcha_text)

        logging.info(" CAPTCHA soumis avec succès.")
        return True

    except Exception as e:
        logging.error(f" Erreur inattendue dans handle_captcha: {e}")
        return False

