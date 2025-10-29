# users/models.py
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils.translation import gettext_lazy as _

class UsuarioManager(BaseUserManager):
    """Manager personalizado para el modelo Usuario con email como campo principal"""
    
    def create_user(self, email, password=None, **extra_fields):
        """Crea y guarda un usuario con el email y contraseña dados"""
        if not email:
            raise ValueError('El email debe ser proporcionado')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def obtener_por_email(self, email):
        """Obtener usuario por email"""
        try:
            return self.get(email=email)
        except Usuario.DoesNotExist:
            return None

    def create_superuser(self, email, password=None, **extra_fields):
        """Crea y guarda un superusuario con el email y contraseña dados"""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)


class Usuario(AbstractUser):
    # Hacer que el email sea el campo único principal
    username = None
    email = models.EmailField(_('email address'), unique=True)

    # Campos específicos según el diagrama UML
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    telefono = models.CharField(max_length=20, null=True, blank=True)
    direccion = models.CharField(max_length=255, null=True, blank=True)
    estado = models.CharField(max_length=50, default='activo')
    fecha_registro = models.DateTimeField(auto_now_add=True)
    ultimo_login = models.DateTimeField(null=True, blank=True)
    
    # Establecer email como campo de identificación
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nombre', 'apellido']

    objects = UsuarioManager()
    
    class Meta:
        db_table = 'usuarios'
    
    def __str__(self):
        return self.email
    
    def get_full_name(self):
        return f"{self.nombre} {self.apellido}"
    
    def get_short_name(self):
        return self.nombre
    
    def save(self, *args, **kwargs):
        # Sincronizar first_name, last_name con nombre, apellido
        self.first_name = self.nombre
        self.last_name = self.apellido
        
        # Sincronizar last_login con ultimo_login
        if self.ultimo_login:
            self.last_login = self.ultimo_login
        
        super().save(*args, **kwargs)

    def actualizar_ultimo_login(self):
        """Actualizar último login"""
        from django.utils import timezone
        self.ultimo_login = timezone.now()
        self.save()
    
    def desactivar(self):
        """Desactivar usuario"""
        self.estado = 'inactivo'
        self.is_active = False
        self.save()
    
    def activar(self):
        """Activar usuario"""
        self.estado = 'activo'
        self.is_active = True
        self.save()

    # MÉTODOS DE ROLES Y PERMISOS PARA EL USUARIO
    def asignar_rol(self, rol):
        """Asigna un rol a este usuario"""
        if isinstance(rol, int):
            rol = Rol.objects.get(id=rol)
        UsuarioRol.objects.get_or_create(usuario=self, rol=rol)
        return True

    def revocar_rol(self, rol):
        """Quita un rol a este usuario"""
        if isinstance(rol, int):
            rol = Rol.objects.get(id=rol)
        UsuarioRol.objects.filter(usuario=self, rol=rol).delete()
        return True

    def obtener_roles(self):
        """Devuelve la lista de roles del usuario"""
        usuario_roles = UsuarioRol.objects.filter(usuario=self).select_related('rol')
        return [ur.rol for ur in usuario_roles]

    def tiene_permiso(self, nombre_permiso):
        """Verifica si el usuario tiene un permiso específico"""
        # Obtener todos los roles del usuario
        usuario_roles = UsuarioRol.objects.filter(usuario=self).values_list('rol_id', flat=True)
        
        # Buscar el permiso
        permiso = Permiso.obtener_por_nombre(nombre_permiso)
        if not permiso:
            return False
        
        # Verificar si algún rol tiene el permiso
        return RolPermiso.objects.filter(
            rol_id__in=usuario_roles, 
            permiso=permiso
        ).exists()


class Rol(models.Model):
    nombre_rol = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(null=True, blank=True)
    
    def __str__(self):
        return self.nombre_rol
    
    def asignar_permiso(self, permiso):
        """Asignar permiso a rol"""
        if isinstance(permiso, int):
            permiso = Permiso.objects.get(id=permiso)
        RolPermiso.objects.get_or_create(rol=self, permiso=permiso)
        return True
    
    def revocar_permiso(self, permiso):
        """Revocar permiso de rol"""
        if isinstance(permiso, int):
            permiso = Permiso.objects.get(id=permiso)
        RolPermiso.objects.filter(rol=self, permiso=permiso).delete()
        return True
    
    def obtener_permisos(self):
        """Obtener todos los permisos del rol"""
        return [rp.permiso for rp in self.rolpermiso_set.select_related('permiso')]
    
    def tiene_permiso(self, nombre_permiso):
        """Verifica si el rol tiene un permiso específico"""
        permiso = Permiso.obtener_por_nombre(nombre_permiso)
        if not permiso:
            return False
        return RolPermiso.objects.filter(rol=self, permiso=permiso).exists()
    
    class Meta:
        db_table = 'roles'


class Permiso(models.Model):
    nombre_permiso = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.nombre_permiso

    @classmethod
    def obtener_por_nombre(cls, nombre_permiso):
        """Obtener permiso por nombre"""
        try:
            return cls.objects.get(nombre_permiso=nombre_permiso)
        except cls.DoesNotExist:
            return None

    class Meta:
        db_table = 'permisos'


class UsuarioRol(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    rol = models.ForeignKey(Rol, on_delete=models.CASCADE)
    
    class Meta:
        db_table = 'usuario_rol'
        unique_together = ('usuario', 'rol')


class RolPermiso(models.Model):
    rol = models.ForeignKey(Rol, on_delete=models.CASCADE)
    permiso = models.ForeignKey(Permiso, on_delete=models.CASCADE)
    
    class Meta:
        db_table = 'rol_permiso'
        unique_together = ('rol', 'permiso')