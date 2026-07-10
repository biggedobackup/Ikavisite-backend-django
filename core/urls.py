"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.shortcuts import render
from django.urls import path, include

from core.api import api

def handler400_view(request, exception=None):
    return render(request, '400.html', status=400)
def handler403_view(request, exception=None):
    return render(request, '403.html', status=403)
def handler404_view(request, exception=None):
    return render(request, '404.html', status=404)
def handler500_view(request):
    return render(request, '500.html', status=500)
def handler502_view(request):
    return render(request, '502.html', status=502)
def handler503_view(request):
    return render(request, '503.html', status=503)

handler400 = 'core.urls.handler400_view'
handler403 = 'core.urls.handler403_view'
handler404 = 'core.urls.handler404_view'
handler500 = 'core.urls.handler500_view'

from core.views import (
    liste_groupes, ajouter_groupe, detail_groupe,
    modifier_groupe, supprimer_groupe,
)

urlpatterns = [
    path('', include('utilisateurs.urls')),
    path('groupes/', ajouter_groupe, name='ajouter_groupe'),
    path('groupes/liste/', liste_groupes, name='liste_groupes'),
    path('groupes/detail/<int:pk>/', detail_groupe, name='detail_groupe'),
    path('groupes/modifier/<int:pk>/', modifier_groupe, name='modifier_groupe'),
    path('groupes/supprimer/<int:pk>/', supprimer_groupe, name='supprimer_groupe'),
    path('entreprise/', include('entreprise.urls')),
    path('portes-entree/', include('entreprise.porte-entree.urls')),
    path('departements/', include('entreprise.departement.urls')),
    path('creneaux-semaine/', include('entreprise.creneaux-semaine.urls')),
    path('personnel/', include('entreprise.personnel.urls')),
    path('visites/', include('visites.urls')),
    path('incidents/', include('incidents.urls')),
    path('objets-oublies/', include('objets_oublies.urls')),
    path('liste-noire/', include('liste_noire.urls')),
    path('alertes/', include('alertes_et_notifications.urls')),
    path('admin/', admin.site.urls),
    path('api/', api.urls),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT) if hasattr(settings, 'STATIC_ROOT') and settings.STATIC_ROOT else []
