from django.urls import path
from . import views

urlpatterns = [
    path('', views.liste_departements, name='liste_departements'),
    path('export/pdf/', views.export_pdf_departements, name='export_pdf_departements'),
    path('export/excel/', views.export_excel_departements, name='export_excel_departements'),
    path('ajouter/', views.ajouter_departement, name='ajouter_departement'),
    path('detail/<int:pk>/', views.detail_departement, name='detail_departement'),
    path('modifier/<int:pk>/', views.modifier_departement, name='modifier_departement'),
    path('supprimer/<int:pk>/', views.supprimer_departement, name='supprimer_departement'),
]
