# orders/models.py
from django.db import models
from users.models import Usuario
from products.models import Producto, Inventario
from django.utils import timezone

class Carrito(models.Model):
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE)
    fecha_ultima_actualizacion = models.DateTimeField(auto_now=True)
    
    def vaciar(self):
        """Vaciar carrito"""
        self.detallecarrito_set.all().delete()
        self.save()
    
    def calcular_total(self):
        """Calcular total del carrito"""
        detalles = self.detallecarrito_set.select_related('producto')
        total = sum(detalle.producto.precio * detalle.cantidad for detalle in detalles)
        return total
    
    def quitar_producto(self, producto_id):
        """Quitar producto del carrito"""
        self.detallecarrito_set.filter(producto_id=producto_id).delete()
        self.save()
        
    class Meta:
        db_table = 'carrito'

class DetalleCarrito(models.Model):
    carrito = models.ForeignKey(Carrito, on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.IntegerField(default=1)
    
    class Meta:
        db_table = 'detalle_carrito'
        unique_together = ('carrito', 'producto')

class Pedido(models.Model):
    ESTADOS_PEDIDO = (
        ('pendiente', 'Pendiente'),
        ('confirmado', 'Confirmado'),
        ('en_proceso', 'En Proceso'),
        ('enviado', 'Enviado'),
        ('entregado', 'Entregado'),
        ('cancelado', 'Cancelado'),
    )
    
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    fecha_pedido = models.DateTimeField(auto_now_add=True)
    monto_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    estado_pedido = models.CharField(max_length=50, choices=ESTADOS_PEDIDO, default='pendiente')
    direccion_envio = models.TextField()
    direccion_facturacion = models.TextField(null=True, blank=True)
    numero_seguimiento = models.CharField(max_length=100, unique=True, null=True, blank=True)
    monto_total = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal_productos = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    costo_envio = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    monto_impuestos = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    def confirmar(self):
        """Confirmar pedido"""
        self.estado_pedido = 'confirmado'
        self.save()
        
        # Registrar en seguimiento
        SeguimientoPedido.objects.create(
            pedido=self,
            estado_anterior='pendiente',
            estado_nuevo='confirmado',
            comentario='Pedido confirmado'
        )
    
    def cancelar(self, motivo=""):
        """Cancelar pedido"""
        self.estado_pedido = 'cancelado'
        self.save()
        
        # Registrar en seguimiento
        SeguimientoPedido.objects.create(
            pedido=self,
            estado_anterior=self.estado_pedido,
            estado_nuevo='cancelado',
            comentario=f'Pedido cancelado: {motivo}'
        )
    
    def calcular_monto_total(self):
        """Recalcula el monto total del pedido"""
        detalles = self.detallepedido_set.all()
        total = sum(detalle.cantidad * detalle.precio_unitario_en_el_momento for detalle in detalles)
        self.monto_total = total
        self.save()
        return total
    
    class Meta:
        db_table = 'pedidos'

class DetallePedido(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.IntegerField()
    precio_unitario_en_el_momento = models.DecimalField(max_digits=10, decimal_places=2)
    
    @classmethod
    def quitar_producto(cls, detalle_id):
        """Quitar producto de pedido"""
        try:
            detalle = cls.objects.get(id=detalle_id)
            pedido = detalle.pedido
            detalle.delete()
            
            # Recalcular total
            pedido.calcular_monto_total()
            return True
        except cls.DoesNotExist:
            return False
        
    class Meta:
        db_table = 'detalle_pedido'

class Comprobante(models.Model):
    TIPOS_COMPROBANTE = (
        ('factura', 'Factura'),
        ('boleta', 'Boleta'),
    )
    
    pedido = models.OneToOneField(Pedido, on_delete=models.CASCADE)
    tipo_comprobante = models.CharField(max_length=50, choices=TIPOS_COMPROBANTE)
    url_pdf = models.URLField(max_length=512, null=True, blank=True)
    fecha_emision = models.DateField(auto_now_add=True)
    
    @classmethod
    def generar_comprobante(cls, pedido_id):
        """Generar comprobante para pedido"""
        pedido = Pedido.objects.get(id=pedido_id)
        
        # Determinar tipo de comprobante basado en monto
        tipo = 'factura' if pedido.monto_total > 700 else 'boleta'
        
        comprobante, created = cls.objects.get_or_create(
            pedido=pedido,
            defaults={
                'tipo_comprobante': tipo,
                'url_pdf': f'/comprobantes/{tipo}_{pedido_id}.pdf'
            }
        )
        
        return comprobante
    
    @classmethod
    def obtener_por_pedido(cls, pedido_id):
        """Obtener comprobante por pedido"""
        try:
            return cls.objects.get(pedido_id=pedido_id)
        except cls.DoesNotExist:
            return None

    class Meta:
        db_table = 'comprobantes'

class Pago(models.Model):
    ESTADOS_PAGO = (
        ('pendiente', 'Pendiente'),
        ('exitoso', 'Exitoso'),
        ('fallido', 'Fallido'),
        ('reembolsado', 'Reembolsado'),
    )
    
    METODOS_PAGO = (
        ('card', 'Tarjeta'),
        ('qr', 'QR'),
    )
    
    pedido = models.OneToOneField(Pedido, on_delete=models.CASCADE)
    stripe_payment_intent_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    stripe_checkout_session_id = models.CharField(max_length=255, null=True, blank=True)
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    moneda = models.CharField(max_length=3, default='BOB')
    estado_pago = models.CharField(max_length=50, choices=ESTADOS_PAGO, default='pendiente')
    fecha_pago = models.DateTimeField(null=True, blank=True)
    metodo_pago = models.CharField(max_length=50, choices=METODOS_PAGO, null=True, blank=True)
    respuesta_stripe = models.JSONField(null=True, blank=True)
    
    def confirmar(self, payment_intent_id):
        """Confirmar pago exitoso"""
        self.stripe_payment_intent_id = payment_intent_id
        self.estado_pago = 'exitoso'
        self.fecha_pago = timezone.now()
        self.save()
        
        # Confirmar pedido asociado
        self.pedido.confirmar()
    
    def fallar(self, motivo):
        """Marcar pago como fallido"""
        self.estado_pago = 'fallido'
        self.respuesta_stripe = {'error': motivo}
        self.save()
    
    def reembolsar(self):
        """Procesar reembolso"""
        # En producción, aquí se integraría con Stripe para el reembolso
        self.estado_pago = 'reembolsado'
        self.save()
        return True

    class Meta:
        db_table = 'pagos'

class Devolucion(models.Model):
    ESTADOS_DEVOLUCION = (
        ('solicitada', 'Solicitada'),
        ('en_revision', 'En Revisión'),
        ('aprobada', 'Aprobada'),
        ('rechazada', 'Rechazada'),
        ('reembolsada', 'Reembolsada'),
    )

    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE)
    producto = models.ForeignKey('products.Producto', on_delete=models.CASCADE)  # ✅ AÑADIDO
    motivo = models.TextField()
    estado = models.CharField(max_length=50, choices=ESTADOS_DEVOLUCION, default='solicitada')
    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    
    def aprobar(self):
        """Aprobar devolución"""
        self.estado = 'aprobada'
        self.save()
        
        # Procesar reembolso automáticamente
        self.procesar_reembolso()
    
    def rechazar(self, motivo=""):
        """Rechazar devolución"""
        self.estado = 'rechazada'
        if motivo:
            self.motivo += f"\n\nRechazado: {motivo}"
        self.save()
    
    def procesar_reembolso(self):
        """Procesar reembolso de la devolución"""
        try:
            # Buscar el pago asociado al pedido
            pago = Pago.objects.get(pedido=self.pedido)
            
            # Procesar reembolso (en producción integrar con Stripe)
            pago.reembolsar()
            
            # Aumentar stock del producto
            inventario = Inventario.objects.get(producto=self.producto)
            detalle_pedido = DetallePedido.objects.get(
                pedido=self.pedido, 
                producto=self.producto
            )
            inventario.aumentar_stock(detalle_pedido.cantidad)
            
            self.estado = 'reembolsada'
            self.save()
            
            return True
        except (Pago.DoesNotExist, Inventario.DoesNotExist, DetallePedido.DoesNotExist) as e:
            return False
    
    @classmethod
    def solicitar_devolucion(cls, datos_devolucion):
        """Solicitar nueva devolución"""
        return cls.objects.create(**datos_devolucion)
    
    class Meta:
        db_table = 'devoluciones'

class SeguimientoPedido(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE)
    estado_anterior = models.CharField(max_length=50)
    estado_nuevo = models.CharField(max_length=50)
    fecha_cambio = models.DateTimeField(auto_now_add=True)
    comentario = models.TextField(null=True, blank=True)

    @classmethod
    def obtener_historial_completo(cls, pedido_id):
        """Obtener historial completo de seguimiento"""
        return cls.objects.filter(pedido_id=pedido_id).order_by('fecha_cambio')
    
    class Meta:
        db_table = 'seguimiento_pedido'