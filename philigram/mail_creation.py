import time, random, requests, logging
from faker import Faker
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from resoudre_captcha import save_captcha_image, solve_captcha_2captcha, submit_captcha
import logging
import smtplib
from email.message import EmailMessage
import os 
from email_utils import envoyer_mail_info
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from seleniumwire import webdriver


# API KEY de sms-activate
API_KEY = os.getenv("SMSACTIVATE_API_KEY")
# --- Génération aléatoire ---
fake = Faker('fr_FR')
first_name = fake.first_name()
last_name = fake.last_name()
login = f"{first_name.lower()}{last_name.lower()}{random.randint(1000,9999)}"
password = fake.password(length=10, special_chars=True)
# Logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
SENDER_EMAIL = os.getenv("SMTP_USER")
SENDER_PASSWORD = os.getenv("SMTP_PASS")
ADMIN_EMAIL = os.getenv("SMTP_USER")


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

def detect_page_state(driver):
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

    return "unknown"

def enter_sms_code(driver, code):
    for attempt in range(3):  
        if not code:
            logging.error("⛔ Aucun code reçu, impossible de continuer.")
            return False

        try:
            logging.info("⌛ Attente du champ de saisie du code SMS...")
            sms_input = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.ID, "passp-field-phoneCode"))
            )
            sms_input.clear()
            sms_input.send_keys(code.replace("-", ""))  # enlever le tiret si présent
            logging.info(f"✅ Code SMS {code} saisi dans le champ.")

            # Cliquer sur le bouton "Continuer"
            continue_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Continuer')]"))
            )
            continue_btn.click()
            logging.info("📤 Bouton 'Continuer' cliqué après saisie du code.")
            return True

        except Exception as e:
            logging.error(f"❌ Erreur pendant la saisie du code : {e}")
            return False


        # Vérifier si on est passé à l'étape suivante
        try:
            WebDriverWait(driver, 5).until_not(
                EC.presence_of_element_located((By.NAME, "smsCode"))
            )
            logging.info("✅ Passage à l'étape suivante confirmé.")
            return True
        except TimeoutException:
            logging.warning("⚠️ Code incorrect ou expiré, nouvel envoi demandé...")
    logging.error("❌ Impossible de passer l'étape SMS après plusieurs tentatives.")
    return False

def get_temp_number():
    url = f"https://sms-activate.org/stubs/handler_api.php?api_key={API_KEY}&action=getNumber&service=ya&country=0"
    response = requests.get(url)

    if response.text.startswith('ACCESS_NUMBER'):
        parts = response.text.split(':')
        activation_id = parts[1]
        phone_number = parts[2]
        logging.info(f"Numéro temporaire obtenu : {phone_number} (ID={activation_id})")

        # ✅ Activer immédiatement la réception des SMS
        act_resp = requests.get(
            f"https://sms-activate.org/stubs/handler_api.php?api_key={API_KEY}&action=setStatus&id={activation_id}&status=1"
        )
        if "ACCESS_READY" in act_resp.text:
            logging.info(f"Activation du numéro {phone_number} validée (status=1).")
        else:
            logging.warning(f"Réponse inattendue à l'activation : {act_resp.text}")

        return activation_id, phone_number

    elif "NO_BALANCE" in response.text:
        logging.warning("Solde insuffisant sur sms-activate.")
        envoyer_mail_info()
    else:
        logging.error(f"Erreur réponse API SMS-Activate : {response.text}")

    raise Exception(f"Erreur get_temp_number(): {response.text}")

def get_sms_code(driver, activation_id, max_attempts=90, delay=5):
    """
    Attend la réception du code SMS depuis SMS-Activate et gère le renvoi du code si nécessaire.
    """
    logging.info(f"📲 Attente de réception du code SMS... (max {max_attempts * delay / 60:.1f} minutes)")

    for i in range(max_attempts):
        r = requests.get(
            f"https://sms-activate.org/stubs/handler_api.php?api_key={API_KEY}&action=getStatus&id={activation_id}"
        )
        api_response = r.text.strip()
        logging.info(f"[{i}] Réponse API SMS-Activate: {api_response}")

        if "STATUS_OK" in api_response:
            code = api_response.split(":")[1]
            logging.info(f"✅ Code SMS reçu : {code}")
            return code

        elif "STATUS_WAIT_CODE" in api_response:
            logging.info(f"[{i}] En attente du SMS... nouvelle vérification dans {delay} sec")

        elif "STATUS_WAIT_RESEND" in api_response:
            logging.warning(f"[{i}] Le service demande un renvoi du code... (on ignore le clic automatique)")

            # 🔒 On désactive le clic automatique sur "Renvoyer"
            # try:
            #     resend_btn = WebDriverWait(driver, 5).until(
            #         EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Renvoyer')]"))
            #     )
            #     driver.execute_script("arguments[0].click();", resend_btn)
            #     logging.info("🔄 Bouton 'Renvoyer' cliqué.")
            # except Exception as e:
            #     logging.error(f"Impossible de cliquer sur 'Renvoyer' : {e}")


        elif "STATUS_CANCEL" in api_response:
            logging.error("❌ Activation annulée côté fournisseur. Abandon.")
            break

        else:
            logging.error(f"⚠ Réponse inattendue : {api_response}")

        time.sleep(delay)

    raise Exception("⏳ Code non reçu dans le délai imparti")

def enter_name_and_surname(driver, prenom="Jean", nom="Dupont"):
    try:
        wait = WebDriverWait(driver, 10)

        # Localiser et remplir le champ Prénom
        prenom_input = wait.until(
            EC.presence_of_element_located((By.ID, "passp-field-firstname"))
        )
        prenom_input.clear()
        prenom_input.send_keys(prenom)
        logging.info(f"✅ Prénom saisi : {prenom}")

        # Localiser et remplir le champ Nom
        nom_input = wait.until(
            EC.presence_of_element_located((By.ID, "passp-field-lastname"))
        )
        nom_input.clear()
        nom_input.send_keys(nom)
        logging.info(f"✅ Nom saisi : {nom}")

        # Cliquer sur le bouton "Continuer"
        continuer_btn = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']"))
        )
        continuer_btn.click()
        logging.info("📤 Bouton 'Continuer' cliqué.")

    except Exception as e:
        logging.error(f"❌ Erreur pendant la saisie du prénom/nom : {e}")

def get_random_french_name():
    prenoms = ["Lucas", "Léo", "Nina", "Emma", "Arthur", "Sophie"]
    noms = ["Dupuis", "Lemoine", "Girard", "Morel", "Marchand", "Faure"]
    return random.choice(prenoms), random.choice(noms)

def enter_or_generate_username(driver, prenom, nom):
    try:
        wait = WebDriverWait(driver, 10)
        login_input = wait.until(
            EC.presence_of_element_located((By.ID, "passp-field-login"))
        )

        suggested_username = login_input.get_attribute("value")
        logging.info(f"Identifiant proposé : {suggested_username}")

        if suggested_username:
            logging.info(f"Identifiant suggéré détecté : {suggested_username}")
        else:
            # Générer un identifiant si le champ est vide
            suggested_username = f"{prenom.lower()}{nom.lower()}{random.randint(100, 999)}"
            login_input.clear()
            login_input.send_keys(suggested_username)
            logging.info(f"Identifiant généré : {suggested_username}")

        # Cliquer sur le bouton Continuer
        continue_btn = wait.until(
            EC.element_to_be_clickable((By.ID, "passp:Login:registration"))
        )
        continue_btn.click()
        logging.info("Bouton 'Continuer' cliqué après la saisie de l'identifiant.")

        return suggested_username

    except Exception as e:
        logging.error(f"Erreur lors de la gestion de l'identifiant : {e}")
        return None

def trigger_sms_send(driver):
    try:
        send_sms_btn = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, "//button[.//span[contains(text(), 'Envoyer un SMS')]]"))
        )
        driver.execute_script("arguments[0].click();", send_sms_btn)
        logging.info("📤 Bouton 'Envoyer un SMS' cliqué pour déclencher l'envoi.")
        time.sleep(2)
    except Exception:
        logging.info("📭 Aucun bouton 'Envoyer un SMS' trouvé — SMS déjà déclenché ?")

# Lance le navigateur
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

driver = setup_driver()
wait = WebDriverWait(driver, 20)

try:
    # Obtenir le numéro temporaire
    activation_id, phone_number = get_temp_number()
    logging.info(f"Numéro obtenu : {phone_number} (activation_id={activation_id})")

    # Aller sur Yandex
    driver.get("https://passport.yandex.com/registration")
    logging.info("Page d'inscription Yandex chargée")

    # 1. Ouvre le menu des pays
    wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "IntPhoneInput-countryButton"))).click()
    time.sleep(1)

        # Les 9 derniers chiffres sont le numéro local
    local_number = phone_number[1:]
        # L’indicatif = tout ce qui est avant
    prefix = phone_number[:1]
    print("+"+prefix)
    print(local_number, type(local_number))

    # Vérifier si c'est probablement un numéro russe
    if phone_number.startswith("79"): 
        country_name = "Russia"
    elif phone_number.startswith("77"): 
        country_name = "Kazakhstan"
    else:
        raise Exception("Impossible d’identifier le pays à partir de ce numéro")


    # 2. Tape "+7" dans l'input de recherche
    search_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[data-t="field:input-country"]')))
    search_input.clear()
    search_input.send_keys(country_name)
    time.sleep(4)  # attendre la mise à jour de la liste

    # 3. Clique sur le premier pays proposé (Kazakhstan ou Russie)
    first_result = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'ul.CountriesPhoneCodesPopup-list li')))
    first_result.click()
    logging.info("Premier pays sélectionné dans la liste ")
    print("Premier résultat texte :", first_result.text)
    time.sleep(4)

    # 4. Attendre que le sélecteur de pays disparaisse avant d’interagir
    try:
        WebDriverWait(driver, 5).until_not(
            EC.presence_of_element_located((By.CLASS_NAME, "CountriesPhoneCodesPopup-wrapper"))
        )
        print("le pop up a bien disparu !")
    except:
        logging.warning("La popup n’a pas disparu, mais on continue.")

    # 6. Saisir le numéro caractère par caractère (ou avec délai)
    local_number = phone_number[-10:]  # en Russie les numéros sont de 10 chiffres après +7
    phone_input = wait.until(EC.presence_of_element_located((By.ID, "passp-field-phone")))
    phone_input.clear()

    for digit in phone_number:
        phone_input.send_keys(digit)
        time.sleep(0.1)  # laisser Yandex analyser petit à petit

    logging.info(f"Numéro saisi manuellement : {phone_number}")

    # 7. Cliquer sur "Suivant"
    next_btn = wait.until(EC.element_to_be_clickable((By.ID, "passp:phone:controls:next")))
    next_btn.click()

    etat = detect_page_state(driver)
    print("Page actuelle :", etat)

    if etat == "captcha":
        if is_captcha_present(driver):
            logging.info("CAPTCHA détecté, résolution en cours...")

            try:
                # Attendre que le captcha soit visible
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "img#captcha-image"))
                )
                logging.info("CAPTCHA image détectée, en attente de saisie manuelle ou résolution auto...")
                
                time.sleep(3)  # petite pause avant d'agir

                # Relocaliser toujours l'image juste avant de récupérer le `src`
                try:
                    captcha_img = driver.find_element(By.CSS_SELECTOR, "img#captcha-image")
                    captcha_src = captcha_img.get_attribute("src")
                    logging.info("Image CAPTCHA récupérée.")
                except StaleElementReferenceException:
                    logging.warning("L'image CAPTCHA est devenue obsolète, nouvelle tentative...")
                    captcha_img = driver.find_element(By.CSS_SELECTOR, "img#captcha-image")
                    captcha_src = captcha_img.get_attribute("src")

                time.sleep(2)  # si nécessaire

            except TimeoutException as e:
                logging.error(f"Erreur pendant l'attente de l'image CAPTCHA : {e}")
                captcha_img = None
                captcha_src = None

            if captcha_img and captcha_src:
                image_path = save_captcha_image(driver, captcha_img)  
                if image_path:
                    solution = solve_captcha_2captcha(image_path)
                    if solution:
                        submit_captcha(driver, solution)
                    else:
                        logging.error("Échec de la résolution du CAPTCHA.")
                else:
                    logging.error("Impossible de sauvegarder l'image CAPTCHA.")
    elif etat == "sms_code":
        print("En attente du code SMS.")
    elif etat == "user_info":
        print("Page d'informations utilisateur.")
    elif etat == "account_ready":
        print("Compte probablement créé avec succès.")
    else:
        print("Page inconnue ou non détectée.")

    # Attendre que la page change / se recharge après soumission du CAPTCHA
    try:
        WebDriverWait(driver, 10).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        time.sleep(1)  # Petite pause supplémentaire (utile si chargement lent)

        #  Re-détecter la page après soumission du CAPTCHA
        etat = detect_page_state(driver)
        logging.info(f" Nouvelle page détectée après CAPTCHA : {etat}")

        if etat == "sms_code":
            logging.info("📲 Étape SMS détectée")
            try:
                trigger_sms_send(driver)
            except Exception:
                logging.info("ℹ️ Aucun clic nécessaire (SMS déjà envoyé automatiquement)")

            logging.info("📲 Attente du code SMS depuis l'API SMS-Activate")
            code_sms = get_sms_code(driver, activation_id)
            enter_sms_code(driver, code_sms)
        elif etat == "captcha":
            logging.warning(" Toujours bloqué sur un CAPTCHA, peut-être mauvaise réponse")
        elif etat == "done":
            logging.info(" Inscription terminée !")
        else:
            logging.warning(f" Page inconnue après CAPTCHA : {etat}")

        logging.info(f" Saisi des informations personnelles : ")
        prenom, nom = get_random_french_name()
        enter_name_and_surname(driver, prenom, nom)

        #  Attendre le champ username
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "passp-field-login"))
        )
        username = enter_or_generate_username(driver, prenom, nom)
        logging.info(f" Saisi de username : ",username)
        logging.info(f" Identifiant final utilisé : {username}")

        # Attendre que le champ du mot de passe apparaisse
        password_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "passp-field-password"))
        )
        logging.info(f" Saisi du mot de passe  ")
        # Entrer le mot de passe
        password_input.send_keys("ton_mot_de_passe")
        logging.info(f"Mot de passe saisi ")

        # Cliquer sur "Connexion" ou valider le formulaire
        submit_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        submit_button.click()

        #  Attendre que la page avec le checkbox se charge (attendre le titre par exemple)
        wait.until(EC.presence_of_element_located(
            (By.XPATH, "//h1[contains(text(), 'Politique de confidentialité')]")
        ))

        # Coche la case
        try:
            checkbox = wait.until(EC.element_to_be_clickable((By.ID, "keep_unsubscribed")))
            if not checkbox.is_selected():
                driver.execute_script("arguments[0].click();", checkbox)
                logging.info(" Case des conditions cochée.")
        except Exception as e:
            logging.error(f" Erreur lors du clic sur la checkbox : {e}")
        time.sleep(15)
        # Clique sur "Terminé"
        try:
            button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Terminé')]")))
            button.click()
            logging.info(" Bouton 'Terminé' cliqué")
        except Exception as e:
            logging.error(f" Erreur lors du clic sur le bouton 'Terminé' : {e}")


    except Exception as e:
        logging.error(f" Erreur : {e}") 
except Exception as e:
    logging.error(f"Erreur : {e}")
    driver.save_screenshot("erreur.png")
finally:
    time.sleep(5)
    driver.quit()
