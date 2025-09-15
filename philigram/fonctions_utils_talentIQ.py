from datetime import datetime
from dotenv import load_dotenv
from seleniumwire import webdriver
from selenium.webdriver.chrome.options import Options
import re, requests, logging, os, random, time, json, threading, urllib.parse
from urllib.parse import parse_qs
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
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
    get_sms_code,
    extraire_infos_depuis_pdf
)
from resoudre_captcha import *
from webdriver_manager.chrome import ChromeDriverManager
from arkose_blob_extractor import get_blob_from_network
from playwright.sync_api import sync_playwright
from arkose_solver import solve_arkose_challenge_2captcha
from email_utils import envoyer_mail_captcha
from groq import Groq
from email_utils import send_personalize_email
from selenium.webdriver.support.ui import Select

SMSACTIVATE_API_KEY = os.getenv("SMSACTIVATE_API_KEY")
# Charger variables d’environnement
load_dotenv()
USERNAME = os.getenv("LINKEDIN_USERNAME")
PASSWORD = os.getenv("LINKEDIN_PASSWORD")
PROMPT_PATH = "prompt.json"
API_KEY = os.getenv("API_KEY")
CHROMEDRIVER_PATH = "C:/Users/HP/.wdm/drivers/  chromedriver/win64/137.0.7151.70/chromedriver-win32/chromedriver"  

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

# 📌 Mapping indicatif ➜ Code pays HTML (valeur du <select>)
INDICATIF_TO_ISO = {
    "+33": "fr", "+93": "af", "+27": "za", "+355": "al",
    "+213": "dz", "+49": "de", "+376": "ad", "+244": "ao",
    "+250": "rw", "+1869": "kn", "+290": "sh", "+1": "lc",
    "+378": "sm", "+508": "pm", "+1": "vc", "+503": "sv",
    "+84": "vn", "+681": "wf", "+967": "ye", "+260": "zm",
    "+263": "zw", "+60": "my"
}

# ✅ Fonction robuste : sélectionner un pays dans le <select> via attribut "extension"
def choisir_pays_par_extension(driver, indicatif):
    try:
        select_element = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "select-register-phone-country"))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", select_element)
        time.sleep(0.5)
        select_element.click()
        time.sleep(0.5)

        options = select_element.find_elements(By.TAG_NAME, "option")
        for option in options:
            ext = option.get_attribute("extension")
            if ext == indicatif:
                country_name = option.text.strip()
                logging.info(f"🌍 Sélection du pays : {country_name} ({ext})")
                driver.execute_script("arguments[0].selected = true;", option)
                driver.execute_script("arguments[0].dispatchEvent(new Event('change', { bubbles: true }));", select_element)
                return

        raise ValueError(f"❌ Aucun pays trouvé avec l’indicatif {indicatif}")
    except Exception as e:
        logging.error(f"❌ Erreur lors de la sélection du pays : {e}")
        raise

# Mapping indicatif ➜ country ID (SMS-Activate)
INDICATIF_TO_COUNTRY_CODE = {
    "+7": 7,       # Russie
    "+33": 73,     # France
    "+1": 187,     # USA
    "+44": 224,    # UK
    "+213": 41,    # Algérie
    "+212": 38,    # Maroc
    "+49": 94      # Allemagne
}

# 🕐 Attente du SMS
def get_sms_code(activation_id, timeout=120):
    logging.info(f"📩 Attente du SMS pour activation_id = {activation_id} (timeout = {timeout}s)")

    for t in range(timeout // 5):
        try:
            url = (
                f"https://api.sms-activate.org/stubs/handler_api.php"
                f"?api_key={SMSACTIVATE_API_KEY}&action=getStatus&id={activation_id}"
            )
            response = requests.get(url).text.strip()
            logging.debug(f"[{t*5}s] Réponse API SMS-Activate : {response}")

            if "STATUS_OK" in response:
                code = response.split(":")[1]
                logging.info(f"✅ Code SMS reçu : {code}")
                return code

            elif "STATUS_CANCEL" in response:
                logging.error("❌ Activation annulée (STATUS_CANCEL)")
                raise Exception("L'activation a été annulée sur SMS-Activate.")

            elif "STATUS_BANNED" in response:
                logging.error("❌ API bannie (STATUS_BANNED)")
                raise Exception("Clé API bannie par SMS-Activate.")

            time.sleep(5)

        except Exception as e:
            logging.warning(f"⚠️ Erreur pendant la récupération du SMS : {e}")
            time.sleep(5)

    raise Exception("⏱️ Timeout : Aucun SMS reçu après 120 secondes.")

def detecter_code_pays_depuis_indicatif(indicatif):
    mapping = {
        "+93": "af", "+355": "al", "+213": "dz", "+376": "ad", "+244": "ao", "+1264": "ai", "+672": "aq", "+54": "ar",
        "+374": "am", "+297": "aw", "+61": "au", "+43": "at", "+994": "az", "+973": "bh", "+880": "bd", "+1246": "bb",
        "+32": "be", "+229": "bj", "+501": "bz", "+1": "us", "+591": "bo", "+387": "ba", "+267": "bw", "+55": "br",
        "+673": "bn", "+359": "bg", "+226": "bf", "+257": "bi", "+855": "kh", "+237": "cm", "+1": "ca", "+238": "cv",
        "+236": "cf", "+235": "td", "+56": "cl", "+86": "cn", "+57": "co", "+269": "km", "+243": "cd", "+242": "cg",
        "+506": "cr", "+385": "hr", "+53": "cu", "+357": "cy", "+420": "cz", "+45": "dk", "+253": "dj", "+670": "tl",
        "+593": "ec", "+20": "eg", "+503": "sv", "+240": "gq", "+291": "er", "+372": "ee", "+251": "et", "+679": "fj",
        "+358": "fi", "+33": "fr", "+241": "ga", "+220": "gm", "+995": "ge", "+49": "de", "+233": "gh", "+30": "gr",
        "+502": "gt", "+224": "gn", "+245": "gw", "+592": "gy", "+509": "ht", "+504": "hn", "+36": "hu", "+91": "in",
        "+62": "id", "+98": "ir", "+964": "iq", "+353": "ie", "+972": "il", "+39": "it", "+81": "jp", "+962": "jo",
        "+7": "ru", "+254": "ke", "+686": "ki", "+850": "kp", "+82": "kr", "+965": "kw", "+996": "kg", "+856": "la",
        "+371": "lv", "+961": "lb", "+266": "ls", "+231": "lr", "+218": "ly", "+423": "li", "+370": "lt", "+352": "lu",
        "+261": "mg", "+265": "mw", "+60": "my", "+960": "mv", "+223": "ml", "+356": "mt", "+692": "mh", "+222": "mr",
        "+230": "mu", "+52": "mx", "+691": "fm", "+373": "md", "+377": "mc", "+976": "mn", "+382": "me", "+212": "ma",
        "+258": "mz", "+95": "mm", "+264": "na", "+674": "nr", "+977": "np", "+31": "nl", "+64": "nz", "+505": "ni",
        "+227": "ne", "+234": "ng", "+47": "no", "+968": "om", "+92": "pk", "+680": "pw", "+970": "ps", "+507": "pa",
        "+675": "pg", "+595": "py", "+51": "pe", "+63": "ph", "+48": "pl", "+351": "pt", "+974": "qa", "+40": "ro",
        "+250": "rw", "+378": "sm", "+239": "st", "+966": "sa", "+221": "sn", "+381": "rs", "+248": "sc", "+232": "sl",
        "+65": "sg", "+421": "sk", "+386": "si", "+252": "so", "+27": "za", "+211": "ss", "+34": "es", "+94": "lk",
        "+249": "sd", "+597": "sr", "+268": "sz", "+46": "se", "+41": "ch", "+963": "sy", "+886": "tw", "+992": "tj",
        "+255": "tz", "+66": "th", "+228": "tg", "+676": "to", "+216": "tn", "+90": "tr", "+993": "tm", "+688": "tv",
        "+256": "ug", "+380": "ua", "+971": "ae", "+44": "gb", "+598": "uy", "+998": "uz", "+678": "vu", "+58": "ve",
        "+84": "vn", "+681": "wf", "+967": "ye", "+260": "zm", "+263": "zw", "+508": "pm", "+1": "lc", "+1": "vc",
        "+1868": "tt", "+1684": "as"
    }
    return mapping.get(indicatif, "fr")  # fallback France

def detect_country_code_from_prefix(prefix):
    mapping = {
        "+33": "fr", "+93": "af", "+27": "za", "+355": "al",
        "+213": "dz", "+49": "de", "+376": "ad", "+244": "ao",
        "+250": "rw", "+1869": "kn", "+290": "sh", "+1": "lc",
        "+378": "sm", "+508": "pm", "+1": "vc", "+503": "sv",
        "+84": "vn", "+681": "wf", "+967": "ye", "+260": "zm",
        "+263": "zw"
    }
    return mapping.get(prefix)

def obtenir_numero_valide(max_essais=5):
    for tentative in range(max_essais):
        activation_id, numero = get_temp_number()  # reçoit 601114331611
        numero = numero.strip().lstrip("+")  

        # Cas correct pour la Malaisie : 60 + 9~10 chiffres
        if numero.startswith("60") and 11 <= len(numero) <= 12:
            indicatif = "+60"
            local_part = numero[2:]  # 1114331611
            numero_complet = indicatif + local_part  # +601114331611

            logging.info(f"✅ Numéro validé : {numero_complet} (local: {local_part})")
            return activation_id, numero_complet

        logging.warning(f"❌ Numéro suspect (tentative {tentative + 1}) : {numero}")

    raise Exception("❌ Aucun numéro valide après plusieurs essais.")

def get_temp_number():
    url = f"https://sms-activate.org/stubs/handler_api.php?api_key={SMSACTIVATE_API_KEY}&action=getNumber&service=ot&country=15"
    r = requests.get(url)

    if r.text.startswith('ACCESS_NUMBER'):
        parts = r.text.split(':')
        activation_id = parts[1]
        local_number = parts[2].strip()
        print(f"📲 numéro obtenu brut : {local_number}")

        if not local_number.startswith("60"):
            raise Exception(f"❌ Numéro invalide (ne commence pas par 60) : {local_number}")

        return activation_id, local_number

    elif "NO_BALANCE" in r.text:
        raise Exception("NO_BALANCE")
    else:
        raise Exception(f"Erreur get_temp_number(): {r.text}")

# 📤 Remplir le champ numéro de téléphone LinkedIn
def remplir_numero_linkedin(driver, numero_complet):
    logging.info(f"📞 remplir_numero_linkedin() appelé avec : {numero_complet}")

    try:
        logging.info("🔍 Début du remplissage du numéro LinkedIn...")

        # ✅ Ajout d’un indicatif si manquant
        if not numero_complet.startswith('+'):
            if numero_complet.startswith('7'):
                numero_complet = '+7' + numero_complet
            elif numero_complet.startswith('33'):
                numero_complet = '+33' + numero_complet[2:]
            elif numero_complet.startswith('1'):
                numero_complet = '+1' + numero_complet
            elif numero_complet.startswith('60'):
                numero_complet = '+60' + numero_complet[2:]
            # Ajoute d'autres règles si tu comptes utiliser d'autres pays
            logging.info(f"📞 Numéro corrigé avec indicatif : {numero_complet}")

        # 🌍 Trouver l’indicatif dans le mapping
        indicatif = next((i for i in INDICATIF_TO_COUNTRY_CODE if numero_complet.startswith(i)), None)
        if not indicatif:
            raise ValueError(f"❌ Aucun indicatif reconnu dans le numéro {numero_complet}")

        local_part = extraire_numero_local(numero_complet)

        # 👇 Sélection du pays dans le menu déroulant
        choisir_pays_par_extension(driver, indicatif)

        # 🧾 Champ numéro
        champ_tel = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "register-verification-phone-number"))
        )
        champ_tel.clear()
        champ_tel.send_keys(local_part)
        logging.info(f"📞 Numéro local saisi : {local_part}")

        # 📤 Clic bouton envoyer
        bouton_envoyer = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "register-phone-submit-button"))
        )
        bouton_envoyer.click()
        logging.info("📨 Bouton Envoyer cliqué.")

        # 🚨 Vérification erreur éventuelle
        time.sleep(2)
        try:
            message_erreur = driver.find_element(By.CLASS_NAME, "input__message").text
            if message_erreur.strip():
                logging.warning(f"⚠️ Erreur détectée : {message_erreur}")
        except:
            logging.info("✅ Aucun message d’erreur détecté.")
    except Exception as e:
        logging.error(f"❌ Erreur lors du remplissage LinkedIn : {e}")
        raise

def extraire_numero_local(numero_complet):
    for indicatif in INDICATIF_TO_COUNTRY_CODE:
        if numero_complet.startswith(indicatif):
            return numero_complet[len(indicatif):].lstrip("0")
    return numero_complet  # fallback

from collections import defaultdict

def detecter_codes_pays_depuis_indicatif(indicatif):
    mapping = defaultdict(list)

    mapping["+93"].append("af")
    mapping["+355"].append("al")
    mapping["+213"].append("dz")
    mapping["+376"].append("ad")
    mapping["+244"].append("ao")
    mapping["+1264"].append("ai")
    mapping["+672"].append("aq")
    mapping["+54"].append("ar")
    mapping["+374"].append("am")
    mapping["+297"].append("aw")
    mapping["+61"].append("au")
    mapping["+43"].append("at")
    mapping["+994"].append("az")
    mapping["+973"].append("bh")
    mapping["+880"].append("bd")
    mapping["+1246"].append("bb")
    mapping["+32"].append("be")
    mapping["+229"].append("bj")
    mapping["+501"].append("bz")
    mapping["+1"].extend(["us", "ca", "ag", "ai", "lc", "vc", "tt", "as", "bm"])
    mapping["+591"].append("bo")
    mapping["+387"].append("ba")
    mapping["+267"].append("bw")
    mapping["+55"].append("br")
    mapping["+673"].append("bn")
    mapping["+359"].append("bg")
    mapping["+226"].append("bf")
    mapping["+257"].append("bi")
    mapping["+855"].append("kh")
    mapping["+237"].append("cm")
    mapping["+238"].append("cv")
    mapping["+236"].append("cf")
    mapping["+235"].append("td")
    mapping["+56"].append("cl")
    mapping["+86"].append("cn")
    mapping["+57"].append("co")
    mapping["+269"].append("km")
    mapping["+243"].append("cd")
    mapping["+242"].append("cg")
    mapping["+506"].append("cr")
    mapping["+385"].append("hr")
    mapping["+53"].append("cu")
    mapping["+357"].append("cy")
    mapping["+420"].append("cz")
    mapping["+45"].append("dk")
    mapping["+253"].append("dj")
    mapping["+670"].append("tl")
    mapping["+593"].append("ec")
    mapping["+20"].append("eg")
    mapping["+503"].append("sv")
    mapping["+240"].append("gq")
    mapping["+291"].append("er")
    mapping["+372"].append("ee")
    mapping["+251"].append("et")
    mapping["+679"].append("fj")
    mapping["+358"].append("fi")
    mapping["+33"].append("fr")
    mapping["+241"].append("ga")
    mapping["+220"].append("gm")
    mapping["+995"].append("ge")
    mapping["+49"].append("de")
    mapping["+233"].append("gh")
    mapping["+30"].append("gr")
    mapping["+502"].append("gt")
    mapping["+224"].append("gn")
    mapping["+245"].append("gw")
    mapping["+592"].append("gy")
    mapping["+509"].append("ht")
    mapping["+504"].append("hn")
    mapping["+36"].append("hu")
    mapping["+91"].append("in")
    mapping["+62"].append("id")
    mapping["+98"].append("ir")
    mapping["+964"].append("iq")
    mapping["+353"].append("ie")
    mapping["+972"].append("il")
    mapping["+39"].append("it")
    mapping["+81"].append("jp")
    mapping["+962"].append("jo")
    mapping["+7"].append("ru")  
    mapping["+254"].append("ke")
    mapping["+686"].append("ki")
    mapping["+850"].append("kp")
    mapping["+82"].append("kr")
    mapping["+965"].append("kw")
    mapping["+996"].append("kg")
    mapping["+856"].append("la")
    mapping["+371"].append("lv")
    mapping["+961"].append("lb")
    mapping["+266"].append("ls")
    mapping["+231"].append("lr")
    mapping["+218"].append("ly")
    mapping["+423"].append("li")
    mapping["+370"].append("lt")
    mapping["+352"].append("lu")
    mapping["+261"].append("mg")
    mapping["+265"].append("mw")
    mapping["+60"].append("my")
    mapping["+960"].append("mv")
    mapping["+223"].append("ml")
    mapping["+356"].append("mt")
    mapping["+692"].append("mh")
    mapping["+222"].append("mr")
    mapping["+230"].append("mu")
    mapping["+52"].append("mx")
    mapping["+691"].append("fm")
    mapping["+373"].append("md")
    mapping["+377"].append("mc")
    mapping["+976"].append("mn")
    mapping["+382"].append("me")
    mapping["+212"].append("ma")
    mapping["+258"].append("mz")
    mapping["+95"].append("mm")
    mapping["+264"].append("na")
    mapping["+674"].append("nr")
    mapping["+977"].append("np")
    mapping["+31"].append("nl")
    mapping["+64"].append("nz")
    mapping["+505"].append("ni")
    mapping["+227"].append("ne")
    mapping["+234"].append("ng")
    mapping["+47"].append("no")
    mapping["+968"].append("om")
    mapping["+92"].append("pk")
    mapping["+680"].append("pw")
    mapping["+970"].append("ps")
    mapping["+507"].append("pa")
    mapping["+675"].append("pg")
    mapping["+595"].append("py")
    mapping["+51"].append("pe")
    mapping["+63"].append("ph")
    mapping["+48"].append("pl")
    mapping["+351"].append("pt")
    mapping["+974"].append("qa")
    mapping["+40"].append("ro")
    mapping["+250"].append("rw")
    mapping["+378"].append("sm")
    mapping["+239"].append("st")
    mapping["+966"].append("sa")
    mapping["+221"].append("sn")
    mapping["+381"].append("rs")
    mapping["+248"].append("sc")
    mapping["+232"].append("sl")
    mapping["+65"].append("sg")
    mapping["+421"].append("sk")
    mapping["+386"].append("si")
    mapping["+252"].append("so")
    mapping["+27"].append("za")
    mapping["+211"].append("ss")
    mapping["+34"].append("es")
    mapping["+94"].append("lk")
    mapping["+249"].append("sd")
    mapping["+597"].append("sr")
    mapping["+268"].append("sz")
    mapping["+46"].append("se")
    mapping["+41"].append("ch")
    mapping["+963"].append("sy")
    mapping["+886"].append("tw")
    mapping["+992"].append("tj")
    mapping["+255"].append("tz")
    mapping["+66"].append("th")
    mapping["+228"].append("tg")
    mapping["+676"].append("to")
    mapping["+216"].append("tn")
    mapping["+90"].append("tr")
    mapping["+993"].append("tm")
    mapping["+688"].append("tv")
    mapping["+256"].append("ug")
    mapping["+380"].append("ua")
    mapping["+971"].append("ae")
    mapping["+44"].append("gb")
    mapping["+598"].append("uy")
    mapping["+998"].append("uz")
    mapping["+678"].append("vu")
    mapping["+58"].append("ve")
    mapping["+84"].append("vn")
    mapping["+681"].append("wf")
    mapping["+967"].append("ye")
    mapping["+260"].append("zm")
    mapping["+263"].append("zw")
    mapping["+508"].append("pm")

    return mapping.get(indicatif, ["fr"])

def detecter_indicatif_affiche(driver):
    try:
        code_div = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "register-phone-country-code"))
        )
        indicatif = code_div.text.strip()
        return indicatif  
    except Exception as e:
        raise Exception(f"❌ Impossible de détecter l’indicatif affiché sur LinkedIn : {e}")

# 🔐 Entrer le code SMS reçu
def entrer_code_sms(driver, code):
    try:
        champ_code = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "input__phone_verification_pin"))
        )
        champ_code.send_keys(code)

        bouton_verif = driver.find_element(By.ID, "email-pin-submit-button")
        bouton_verif.click()
        print("🔑 Code SMS soumis.")
    except Exception as e:
        raise Exception(f"Erreur saisie code : {e}")

# 🧠 Extraire la partie locale d’un numéro
def extraire_numero_local(numero_complet):
    for indicatif in INDICATIF_TO_COUNTRY_CODE:
        if numero_complet.startswith(indicatif):
            return numero_complet[len(indicatif):]
    return numero_complet  # fallback

# 👁️ Détecter l’indicatif affiché sur la page LinkedIn
def detecter_indicatif_affiche(driver):
    try:
        code_div = driver.find_element(By.ID, "register-phone-country-code")
        return code_div.text.strip()
    except Exception as e:
        raise Exception(f"Impossible de détecter l’indicatif affiché sur LinkedIn : {e}")

def enter_phone_number(driver, phone_number):
    try:
        # 1. Prétraitement du numéro
        full = phone_number.strip()
        if not full.startswith("+"):
            full = "+7" + full  # Par défaut Russie si pas d'indicatif

        match = re.match(r"^\+(\d{1,4})(\d+)$", full)
        if not match:
            raise ValueError(f"Numéro invalide : {full}")
        prefix, local_number = match.groups()
        local_number = local_number.lstrip("0")  # Pas de 0 initial

        code_iso = detect_country_code_from_prefix(f"+{prefix}")
        if not code_iso:
            raise ValueError(f"Aucun pays trouvé pour l'indicatif +{prefix}")

        # 2. Sélectionner le pays
        select = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "select-register-phone-country"))
        )
        Select(select).select_by_value(code_iso)
        logging.info(f"🌍 Pays sélectionné : {code_iso}")

        # 3. Saisir le numéro sans indicatif
        input_field = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "register-verification-phone-number"))
        )
        input_field.clear()
        input_field.send_keys(local_number)
        logging.info(f"📞 Numéro saisi : {local_number}")

        # 4. Cliquer sur "Envoyer"
        submit_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "register-phone-submit-button"))
        )
        submit_btn.click()
        logging.info("📤 Bouton 'Envoyer' cliqué.")

    except Exception as e:
        logging.error(f"❌ Erreur lors de la saisie du numéro LinkedIn : {e}")

def gerer_verifications(driver):
    etat = detect_page_state(driver)
    print(f"⚙️ [DEBUG] gerer_verifications() appelé avec etat = {etat}")
    print(f" État de la page détecté : {etat}")

    if etat not in ["captcha", "phone_number_required"]:
        print(f"⛔ État inattendu dans gerer_verifications: {etat}")
        return
    
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
                time.sleep(30)  

            except Exception as e:
                print(f"❌ Erreur lors du traitement du CAPTCHA Arkose : {e}")

    elif etat == "phone_number_required":
        logging.info("📲 -----Vérification par numéro de téléphone détectée !")

        try:
            activation_id, numero = obtenir_numero_valide()
            logging.info(f"📲 Numéro obtenu : {numero}")
            logging.info(f"📲 activation_id : {activation_id}")
            remplir_numero_linkedin(driver, numero)
            sms_code = get_sms_code(activation_id)
            entrer_code_sms(driver, sms_code)

            logging.info("✅ Vérification téléphone réussie.")
        except Exception as e:
            if "NO_BALANCE" in str(e):
                logging.error("❌ Erreur : NO_BALANCE détecté. Envoi d'un e-mail.")
                send_personalize_email(
                    USERNAME,
                    PASSWORD,
                    "sms-activate.io",
                    "no balance dans sms-activate",
                    "Veuillez recharger le compte SMS-Activate pour poursuivre l'automatisation LinkedIn."
                )
            else :
                logging.error(f"❌ Échec vérification téléphone : {e}")
            
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
        send_personalize_email(USERNAME, PASSWORD, "linkedin", "Vérification par appel vocal", "Une vérification par appel vocal")
        time.sleep(3600)  # pause longue pour intervention humaine

    elif etat == "unknown":
        print("❓ État inconnu détecté. Aucune action prise.")

def guess_country_code(phone):
    if phone.startswith("60"):     # Malaisie
        return "+60"
    elif phone.startswith("33"):   # France
        return "+33"
    elif phone.startswith("213"):  # Algérie
        return "+213"
    # Ajoute d'autres pays si besoin
    else:
        logging.warning(f"Aucun pays trouvé pour le préfixe {phone[:4]}")
        return None

def compose_full_number(phone):
    prefix = guess_country_code(phone)
    if prefix is None:
        raise ValueError(f"Aucun pays trouvé pour l'indicatif +{phone[:4]}")

    # Supprimer le code pays du numéro s’il est déjà présent
    local_part = phone
    prefix_digits = prefix.replace("+", "")
    if phone.startswith(prefix_digits):
        local_part = phone[len(prefix_digits):]

    # Supprimer un zéro en début (utile si présent)
    local_part = local_part.lstrip("0")

    # Retourner le numéro complet
    return prefix + local_part

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

    print(f" URL du site : {site_url}")
    print(" Tentative de récupération automatique du blob...")

    blob = get_arkose_blob_from_driver(driver)
    if not blob:
        print("❌ Blob non trouvé, résolution impossible.")
        return None

    print(" Envoi de la requête à 2Captcha...")

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

def recuperer_profils_visibles(driver, mots_cles, max_profils=20):
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    import time, random

    recherche = mots_cles.replace(" ", "%20")
    url_recherche = f"https://www.linkedin.com/search/results/people/?keywords={recherche}&origin=GLOBAL_SEARCH_HEADER"
    driver.get(url_recherche)
    time.sleep(random.uniform(3, 5))

    profils = set()
    scroll_count = 0

    while len(profils) < max_profils and scroll_count < 6:
        time.sleep(random.uniform(2, 3))
        cartes = driver.find_elements(By.XPATH, "//li[contains(@class, 'reusable-search__result-container')]")
        
        for carte in cartes:
            try:
                nom_elem = carte.find_element(By.CSS_SELECTOR, "span.entity-result__title-text a span[aria-hidden='true']")
                nom = nom_elem.text.strip()

                lien_elem = carte.find_element(By.CSS_SELECTOR, "a.app-aware-link")
                url_profil = lien_elem.get_attribute("href").split("?")[0]

                try:
                    titre_elem = carte.find_element(By.CLASS_NAME, "entity-result__primary-subtitle")
                    titre = titre_elem.text.strip()
                except:
                    titre = ""

                profils.add((nom, titre, url_profil))

                if len(profils) >= max_profils:
                    break
            except Exception as e:
                print(f"[!] Erreur récupération carte profil : {e}")

        # Scroll pour charger plus de résultats
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(random.uniform(2.5, 4))
        scroll_count += 1

    print(f"[✓] Profils récupérés : {len(profils)}")
    return list(profils)

def get_or_create_session(data, driver=None):
    print("🔄 Exécution de get_or_create_session()")
    criteres = data.get("criteres", {})

    mots_cles = criteres.get("mots_cles", "")
    localisation = criteres.get("location", "")
    experience = criteres.get("experience", "")
    competences = criteres.get("skills", [])

    print("Mots-clés      :", mots_cles)
    print("Localisation   :", localisation)
    print("Expérience     :", experience)
    print("Compétences    :", ", ".join(competences))

    if driver is None:
        print("[INFO] Aucun driver fourni, création d'une nouvelle session WebDriver...")
        driver = setup_driver()

    etat_courant = None
    etat_bloquant = False

    try:
        login_linkedin(driver)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Connecté à LinkedIn.")

        # Boucle de gestion des états bloquants (captcha, etc.)
        while True:
            nouvel_etat = detect_page_state(driver)

            etat = detect_page_state(driver)

            if etat == "ok":
                print("✅ Naviguation LinkedIn normale détectée.")
                break  

            if etat_bloquant:
                if nouvel_etat != etat_courant:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] État changé : {etat_courant} ➜ {nouvel_etat}")
                    etat_courant = nouvel_etat
                    etat_bloquant = False
                else:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] État bloquant toujours actif : {nouvel_etat}")
                    time.sleep(5)
                    continue

            if nouvel_etat in ["captcha", "captcha_arkose", "sms_code", "phone_number_required", "user_info", "phone_call"]:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ État bloquant détecté : {nouvel_etat}")
                etat_courant = nouvel_etat
                etat_bloquant = True
                gerer_verifications(driver)
                time.sleep(5)
                continue

            # Aucun état bloquant, on sort
            break

        # On est connecté ✅, maintenant on exécute les autres actions du JSON
        print("✅ Connexion réussie, exécution des fonctions restantes...")
        context = {
            "driver": driver,
            "prompt": data.get("prompt", ""),
            "criteres": data.get("criteres", {}),
            "usernames": []
        }

        alias_fonctions = {
            "rechercher_profils": "ajouter_profils_cibles",
            "ouvrir_linkedIn": "get_or_create_session",
        }

        fonctions_a_ignorer = {"comprendre_criteres", "ouvrir_linkedIn"}

        for action in data.get("actions", []):
            nom_action = action["name"]
            if nom_action in fonctions_a_ignorer:
                continue

            fonction_name = alias_fonctions.get(nom_action, nom_action)
            fonction = globals().get(fonction_name)

            if fonction:
                print(f"Exécution de {fonction_name}()")
                if fonction_name == "ajouter_profils_cibles":
                    ajouter_profils_cibles(driver, mots_cles+localisation)
                elif fonction_name == "download_linkedin_profile_pdf":
                    for username in recuperer_profils_visibles(driver, mots_cles+localisation, max_profils=20) :
                        verifier_match_profil(driver, data, username)
            else:
                print(f"⚠️ Fonction {fonction_name} non trouvée.")

    except Exception as e:
        print(f"[ERREUR] Exception dans get_or_create_session : {e}")

    return driver
client_groq = os.getenv("client_groq")
client = Groq(api_key=client_groq)

def verifier_match_profil(driver, data, username):
    try:
        # Étape 1 : Télécharger le PDF
        download_linkedin_profile_pdf(driver, username)
        print(f"[INFO] PDF du profil {username} téléchargé.")

        # Étape 2 : Trouver le fichier PDF téléchargé
        dossier = os.path.expanduser("~/Downloads")  
        fichiers_pdf = [f for f in os.listdir(dossier) if f.endswith(".pdf")]
        fichiers_pdf.sort(key=lambda f: os.path.getmtime(os.path.join(dossier, f)), reverse=True)
        dernier_pdf = os.path.join(dossier, fichiers_pdf[0]) if fichiers_pdf else None

        if not dernier_pdf:
            print("[ERROR] Aucun fichier PDF trouvé.")
            return False

        # Étape 3 : Extraire les infos depuis le PDF
        infos_profil = extraire_infos_depuis_pdf(dernier_pdf)
        print("[INFO] Infos extraites du profil :", infos_profil)

        # Étape 4 : Préparer la comparaison avec les critères
        criteres = data.get("criteres", {})
        prompt = f"""
Compare les critères suivants avec le profil extrait.

CRITÈRES :
- Mots-clés : {criteres.get('mots_cles', '')}
- Localisation : {criteres.get('location', '')}
- Expérience : {criteres.get('experience', '')}
- Compétences : {', '.join(criteres.get('skills', []))}

PROFIL :
- Nom : {infos_profil.get("nom", "")}
- Titre : {infos_profil.get("titre", "")}
- Entreprise : {infos_profil.get("entreprise", "")}

Réponds uniquement par "MATCH" ou "NO MATCH" en majuscules selon si le profil correspond aux critères.
"""

        # Étape 5 : Envoi à LLaMA 4 via Groq
        response = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2
        )

        result = response.choices[0].message.content.strip()
        print(f"[🤖 LLaMA] Résultat : {result}")
        print("Ce profil est selectionné : ", )
        if result == "MATCH" :
            print("Le profil : ", username,"matche les critéres")

    except Exception as e:
        print(f"[ERROR] Échec de vérification du profil : {e}")
        return False

