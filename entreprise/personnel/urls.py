from django.urls import path
from . import views

urlpatterns = [
    path('', views.liste_personnel, name='liste_personnel'),
    path('export/pdf/', views.export_pdf_personnel, name='export_pdf_personnel'),
    path('export/excel/', views.export_excel_personnel, name='export_excel_personnel'),
    path('ajouter/', views.ajouter_personnel, name='ajouter_personnel'),
    path('detail/<int:pk>/', views.detail_personnel, name='detail_personnel'),
    path('modifier/<int:pk>/', views.modifier_personnel, name='modifier_personnel'),
    path('supprimer/<int:pk>/', views.supprimer_personnel, name='supprimer_personnel'),
    path('modele-csv/', views.telecharger_modele_csv_personnel, name='modele_csv_personnel'),
    path('import-csv/', views.import_csv_personnel, name='import_csv_personnel'),
]
