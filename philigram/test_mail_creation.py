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
    response = requests.get(url)

    if response.text.startswith('ACCESS_NUMBER'):
        parts = response.text.split(':')
        logging.info(f"Numéro temporaire obtenu : {parts[2]}")
        return parts[1], parts[2] 

    elif "NO_BALANCE" in response.text:
        logging.warning(" Erreur : solde insuffisant sur sms-activate.")
        envoyer_mail_info()
    else:
        logging.error(f"Erreur réponse API SMS-Activate : {response.text}")

    raise Exception(f"Erreur get_temp_number(): {response.text}")


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


# Lance le navigateur
driver = uc.Chrome()
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
            logging.info("📲 Attente du code SMS depuis l'API SMS-Activate")
            code_sms = get_sms_code(activation_id)
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
