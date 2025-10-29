# management/commands/seed_data.py
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from users.models import Usuario, Rol, Permiso, UsuarioRol
from products.models import Categoria, Marca, Producto, Inventario
from orders.models import Carrito
from system.models import ConfiguracionSistema
import random
from decimal import Decimal

Usuario = get_user_model()

class Command(BaseCommand):
    help = 'Poblar la base de datos con datos de prueba para SmartSales365'

    def handle(self, *args, **options):
        self.stdout.write('Iniciando seeding de datos...')
        
        try:
            with transaction.atomic():
                self.crear_roles_y_permisos()
                self.crear_usuarios()
                self.crear_categorias_y_marcas()
                self.crear_productos()
                self.crear_configuraciones()
                
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
                'nombre': 'Ana',
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
        
        # Crear carrito para el cliente
        Carrito.objects.get_or_create(usuario=cliente_user)
        
        # Usuarios adicionales de prueba
        usuarios_extra = [
            {
                'email': 'vendedor@smartsales365.com',
                'nombre': 'María',
                'apellido': 'López',
                'password': 'Vendedor123!',
                'telefono': '555123456',
                'direccion': 'Calle Comercio 789, Santa Cruz, Bolivia'
            },
            {
                'email': 'analista@smartsales365.com', 
                'nombre': 'Roberto',
                'apellido': 'Martínez',
                'password': 'Analista123!',
                'telefono': '555654321',
                'direccion': 'Av. Industrial 321, Santa Cruz, Bolivia'
            }
        ]
        
        for user_data in usuarios_extra:
            user, created = Usuario.objects.get_or_create(
                email=user_data['email'],
                defaults={
                    'nombre': user_data['nombre'],
                    'apellido': user_data['apellido'],
                    'telefono': user_data['telefono'],
                    'direccion': user_data['direccion'],
                    'estado': 'activo'
                }
            )
            
            if created:
                user.set_password(user_data['password'])
                user.save()
                Carrito.objects.get_or_create(usuario=user)
                self.stdout.write(f'  ✅ Usuario adicional creado: {user_data["email"]} / {user_data["password"]}')

    def crear_categorias_y_marcas(self):
        """Crear categorías y marcas de productos"""
        self.stdout.write('Creando categorías y marcas...')
        
        # Categorías
        categorias_data = [
            'Línea Blanca',
            'Pequeños Electrodomésticos', 
            'Tecnología',
            'Hogar y Muebles',
            'Deportes y Aire Libre'
        ]
        
        categorias = {}
        for nombre in categorias_data:
            categoria, created = Categoria.objects.get_or_create(nombre_categoria=nombre)
            categorias[nombre] = categoria
        
        # Marcas
        marcas_data = [
            'Samsung',
            'LG',
            'Oster',
            'Philips',
            'Mabe',
            'Whirlpool',
            'Xiaomi',
            'Apple',
            'Sony'
        ]
        
        marcas = {}
        for nombre in marcas_data:
            marca, created = Marca.objects.get_or_create(nombre_marca=nombre)
            marcas[nombre] = marca
        
        self.stdout.write('  ✅ Categorías y marcas creadas')

    def crear_productos(self):
        """Crear productos de prueba con inventario"""
        self.stdout.write('Creando productos...')
        
        # Obtener categorías y marcas
        linea_blanca = Categoria.objects.get(nombre_categoria='Línea Blanca')
        electrodomesticos = Categoria.objects.get(nombre_categoria='Pequeños Electrodomésticos')
        tecnologia = Categoria.objects.get(nombre_categoria='Tecnología')
        
        samsung = Marca.objects.get(nombre_marca='Samsung')
        lg = Marca.objects.get(nombre_marca='LG')
        oster = Marca.objects.get(nombre_marca='Oster')
        philips = Marca.objects.get(nombre_marca='Philips')
        xiaomi = Marca.objects.get(nombre_marca='Xiaomi')
        
        productos_data = [
            {
                'sku': 'REF-SAM-001',
                'nombre': 'Refrigerador Samsung French Door',
                'descripcion': 'Refrigerador de 600Lts con tecnología Digital Inverter, dispensador de agua y hielo.',
                'precio': Decimal('1899.99'),
                'categoria': linea_blanca,
                'marca': samsung,
                'imagen_url': '/media/productos/refrigerador_samsung.jpg',
                'stock_inicial': 15,
                'stock_minimo': 5
            },
            {
                'sku': 'LIC-OST-001',
                'nombre': 'Licuadora Oster Pro 1200',
                'descripcion': 'Licuadora profesional de 1200W con 10 velocidades y jarra de vidrio.',
                'precio': Decimal('89.99'),
                'categoria': electrodomesticos,
                'marca': oster,
                'imagen_url': '/media/productos/licuadora_oster.jpg',
                'stock_inicial': 50,
                'stock_minimo': 10
            },
            {
                'sku': 'TV-LG-055',
                'nombre': 'Smart TV LG 55" 4K UHD',
                'descripcion': 'Televisor 55 pulgadas 4K UHD con WebOS, Alexa y Google Assistant integrados.',
                'precio': Decimal('699.99'),
                'categoria': tecnologia,
                'marca': lg,
                'imagen_url': '/media/productos/tv_lg_55.jpg',
                'stock_inicial': 25,
                'stock_minimo': 8
            },
            {
                'sku': 'MIC-SAM-025',
                'nombre': 'Microondas Samsung 25L',
                'descripcion': 'Microondas de 25 litros con grill y 10 niveles de potencia.',
                'precio': Decimal('149.50'),
                'categoria': electrodomesticos,
                'marca': samsung,
                'imagen_url': '/media/productos/microondas_samsung.jpg',
                'stock_inicial': 30,
                'stock_minimo': 12
            },
            {
                'sku': 'AUD-PHI-450',
                'nombre': 'Auriculares Philips ANC',
                'descripcion': 'Auriculares inalámbricos con cancelación activa de ruido y 30h de batería.',
                'precio': Decimal('129.99'),
                'categoria': tecnologia,
                'marca': philips,
                'imagen_url': '/media/productos/auriculares_philips.jpg',
                'stock_inicial': 100,
                'stock_minimo': 20
            },
            {
                'sku': 'LAV-LG-18',
                'nombre': 'Lavadora LG TurboWash 18kg',
                'descripcion': 'Lavadora de carga frontal 18kg con tecnología TurboWash y 6 motion DD.',
                'precio': Decimal('899.99'),
                'categoria': linea_blanca,
                'marca': lg,
                'imagen_url': '/media/productos/lavadora_lg.jpg',
                'stock_inicial': 12,
                'stock_minimo': 4
            },
            {
                'sku': 'CEL-XIA-12',
                'nombre': 'Smartphone Xiaomi Redmi Note 12',
                'descripcion': 'Smartphone 128GB, 8GB RAM, cámara triple 50MP, pantalla AMOLED 120Hz.',
                'precio': Decimal('299.99'),
                'categoria': tecnologia,
                'marca': xiaomi,
                'imagen_url': '/media/productos/xiaomi_redmi_note12.jpg',
                'stock_inicial': 75,
                'stock_minimo': 15
            },
            {
                'sku': 'ASP-SAM-2000',
                'nombre': 'Aspiradora Samsung Jet 2000',
                'descripcion': 'Aspiradora inalámbrica con tecnología Digital Inverter y 2 baterías.',
                'precio': Decimal('249.99'),
                'categoria': electrodomesticos,
                'marca': samsung,
                'imagen_url': '/media/productos/aspiradora_samsung.jpg',
                'stock_inicial': 40,
                'stock_minimo': 8
            }
        ]
        
        for producto_data in productos_data:
            # Crear producto
            producto, created = Producto.objects.get_or_create(
                sku=producto_data['sku'],
                defaults={
                    'nombre': producto_data['nombre'],
                    'descripcion': producto_data['descripcion'],
                    'precio': producto_data['precio'],
                    'categoria': producto_data['categoria'],
                    'marca': producto_data['marca'],
                    'imagen_url': producto_data['imagen_url'],
                    'estado': 'activo'
                }
            )
            
            # Crear inventario
            if created:
                Inventario.objects.create(
                    producto=producto,
                    stock_actual=producto_data['stock_inicial'],
                    stock_minimo=producto_data['stock_minimo'],
                    ubicacion_almacen=f'Almacén {random.choice(["A", "B", "C"])}-{random.randint(1, 50):02d}'
                )
        
        self.stdout.write(f'  ✅ {len(productos_data)} productos creados')

    def crear_configuraciones(self):
        """Crear configuraciones del sistema"""
        self.stdout.write('Creando configuraciones del sistema...')
        
        configuraciones = [
            {
                'clave': 'nombre_tienda',
                'valor': 'SmartSales365',
                'descripcion': 'Nombre de la tienda online'
            },
            {
                'clave': 'moneda_default',
                'valor': 'PEN',
                'descripcion': 'Moneda por defecto del sistema'
            },
            {
                'clave': 'iva_porcentaje',
                'valor': '13',
                'descripcion': 'Porcentaje de IVA aplicable'
            },
            {
                'clave': 'stock_minimo_alerta',
                'valor': '10',
                'descripcion': 'Umbral mínimo de stock para generar alertas'
            },
            {
                'clave': 'dias_para_devolucion',
                'valor': '15',
                'descripcion': 'Días máximos para solicitar devolución'
            },
            {
                'clave': 'email_soporte',
                'valor': 'soporte@smartsales365.com',
                'descripcion': 'Email de soporte al cliente'
            },
            {
                'clave': 'telefono_soporte',
                'valor': '+591-3-1234567',
                'descripcion': 'Teléfono de soporte al cliente'
            }
        ]
        
        for config in configuraciones:
            ConfiguracionSistema.objects.get_or_create(
                clave=config['clave'],
                defaults={
                    'valor': config['valor'],
                    'descripcion': config['descripcion']
                }
            )
        
        self.stdout.write('  ✅ Configuraciones del sistema creadas')