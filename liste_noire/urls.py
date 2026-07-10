from django.urls import path
from . import views

urlpatterns = [
    # Types de liste noire
    path('types/', views.liste_types_liste_noire, name='liste_types_liste_noire'),
    path('types/ajouter/', views.ajouter_type_liste_noire, name='ajouter_type_liste_noire'),
    path('types/detail/<int:pk>/', views.detail_type_liste_noire, name='detail_type_liste_noire'),
    path('types/modifier/<int:pk>/', views.modifier_type_liste_noire, name='modifier_type_liste_noire'),
    path('types/supprimer/<int:pk>/', views.supprimer_type_liste_noire, name='supprimer_type_liste_noire'),
    path('types/export/pdf/', views.export_pdf_types_liste_noire, name='export_pdf_types_liste_noire'),
    path('types/export/excel/', views.export_excel_types_liste_noire, name='export_excel_types_liste_noire'),
    # Listes noires
    path('listes/', views.liste_listes_noires, name='liste_listes_noires'),
    path('listes/ajouter/', views.ajouter_liste_noire, name='ajouter_liste_noire'),
    path('listes/detail/<int:pk>/', views.detail_liste_noire, name='detail_liste_noire'),
    path('listes/modifier/<int:pk>/', views.modifier_liste_noire, name='modifier_liste_noire'),
    path('listes/supprimer/<int:pk>/', views.supprimer_liste_noire, name='supprimer_liste_noire'),
    path('listes/toggle/<int:pk>/', views.toggle_statut_liste_noire, name='toggle_statut_liste_noire'),
    path('listes/export/pdf/', views.export_pdf_listes_noires, name='export_pdf_listes_noires'),
    path('listes/export/excel/', views.export_excel_listes_noires, name='export_excel_listes_noires'),
    # Détections liste noire
    path('detections/', views.liste_detections_liste_noire, name='liste_detections_liste_noire'),
    path('detections/detail/<int:pk>/', views.detail_detection_liste_noire, name='detail_detection_liste_noire'),
    path('detections/traiter/<int:pk>/', views.traiter_detection_liste_noire, name='traiter_detection_liste_noire'),
    path('detections/export/pdf/', views.export_pdf_detections_liste_noire, name='export_pdf_detections_liste_noire'),
    path('detections/export/excel/', views.export_excel_detections_liste_noire, name='export_excel_detections_liste_noire'),
]
