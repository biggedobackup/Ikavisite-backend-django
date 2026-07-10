from django.urls import path
from . import views
from core.views import tableau_de_bord

urlpatterns = [
    path('', views.connexion_view, name='connexion'),
    path('tableau-de-bord/', tableau_de_bord, name='tableau_de_bord'),
    path('profil/', views.profil_view, name='profil'),
    path('deconnexion/', views.deconnexion_view, name='deconnexion'),
    path('utilisateurs/', views.liste_utilisateurs, name='liste_utilisateurs'),
    path('utilisateurs/export/pdf/', views.export_pdf_utilisateurs, name='export_pdf_utilisateurs'),
    path('utilisateurs/export/excel/', views.export_excel_utilisateurs, name='export_excel_utilisateurs'),
    path('utilisateurs/ajouter/', views.ajouter_utilisateur, name='ajouter_utilisateur'),
    path('utilisateurs/detail/<int:pk>/', views.detail_utilisateur, name='detail_utilisateur'),
    path('utilisateurs/modifier/<int:pk>/', views.modifier_utilisateur, name='modifier_utilisateur'),
    path('utilisateurs/supprimer/<int:pk>/', views.supprimer_utilisateur, name='supprimer_utilisateur'),
    path('historique-actions/', views.liste_historique_actions, name='liste_historique_actions'),
]
