from django.urls import path
from . import views

urlpatterns = [
    path('', views.liste_incidents, name='liste_incidents'),
    path('ajouter/', views.ajouter_incident, name='ajouter_incident'),
    path('detail/<int:pk>/', views.detail_incident, name='detail_incident'),
    path('modifier/<int:pk>/', views.modifier_incident, name='modifier_incident'),
    path('supprimer/<int:pk>/', views.supprimer_incident, name='supprimer_incident'),
    path('fermer/<int:pk>/', views.fermer_incident, name='fermer_incident'),
    path('recherche-visiteurs/', views.recherche_visiteurs_json, name='recherche_visiteurs_json'),
    path('export/pdf/', views.export_pdf_incidents, name='export_pdf_incidents'),
    path('export/excel/', views.export_excel_incidents, name='export_excel_incidents'),
    # Types d'incident (CRUD)
    path('types/', views.liste_types_incident, name='liste_types_incident'),
    path('types/ajouter/', views.ajouter_type_incident, name='ajouter_type_incident'),
    path('types/modifier/<int:pk>/', views.modifier_type_incident, name='modifier_type_incident'),
    path('types/supprimer/<int:pk>/', views.supprimer_type_incident, name='supprimer_type_incident'),
]
