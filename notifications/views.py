# notifications/views.py
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Notificacion, PreferenciaNotificacionUsuario
from .serializers import (NotificacionSerializer, PreferenciaNotificacionSerializer,
                         MarcarLeidaSerializer)

class NotificacionListView(generics.ListAPIView):
    serializer_class = NotificacionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Notificacion.objects.filter(usuario=self.request.user).order_by('-fecha_creacion')

class NotificacionNoLeidasView(generics.ListAPIView):
    serializer_class = NotificacionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Notificacion.objects.filter(
            usuario=self.request.user,
            estado__in=['pendiente', 'enviada']
        ).order_by('-fecha_creacion')

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def marcar_como_leida(request):
    serializer = MarcarLeidaSerializer(data=request.data)
    if serializer.is_valid():
        try:
            notificacion = Notificacion.objects.get(
                id=serializer.validated_data['notificacion_id'],
                usuario=request.user
            )
            notificacion.estado = 'leida'
            notificacion.save()
            
            return Response({'mensaje': 'Notificación marcada como leída'})
            
        except Notificacion.DoesNotExist:
            return Response({'error': 'Notificación no encontrada'}, status=status.HTTP_404_NOT_FOUND)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def marcar_todas_leidas(request):
    Notificacion.objects.filter(
        usuario=request.user,
        estado__in=['pendiente', 'enviada']
    ).update(estado='leida')
    
    return Response({'mensaje': 'Todas las notificaciones marcadas como leídas'})

class PreferenciaNotificacionView(generics.ListCreateAPIView):
    serializer_class = PreferenciaNotificacionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return PreferenciaNotificacionUsuario.objects.filter(usuario=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(usuario=self.request.user)

@api_view(['POST'])
def crear_notificacion_sistema(request):
    """Endpoint para que otras apps creen notificaciones"""
    if request.method == 'POST':
        usuario_id = request.data.get('usuario_id')
        tipo = request.data.get('tipo', 'sistema')
        titulo = request.data.get('titulo')
        mensaje = request.data.get('mensaje')
        datos_adicionales = request.data.get('datos_adicionales')
        
        if not all([usuario_id, titulo, mensaje]):
            return Response({'error': 'Faltan campos requeridos'}, status=status.HTTP_400_BAD_REQUEST)
        
        notificacion = Notificacion.objects.create(
            usuario_id=usuario_id,
            tipo=tipo,
            titulo=titulo,
            mensaje=mensaje,
            datos_adicionales=datos_adicionales,
            estado='enviada'
        )
        
        return Response(NotificacionSerializer(notificacion).data, status=status.HTTP_201_CREATED)