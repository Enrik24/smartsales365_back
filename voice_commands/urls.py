# voice_commands/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('procesar/', views.procesar_comando, name='procesar_comando'),
    path('voz/historial/', views.ComandoVozListView.as_view(), name='historial_voz'),
    path('texto/historial/', views.ComandoTextoListView.as_view(), name='historial_texto'),
    path('sugerencias/', views.obtener_comandos_frecuentes, name='comandos_frecuentes'),
]