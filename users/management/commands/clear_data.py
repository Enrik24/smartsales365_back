# management/commands/clear_data.py
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction

Usuario = get_user_model()

class Command(BaseCommand):
    help = 'Limpiar datos de prueba (CUIDADO: elimina datos reales)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirmar eliminación de datos',
        )

    def handle(self, *args, **options):
        if not options['confirm']:
            self.stdout.write(
                self.style.WARNING('⚠️  Este comando eliminará datos. Use --confirm para proceder')
            )
            return

        self.stdout.write('Limpiando datos de prueba...')
        
        try:
            with transaction.atomic():
                # Eliminar en orden para respetar constraints
                from orders.models import Pedido, Carrito, Pago, Devolucion
                from products.models import Producto, Inventario, Favorito
                from users.models import UsuarioRol, RolPermiso
                from analytics.models import ReporteGenerado
                from ai_models.models import PrediccionVentas, ModeloIA
                from notifications.models import Notificacion, PreferenciaNotificacionUsuario
                from voice_commands.models import ComandoVoz, ComandoTexto
                
                # Mantener usuarios admin y configuraciones del sistema
                usuarios_a_mantener = ['admin@smartsales365.com']
                
                # Eliminar datos en orden inverso de dependencias
                ComandoVoz.objects.exclude(usuario__email__in=usuarios_a_mantener).delete()
                ComandoTexto.objects.exclude(usuario__email__in=usuarios_a_mantener).delete()
                ReporteGenerado.objects.exclude(usuario__email__in=usuarios_a_mantener).delete()
                PrediccionVentas.objects.all().delete()
                Notificacion.objects.exclude(usuario__email__in=usuarios_a_mantener).delete()
                PreferenciaNotificacionUsuario.objects.exclude(usuario__email__in=usuarios_a_mantener).delete()
                Devolucion.objects.all().delete()
                Pago.objects.all().delete()
                Pedido.objects.exclude(usuario__email__in=usuarios_a_mantener).delete()
                Carrito.objects.exclude(usuario__email__in=usuarios_a_mantener).delete()
                Favorito.objects.exclude(usuario__email__in=usuarios_a_mantener).delete()
                Inventario.objects.all().delete()
                Producto.objects.all().delete()
                UsuarioRol.objects.exclude(usuario__email__in=usuarios_a_mantener).delete()
                Usuario.objects.exclude(email__in=usuarios_a_mantener).delete()
                
                self.stdout.write(
                    self.style.SUCCESS('✅ Datos de prueba eliminados exitosamente')
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error limpiando datos: {str(e)}')
            )