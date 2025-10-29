# analytics/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('reportes/', views.ReporteGeneradoListView.as_view(), name='lista_reportes'),
    path('reportes/generar/', views.generar_reporte, name='generar_reporte'),

    path('reportes/<int:reporte_id>/', views.obtener_reporte_por_id, name='obtener_reporte_por_id'),
    path('reportes/usuario/<int:usuario_id>/', views.listar_reportes_usuario, name='reportes_usuario'),
    path('reportes/mis-reportes/', views.listar_reportes_usuario, name='mis_reportes'),
]