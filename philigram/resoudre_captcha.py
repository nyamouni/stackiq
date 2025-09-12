import base64
from PIL import Image
from io import BytesIO
import requests
import time
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

API_KEY = "c0c15f74a9955364a43d1557773935a6"

def save_captcha_image(driver, captcha_img):

    # Attendre que le src apparaisse (max 5 secondes)
    WebDriverWait(driver, 5).until(lambda d: captcha_img.get_attribute("src") and captcha_img.get_attribute("src").startswith("http"))

    src = captcha_img.get_attribute("src")
    
    if not src:
        logging.error(" L'attribut src de l'image CAPTCHA est vide ou None.")
        return None

    if src.startswith("http"):
        image_path = "captcha.png"
        try:
            response = requests.get(src)
            with open(image_path, "wb") as f:
                f.write(response.content)
            logging.info(f" CAPTCHA téléchargé et sauvegardé dans {image_path}")
            return image_path
        except Exception as e:
            logging.error(f" Erreur lors du téléchargement du CAPTCHA : {e}")
            return None
        
    elif src.startswith("data:image"):
        header, encoded = src.split(",", 1)
        image_data = base64.b64decode(encoded)
        image_path = "captcha.png"
        with open(image_path, "wb") as f:
            f.write(image_data)
        logging.info(f" CAPTCHA base64 sauvegardé dans {image_path}")
        return image_path
    
    else:
        logging.error(f" Lien CAPTCHA invalide : {src}")
        return None


def solve_captcha_2captcha(image_path):
    # 1. Envoyer le fichier image
    with open(image_path, 'rb') as f:
        response = requests.post(
            'http://2captcha.com/in.php',
            files={'file': f},
            data={'key': API_KEY, 'method': 'post'}
        )
    if "OK|" not in response.text:
        logging.error(f" Erreur d'envoi à 2Captcha: {response.text}")
        return None

    captcha_id = response.text.split('|')[1]

    # 2. Attendre et interroger pour la réponse
    for i in range(20):  # 20 tentatives max
        time.sleep(5)
        res = requests.get(f"http://2captcha.com/res.php?key={API_KEY}&action=get&id={captcha_id}")
        if res.text == "CAPCHA_NOT_READY":
            continue
        elif "OK|" in res.text:
            return res.text.split('|')[1] 
        else:
            logging.error(f" Erreur réponse 2Captcha: {res.text}")
            return None
    logging.error(" Délai d'attente dépassé pour la réponse CAPTCHA")
    return None

def submit_captcha(driver, captcha_text):
    try:
        input_box = driver.find_element(By.NAME, 'captcha')  
        input_box.clear()
        input_box.send_keys(captcha_text)
        logging.info(f"CAPTCHA résolu avec : {captcha_text}")

        # Cliquer sur le bouton "Suivant" ou autre selon le contexte
        submit_btn = driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
        submit_btn.click()
    except Exception as e:
        logging.error(f"Erreur soumission CAPTCHA : {e}")
