from django.urls import path
from . import views

urlpatterns = [
    path('', views.liste_portes_entree, name='liste_portes_entree'),
    path('export/pdf/', views.export_pdf_portes_entree, name='export_pdf_portes_entree'),
    path('export/excel/', views.export_excel_portes_entree, name='export_excel_portes_entree'),
    path('ajouter/', views.ajouter_porte_entree, name='ajouter_porte_entree'),
    path('detail/<int:pk>/', views.detail_porte_entree, name='detail_porte_entree'),
    path('modifier/<int:pk>/', views.modifier_porte_entree, name='modifier_porte_entree'),
    path('supprimer/<int:pk>/', views.supprimer_porte_entree, name='supprimer_porte_entree'),
]
