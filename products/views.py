# products/views.py
from rest_framework import generics, filters, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, F
from .models import Categoria, Marca, Producto, Inventario, Favorito
from .serializers import (CategoriaSerializer, MarcaSerializer, 
                        ProductoSerializer, ProductoCreateSerializer,
                        InventarioSerializer, FavoritoSerializer)

class CategoriaListCreateView(generics.ListCreateAPIView):
    queryset = Categoria.objects.all()
    serializer_class = CategoriaSerializer
    permission_classes = [IsAuthenticated]
    
    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAdminUser()]
        return [IsAuthenticated()]

class CategoriaDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Categoria.objects.all()
    serializer_class = CategoriaSerializer
    
    def get_permissions(self):
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            return [IsAdminUser()]
        return [IsAuthenticated()]

class MarcaListCreateView(generics.ListCreateAPIView):
    queryset = Marca.objects.all()
    serializer_class = MarcaSerializer
    permission_classes = [IsAuthenticated]
    
    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAdminUser()]
        return [IsAuthenticated()]

class MarcaDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Marca.objects.all()
    serializer_class = MarcaSerializer
    
    def get_permissions(self):
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            return [IsAdminUser()]
        return [IsAuthenticated()]

class ProductoListCreateView(generics.ListCreateAPIView):
    queryset = Producto.objects.select_related('categoria', 'marca', 'inventario')
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['categoria', 'marca', 'estado']
    search_fields = ['nombre', 'descripcion', 'sku']
    ordering_fields = ['precio', 'fecha_creacion', 'nombre']
    
    def get_serializer_class(self):
        if self.request.method in ['POST', 'PUT', 'PATCH']:
            return ProductoCreateSerializer
        return ProductoSerializer
    
    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAdminUser()]
        return [IsAuthenticated()]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        # Filtrar productos activos para usuarios normales
        if not self.request.user.is_staff:
            queryset = queryset.filter(estado='activo')
        return queryset
    

class ProductoDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Producto.objects.select_related('categoria', 'marca', 'inventario')
    serializer_class = ProductoSerializer
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return ProductoCreateSerializer  # Usar el mismo serializer para actualizar
        return ProductoSerializer
    
    def get_permissions(self):
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            return [IsAdminUser()]
        return [IsAuthenticated()]

class InventarioListView(generics.ListAPIView):
    queryset = Inventario.objects.select_related('producto')
    serializer_class = InventarioSerializer
    permission_classes = [IsAdminUser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['stock_actual', 'ubicacion_almacen']
    search_fields = ['producto__nombre', 'producto__sku']

class InventarioUpdateView(generics.UpdateAPIView):
    queryset = Inventario.objects.all()
    serializer_class = InventarioSerializer
    permission_classes = [IsAdminUser]

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def productos_bajo_stock(request):
    """Obtener productos con stock por debajo del mínimo"""
    inventarios = Inventario.objects.filter(
        stock_actual__lt=F('stock_minimo')
    ).select_related('producto')
    serializer = InventarioSerializer(inventarios, many=True)
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAdminUser])
def activar_producto(request, producto_id):
    """Activar producto"""
    try:
        producto = Producto.objects.get(id=producto_id)
        producto.activar()
        return Response({'mensaje': 'Producto activado correctamente'})
    except Producto.DoesNotExist:
        return Response({'error': 'Producto no encontrado'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
@permission_classes([IsAdminUser])
def desactivar_producto(request, producto_id):
    """Desactivar producto"""
    try:
        producto = Producto.objects.get(id=producto_id)
        producto.desactivar()
        return Response({'mensaje': 'Producto desactivado correctamente'})
    except Producto.DoesNotExist:
        return Response({'error': 'Producto no encontrado'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
@permission_classes([IsAdminUser])
def ajustar_stock(request, producto_id):
    """Ajustar stock de producto"""
    try:
        cantidad = request.data.get('cantidad')
        if cantidad is None:
            return Response({'error': 'La cantidad es requerida'}, status=status.HTTP_400_BAD_REQUEST)
        
        inventario = Inventario.objects.get(producto_id=producto_id)
        inventario.ajustar_stock(cantidad)
        
        return Response({
            'mensaje': 'Stock ajustado correctamente',
            'stock_actual': inventario.stock_actual
        })
    except Inventario.DoesNotExist:
        return Response({'error': 'Inventario no encontrado'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
@permission_classes([IsAdminUser])
def aumentar_stock(request, producto_id):
    """Aumentar stock de producto"""
    try:
        cantidad = request.data.get('cantidad')
        if cantidad is None:
            return Response({'error': 'La cantidad es requerida'}, status=status.HTTP_400_BAD_REQUEST)
        
        inventario = Inventario.objects.get(producto_id=producto_id)
        inventario.aumentar_stock(cantidad)
        
        return Response({
            'mensaje': 'Stock aumentado correctamente',
            'stock_actual': inventario.stock_actual
        })
    except Inventario.DoesNotExist:
        return Response({'error': 'Inventario no encontrado'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
@permission_classes([IsAdminUser])
def alertas_bajo_stock(request):
    """Obtener alertas de bajo stock"""
    alertas = Inventario.generar_alertas_bajo_stock()  # <- Ahora es un método de clase
    return Response(alertas)

class FavoritoListCreateView(generics.ListCreateAPIView):
    serializer_class = FavoritoSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Favorito.objects.filter(usuario=self.request.user).select_related('producto')
    
    def perform_create(self, serializer):
        serializer.save(usuario=self.request.user)

class FavoritoDestroyView(generics.DestroyAPIView):
    serializer_class = FavoritoSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Favorito.objects.filter(usuario=self.request.user)
    
# =============================================================================
# AGREGAR VIEW DE FAVORITOS
# =============================================================================
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def verificar_favorito(request, producto_id):
    """Verificar si producto está en favoritos"""
    esta_en_favoritos = Favorito.esta_en_favoritos(request.user.id, producto_id)
    return Response({'esta_en_favoritos': esta_en_favoritos})