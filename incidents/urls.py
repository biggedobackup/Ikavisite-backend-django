from django.urls import path
from . import views

urlpatterns = [
    path('', views.liste_incidents, name='liste_incidents'),
    path('detection/', views.detection_incidents, name='detection_incidents'),
    path('ajouter/', views.ajouter_incident, name='ajouter_incident'),
    path('detail/<int:pk>/', views.detail_incident, name='detail_incident'),
    path('modifier/<int:pk>/', views.modifier_incident, name='modifier_incident'),
    path('supprimer/<int:pk>/', views.supprimer_incident, name='supprimer_incident'),
    path('fermer/<int:pk>/', views.fermer_incident, name='fermer_incident'),
    path('export/pdf/', views.export_pdf_incidents, name='export_pdf_incidents'),
    path('export/excel/', views.export_excel_incidents, name='export_excel_incidents'),
]
