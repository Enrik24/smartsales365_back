# users/views.py
from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.core.mail import send_mail
from django.conf import settings
from .models import Usuario, Rol, Permiso, UsuarioRol, RolPermiso
from .serializers import (UsuarioSerializer, UsuarioRegistroSerializer, 
                        LoginSerializer, CambioPasswordSerializer,
                        RecuperarPasswordSerializer, RolSerializer, 
                        PermisoSerializer, UsuarioRolSerializer, 
                        RolPermisoSerializer)

@api_view(['POST'])
@permission_classes([AllowAny])
def registro_usuario(request):
    serializer = UsuarioRegistroSerializer(data=request.data)
    if serializer.is_valid():
        usuario = serializer.save()
        refresh = RefreshToken.for_user(usuario)
        return Response({
            'usuario': UsuarioSerializer(usuario).data,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([AllowAny])
def login_usuario(request):
    serializer = LoginSerializer(data=request.data)
    if serializer.is_valid():
        usuario = serializer.validated_data['user']
        refresh = RefreshToken.for_user(usuario)
        return Response({
            'usuario': UsuarioSerializer(usuario).data,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        })
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_usuario(request):
    try:
        refresh_token = request.data["refresh_token"]
        token = RefreshToken(refresh_token)
        token.blacklist()
        return Response(status=status.HTTP_205_RESET_CONTENT)
    except Exception as e:
        return Response(status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cambiar_password(request):
    serializer = CambioPasswordSerializer(data=request.data)
    if serializer.is_valid():
        usuario = request.user
        
        # Verificar password actual
        if not usuario.check_password(serializer.validated_data['password_actual']):
            return Response(
                {'error': 'La contraseña actual es incorrecta'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Cambiar password
        usuario.set_password(serializer.validated_data['nuevo_password'])
        usuario.save()
        
        return Response({'mensaje': 'Contraseña cambiada exitosamente'})
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([AllowAny])
def recuperar_password(request):
    serializer = RecuperarPasswordSerializer(data=request.data)
    if serializer.is_valid():
        email = serializer.validated_data['email']
        
        try:
            usuario = Usuario.objects.get(email=email)
            
            # Generar token para recuperación
            token_generator = PasswordResetTokenGenerator()
            token = token_generator.make_token(usuario)
            uid = urlsafe_base64_encode(force_bytes(usuario.pk))
            
            # Enviar email (simulación)
            reset_url = f"{settings.FRONTEND_URL}/reset-password/{uid}/{token}/"
            
            # En producción, enviar email real
            print(f"URL para resetear password: {reset_url}")
            
            return Response({
                'mensaje': 'Se ha enviado un enlace de recuperación a su email'
            })
            
        except Usuario.DoesNotExist:
            # Por seguridad, no revelar si el email existe o no
            return Response({
                'mensaje': 'Si el email existe, se ha enviado un enlace de recuperación'
            })
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def asignar_rol_usuario(request):
    """Asigna un rol a un usuario"""
    usuario_id = request.data.get('usuario_id')
    rol_id = request.data.get('rol_id')
    
    if not usuario_id or not rol_id:
        return Response({'error': 'usuario_id y rol_id son requeridos'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # CORRECCIÓN: Usar el método del modelo Usuario
        usuario = Usuario.objects.get(id=usuario_id)
        usuario.asignar_rol(rol_id)
        return Response({'mensaje': 'Rol asignado correctamente'})
    except Usuario.DoesNotExist:
        return Response({'error': 'Usuario no encontrado'}, status=status.HTTP_404_NOT_FOUND)
    except Rol.DoesNotExist:
        return Response({'error': 'Rol no encontrado'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def revocar_rol_usuario(request):
    """Revoca un rol de un usuario"""
    usuario_id = request.data.get('usuario_id')
    rol_id = request.data.get('rol_id')
    
    if not usuario_id or not rol_id:
        return Response({'error': 'usuario_id y rol_id son requeridos'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # CORRECCIÓN: Usar el método del modelo Usuario
        usuario = Usuario.objects.get(id=usuario_id)
        usuario.revocar_rol(rol_id)
        return Response({'mensaje': 'Rol revocado correctamente'})
    except Usuario.DoesNotExist:
        return Response({'error': 'Usuario no encontrado'}, status=status.HTTP_404_NOT_FOUND)
    except Rol.DoesNotExist:
        return Response({'error': 'Rol no encontrado'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obtener_roles_usuario(request, usuario_id):
    """Obtiene los roles de un usuario"""
    try:
        # CORRECCIÓN: Usar el método del modelo Usuario
        usuario = Usuario.objects.get(id=usuario_id)
        roles = usuario.obtener_roles()
        serializer = RolSerializer(roles, many=True)
        return Response(serializer.data)
    except Usuario.DoesNotExist:
        return Response({'error': 'Usuario no encontrado'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def verificar_permiso_usuario(request, usuario_id):
    """Verifica si un usuario tiene un permiso"""
    nombre_permiso = request.query_params.get('permiso')
    
    if not nombre_permiso:
        return Response({'error': 'El parámetro permiso es requerido'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # CORRECCIÓN: Usar el método del modelo Usuario
        usuario = Usuario.objects.get(id=usuario_id)
        tiene_permiso = usuario.tiene_permiso(nombre_permiso)
        return Response({'tiene_permiso': tiene_permiso})
    except Usuario.DoesNotExist:
        return Response({'error': 'Usuario no encontrado'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def desactivar_usuario(request, usuario_id):
    """Desactiva un usuario"""
    try:
        usuario = Usuario.objects.get(id=usuario_id)
        usuario.desactivar()
        return Response({'mensaje': 'Usuario desactivado correctamente'})
    except Usuario.DoesNotExist:
        return Response({'error': 'Usuario no encontrado'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def activar_usuario(request, usuario_id):
    """Activa un usuario"""
    try:
        usuario = Usuario.objects.get(id=usuario_id)
        usuario.activar()
        return Response({'mensaje': 'Usuario activado correctamente'})
    except Usuario.DoesNotExist:
        return Response({'error': 'Usuario no encontrado'}, status=status.HTTP_404_NOT_FOUND)

class UsuarioListView(generics.ListAPIView):
    queryset = Usuario.objects.all()
    serializer_class = UsuarioSerializer
    permission_classes = [IsAuthenticated]

class UsuarioDetailView(generics.RetrieveUpdateAPIView):
    queryset = Usuario.objects.all()
    serializer_class = UsuarioSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        if self.kwargs.get('pk') == 'me':
            return self.request.user
        return super().get_object()

class RolListCreateView(generics.ListCreateAPIView):
    queryset = Rol.objects.all()
    serializer_class = RolSerializer
    permission_classes = [IsAuthenticated]
    
    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated()]
        return [IsAuthenticated()]

class PermisoListCreateView(generics.ListCreateAPIView):
    queryset = Permiso.objects.all()
    serializer_class = PermisoSerializer
    permission_classes = [IsAuthenticated]

class UsuarioRolListCreateView(generics.ListCreateAPIView):
    queryset = UsuarioRol.objects.all()
    serializer_class = UsuarioRolSerializer
    permission_classes = [IsAuthenticated]

class RolPermisoListCreateView(generics.ListCreateAPIView):
    queryset = RolPermiso.objects.all()
    serializer_class = RolPermisoSerializer
    permission_classes = [IsAuthenticated]