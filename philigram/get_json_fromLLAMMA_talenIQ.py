import json
import re
from groq import Groq
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
import os
import undetected_chromedriver as uc
import re
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
import fitz 
import time, random, requests, logging
from fonctions_utils_talentIQ import *
import sys
import signal

def log(message):
    log(message)
    sys.stdout.flush()

# === CONFIGURATION CLIENT ===
client_groq = os.getenv("client_groq")
client = Groq(api_key=client_groq)

# === NETTOYAGE DU TEXTE POUR ÉVITER LES ERREURS DE PARSING ===
def nettoyer_json_brut(texte):
    # 1. Supprimer les commentaires // comme dans : // liste de liens à scanner
    texte = re.sub(r'//.*', '', texte)

    # 2. Remplacer les chaînes "lien": "https: sans guillemets fermants
    texte = re.sub(r'"lien"\s*:\s*"https:[^"]*', '"lien": "https://placeholder"', texte)

    # 3. Supprimer les espaces en trop autour des clefs
    texte = re.sub(r'\s+"([^"]+)"\s*:', r'"\1":', texte)

    # 4. S'assurer que les guillemets sont bien fermés
    texte = re.sub(r'\\(?=[^"\\/bfnrtu])', r'\\\\', texte)  # Échapper les backslashes mal placés

    return texte.strip()

def ajouter_profils_cibles(driver, mots_cles, nombre_max=10):

    recherche = mots_cles.replace(" ", "%20")
    url_recherche = f"https://www.linkedin.com/search/results/people/?keywords={recherche}&origin=GLOBAL_SEARCH_HEADER"
    driver.get(url_recherche)
    time.sleep(random.uniform(3, 6))

    demandes_envoyees = 0
    scroll_count = 0

    while demandes_envoyees < nombre_max and scroll_count < 6:
        boutons_connecter = driver.find_elements(By.XPATH, "//button[contains(@aria-label, 'Invitez')]")
        log(f"[INFO] Boutons 'Se connecter' trouvés : {len(boutons_connecter)}")

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
                    log(f"[✓] Demande envoyée sans note ({demandes_envoyees+1})")
                    demandes_envoyees += 1
                    time.sleep(random.uniform(1, 2))

                except:
                    # Sinon, essayer "Envoyer maintenant"
                    try:
                        envoyer_btn = WebDriverWait(driver, 3).until(
                            EC.element_to_be_clickable((By.XPATH, "//button[@aria-label='Envoyer maintenant']"))
                        )
                        envoyer_btn.click()
                        log(f"[✓] Demande envoyée avec 'Envoyer maintenant' ({demandes_envoyees+1})")
                        demandes_envoyees += 1
                        time.sleep(random.uniform(1, 2))
                    except:
                        log("[INFO] Aucun bouton 'Envoyer' trouvé, tentative de fermeture du pop-up.")
                        try:
                            fermer_btn = driver.find_element(By.XPATH, "//button[@aria-label='Fermer']")
                            fermer_btn.click()
                        except:
                            pass

            except Exception as e:
                log(f"[!] Erreur : {e}")

        # Scroll pour charger plus de résultats
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(random.uniform(4, 6))
        scroll_count += 1

    log(f"[✓] Total de demandes envoyées : {demandes_envoyees}")

def download_linkedin_profile_pdf(driver, username):
    try:
        profile_url = f"https://www.linkedin.com/in/{username}/"
        log(f"[DEBUG] Accès au profil : {profile_url}")
        driver.get(profile_url)
        time.sleep(random.uniform(4, 6))

        log("[DEBUG] Recherche du bouton 'Plus d’actions' (SVG)...")
        
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

        log("[DEBUG] Recherche du bouton 'Enregistrer au format PDF'...")
        pdf_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((
                By.XPATH,
                "//span[contains(text(), 'Enregistrer au format PDF') or contains(text(), 'Save to PDF')]"
            ))
        )
        driver.execute_script("arguments[0].click();", pdf_button)
        log(f"[✓] Téléchargement PDF lancé pour : {username}")
        time.sleep(5)

    except Exception as e:
        log(f"[ERROR] Impossible de télécharger le PDF du profil : {e}")

        # Capture HTML pour debug si besoin
        try:
            html = driver.page_source
            log("[DEBUG] HTML actuel (extrait) :")
            log(html[:1500])
        except Exception as html_error:
            log(f"[DEBUG] Impossible de capturer le HTML : {html_error}")

def comprendre_criteres(criteres):
    log("\n* Critères extraits du prompt :")

    mots_cles = criteres.get("mots_cles", "N/A")
    location = criteres.get("location", "N/A")
    experience = criteres.get("experience", "N/A")
    skills = criteres.get("skills", [])

    log(f"- Mots-clés       : {mots_cles}")
    log(f"- Localisation    : {location}")
    log(f"- Expérience      : {experience}")
    log(f"- Compétences     : {', '.join(skills) if skills else 'Aucune'}")
    log("\n")

def verifier_critere_du_profil(profile_data):
    log(f"🧪 [verifier_critere_du_profil] Vérifie : {profile_data}")
    return True

def afficher_les_profils_cibles(profils):
    log("📋 Profils ciblés :")
    for p in profils:
        log(" -", p)

def executer_actions(prompt, driver=None):
    if not prompt.strip():
        log("Prompt vide. Veuillez entrer une instruction valide.")
        return
    # Appel de LLaMA pour obtenir JSON
    data = get_instructions_llamma4(prompt)
    log("*************la variable data : ", data)
    log(data)
    if not data:
        log("Aucune donnée reçue depuis LLaMA.")
        return

    # Préparer le contexte global
    context = {
        "prompt": prompt,
        "criteres": data.get("criteres", {}),
        "driver": None,  
        "usernames": [] 
    }

    alias_fonctions = {
        "rechercher_profils": "ajouter_profils_cibles",
        "ouvrir_linkedIn": "get_or_create_session"
    }

    # actions_list = [action["name"] for action in data.get("actions", [])]

    log("\n🔄 Liste des fonctions disponibles et à exécuter dans l'ordre :")
    for action in data.get("actions", []):
        action_name = action["name"]

        # Vérifier si c’est un alias
        fonction_name = alias_fonctions.get(action_name, action_name)
        fonction = globals().get(fonction_name)

        if fonction:

            log(f" {action_name}() → {fonction_name}() sera exécutée")
            
            if fonction_name == "comprendre_criteres":
                fonction(context["criteres"])
            elif fonction_name == "get_or_create_session":
                log("le bloque est éxécuté")
                driver = get_or_create_session(data, context["driver"])
                context["driver"] = driver
        else:
            log(f" {action_name}() ignorée (non définie)")

# === FONCTION de llamma ===
def get_instructions_llamma4(prompt_utilisateur):
    prompt = f"""
Tu es un assistant Python qui aide à automatiser la recherche de profils LinkedIn.

À partir de l'intention utilisateur suivante :
\"\"\"{prompt_utilisateur}\"\"\"

Tu dois :
1. Déduire les **critères de recherche** pertinents (mots-clés, lieu, expérience, compétences, etc.)
2. Proposer une **liste d'actions** à exécuter dans l’ordre pour automatiser la recherche sur LinkedIn.

Retourne uniquement un JSON au format suivant et Ne retourne que les actions suivantes dans le tableau `actions` :

{{
  "criteres": {{
    "mots_cles": "...",
    "location": "...",
    "experience": "...",
    "skills": ["..."]
  }},
  "actions": [
    {{ "name": "comprendre_criteres" }},
    {{ "name": "ouvrir_linkedIn" }},
    {{ "name": "ajouter_profils_cibles" }},
    {{ "name": "download_linkedin_profile_pdf" }},
    {{ "name": "verifier_critere_du_profil" }},
    {{ "name": "afficher_les_profils_cibles" }}
  ]
}}

Important :
- Pas de texte hors du JSON.
- Tous les champs doivent être remplis de manière cohérente.
"""


    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "Tu es un assistant Python expert."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2
        )

        content = response.choices[0].message.content.strip()
        # log("📥 Contenu brut reçu de LLaMA 4:\n", content)

        # ⚠️ Tentative de parsing JSON directement
        data = json.loads(content)
        return data
        # log("✅ JSON parsé avec succès :", data)


    except json.JSONDecodeError as e:
        log("❌ Erreur lors du parsing JSON :", e)
        log("⛔ Contenu brut :\n", content)
        return None
    except Exception as e:
        log("🔥 Erreur d'exécution :", e)
        return None

# === POINT D’ENTRÉE ===
# if __name__ == "__main__":
#     prompt = input("Entrez une instruction (ex: Trouve les profils tech à Paris avec 5 ans d’expérience) :\n> ")
#     executer_actions(prompt)
