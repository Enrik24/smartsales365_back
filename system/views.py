# system/views.py
from rest_framework import generics, permissions, status
from django_filters.rest_framework import DjangoFilterBackend
from .models import BitacoraSistema, ConfiguracionSistema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from .serializers import (BitacoraSistemaSerializer, BitacoraSistemaCreateSerializer, 
                        ConfiguracionSistemaSerializer)

class BitacoraSistemaListView(generics.ListAPIView):
    queryset = BitacoraSistema.objects.select_related('usuario').all()
    serializer_class = BitacoraSistemaSerializer
    permission_classes = [permissions.IsAdminUser]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['estado', 'usuario']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filtrar por fecha si se proporciona
        fecha_desde = self.request.query_params.get('fecha_desde')
        fecha_hasta = self.request.query_params.get('fecha_hasta')
        accion = self.request.query_params.get('accion')
        
        if fecha_desde:
            queryset = queryset.filter(fecha_accion__gte=fecha_desde)
        if fecha_hasta:
            queryset = queryset.filter(fecha_accion__lte=fecha_hasta)
        if accion:
            queryset = queryset.filter(accion__icontains=accion)
        
        return queryset

class BitacoraSistemaCreateView(generics.CreateAPIView):
    """View para que el frontend registre acciones en la bitácora"""
    queryset = BitacoraSistema.objects.all()
    serializer_class = BitacoraSistemaCreateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def perform_create(self, serializer):
        # Asignar usuario automáticamente si no se proporciona
        if not serializer.validated_data.get('usuario'):
            serializer.validated_data['usuario'] = self.request.user
        serializer.save()

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def registrar_accion_bitacora(request):
    """
    Endpoint simplificado para que el frontend registre acciones
    """
    accion = request.data.get('accion')
    estado = request.data.get('estado', 'exitoso')
    ip = request.data.get('ip')
    
    if not accion:
        return Response(
            {'error': 'El campo "accion" es requerido'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Validar estado
    estados_validos = ['exitoso', 'fallido', 'advertencia']
    if estado not in estados_validos:
        return Response(
            {'error': f'Estado debe ser uno de: {", ".join(estados_validos)}'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Registrar acción
    bitacora = BitacoraSistema.registrar_accion(
        usuario=request.user,
        accion=accion,
        estado=estado,
        ip=ip or get_client_ip(request)
    )
    
    serializer = BitacoraSistemaSerializer(bitacora)
    return Response(serializer.data, status=status.HTTP_201_CREATED)

def get_client_ip(request):
    """Obtener IP real del cliente"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

class ConfiguracionSistemaListCreateView(generics.ListCreateAPIView):
    queryset = ConfiguracionSistema.objects.all()
    serializer_class = ConfiguracionSistemaSerializer
    permission_classes = [permissions.IsAdminUser]

class ConfiguracionSistemaDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ConfiguracionSistema.objects.all()
    serializer_class = ConfiguracionSistemaSerializer
    permission_classes = [permissions.IsAdminUser]
    lookup_field = 'clave'

# =============================================================================
# AGREGAR VIEWS DE CONFIGURACIÓN
# =============================================================================
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obtener_configuracion_valor(request, clave):
    """Obtener valor de configuración específica"""
    valor = ConfiguracionSistema.obtener_configuracion(clave)
    if valor is not None:
        return Response({'clave': clave, 'valor': valor})
    else:
        return Response({'error': 'Configuración no encontrada'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
@permission_classes([IsAdminUser])
def establecer_configuracion_valor(request):
    """Establecer o actualizar configuración"""
    clave = request.data.get('clave')
    valor = request.data.get('valor')
    descripcion = request.data.get('descripcion')
    
    if not clave or not valor:
        return Response(
            {'error': 'clave y valor son requeridos'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    config = ConfiguracionSistema.establecer_configuracion(clave, valor, descripcion)
    serializer = ConfiguracionSistemaSerializer(config)
    return Response(serializer.data)
