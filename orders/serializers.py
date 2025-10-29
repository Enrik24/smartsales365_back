# orders/serializers.py
from rest_framework import serializers
from .models import (Carrito, DetalleCarrito, Pedido, DetallePedido, 
                    Comprobante, Pago, Devolucion, SeguimientoPedido)
from products.serializers import ProductoSerializer

class DetalleCarritoSerializer(serializers.ModelSerializer):
    producto_detalle = ProductoSerializer(source='producto', read_only=True)
    subtotal = serializers.SerializerMethodField()
    
    class Meta:
        model = DetalleCarrito
        fields = ('id', 'carrito', 'producto', 'producto_detalle', 'cantidad', 'subtotal')
    
    def get_subtotal(self, obj):
        return obj.producto.precio * obj.cantidad

class CarritoSerializer(serializers.ModelSerializer):
    items = DetalleCarritoSerializer(many=True, read_only=True, source='detallecarrito_set')
    total = serializers.SerializerMethodField()
    
    class Meta:
        model = Carrito
        fields = ('id', 'usuario', 'fecha_ultima_actualizacion', 'items', 'total')
    
    def get_total(self, obj):
        total = 0
        for item in obj.detallecarrito_set.all():
            total += item.producto.precio * item.cantidad
        return total

class DetallePedidoSerializer(serializers.ModelSerializer):
    producto_detalle = ProductoSerializer(source='producto', read_only=True)
    subtotal = serializers.SerializerMethodField()
    
    class Meta:
        model = DetallePedido
        fields = ('id', 'pedido', 'producto', 'producto_detalle', 'cantidad', 
                'precio_unitario_en_el_momento', 'subtotal')
    
    def get_subtotal(self, obj):
        return obj.precio_unitario_en_el_momento * obj.cantidad

class PedidoSerializer(serializers.ModelSerializer):
    detalles = DetallePedidoSerializer(many=True, read_only=True, source='detallepedido_set')
    usuario_nombre = serializers.CharField(source='usuario.get_full_name', read_only=True)
    
    class Meta:
        model = Pedido
        fields = ('id', 'usuario', 'usuario_nombre', 'fecha_pedido', 'monto_total',
                'estado_pedido', 'direccion_envio', 'direccion_facturacion',
                'numero_seguimiento', 'detalles')

class PedidoCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pedido
        fields = ('direccion_envio', 'direccion_facturacion')

class ComprobanteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comprobante
        fields = '__all__'

class PagoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pago
        fields = '__all__'

class DevolucionSerializer(serializers.ModelSerializer):
    producto_detalle = ProductoSerializer(source='producto', read_only=True)
    
    class Meta:
        model = Devolucion
        fields = '__all__'

class SeguimientoPedidoSerializer(serializers.ModelSerializer):
    class Meta:
        model = SeguimientoPedido
        fields = '__all__'