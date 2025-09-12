from django.contrib import admin
from .models import Candidat

@admin.register(Candidat)
class CandidatAdmin(admin.ModelAdmin):
    list_display = ('prenom', 'nom', 'email', 'le_bot_qui_a_trouve_ce_profil', 'date_trouve')
    search_fields = ('prenom', 'nom', 'competences', 'certificats')
