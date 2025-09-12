import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import os
import sys

# Charger les variables d'environnement depuis le fichier .env
load_dotenv()

SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
MAIL_RECEIVER = os.getenv("MAIL_RECEIVER")

def log(message):
    log(message)
    sys.stdout.flush()

def envoyer_mail_captcha(utilisateur, mot_de_passe, site_url):
    """
    Envoie un email avec les identifiants pour intervention humaine.
    """
    try:
        sujet = f"[Action requise] CAPTCHA Arkose détecté pour {utilisateur}"
        corps = f"""
        Bonjour,

        Un captcha Arkose a été détecté lors de la tentative de connexion pour :

        🔐 Utilisateur : {utilisateur}
        🔑 Mot de passe : {mot_de_passe}
        🌐 URL : {site_url}

        Merci d'intervenir manuellement pour compléter le captcha.

        -- Bot LinkedIn
        """

        message = MIMEMultipart()
        message["From"] = SMTP_USER
        message["To"] = MAIL_RECEIVER
        message["Subject"] = sujet
        message.attach(MIMEText(corps, "plain"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as smtp:
            smtp.starttls()
            smtp.login(SMTP_USER, SMTP_PASS)
            smtp.send_message(message)

        log(" Mail envoyé à l'humain pour résoudre le CAPTCHA Arkose.")
    except Exception as e:
        log(f" Erreur envoi mail : {e}")

def send_personalize_email(utilisateur, mot_de_passe, site_url, sujet, corps):
    """
    Envoie un email avec les identifiants pour intervention humaine.
    """
    try:
        sujet += f" {utilisateur}"
        corps += f"""
        utilisateur concerné est :

        🔐 Utilisateur : {utilisateur}
        🔑 Mot de passe : {mot_de_passe}
        🌐 URL : {site_url}

        -- Bot LinkedIn
        """

        message = MIMEMultipart()
        message["From"] = SMTP_USER
        message["To"] = MAIL_RECEIVER
        message["Subject"] = sujet
        message.attach(MIMEText(corps, "plain"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as smtp:
            smtp.starttls()
            smtp.login(SMTP_USER, SMTP_PASS)
            smtp.send_message(message)

        log(" Mail personalisé envoyé à l'humain.")
    except Exception as e:
        log(f" Erreur envoi mail : {e}")

def envoyer_mail_info():
    
    """
    Envoie un email avec les identifiants pour intervention humaine.
    """
    try:
        site_url = "https://sms-activate.io/"
        sujet = f"[Action requise] Recharger le compte de sms-activate"
        corps = f"""
        Bonjour,

        Un votre crédit est insuffisant pour créer des nouveaux e-mails.

        🌐 URL : {site_url}

        Merci d'intervenir manuellement.

        -- Bot LinkedIn
        """

        message = MIMEMultipart()
        message["From"] = SMTP_USER
        message["To"] = MAIL_RECEIVER
        message["Subject"] = sujet
        message.attach(MIMEText(corps, "plain"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as smtp:
            smtp.starttls()
            smtp.login(SMTP_USER, SMTP_PASS)
            smtp.send_message(message)

        log(" Mail envoyé à l'humain pour résoudre le CAPTCHA Arkose.")
    except Exception as e:
        log(f" Erreur envoi mail : {e}")