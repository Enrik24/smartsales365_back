# ai_models/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('modelos/', views.ModeloIAListView.as_view(), name='lista_modelos'),
    path('modelos/entrenar-ventas/', views.entrenar_modelo_ventas, name='entrenar_modelo_ventas'),
    path('predicciones/', views.PrediccionVentasListView.as_view(), name='lista_predicciones'),
    path('predicciones/generar/', views.generar_prediccion_ventas, name='generar_prediccion'),
    path('metricas/ventas/', views.obtener_metricas_ventas, name='metricas_ventas'),

    path('modelos/<int:modelo_id>/actualizar/', views.actualizar_modelo, name='actualizar_modelo'),
]