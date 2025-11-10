# products/serializers.py

from rest_framework import serializers
from .models import Categoria, Marca, Producto, Inventario, Favorito
import cloudinary
import cloudinary.uploader

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
    stock_minimo = serializers.IntegerField(source='inventario.stock_minimo', read_only=True)

    class Meta:
        model = Producto
        fields = ('id', 'sku', 'nombre', 'descripcion', 'precio', 'categoria', 
                'marca', 'categoria_nombre', 'marca_nombre', 'imagen_url', 
                'ficha_tecnica_url', 'estado', 'fecha_creacion', 'stock_actual','stock_minimo')

class ProductoCreateSerializer(serializers.ModelSerializer):
    stock_inicial = serializers.IntegerField(write_only=True, required=False, default=0)
    stock_minimo = serializers.IntegerField(write_only=True, required=False, default=0)
    imagen_file = serializers.FileField(write_only=True, required=False)
    ficha_tecnica_file = serializers.FileField(write_only=True, required=False)

    class Meta:
        model = Producto
        fields = (
            'sku', 'nombre', 'descripcion', 'precio',
            'categoria', 'marca', 'estado',
            'stock_inicial', 'stock_minimo',
            'imagen_file', 'ficha_tecnica_file'
        )
    
    """ def create(self, validated_data):
        stock_inicial = validated_data.pop('stock_inicial', 0)
        stock_minimo = validated_data.pop('stock_minimo', 0)

        imagen_file = validated_data.pop('imagen_file', None)
        ficha_file = validated_data.pop('ficha_tecnica_file', None)

        
        producto = Producto.objects.create(**validated_data)

        # Subir imagen
        if imagen_file:
            upload_result = cloudinary.uploader.upload(imagen_file)
            producto.imagen_url = upload_result.get('secure_url')

        # Subir PDF
        if ficha_file:
            upload_result = cloudinary.uploader.upload(ficha_file, resource_type='raw')
            producto.ficha_tecnica_url = upload_result.get('secure_url')

        producto.save()
        
        # Crear registro de inventario automáticamente
        Inventario.objects.create(
            producto=producto,
            stock_actual=stock_inicial,
            stock_minimo=stock_minimo
        )
        
        return producto """
    def create(self, validated_data):
        stock_inicial = validated_data.pop('stock_inicial', 0)
        stock_minimo = validated_data.pop('stock_minimo', 0)

        imagen_file = validated_data.pop('imagen_file', None)
        ficha_file = validated_data.pop('ficha_tecnica_file', None)

        #Extraemos los objetos Categoria y Marca validados
        categoria_obj = validated_data.pop('categoria', None)
        marca_obj = validated_data.pop('marca', None)

        # Crear el producto primero
        producto = Producto.objects.create(**validated_data)

        if categoria_obj:
            producto.categoria = categoria_obj
        if marca_obj:
            producto.marca = marca_obj

        # Subir imagen con manejo de errores
        if imagen_file:
            try:
                upload_result = cloudinary.uploader.upload(
                    imagen_file,
                    folder="productos/imagenes",
                    resource_type="image",
                    transformation=[
                        {'width': 800, 'height': 600, 'crop': 'limit'},
                        {'quality': 'auto'}
                    ]
                )
                producto.imagen_url = upload_result.get('secure_url')
            except Exception as e:
                raise serializers.ValidationError({
                    'imagen_file': f'Error al subir la imagen: {str(e)}'
                })

        # Subir PDF con manejo de errores
        if ficha_file:
            try:
                upload_result = cloudinary.uploader.upload(
                    ficha_file,
                    folder="productos/fichas_tecnicas",
                    resource_type="raw",
                    format="pdf"
                )
                producto.ficha_tecnica_url = upload_result.get('secure_url')
            except Exception as e:
                raise serializers.ValidationError({
                    'ficha_tecnica_file': f'Error al subir el PDF: {str(e)}'
                })

        producto.save()
        
        # Crear registro de inventario automáticamente
        Inventario.objects.create(
            producto=producto,
            stock_actual=stock_inicial,
            stock_minimo=stock_minimo
        )
        
        return producto
    
    def update(self, instance, validated_data):
        imagen_file = validated_data.pop('imagen_file', None)
        ficha_file = validated_data.pop('ficha_tecnica_file', None)
        
        # Actualizar campos del modelo
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        # Subir nueva imagen si se proporciona
        if imagen_file:
            try:
                # Eliminar imagen anterior si existe
                if instance.imagen_url:
                    public_id = instance.imagen_url.split('/')[-1].split('.')[0]
                    cloudinary.uploader.destroy(f"productos/imagenes/{public_id}")
                
                # Subir nueva imagen
                upload_result = cloudinary.uploader.upload(
                    imagen_file,
                    folder="productos/imagenes",
                    resource_type="image",
                    transformation=[
                        {'width': 800, 'height': 600, 'crop': 'limit'},
                        {'quality': 'auto'}
                    ]
                )
                instance.imagen_url = upload_result.get('secure_url')
            except Exception as e:
                raise serializers.ValidationError({
                    'imagen_file': f'Error al subir la imagen: {str(e)}'
                })
        
        # Subir nuevo PDF si se proporciona
        if ficha_file:
            try:
                # Eliminar PDF anterior si existe
                if instance.ficha_tecnica_url:
                    public_id = instance.ficha_tecnica_url.split('/')[-1].split('.')[0]
                    cloudinary.uploader.destroy(f"productos/fichas_tecnicas/{public_id}", resource_type="raw")
                
                # Subir nuevo PDF
                upload_result = cloudinary.uploader.upload(
                    ficha_file,
                    folder="productos/fichas_tecnicas",
                    resource_type="raw",
                    format="pdf"
                )
                instance.ficha_tecnica_url = upload_result.get('secure_url')
            except Exception as e:
                raise serializers.ValidationError({
                    'ficha_tecnica_file': f'Error al subir el PDF: {str(e)}'
                })
        
        instance.save()
        return instance
    

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