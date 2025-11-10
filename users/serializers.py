# users/serializers.py
from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import Usuario, Rol, Permiso, UsuarioRol, RolPermiso

class UsuarioSerializer(serializers.ModelSerializer):
    roles = serializers.SerializerMethodField()

    class Meta:
        model = Usuario
        # fields = ('id', 'email', 'nombre', 'apellido', 
        #         'telefono', 'direccion', 'estado', 'fecha_registro', 
        #         'ultimo_login', 'is_active', 'is_staff')
        fields = ('id', 'email', 'nombre', 'apellido', 
                'telefono', 'direccion', 'estado', 'fecha_registro', 
                'ultimo_login', 'is_active', 'is_staff', 'roles')
        read_only_fields = ('fecha_registro', 'ultimo_login', 'is_active', 'is_staff')

    def get_roles(self, obj):
        """
        Obtiene los roles del usuario y los serializa.
        """
        roles = obj.obtener_roles()
        return RolSerializer(roles, many=True).data

class PerfilUsuarioUpdateSerializer(serializers.ModelSerializer):
    roles = serializers.PrimaryKeyRelatedField(
        many=True, 
        queryset=Rol.objects.all(), 
        required=False
    )

    class Meta:
        model = Usuario
        fields = ('nombre', 'apellido', 'telefono', 'direccion', 'roles')

    def update(self, instance, validated_data):
        # Actualizar roles si se proporcionan
        if 'roles' in validated_data:
            roles_data = validated_data.pop('roles')
            # Eliminar roles actuales
            instance.usuariorol_set.all().delete()
            # Asignar nuevos roles
            for rol in roles_data:
                UsuarioRol.objects.create(usuario=instance, rol=rol)
        
        # Actualizar los otros campos del perfil
        return super().update(instance, validated_data)

class UsuarioRegistroSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True, min_length=6)
    rol = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = Usuario
        fields = ('email', 'password','confirm_password', 'nombre', 'apellido',
                'telefono', 'direccion', 'rol')
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
        rol_nombre = validated_data.pop('rol', None)
        validated_data.pop('confirm_password')
        password = validated_data.pop('password')
        
        usuario = Usuario(**validated_data)
        usuario.set_password(password)
        usuario.save()

        if rol_nombre:
            try:
                rol = Rol.objects.get(nombre_rol=rol_nombre)
                usuario.asignar_rol(rol)
            except Rol.DoesNotExist:
                # Opcional: manejar el caso en que el rol no existe.
                # Por ahora, simplemente no se asigna y no se genera error.
                pass
        
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
    permisos = serializers.PrimaryKeyRelatedField(
        many=True, 
        queryset=Permiso.objects.all(), 
        required=False
    )

    class Meta:
        model = Rol
        fields = ['id', 'nombre_rol', 'descripcion', 'permisos']

    def create(self, validated_data):
        permisos_data = validated_data.pop('permisos', None)
        rol = Rol.objects.create(**validated_data)
        if permisos_data:
            rol.permisos.set(permisos_data)
        return rol

    def update(self, instance, validated_data):
        permisos_data = validated_data.pop('permisos', None)
        instance = super().update(instance, validated_data)
        if permisos_data is not None:
            instance.permisos.set(permisos_data)
        return instance

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