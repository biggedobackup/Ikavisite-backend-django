from django.urls import path
from . import views

urlpatterns = [
    # Types de visite
    path('types/', views.liste_types_visite, name='liste_types_visite'),
    path('types/ajouter/', views.ajouter_type_visite, name='ajouter_type_visite'),
    path('types/detail/<int:pk>/', views.detail_type_visite, name='detail_type_visite'),
    path('types/modifier/<int:pk>/', views.modifier_type_visite, name='modifier_type_visite'),
    path('types/supprimer/<int:pk>/', views.supprimer_type_visite, name='supprimer_type_visite'),
    path('types/export/pdf/', views.export_pdf_types_visite, name='export_pdf_types_visite'),
    path('types/export/excel/', views.export_excel_types_visite, name='export_excel_types_visite'),
    # Visites
    path('', views.liste_visites, name='liste_visites'),
    path('ajouter/', views.ajouter_visite, name='ajouter_visite'),
    path('enregistrer-refus/', views.enregistrer_refus_visite, name='enregistrer_refus_visite'),
    path('detail/<int:pk>/', views.detail_visite, name='detail_visite'),
    path('modifier/<int:pk>/', views.modifier_visite, name='modifier_visite'),
    path('terminer/<int:pk>/', views.terminer_visite, name='terminer_visite'),
    path('supprimer/<int:pk>/', views.supprimer_visite, name='supprimer_visite'),
    path('export/pdf/', views.export_pdf_visites, name='export_pdf_visites'),
    path('export/excel/', views.export_excel_visites, name='export_excel_visites'),
    # En cours
    path('en-cours/', views.liste_visites_encours, name='liste_visites_encours'),
    path('en-cours/detail/<int:pk>/', views.detail_visite_encours, name='detail_visite_encours'),
    path('en-cours/export/pdf/', views.export_pdf_visites_encours, name='export_pdf_visites_encours'),
    path('en-cours/export/excel/', views.export_excel_visites_encours, name='export_excel_visites_encours'),
    # Terminées
    path('terminees/', views.liste_visites_terminees, name='liste_visites_terminees'),
    path('terminees/detail/<int:pk>/', views.detail_visite_terminee, name='detail_visite_terminee'),
    path('terminees/export/pdf/', views.export_pdf_visites_terminees, name='export_pdf_visites_terminees'),
    path('terminees/export/excel/', views.export_excel_visites_terminees, name='export_excel_visites_terminees'),
    # Excédées
    path('excedees/', views.liste_visites_excedees, name='liste_visites_excedees'),
    path('excedees/detail/<int:pk>/', views.detail_visite_excedee, name='detail_visite_excedee'),
    path('excedees/export/pdf/', views.export_pdf_visites_excedees, name='export_pdf_visites_excedees'),
    path('excedees/export/excel/', views.export_excel_visites_excedees, name='export_excel_visites_excedees'),
    # Visiteurs
    path('visiteurs/', views.liste_visiteurs, name='liste_visiteurs'),
    path('visiteurs/detail/<int:pk>/', views.detail_visiteur, name='detail_visiteur'),
]
