# orders/views.py
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.db import transaction
from django.utils import timezone
from django.shortcuts import get_object_or_404
from .models import (Carrito, DetalleCarrito, Pedido, DetallePedido, 
                    Comprobante, Pago, Devolucion, SeguimientoPedido)
from .serializers import (CarritoSerializer, DetalleCarritoSerializer,
                        PedidoSerializer, PedidoCreateSerializer,
                        DetallePedidoSerializer, ComprobanteSerializer,
                        PagoSerializer, DevolucionSerializer, 
                        SeguimientoPedidoSerializer)

class CarritoDetailView(generics.RetrieveAPIView):
    serializer_class = CarritoSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        carrito, created = Carrito.objects.get_or_create(usuario=self.request.user)
        return carrito

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def agregar_al_carrito(request):
    carrito, created = Carrito.objects.get_or_create(usuario=request.user)
    producto_id = request.data.get('producto_id')
    cantidad = request.data.get('cantidad', 1)
    
    detalle, created = DetalleCarrito.objects.get_or_create(
        carrito=carrito,
        producto_id=producto_id,
        defaults={'cantidad': cantidad}
    )
    
    if not created:
        detalle.cantidad += cantidad
        detalle.save()
    
    serializer = DetalleCarritoSerializer(detalle)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def actualizar_cantidad_carrito(request, producto_id):
    carrito = get_object_or_404(Carrito, usuario=request.user)
    detalle = get_object_or_404(DetalleCarrito, carrito=carrito, producto_id=producto_id)
    
    cantidad = request.data.get('cantidad')
    if cantidad is None:
        return Response({'error': 'La cantidad es requerida'}, status=status.HTTP_400_BAD_REQUEST)
    
    if cantidad <= 0:
        detalle.delete()
        return Response({'message': 'Producto eliminado del carrito'}, status=status.HTTP_200_OK)
    
    detalle.cantidad = cantidad
    detalle.save()
    
    serializer = DetalleCarritoSerializer(detalle)
    return Response(serializer.data)
# =============================================================================
# VISTAS DE PEDIDOS
# =============================================================================
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@transaction.atomic
def crear_pedido_desde_carrito(request):
    carrito = get_object_or_404(Carrito, usuario=request.user)
    items_carrito = carrito.detallecarrito_set.select_related('producto').all()
    
    if not items_carrito:
        return Response({'error': 'El carrito está vacío'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Verificar stock disponible
    for item in items_carrito:
        if item.producto.inventario.stock_actual < item.cantidad:
            return Response(
                {'error': f'Stock insuficiente para {item.producto.nombre}'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    # Crear pedido
    pedido_serializer = PedidoCreateSerializer(data=request.data)
    if pedido_serializer.is_valid():
        pedido = pedido_serializer.save(usuario=request.user)
        monto_total = 0
        
        # Crear detalles del pedido y actualizar inventario
        for item in items_carrito:
            DetallePedido.objects.create(
                pedido=pedido,
                producto=item.producto,
                cantidad=item.cantidad,
                precio_unitario_en_el_momento=item.producto.precio
            )
            monto_total += item.producto.precio * item.cantidad
            
            # Actualizar inventario
            inventario = item.producto.inventario
            inventario.stock_actual -= item.cantidad
            inventario.save()
        
        pedido.monto_total = monto_total
        pedido.save()
        
        # Vaciar carrito
        carrito.detallecarrito_set.all().delete()
        
        # Crear registro de seguimiento
        SeguimientoPedido.objects.create(
            pedido=pedido,
            estado_anterior='pendiente',
            estado_nuevo='pendiente',
            comentario='Pedido creado exitosamente'
        )
        
        serializer = PedidoSerializer(pedido)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    return Response(pedido_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class PedidoListView(generics.ListAPIView):
    serializer_class = PedidoSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if self.request.user.is_staff:
            return Pedido.objects.select_related('usuario').prefetch_related('detallepedido_set').all()
        return Pedido.objects.filter(usuario=self.request.user).select_related('usuario').prefetch_related('detallepedido_set')

class PedidoDetailView(generics.RetrieveAPIView):
    serializer_class = PedidoSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if self.request.user.is_staff:
            return Pedido.objects.select_related('usuario').prefetch_related('detallepedido_set').all()
        return Pedido.objects.filter(usuario=self.request.user).select_related('usuario').prefetch_related('detallepedido_set')


@api_view(['POST'])
@permission_classes([IsAdminUser])
def actualizar_estado_pedido(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id)
    nuevo_estado = request.data.get('estado')
    comentario = request.data.get('comentario', '')
    
    if not nuevo_estado:
        return Response({'error': 'El estado es requerido'}, status=status.HTTP_400_BAD_REQUEST)
    
    estado_anterior = pedido.estado_pedido
    pedido.estado_pedido = nuevo_estado
    pedido.save()
    
    # Registrar en seguimiento
    SeguimientoPedido.objects.create(
        pedido=pedido,
        estado_anterior=estado_anterior,
        estado_nuevo=nuevo_estado,
        comentario=comentario
    )
    
    serializer = PedidoSerializer(pedido)
    return Response(serializer.data)
# =============================================================================
# NUEVAS VISTAS DE GESTIÓN DE PEDIDOS
# =============================================================================
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def confirmar_pedido(request, pedido_id):
    """Confirmar pedido"""
    try:
        pedido = Pedido.objects.get(id=pedido_id)
        pedido.confirmar()
        return Response({'mensaje': 'Pedido confirmado correctamente'})
    except Pedido.DoesNotExist:
        return Response({'error': 'Pedido no encontrado'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancelar_pedido(request, pedido_id):
    """Cancelar pedido"""
    motivo = request.data.get('motivo', '')
    try:
        pedido = Pedido.objects.get(id=pedido_id)
        pedido.cancelar(motivo)
        return Response({'mensaje': 'Pedido cancelado correctamente'})
    except Pedido.DoesNotExist:
        return Response({'error': 'Pedido no encontrado'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def quitar_producto_pedido(request, detalle_id):
    """Quitar producto de pedido"""
    try:
        success = DetallePedido.quitar_producto(detalle_id)
        if success:
            return Response({'mensaje': 'Producto eliminado del pedido'})
        else:
            return Response({'error': 'Detalle no encontrado'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generar_comprobante_pedido(request, pedido_id):
    """Generar comprobante para pedido"""
    try:
        comprobante = Comprobante.generar_comprobante(pedido_id)
        serializer = ComprobanteSerializer(comprobante)
        return Response(serializer.data)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obtener_comprobante_pedido(request, pedido_id):
    """Obtener comprobante de pedido"""
    comprobante = Comprobante.obtener_por_pedido(pedido_id)
    if comprobante:
        serializer = ComprobanteSerializer(comprobante)
        return Response(serializer.data)
    else:
        return Response({'error': 'Comprobante no encontrado'}, status=status.HTTP_404_NOT_FOUND)

class DevolucionListCreateView(generics.ListCreateAPIView):
    serializer_class = DevolucionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if self.request.user.is_staff:
            return Devolucion.objects.select_related('pedido', 'producto').all()
        return Devolucion.objects.filter(pedido__usuario=self.request.user).select_related('pedido', 'producto')
    
    def perform_create(self, serializer):
        serializer.save()
# =============================================================================
# VISTAS DE PAGOS
# =============================================================================
@api_view(['POST'])
@permission_classes([IsAdminUser])
def procesar_pago_stripe(request, pedido_id):
    # Esta es una implementación básica - integrar con Stripe API
    pedido = get_object_or_404(Pedido, id=pedido_id)
    
    # Simulación de pago con Stripe
    # En producción, aquí se integraría con la API de Stripe
    pago = Pago.objects.create(
        pedido=pedido,
        stripe_payment_intent_id=f"pi_simulado_{pedido.id}",
        monto=pedido.monto_total,
        estado_pago='exitoso',
        fecha_pago=timezone.now(),
        metodo_pago=request.data.get('metodo_pago', 'tarjeta_credito'),
        respuesta_stripe={'status': 'succeeded', 'simulado': True}
    )
    
    # Actualizar estado del pedido
    pedido.estado_pedido = 'confirmado'
    pedido.save()
    
    # Crear comprobante
    Comprobante.objects.create(
        pedido=pedido,
        tipo_comprobante='factura' if pedido.monto_total > 700 else 'boleta'
    )
    
    serializer = PagoSerializer(pago)
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAdminUser])
def confirmar_pago_stripe(request):
    """Confirmar pago desde webhook de Stripe"""
    stripe_payment_intent_id = request.data.get('stripe_payment_intent_id')
    
    if not stripe_payment_intent_id:
        return Response({'error': 'stripe_payment_intent_id es requerido'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        pago = Pago.objects.get(stripe_payment_intent_id=stripe_payment_intent_id)
        pago.confirmar(stripe_payment_intent_id)
        return Response({'mensaje': 'Pago confirmado correctamente'})
    except Pago.DoesNotExist:
        return Response({'error': 'Pago no encontrado'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
@permission_classes([IsAdminUser])
def reembolsar_pago(request, pago_id):
    """Reembolsar pago"""
    try:
        pago = Pago.objects.get(id=pago_id)
        success = pago.reembolsar()
        if success:
            return Response({'mensaje': 'Reembolso procesado correctamente'})
        else:
            return Response({'error': 'Error en el reembolso'}, status=status.HTTP_400_BAD_REQUEST)
    except Pago.DoesNotExist:
        return Response({'error': 'Pago no encontrado'}, status=status.HTTP_404_NOT_FOUND)
    
# =============================================================================
#  VIEWS DE DEVOLUCIONES
# =============================================================================
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def solicitar_devolucion(request):
    """Solicitar nueva devolución"""
    serializer = DevolucionSerializer(data=request.data)
    if serializer.is_valid():
        try:
            # Verificar que el usuario es dueño del pedido
            pedido = Pedido.objects.get(
                id=serializer.validated_data['pedido'].id,
                usuario=request.user
            )
            
            devolucion = Devolucion.solicitar_devolucion(serializer.validated_data)
            return Response(
                DevolucionSerializer(devolucion).data, 
                status=status.HTTP_201_CREATED
            )
        except Pedido.DoesNotExist:
            return Response(
                {'error': 'Pedido no encontrado o no autorizado'}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAdminUser])
def aprobar_devolucion(request, devolucion_id):
    """Aprobar devolución"""
    try:
        devolucion = Devolucion.objects.get(id=devolucion_id)
        devolucion.aprobar()
        return Response({'mensaje': 'Devolución aprobada y reembolso procesado'})
    except Devolucion.DoesNotExist:
        return Response({'error': 'Devolución no encontrada'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
@permission_classes([IsAdminUser])
def rechazar_devolucion(request, devolucion_id):
    """Rechazar devolución"""
    motivo = request.data.get('motivo', '')
    try:
        devolucion = Devolucion.objects.get(id=devolucion_id)
        devolucion.rechazar(motivo)
        return Response({'mensaje': 'Devolución rechazada'})
    except Devolucion.DoesNotExist:
        return Response({'error': 'Devolución no encontrada'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
@permission_classes([IsAdminUser])
def procesar_reembolso_devolucion(request, devolucion_id):
    """Procesar reembolso manual para devolución"""
    try:
        devolucion = Devolucion.objects.get(id=devolucion_id)
        success = devolucion.procesar_reembolso()
        if success:
            return Response({'mensaje': 'Reembolso procesado correctamente'})
        else:
            return Response({'error': 'Error al procesar el reembolso'}, status=status.HTTP_400_BAD_REQUEST)
    except Devolucion.DoesNotExist:
        return Response({'error': 'Devolución no encontrada'}, status=status.HTTP_404_NOT_FOUND)
    
# =============================================================================
# AGREGAR VIEWS DE CARRITO
# =============================================================================
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def vaciar_carrito(request):
    """Vaciar carrito del usuario"""
    try:
        carrito = Carrito.objects.get(usuario=request.user)
        carrito.vaciar()
        return Response({'mensaje': 'Carrito vaciado correctamente'})
    except Carrito.DoesNotExist:
        return Response({'error': 'Carrito no encontrado'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def quitar_producto_carrito(request, producto_id):
    """Quitar producto del carrito"""
    try:
        carrito = Carrito.objects.get(usuario=request.user)
        carrito.quitar_producto(producto_id)
        return Response({'mensaje': 'Producto eliminado del carrito'})
    except Carrito.DoesNotExist:
        return Response({'error': 'Carrito no encontrado'}, status=status.HTTP_404_NOT_FOUND)
# =============================================================================
# AGREGAR VIEWS DE SEGUIMIENTO
# =============================================================================
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obtener_historial_seguimiento(request, pedido_id):
    """Obtener historial completo de seguimiento de pedido"""
    try:
        # Verificar que el usuario tiene acceso al pedido
        if request.user.is_staff:
            pedido = Pedido.objects.get(id=pedido_id)
        else:
            pedido = Pedido.objects.get(id=pedido_id, usuario=request.user)
        
        historial = SeguimientoPedido.obtener_historial_completo(pedido_id)
        serializer = SeguimientoPedidoSerializer(historial, many=True)
        return Response(serializer.data)
    except Pedido.DoesNotExist:
        return Response({'error': 'Pedido no encontrado'}, status=status.HTTP_404_NOT_FOUND)