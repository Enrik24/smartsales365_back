# products/serializers.py
from rest_framework import serializers
from .models import Categoria, Marca, Producto, Inventario, Favorito

class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = '__all__'

class MarcaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Marca
        fields = '__all__'

class ProductoSerializer(serializers.ModelSerializer):
    categoria_nombre = serializers.CharField(source='categoria.nombre_categoria', read_only=True)
    marca_nombre = serializers.CharField(source='marca.nombre_marca', read_only=True)
    stock_actual = serializers.IntegerField(source='inventario.stock_actual', read_only=True)
    
    class Meta:
        model = Producto
        fields = ('id', 'sku', 'nombre', 'descripcion', 'precio', 'categoria', 
                'marca', 'categoria_nombre', 'marca_nombre', 'imagen_url', 
                'ficha_tecnica_url', 'estado', 'fecha_creacion', 'stock_actual')

class ProductoCreateSerializer(serializers.ModelSerializer):
    stock_inicial = serializers.IntegerField(write_only=True, required=False, default=0)
    stock_minimo = serializers.IntegerField(write_only=True, required=False, default=0)
    
    class Meta:
        model = Producto
        fields = ('sku', 'nombre', 'descripcion', 'precio', 'categoria', 
                'marca', 'imagen_url', 'ficha_tecnica_url', 'estado', 
                'stock_inicial', 'stock_minimo')
    
    def create(self, validated_data):
        stock_inicial = validated_data.pop('stock_inicial', 0)
        stock_minimo = validated_data.pop('stock_minimo', 0)
        
        producto = Producto.objects.create(**validated_data)
        
        # Crear registro de inventario automáticamente
        Inventario.objects.create(
            producto=producto,
            stock_actual=stock_inicial,
            stock_minimo=stock_minimo
        )
        
        return producto

class InventarioSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True)
    producto_sku = serializers.CharField(source='producto.sku', read_only=True)
    
    class Meta:
        model = Inventario
        fields = '__all__'

class FavoritoSerializer(serializers.ModelSerializer):
    producto_detalle = ProductoSerializer(source='producto', read_only=True)
    
    class Meta:
        model = Favorito
        fields = ('id', 'usuario', 'producto', 'producto_detalle', 'fecha_agregado')