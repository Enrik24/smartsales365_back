# analytics/models.py
from django.db import models
from users.models import Usuario

class ReporteGenerado(models.Model):
    FORMATOS_SALIDA = (
        ('pdf', 'PDF'),
        ('excel', 'Excel'),
        ('csv', 'CSV'),
    )
    
    TIPOS_REPORTE = (
        ('ventas', 'Ventas'),
        ('clientes', 'Clientes'),
        ('productos', 'Productos'),
        ('inventario', 'Inventario'),
    )
    TIPOS_COMANDO = (
        ('voice', 'Voz'),
        ('text', 'Texto'),
    )
    ESTADOS_REPORTE = (
        ('pendiente', 'Pendiente'),
        ('procesando', 'Procesando'),
        ('completado', 'Completado'),
        ('error', 'Error'),
    )

    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    comando_voz = models.ForeignKey('voice_commands.ComandoVoz', on_delete=models.CASCADE, null=True, blank=True)
    comando_texto = models.ForeignKey('voice_commands.ComandoTexto', on_delete=models.CASCADE, null=True, blank=True)
    tipo_comando = models.CharField(max_length=50, choices=TIPOS_COMANDO, null=True, blank=True)  # ✅ AÑADIDO
    tipo_reporte = models.CharField(max_length=50, choices=TIPOS_REPORTE)
    formato_salida = models.CharField(max_length=20, choices=FORMATOS_SALIDA)
    parametros = models.JSONField(null=True, blank=True)
    consulta_sql = models.TextField(null=True, blank=True)
    url_descarga = models.URLField(max_length=500, null=True, blank=True)
    fecha_generacion = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=20, choices=ESTADOS_REPORTE, default='pendiente')

    @classmethod
    def obtener_por_id(cls, reporte_id):
        """Obtener reporte por ID"""
        try:
            return cls.objects.get(id=reporte_id)
        except cls.DoesNotExist:
            return None
    
    @classmethod
    def listar_por_usuario(cls, usuario_id):
        """Listar reportes de usuario"""
        return cls.objects.filter(usuario_id=usuario_id).order_by('-fecha_generacion')

    class Meta:
        db_table = 'reportes_generados'