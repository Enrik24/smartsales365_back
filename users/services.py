# users/services.py
from .models import Usuario, Rol, Permiso, UsuarioRol, RolPermiso

class ServicioGestionRoles:
    """Servicio para la gestión centralizada de roles y permisos"""
    
    @staticmethod
    def asignar_rol_a_usuario(usuario_id, rol_id):
        """Asigna un rol a un usuario"""
        usuario = Usuario.objects.get(id=usuario_id)
        return usuario.asignar_rol(rol_id)

    @staticmethod
    def revocar_rol_de_usuario(usuario_id, rol_id):
        """Quita un rol a un usuario"""
        usuario = Usuario.objects.get(id=usuario_id)
        return usuario.revocar_rol(rol_id)

    @staticmethod
    def asignar_permiso_a_rol(rol_id, permiso_id):
        """Asigna un permiso a un rol"""
        rol = Rol.objects.get(id=rol_id)
        return rol.asignar_permiso(permiso_id)

    @staticmethod
    def obtener_roles_de_usuario(usuario_id):
        """Devuelve la lista de roles de un usuario"""
        usuario = Usuario.objects.get(id=usuario_id)
        return usuario.obtener_roles()

    @staticmethod
    def usuario_tiene_permiso(usuario_id, nombre_permiso):
        """Verifica si un usuario tiene un permiso específico"""
        usuario = Usuario.objects.get(id=usuario_id)
        return usuario.tiene_permiso(nombre_permiso)