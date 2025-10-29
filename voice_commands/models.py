# voice_commands/models.py
from django.db import models
from users.models import Usuario

class ComandoVoz(models.Model):
    TIPOS_COMANDO = (
        ('reporte', 'Generar Reporte'),
        ('busqueda', 'Búsqueda'),
        ('navegacion', 'Navegación'),
        ('accion', 'Acción del Sistema'),
    )
    
    CONTEXTOS_APLICACION = (
        ('reports', 'Reportes'),
        ('products', 'Productos'),
        ('orders', 'Pedidos'),
        ('dashboard', 'Dashboard'),
    )
    
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    transcript_original = models.TextField()
    transcript_procesado = models.TextField(null=True, blank=True)
    tipo_comando = models.CharField(max_length=50, choices=TIPOS_COMANDO)
    contexto_aplicacion = models.CharField(max_length=100, choices=CONTEXTOS_APLICACION)
    intencion_detectada = models.CharField(max_length=100, null=True, blank=True)
    parametros_extraidos = models.JSONField(null=True, blank=True)
    fecha_ejecucion = models.DateTimeField(auto_now_add=True)
    duracion_procesamiento = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True)
    exito = models.BooleanField(default=True)
    respuesta_sistema = models.TextField(null=True, blank=True)
    
    class Meta:
        db_table = 'comandos_voz'

class ComandoTexto(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    texto_original = models.TextField()
    texto_procesado = models.TextField(null=True, blank=True)
    tipo_comando = models.CharField(max_length=50, choices=ComandoVoz.TIPOS_COMANDO)
    contexto_aplicacion = models.CharField(max_length=100, choices=ComandoVoz.CONTEXTOS_APLICACION)
    intencion_detectada = models.CharField(max_length=100, null=True, blank=True)
    parametros_extraidos = models.JSONField(null=True, blank=True)
    fecha_ejecucion = models.DateTimeField(auto_now_add=True)
    exito = models.BooleanField(default=True)
    respuesta_sistema = models.TextField(null=True, blank=True)
    
    class Meta:
        db_table = 'comandos_texto'