from django.urls import path
from . import views

urlpatterns = [
    path('', views.entreprise_view, name='entreprise'),
]
