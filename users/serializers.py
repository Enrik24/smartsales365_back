# users/serializers.py
from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import Usuario, Rol, Permiso, UsuarioRol, RolPermiso

class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ('id', 'email', 'nombre', 'apellido', 
                'telefono', 'direccion', 'estado', 'fecha_registro', 
                'ultimo_login', 'is_active', 'is_staff')
        read_only_fields = ('fecha_registro', 'ultimo_login', 'is_active', 'is_staff')

class UsuarioRegistroSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = Usuario
        fields = ('email', 'password','confirm_password', 'nombre', 'apellido',
                'telefono', 'direccion')
        extra_kwargs = {
            'email': {'required': True},
            'nombre': {'required': True},
            'apellido': {'required': True},
        }
    
    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError("Las contraseñas no coinciden")
        return data
    
    def create(self, validated_data):
        validated_data.pop('confirm_password')
        password = validated_data.pop('password')
        usuario = Usuario(**validated_data)
        usuario.set_password(password)
        usuario.save()
        return usuario

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()  # Cambiar de username a email
    password = serializers.CharField()

    def validate(self, data):
        email = data.get('email')
        password = data.get('password')
        
        if email and password:
            # Buscar usuario por email en lugar de username
            try:
                user = Usuario.objects.get(email=email)
                if user.check_password(password):
                    if user.is_active:
                        # Actualizar último login
                        from django.utils import timezone
                        user.ultimo_login = timezone.now()
                        user.save()
                        
                        data['user'] = user
                    else:
                        raise serializers.ValidationError('Cuenta desactivada')
                else:
                    raise serializers.ValidationError('Credenciales inválidas')
            except Usuario.DoesNotExist:
                raise serializers.ValidationError('Credenciales inválidas')
        else:
            raise serializers.ValidationError('Debe proporcionar email y password')
        
        return data
    
class CambioPasswordSerializer(serializers.Serializer):
    password_actual = serializers.CharField(required=True)
    nuevo_password = serializers.CharField(required=True, min_length=6)
    confirmar_password = serializers.CharField(required=True, min_length=6)
    
    def validate(self, data):
        if data['nuevo_password'] != data['confirmar_password']:
            raise serializers.ValidationError("Los nuevos passwords no coinciden")
        return data

class RecuperarPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)


class RolSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rol
        fields = '__all__'

class PermisoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permiso
        fields = '__all__'

class UsuarioRolSerializer(serializers.ModelSerializer):
    usuario_email = serializers.EmailField(source='usuario.email', read_only=True)
    rol_nombre = serializers.CharField(source='rol.nombre_rol', read_only=True)
    
    class Meta:
        model = UsuarioRol
        fields = '__all__'

class RolPermisoSerializer(serializers.ModelSerializer):
    rol_nombre = serializers.CharField(source='rol.nombre_rol', read_only=True)
    permiso_nombre = serializers.CharField(source='permiso.nombre_permiso', read_only=True)
    
    class Meta:
        model = RolPermiso
        fields = '__all__'