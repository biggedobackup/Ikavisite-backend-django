from django.urls import path
from . import views

urlpatterns = [
    path('marquer-lu/<int:pk>/', views.marquer_lu, name='marquer_alerte_lu'),
    path('marquer-tout-lu/', views.marquer_tout_lu, name='marquer_tout_lu'),
]
