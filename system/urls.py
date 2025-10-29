# system/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Bitácora
    path('bitacora/', views.BitacoraSistemaListView.as_view(), name='bitacora_lista'),
    path('bitacora/registrar/', views.BitacoraSistemaCreateView.as_view(), name='bitacora_registrar'),
    path('bitacora/accion/', views.registrar_accion_bitacora, name='bitacora_accion_rapida'),
    # Configuraciones del sistema
    path('configuraciones/', views.ConfiguracionSistemaListCreateView.as_view(), name='configuraciones_lista'),
    path('configuraciones/<str:clave>/', views.ConfiguracionSistemaDetailView.as_view(), name='configuracion_detalle'),

    path('configuraciones/<str:clave>/valor/', views.obtener_configuracion_valor, name='obtener_configuracion_valor'),
    path('configuraciones/establecer/', views.establecer_configuracion_valor, name='establecer_configuracion_valor'),
]