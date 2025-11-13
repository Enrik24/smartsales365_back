# orders/views.py
import stripe
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
from django.views import View
from rest_framework import status
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser,AllowAny
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

# Configurar la clave secreta de Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY

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
        # Generar numero_seguimiento
        ultimo_pedido = Pedido.objects.order_by('id').last()
        if ultimo_pedido:
            # Extraer el número del último numero_seguimiento
            try:
                ultimo_numero = int(ultimo_pedido.numero_seguimiento.split('-')[1])
                nuevo_numero = ultimo_numero + 1
            except (AttributeError, IndexError, ValueError):
                # Fallback si el numero_seguimiento no tiene el formato esperado o es nulo
                nuevo_numero = (ultimo_pedido.id or 0) + 1
        else:
            # Si no hay pedidos, empezar desde 1
            nuevo_numero = 1
        
        numero_seguimiento = f'ORD-{nuevo_numero:05d}'

        pedido = pedido_serializer.save(usuario=request.user, numero_seguimiento=numero_seguimiento)
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

class PagoListView(generics.ListAPIView):
    serializer_class = PagoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_staff:
            return Pago.objects.select_related('pedido__usuario').all()
        return Pago.objects.filter(pedido__usuario=self.request.user).select_related('pedido__usuario')

class PagoDetailView(generics.RetrieveAPIView):
    serializer_class = PagoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_staff:
            return Pago.objects.select_related('pedido__usuario').all()
        return Pago.objects.filter(pedido__usuario=self.request.user).select_related('pedido__usuario')

""" @api_view(['POST'])
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
    return Response(serializer.data) """

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def procesar_pago_stripe(request, pedido_id):
    """
    Inicia el proceso de pago con Stripe Checkout Session
    """
    try:
        pedido = get_object_or_404(Pedido, id=pedido_id, usuario=request.user)
        
        # Verificar que el pedido no tenga un pago ya procesado
        if hasattr(pedido, 'pago'):
            pago = pedido.pago
            if pago.estado_pago == 'exitoso':
                return Response(
                    {'error': 'Este pedido ya ha sido pagado'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            elif pago.estado_pago == 'pendiente':
                # Si ya hay un pago pendiente, devolver la URL de la sesión existente
                if pago.stripe_checkout_session_id:
                    try:
                        session = stripe.checkout.Session.retrieve(pago.stripe_checkout_session_id)
                        return Response({
                            'sessionId': session.id,
                            'checkoutUrl': session.url
                        })
                    except stripe.error.StripeError:
                        # Si la sesión ya no es válida, crear una nueva
                        pass
        
        # Crear una nueva Checkout Session
        return crear_checkout_session_stripe(request, pedido_id)
        
    except Exception as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_400_BAD_REQUEST
        )

""" @api_view(['POST'])
@permission_classes([IsAdminUser])
def confirmar_pago_stripe(request):
    Confirmar pago desde webhook de Stripe
    stripe_payment_intent_id = request.data.get('stripe_payment_intent_id')
    
    if not stripe_payment_intent_id:
        return Response({'error': 'stripe_payment_intent_id es requerido'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        pago = Pago.objects.get(stripe_payment_intent_id=stripe_payment_intent_id)
        pago.confirmar(stripe_payment_intent_id)
        return Response({'mensaje': 'Pago confirmado correctamente'})
    except Pago.DoesNotExist:
        return Response({'error': 'Pago no encontrado'}, status=status.HTTP_404_NOT_FOUND) """
# Reemplaza tu función actual con esta
@api_view(['POST'])
@permission_classes([AllowAny]) # <-- CORRECCIÓN: Permitir llamadas externas
def confirmar_pago_stripe(request):
    """
    Webhook de Stripe para confirmar pagos exitosos.
    """
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')

    try:
        # CORRECCIÓN: Verificar la firma para asegurar que la llamada es legítima
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        # Payload inválido
        return Response(status=status.HTTP_400_BAD_REQUEST)
    except stripe.error.SignatureVerificationError as e:
        # Firma inválida (no es una llamada real de Stripe)
        return Response(status=status.HTTP_400_BAD_REQUEST)

    # Manejar el evento de checkout completado
    if event.type == 'checkout.session.completed':
        session = event['data']['object'] # Contiene toda la info de la sesión

        # Obtenemos los IDs que guardamos en los metadatos al crear la sesión
        pedido_id = session['metadata']['pedido_id']
        pago_id = session['metadata']['pago_id']
        stripe_payment_intent_id = session.get('payment_intent') # El ID del pago real

        try:
            # Buscamos el pago por su ID, que es más seguro que por el payment_intent_id
            pago = Pago.objects.get(id=pago_id)
            
            # Usamos tu método del modelo para confirmar
            pago.confirmar(stripe_payment_intent_id)
            
            # O si no tienes ese método, lo actualizas manualmente:
            # pago.estado_pago = 'exitoso'
            # pago.stripe_payment_intent_id = stripe_payment_intent_id
            # pago.fecha_pago = timezone.now()
            # pago.save()

            return Response({'mensaje': 'Pago confirmado correctamente'}, status=status.HTTP_200_OK)

        except Pago.DoesNotExist:
            return Response({'error': 'Pago no encontrado'}, status=status.HTTP_404_NOT_FOUND)
    else:
        # Manejar otros tipos de eventos si es necesario
        return Response({'mensaje': f'Evento no manejado: {event.type}'}, status=status.HTTP_200_OK)


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
    
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def crear_checkout_session_stripe(request, pedido_id):
    """
    Crea una Checkout Session de Stripe para el pedido especificado
    """
    try:
        pedido = get_object_or_404(Pedido, id=pedido_id, usuario=request.user)
        
        # Si el pedido ya está pagado, no se puede volver a pagar.
        if hasattr(pedido, 'pago') and pedido.pago.estado_pago == 'exitoso':
            return Response(
                {'error': 'Este pedido ya ha sido pagado.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # Busca un pago existente o crea uno nuevo.
        # Esto permite reintentar un pago si la sesión anterior falló o expiró.
        pago, created = Pago.objects.get_or_create(
            pedido=pedido,
            defaults={
                'monto': pedido.monto_total,
                'estado_pago': 'pendiente',
                'metodo_pago': 'tarjeta'  # Asignamos el método de pago aquí
            }
        )

        # Si el pago no es nuevo y no está pendiente, algo está mal.
        if not created and pago.estado_pago != 'pendiente':
             # Opcional: podrías querer resetear el estado a 'pendiente' o manejarlo de otra forma
             pago.estado_pago = 'pendiente'
             pago.stripe_checkout_session_id = None
             pago.stripe_payment_intent_id = None
             pago.save()

        # Crear Checkout Session
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[
                {
                    'price_data': {
                        'currency': 'BOB',  # Ajustar según tu moneda
                        'product_data': {
                            'name': f'Pedido #{pedido.id}',
                            'description': f'Productos del pedido #{pedido.id}',
                        },
                        'unit_amount': int(pedido.monto_total * 100),  # Stripe trabaja en centavos
                    },
                    'quantity': 1,
                },
            ],
            mode='payment',
            success_url=f"{settings.FRONTEND_URL}/pago/exitoso?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{settings.FRONTEND_URL}/pago/cancelado?session_id={{CHECKOUT_SESSION_ID}}",
            metadata={
                'pedido_id': pedido.id,
                'pago_id': pago.id
            }
        )
        
        # Guardar el ID de la sesión en el registro de pago
        pago.stripe_checkout_session_id = checkout_session.id
        pago.save()
        
        return Response({
            'sessionId': checkout_session.id,
            'checkoutUrl': checkout_session.url
        })
        
    except Exception as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_400_BAD_REQUEST
        )

@method_decorator(csrf_exempt, name='dispatch')
class StripeWebhookView(View):
    """
    Vista para procesar webhooks de Stripe
    """
    def post(self, request, *args, **kwargs):
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
        event = None

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
        except ValueError as e:
            # Payload inválido
            return JsonResponse({'error': str(e)}, status=400)
        except stripe.error.SignatureVerificationError as e:
            # Firma inválida
            return JsonResponse({'error': str(e)}, status=400)

        # Manejar el evento
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            
            # Obtener el ID del pago desde los metadatos
            pago_id = session['metadata']['pago_id']
            payment_intent_id = session['payment_intent']
            
            try:
                # Actualizar el registro de pago
                pago = Pago.objects.get(id=pago_id)
                pago.confirmar(payment_intent_id)
                
                # Actualizar el estado del pedido
                pedido = pago.pedido
                pedido.estado_pedido = 'confirmado'
                pedido.save()
                
                # Crear comprobante
                from .models import Comprobante
                Comprobante.objects.create(
                    pedido=pedido,
                    tipo_comprobante='factura' if pedido.monto_total > 700 else 'boleta'
                )
                
                return JsonResponse({'status': 'success'}, status=200)
                
            except Pago.DoesNotExist:
                return JsonResponse({'error': 'Pago no encontrado'}, status=404)
        
        elif event['type'] == 'checkout.session.expired':
            session = event['data']['object']
            
            # Obtener el ID del pago desde los metadatos
            pago_id = session['metadata']['pago_id']
            
            try:
                # Actualizar el registro de pago como fallido
                pago = Pago.objects.get(id=pago_id)
                pago.fallar('La sesión de pago expiró')
                
                return JsonResponse({'status': 'success'}, status=200)
                
            except Pago.DoesNotExist:
                return JsonResponse({'error': 'Pago no encontrado'}, status=404)
        
        # ... manejar otros tipos de eventos si es necesario
        
        return JsonResponse({'status': 'success'}, status=200)