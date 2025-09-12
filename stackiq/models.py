from django.db import models

class Candidat(models.Model):
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    lien_du_profile = models.URLField(max_length=500)
    certificats = models.TextField(blank=True)
    competences = models.TextField(blank=True)
    le_bot_qui_a_trouve_ce_profil = models.CharField(max_length=100)

    email = models.EmailField(blank=True, null=True)
    telephone = models.CharField(max_length=20, blank=True)
    date_trouve = models.DateTimeField(auto_now_add=True)
    origine_du_profil = models.CharField(max_length=100, blank=True)  

    def __str__(self):
        return f"{self.prenom} {self.nom}"
    
class LinkedInAccount(models.Model):
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=255) 
    date_ajout = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email
