# products/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('categorias/', views.CategoriaListCreateView.as_view(), name='lista_categorias'),
    path('categorias/<int:pk>/', views.CategoriaDetailView.as_view(), name='detalle_categoria'),
    path('marcas/', views.MarcaListCreateView.as_view(), name='lista_marcas'),
    path('marcas/<int:pk>/', views.MarcaDetailView.as_view(), name='detalle_marca'),
    path('productos/', views.ProductoListCreateView.as_view(), name='lista_productos'),
    path('productos/<slug:slug>/', views.ProductoDetailView.as_view(), name='detalle_producto'),
    path('inventario/', views.InventarioListView.as_view(), name='lista_inventario'),
    path('inventario/<int:pk>/', views.InventarioUpdateView.as_view(), name='actualizar_inventario'),
    path('inventario/bajo-stock/', views.productos_bajo_stock, name='productos_bajo_stock'),
    path('favoritos/', views.FavoritoListCreateView.as_view(), name='lista_favoritos'),
    path('favoritos/<int:pk>/', views.FavoritoDestroyView.as_view(), name='eliminar_favorito'),

    path('productos/<int:producto_id>/activar/', views.activar_producto, name='activar_producto'),
    path('productos/<int:producto_id>/desactivar/', views.desactivar_producto, name='desactivar_producto'),
    path('inventario/<int:producto_id>/ajustar-stock/', views.ajustar_stock, name='ajustar_stock'),
    path('inventario/<int:producto_id>/aumentar-stock/', views.aumentar_stock, name='aumentar_stock'),
    path('inventario/alertas-bajo-stock/', views.alertas_bajo_stock, name='alertas_bajo_stock'),
    path('favoritos/verificar/<int:producto_id>/', views.verificar_favorito, name='verificar_favorito'),
    # NUEVAS URLs para envíos
    path('categorias-envio/', views.CategoriaEnvioListCreateView.as_view(), name='lista_categorias_envio'),
    path('categorias-envio/<int:pk>/', views.CategoriaEnvioDetailView.as_view(), name='detalle_categoria_envio'),
    path('calcular-envio/', views.calcular_envio_carrito, name='calcular_envio'),
    path('actualizar-categorias-envio/', views.actualizar_categorias_envio_masivo, name='actualizar_categorias_envio'),
    
]