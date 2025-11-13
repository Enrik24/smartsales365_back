# products/models.py
from django.db import models
from users.models import Usuario
from cloudinary.models import CloudinaryField
from django.utils.text import slugify

class Categoria(models.Model):
    nombre_categoria = models.CharField(max_length=100)
    categoria_padre = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    
    class Meta:
        db_table = 'categorias'

class Marca(models.Model):
    nombre_marca = models.CharField(max_length=100, unique=True)
    description = models.TextField(null=True, blank=True)
    class Meta:
        db_table = 'marcas'

class Producto(models.Model):
    ESTADOS = (
        ('activo', 'Activo'),
        ('inactivo', 'Inactivo'),
        ('agotado', 'Agotado'),
    )
    
    sku = models.CharField(max_length=100, unique=True)
    nombre = models.CharField(max_length=255)
    descripcion = models.TextField(null=True, blank=True)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    categoria = models.ForeignKey(Categoria, on_delete=models.SET_NULL, null=True, blank=True)
    marca = models.ForeignKey(Marca, on_delete=models.SET_NULL, null=True, blank=True)
    imagen_url = models.URLField(max_length=512, null=True, blank=True)
    ficha_tecnica_url = models.URLField(max_length=512, null=True, blank=True)
    estado = models.CharField(max_length=50, choices=ESTADOS, default='activo')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    slug = models.SlugField(max_length=255, unique=True)  # Nuevo
    precio_original = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # Nuevo
    # Específicos para electrodomésticos
    modelo = models.CharField(max_length=100, null=True, blank=True)  # Nuevo
    voltaje = models.CharField(max_length=50, null=True, blank=True)  # Nuevo
    garantia_meses = models.IntegerField(null=True, blank=True)  # Nuevo
    eficiencia_energetica = models.CharField(max_length=10, null=True, blank=True)  # Nuevo
    color = models.CharField(max_length=100, null=True, blank=True)  # Nuevo
    # Dimensiones y envío
    peso = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)  # Nuevo
    alto = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)  # Nuevo
    ancho = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)  # Nuevo
    profundidad = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)  # Nuevo
    # Negocio
    costo = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # Nuevo
    envio_gratis = models.BooleanField(default=False)  # Nuevo
    destacado = models.BooleanField(default=False)  # Nuevo
    fecha_actualizacion = models.DateTimeField(auto_now=True)  # Nuevo
    

    def activar(self):
        """Activar producto"""
        self.estado = 'activo'
        self.save()
    
    def desactivar(self):
        """Desactivar producto"""
        self.estado = 'inactivo'
        self.save()
    
    def marcar_agotado(self):
        """Marcar producto como agotado"""
        self.estado = 'agotado'
        self.save()

    def save(self, *args, **kwargs):
        if not self.slug:
            # Usar nombre + SKU que ya es único
            self.slug = slugify(f"{self.nombre} {self.sku}")
        super().save(*args, **kwargs)
        
    class Meta:
        db_table = 'productos'

class Inventario(models.Model):
    producto = models.OneToOneField(Producto, on_delete=models.CASCADE)
    stock_actual = models.IntegerField(default=0)
    stock_minimo = models.IntegerField(default=0, null=True, blank=True)
    ultima_actualizacion = models.DateTimeField(auto_now=True)
    
    def ajustar_stock(self, nueva_cantidad):
        """Establece un nuevo nivel de stock"""
        self.stock_actual = nueva_cantidad
        self.save()
    
    def reducir_stock(self, cantidad):
        """Reduce el stock"""
        if self.stock_actual >= cantidad:
            self.stock_actual -= cantidad
            self.save()
            return True
        return False
    
    def aumentar_stock(self, cantidad):
        """Aumenta el stock"""
        self.stock_actual += cantidad
        self.save()
        return True
    
    def verificar_disponibilidad(self, cantidad):
        """Verifica si hay stock suficiente"""
        return self.stock_actual >= cantidad
    
    def necesita_reabastecimiento(self):
        """Verifica si el stock está por debajo del mínimo"""
        return self.stock_actual <= self.stock_minimo

    @classmethod
    def generar_alertas_bajo_stock(cls):
        """Genera alertas para productos con stock bajo"""
        inventarios_bajos = cls.objects.filter(
            stock_actual__lte=models.F('stock_minimo')
        ).select_related('producto')
            
        alertas = []
        for inventario in inventarios_bajos:
            alertas.append({
                'producto_id': inventario.producto.id,
                'producto_nombre': inventario.producto.nombre,
                'stock_actual': inventario.stock_actual,
                'stock_minimo': inventario.stock_minimo,
                'diferencia': inventario.stock_minimo - inventario.stock_actual
            })
            
        return alertas


    class Meta:
        db_table = 'inventario'

class Favorito(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    fecha_agregado = models.DateTimeField(auto_now_add=True)
    
    @classmethod
    def esta_en_favoritos(cls, usuario_id, producto_id):
        """Verificar si producto está en favoritos"""
        return cls.objects.filter(
            usuario_id=usuario_id, 
            producto_id=producto_id
        ).exists()
    
    class Meta:
        db_table = 'favoritos'
        unique_together = ('usuario', 'producto')
