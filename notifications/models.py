# notifications/models.py
from django.db import models
from users.models import Usuario

class Notificacion(models.Model):
    TIPOS_NOTIFICACION = (
        ('sistema', 'Sistema'),
        ('pedido', 'Pedido'),
        ('inventario', 'Inventario'),
        ('promocion', 'Promoción'),
    )
    
    ESTADOS_NOTIFICACION = (
        ('pendiente', 'Pendiente'),
        ('enviada', 'Enviada'),
        ('leida', 'Leída'),
        ('error', 'Error'),
    )
    
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    tipo = models.CharField(max_length=50, choices=TIPOS_NOTIFICACION)
    titulo = models.CharField(max_length=255)
    mensaje = models.TextField()
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_envio = models.DateTimeField(null=True, blank=True)
    estado = models.CharField(max_length=50, choices=ESTADOS_NOTIFICACION, default='pendiente')
    datos_adicionales = models.JSONField(null=True, blank=True)
    
    class Meta:
        db_table = 'notificaciones'

class PreferenciaNotificacionUsuario(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    tipo_notificacion = models.CharField(max_length=100)
    activo = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'preferencias_notificacion_usuario'
        unique_together = ('usuario', 'tipo_notificacion')