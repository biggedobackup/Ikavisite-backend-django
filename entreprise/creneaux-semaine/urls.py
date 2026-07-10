from django.urls import path
from . import views

urlpatterns = [
    path('', views.liste_creneaux, name='liste_creneaux'),
    path('export/pdf/', views.export_pdf_creneaux, name='export_pdf_creneaux'),
    path('export/excel/', views.export_excel_creneaux, name='export_excel_creneaux'),
    path('ajouter/', views.ajouter_creneau, name='ajouter_creneau'),
    path('detail/<int:pk>/', views.detail_creneau, name='detail_creneau'),
    path('modifier/<int:pk>/', views.modifier_creneau, name='modifier_creneau'),
    path('supprimer/<int:pk>/', views.supprimer_creneau, name='supprimer_creneau'),
]
