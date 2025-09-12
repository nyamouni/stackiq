import time, random, requests, logging
from faker import Faker
import os
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from resoudre_captcha import save_captcha_image, solve_captcha_2captcha, submit_captcha

# API KEY de sms-activate
API_KEY = os.getenv("SMSACTIVATE_API_KEY")

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
        # CAPTCHA présent ?
        #driver.find_element(By.CSS_SELECTOR, 'img.Captcha-Image')
        if is_captcha_present(driver) :
            return "captcha"
    except:
        pass

    try:
        # Champ de code de confirmation par SMS
        driver.find_element(By.ID, "passp-field-phoneCode")
        return "sms_code"
    except:
        pass

    try:
        # Champs prénom / nom visibles ?
        driver.find_element(By.ID, "passp-field-firstname")
        return "user_info"
    except:
        pass

    try:
        # Page finale ou bouton de confirmation ?
        if "account" in driver.current_url:
            return "account_ready"
    except:
        pass

    return "unknown"

# --- Génération aléatoire ---
fake = Faker('fr_FR')
first_name = fake.first_name()
last_name = fake.last_name()
login = f"{first_name.lower()}{last_name.lower()}{random.randint(1000,9999)}"
password = fake.password(length=10, special_chars=True)

# Logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_temp_number():
    url = f"https://sms-activate.org/stubs/handler_api.php?api_key={API_KEY}&action=getNumber&service=ya&country=0"
    r = requests.get(url)
    if r.text.startswith('ACCESS_NUMBER'):
        parts = r.text.split(':')
        return parts[1], parts[2]
    raise Exception(f"Erreur get_temp_number(): {r.text}")

def get_sms_code(activation_id):
    for _ in range(60):
        r = requests.get(f"https://sms-activate.org/stubs/handler_api.php?api_key={API_KEY}&action=getStatus&id={activation_id}")
        if "STATUS_OK" in r.text:
            return r.text.split(":")[1]
        time.sleep(3)
    raise Exception("Code non reçu dans le délai imparti")

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
    if phone_number.startswith("79"):  # tous les numéros russes mobiles commencent par 79
        country_name = "Russia"
    elif phone_number.startswith("77"):  # Kazakhstan commence souvent par 77
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
        print("captcha détcté")
    elif etat == "sms_code":
        print("En attente du code SMS.")
    elif etat == "user_info":
        print("Page d'informations utilisateur.")
    elif etat == "account_ready":
        print("Compte probablement créé avec succès.")
    else:
        print("Page inconnue ou non détectée.")

    
except Exception as e:
    logging.error(f"Erreur : {e}")
    driver.save_screenshot("erreur.png")
finally:
    time.sleep(5)
    driver.quit()
