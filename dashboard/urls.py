from django.urls import path
from . import views
from django.contrib.auth.views import LogoutView

urlpatterns = [
    path('', views.login_view, name='login'),
    path('home/', views.index, name='home'),
    path('importcv/', views.importcv, name='importcv'),
    path('prospectiq/', views.prospectiq, name='prospectiq'),
    path('lancer_bot/', views.lancer_bot, name='lancer_bot'),
    path('arreter_bot/', views.arreter_bot, name='arreter_bot'),
    path('createlinkedin/', views.createlinkedin, name='createlinkedin'),
    path('logs/', views.stream_logs, name='stream_logs'),
    path('envoyer_prompt/', views.envoyer_prompt, name='envoyer_prompt'),
    path('candidats/', views.view_candidates, name='view_candidates'),
    path('logout/', views.logout_view, name='logout'),
    path('candidats/ajouter/', views.ajouter_candidat, name='ajouter_candidat'),
    path('candidats/modifier/<int:candidat_id>/', views.modifier_candidat, name='modifier_candidat'),
    path('scanner-cv/', views.scanner_cv, name='scanner_cv'),
    path('candidats/supprimer/<int:candidat_id>/', views.supprimer_candidat, name='supprimer_candidat'),
    path('lancer_prospectiq/', views.lancer_prospectiq, name='lancer_prospectiq'),
    path('arreter_prospectiq/', views.arreter_prospectiq, name='arreter_prospectiq'),
    path('logs_prospectiq/', views.stream_logs_prospectiq, name='stream_logs_prospectiq'),
    path('ajouter-linkedin/', views.ajouter_compte_linkedin, name='ajouter_compte_linkedin'),
    path('createlinkedin/', views.liste_linkedin, name='liste_linkedin'),
    path('voirlinkedin/', views.voirlinkedin, name='voirlinkedin'),
    path('linkedin/modifier/<int:account_id>/', views.modifier_compte_linkedin, name='modifier_compte_linkedin'),
    path('linkedin/supprimer/<int:account_id>/', views.supprimer_compte_linkedin, name='supprimer_compte_linkedin'),
]
