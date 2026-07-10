from django.urls import path
from . import views

urlpatterns = [
    path('', views.liste_objets_oublies, name='liste_objets_oublies'),
    path('detection/', views.detection_objets_oublies, name='detection_objets_oublies'),
    path('ajouter/', views.ajouter_objet_oublie, name='ajouter_objet_oublie'),
    path('detail/<int:pk>/', views.detail_objet_oublie, name='detail_objet_oublie'),
    path('modifier/<int:pk>/', views.modifier_objet_oublie, name='modifier_objet_oublie'),
    path('supprimer/<int:pk>/', views.supprimer_objet_oublie, name='supprimer_objet_oublie'),
    path('restituer/<int:pk>/', views.restituer_objet_oublie, name='restituer_objet_oublie'),
    path('export/pdf/', views.export_pdf_objets_oublies, name='export_pdf_objets_oublies'),
    path('export/excel/', views.export_excel_objets_oublies, name='export_excel_objets_oublies'),
]
