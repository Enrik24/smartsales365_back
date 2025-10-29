# notifications/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('notificaciones/', views.NotificacionListView.as_view(), name='lista_notificaciones'),
    path('notificaciones/no-leidas/', views.NotificacionNoLeidasView.as_view(), name='notificaciones_no_leidas'),
    path('notificaciones/marcar-leida/', views.marcar_como_leida, name='marcar_leida'),
    path('notificaciones/marcar-todas-leidas/', views.marcar_todas_leidas, name='marcar_todas_leidas'),
    path('preferencias/', views.PreferenciaNotificacionView.as_view(), name='preferencias_notificaciones'),
    path('sistema/crear/', views.crear_notificacion_sistema, name='crear_notificacion_sistema'),
]