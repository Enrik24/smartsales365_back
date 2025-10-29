# orders/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Carrito
    path('carrito/', views.CarritoDetailView.as_view(), name='carrito'),
    path('carrito/agregar/', views.agregar_al_carrito, name='agregar_carrito'),
    path('carrito/actualizar/<int:producto_id>/', views.actualizar_cantidad_carrito, name='actualizar_carrito'),
    
    # Pedidos
    path('pedidos/crear/', views.crear_pedido_desde_carrito, name='crear_pedido'),
    path('pedidos/', views.PedidoListView.as_view(), name='lista_pedidos'),
    path('pedidos/<int:pk>/', views.PedidoDetailView.as_view(), name='detalle_pedido'),
    path('pedidos/<int:pedido_id>/actualizar-estado/', views.actualizar_estado_pedido, name='actualizar_estado_pedido'),
    path('pedidos/<int:pedido_id>/pago/', views.procesar_pago_stripe, name='procesar_pago'),
    
    # Devoluciones
    path('devoluciones/', views.DevolucionListCreateView.as_view(), name='lista_devoluciones'),

    path('pedidos/<int:pedido_id>/confirmar/', views.confirmar_pedido, name='confirmar_pedido'),
    path('pedidos/<int:pedido_id>/cancelar/', views.cancelar_pedido, name='cancelar_pedido'),
    path('detalle-pedido/<int:detalle_id>/quitar/', views.quitar_producto_pedido, name='quitar_producto_pedido'),
    path('pedidos/<int:pedido_id>/generar-comprobante/', views.generar_comprobante_pedido, name='generar_comprobante'),
    path('pedidos/<int:pedido_id>/comprobante/', views.obtener_comprobante_pedido, name='obtener_comprobante'),
    path('pagos/confirmar-stripe/', views.confirmar_pago_stripe, name='confirmar_pago_stripe'),
    path('pagos/<int:pago_id>/reembolsar/', views.reembolsar_pago, name='reembolsar_pago'),
    path('devoluciones/solicitar/', views.solicitar_devolucion, name='solicitar_devolucion'),
    path('devoluciones/<int:devolucion_id>/aprobar/', views.aprobar_devolucion, name='aprobar_devolucion'),
    path('devoluciones/<int:devolucion_id>/rechazar/', views.rechazar_devolucion, name='rechazar_devolucion'),
    path('devoluciones/<int:devolucion_id>/reembolsar/', views.procesar_reembolso_devolucion, name='reembolso_devolucion'),
    path('carrito/vaciar/', views.vaciar_carrito, name='vaciar_carrito'),
    path('carrito/quitar/<int:producto_id>/', views.quitar_producto_carrito, name='quitar_producto_carrito'),
    path('pedidos/<int:pedido_id>/seguimiento/', views.obtener_historial_seguimiento, name='historial_seguimiento'),
]