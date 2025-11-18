# management/commands/seed_data.py
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from users.models import Usuario, Rol, Permiso, UsuarioRol


Usuario = get_user_model()

class Command(BaseCommand):
    help = 'Poblar la base de datos con datos de prueba para SmartSales365'

    def handle(self, *args, **options):
        self.stdout.write('Iniciando seeding de datos...')
        
        try:
            with transaction.atomic():
                self.crear_roles_y_permisos()
                self.crear_usuarios()
                
            self.stdout.write(
                self.style.SUCCESS('✅ Seeding completado exitosamente!')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error en seeding: {str(e)}')
            )
            raise

    def crear_roles_y_permisos(self):
        """Crear roles y permisos del sistema"""
        self.stdout.write('Creando roles y permisos...')
        
        # Roles
        rol_admin, created = Rol.objects.get_or_create(
            nombre_rol='administrador',
            defaults={'descripcion': 'Acceso completo al sistema'}
        )
        
        rol_cliente, created = Rol.objects.get_or_create(
            nombre_rol='cliente',
            defaults={'descripcion': 'Usuario final de la tienda'}
        )
        
        # Permisos
        permisos_data = [
            ('gestionar_usuarios', 'Crear, editar, eliminar usuarios'),
            ('gestionar_productos', 'Crear, editar, eliminar productos'),
            ('gestionar_pedidos', 'Gestionar todos los pedidos'),
            ('ver_reportes', 'Acceso a los reportes del sistema'),
            ('gestionar_inventario', 'Gestionar stock e inventario'),
            ('realizar_compra', 'Procesar un pedido como cliente'),
            ('ver_dashboard', 'Ver dashboard administrativo'),
        ]
        
        for nombre_permiso, descripcion in permisos_data:
            permiso, created = Permiso.objects.get_or_create(
                nombre_permiso=nombre_permiso,
                defaults={'descripcion': descripcion}
            )
            
            # Asignar permisos al rol administrador (todos los permisos)
            if nombre_permiso in ['gestionar_usuarios', 'gestionar_productos', 'gestionar_pedidos', 
                                'ver_reportes', 'gestionar_inventario', 'ver_dashboard']:
                rol_admin.asignar_permiso(permiso)
            
            # Asignar permisos al rol cliente
            if nombre_permiso in ['realizar_compra', 'ver_dashboard']:
                rol_cliente.asignar_permiso(permiso)
        
        self.stdout.write('  ✅ Roles y permisos creados')

    def crear_usuarios(self):
        """Crear usuarios de prueba"""
        self.stdout.write('Creando usuarios...')
        
        # Usuario Administrador
        admin_user, created = Usuario.objects.get_or_create(
            email='admin@smartsales365.com',
            defaults={
                'nombre': 'Pedro',
                'apellido': 'García',
                'telefono': '987654321',
                'direccion': 'Calle Falsa 123, Santa Cruz, Bolivia',
                'estado': 'activo',
                'is_staff': True,
                'is_superuser': True
            }
        )
        
        if created:
            admin_user.set_password('Admin123!')
            admin_user.save()
            self.stdout.write('  ✅ Usuario administrador creado: admin@smartsales365.com / Admin123!')
        
        # Asignar rol de administrador
        rol_admin = Rol.objects.get(nombre_rol='administrador')
        UsuarioRol.objects.get_or_create(usuario=admin_user, rol=rol_admin)
        
        # Usuario Cliente
        cliente_user, created = Usuario.objects.get_or_create(
            email='cliente@smartsales365.com',
            defaults={
                'nombre': 'Carlos',
                'apellido': 'Pérez',
                'telefono': '123456789',
                'direccion': 'Av. Principal 456, Santa Cruz, Bolivia',
                'estado': 'activo'
            }
        )
        
        if created:
            cliente_user.set_password('Cliente123!')
            cliente_user.save()
            self.stdout.write('  ✅ Usuario cliente creado: cliente@smartsales365.com / Cliente123!')
        
        # Asignar rol de cliente
        rol_cliente = Rol.objects.get(nombre_rol='cliente')
        UsuarioRol.objects.get_or_create(usuario=cliente_user, rol=rol_cliente)
