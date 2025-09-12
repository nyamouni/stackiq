from django.shortcuts import render, redirect, get_object_or_404
import subprocess
import os
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, StreamingHttpResponse, HttpResponse
import time
import signal
import psutil
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from stackiq.models import Candidat
from django.contrib.auth.decorators import login_required
from stackiq.forms import CandidatForm
from .traitement_cv import formatter_resultat_cv
from stackiq.models import LinkedInAccount


PID_FILE = "bot.pid"
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_FILE_PATH = os.path.join(BASE_DIR, "philigram", "logs.txt")
BOT_SCRIPT = os.path.join(BASE_DIR, "philigram", "main_talentIQ.py")

def index(request):
    comptes = LinkedInAccount.objects.all().order_by('-date_ajout')
    return render(request, 'dashboard/index.html', {'linkedin_accounts': comptes})

def importcv(request):
    return render(request, 'dashboard/importcv.html')

def createlinkedin(request):
    return render(request, 'dashboard/createlinkedin.html')

def prospectiq(request):
    comptes = LinkedInAccount.objects.all().order_by('-date_ajout')
    return render(request, 'dashboard/prospect.html', {'linkedin_accounts': comptes})

@csrf_exempt
def lancer_bot(request):
    if request.method == 'POST':
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            script_path = os.path.join(base_dir, "philigram", "main_talentIQ.py")

            process = subprocess.Popen(["python3", script_path])
            # Sauvegarde du PID
            pid_file = os.path.join(base_dir, "philigram", "bot.pid")
            if os.path.exists(pid_file):
                return JsonResponse({"status": "error", "message": "⚠️ Bot déjà en cours d'exécution."})

            with open(pid_file, "w") as f:
                f.write(str(process.pid))

            return JsonResponse({"status": "ok", "message": f"Bot lancé avec PID {process.pid}"})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)})
    return JsonResponse({"status": "error", "message": "Méthode non autorisée"})

@csrf_exempt
def arreter_bot(request):
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    pid_file = os.path.join(base_dir, "philigram", "bot.pid")

    if not os.path.exists(pid_file):
        return JsonResponse({"status": "error", "message": "⚠️ Aucun bot à arrêter"})

    try:
        with open(pid_file, "r") as f:
            pid = int(f.read().strip())

        # Utilise psutil pour tuer tout le groupe de processus
        parent = psutil.Process(pid)

        # Tuer récursivement tous les enfants
        children = parent.children(recursive=True)
        for child in children:
            child.kill()  # Force kill des sous-processus
        parent.kill()  # Kill du processus principal

        os.remove(pid_file)

        return JsonResponse({"status": "ok", "message": "✅ Bot arrêté avec succès."})

    except Exception as e:
        return JsonResponse({"status": "error", "message": f"❌ Erreur lors de l'arrêt du bot : {str(e)}"})

def stream_logs(request):
    log_path = os.path.join(BASE_DIR, "philigram", "logs.txt")


    def generate():
        with open(log_path, "r") as f:
            f.seek(0, os.SEEK_END)  
            while True:
                line = f.readline()
                if line:
                    yield f"data: {line.strip()}\n\n"
                else:
                    time.sleep(1)

    return StreamingHttpResponse(generate(), content_type='text/event-stream')

@csrf_exempt
def envoyer_prompt(request):
    if request.method == 'POST':
        try:
            prompt = request.POST.get("prompt")
            if not prompt:
                return JsonResponse({"status": "error", "message": "Prompt vide"})

            prompt_file = os.path.join(BASE_DIR, "philigram", "pending_prompt.txt")
            with open(prompt_file, "w") as f:
                f.write(prompt.strip())

            return JsonResponse({"status": "ok", "message": "✅ Prompt envoyé avec succès."})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)})

    return JsonResponse({"status": "error", "message": "Méthode non autorisée"})

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect('home')  
        else:
            messages.error(request, 'Nom d’utilisateur ou mot de passe incorrect.')
    
    return render(request, 'dashboard/login.html')  

@login_required
def view_candidates(request):
    candidats = Candidat.objects.all()
    return render(request, 'dashboard/view_candidates.html', {'candidats': candidats})

def supprimer_candidat(request, candidat_id):
    candidat = get_object_or_404(Candidat, id=candidat_id)
    candidat.delete()
    return redirect('view_candidates')

def logout_view(request):
    logout(request)
    return redirect('/')

@login_required
def modifier_candidat(request, candidat_id):
    print(f"MODIFICATION de {candidat_id}")  
    candidat = get_object_or_404(Candidat, id=candidat_id)
    if request.method == 'POST':
        form = CandidatForm(request.POST, instance=candidat)
        if form.is_valid():
            form.save()
            return redirect('view_candidates')
    else:
        form = CandidatForm(instance=candidat)
    return render(request, 'dashboard/ajouter_candidat.html', {'form': form})

@login_required
def scanner_cv(request):
    if request.method == 'POST' and request.FILES.get('cv_file'):
        fichier = request.FILES['cv_file']

        # Simule l'analyse (tu peux ici mettre un vrai traitement)
        resultats = {
            'nom': 'Dupont',
            'prenom': 'Jean',
            'competences': 'Python, Django',
            'certificats': 'AWS, Scrum Master',
            'linkedin': 'https://linkedin.com/in/jeandupont'
        }

        return JsonResponse(resultats)

    return JsonResponse({'error': 'Fichier non reçu'}, status=400)

@login_required
def ajouter_candidat(request):
    if request.method == 'POST':
        print("POST reçu")

        action = request.POST.get('action')
        if action == 'scan':
            cv_file = request.FILES.get('cv_file')
            if cv_file:
                nom, prenom, competences, certificats, linkedin = formatter_resultat_cv(cv_file)
                print(nom, prenom, competences, certificats, linkedin)
                return JsonResponse({
                    'success': True,
                    'nom': nom,
                    'prenom': prenom,
                    'competences': competences,
                    'certificats': certificats,
                    'linkedin': linkedin,
                })
            return JsonResponse({'success': False, 'error': 'Aucun fichier fourni.'})

        # Cas : Enregistrement du formulaire (bouton "Enregistrer")
        nom = request.POST.get('nom')
        prenom = request.POST.get('prenom')
        competences = request.POST.get('competences')
        certificats = request.POST.get('certificats')
        linkedin = request.POST.get('linkedin')

        print("📝 Nom :", nom)
        print("📝 Prénom :", prenom)

        if nom and prenom:
            Candidat.objects.create(
                nom=nom,
                prenom=prenom,
                competences=competences,
                certificats=certificats,
                lien_du_profile=linkedin,
                le_bot_qui_a_trouve_ce_profil="Ajout manuel"
            )
            print("✅ Enregistré !")
            return redirect('view_candidates')
        else:
            print("❌ Champ nom ou prénom vide !")

    return render(request, 'dashboard/ajouter_candidat.html')

@csrf_exempt
def lancer_prospectiq(request):
    if request.method == 'POST':
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            script_path = os.path.join(base_dir, "philigram", "main.py")
            pid_file = os.path.join(base_dir, "philigram", "bot_prospect.pid")
            log_file = os.path.join(base_dir, "philigram", "bot_prospect.txt")

            # Vérifier si déjà lancé
            if os.path.exists(pid_file):
                return JsonResponse({"status": "error", "message": "⚠️ Bot déjà en cours d'exécution."})

            # Vider les anciens logs
            open(log_file, "w").close()

            # Lancer en redirigeant stdout & stderr vers le fichier log
            with open(log_file, "a") as f:
                process = subprocess.Popen(
                    ["python3", script_path],
                    stdout=f,
                    stderr=f,
                    cwd=os.path.dirname(script_path)  # Assure que main.py s'exécute dans son dossier
                )

            # Sauvegarder le PID
            with open(pid_file, "w") as f:
                f.write(str(process.pid))

            return JsonResponse({"status": "ok", "message": f"Bot ProspectIQ lancé avec PID {process.pid}"})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)})
    return JsonResponse({"status": "error", "message": "Méthode non autorisée"})

@csrf_exempt
def arreter_prospectiq(request):
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    pid_file = os.path.join(base_dir, "philigram", "bot_prospect.pid")

    if not os.path.exists(pid_file):
        return JsonResponse({"status": "error", "message": "⚠️ Aucun bot ProspectIQ à arrêter"})

    try:
        with open(pid_file, "r") as f:
            pid = int(f.read().strip())

        parent = psutil.Process(pid)

        # Tuer récursivement tous les enfants
        children = parent.children(recursive=True)
        for child in children:
            child.kill()
        parent.kill()

        os.remove(pid_file)

        return JsonResponse({"status": "ok", "message": "✅ Bot ProspectIQ arrêté avec succès."})

    except Exception as e:
        return JsonResponse({"status": "error", "message": f"❌ Erreur lors de l'arrêt du bot ProspectIQ : {str(e)}"})

def stream_logs_prospectiq(request):
    log_path = os.path.join(BASE_DIR, "philigram", "bot_prospect.txt")

    def generate():
        with open(log_path, "r") as f:
            f.seek(0, os.SEEK_END)
            while True:
                line = f.readline()
                if line:
                    yield f"data: {line.strip()}\n\n"
                else:
                    time.sleep(1)

    return StreamingHttpResponse(generate(), content_type='text/event-stream')

def supprimer_compte_linkedin(request, account_id):
    compte = get_object_or_404(LinkedInAccount, id=account_id)
    compte.delete()
    return redirect('liste_linkedin')

def modifier_compte_linkedin(request, account_id):
    compte = get_object_or_404(LinkedInAccount, id=account_id)
    if request.method == "POST":
        compte.email = request.POST.get("email")
        compte.password = request.POST.get("password")
        compte.save()
        return redirect('liste_linkedin')
    return render(request, "modifier_linkedin.html", {"compte": compte})

def liste_linkedin(request):
    comptes = LinkedInAccount.objects.all().order_by('-date_ajout')
    return render(request, 'dashboard/liste_linkedin.html', {'linkedin_accounts': comptes})

def ajouter_compte_linkedin(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        if LinkedInAccount.objects.filter(email=email).exists():
            messages.error(request, "Ce compte LinkedIn existe déjà.")
        else:
            LinkedInAccount.objects.create(email=email, password=password)
            messages.success(request, "Compte LinkedIn ajouté avec succès.")
        return redirect('liste_linkedin')

    return render(request, "dashboard/createlinkedin.html")

def voirlinkedin(request):
    comptes = LinkedInAccount.objects.all().order_by('-date_ajout')
    return render(request, 'dashboard/liste_linkedin.html', {'linkedin_accounts': comptes})
