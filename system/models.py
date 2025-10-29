# system/models.py
from django.db import models
from users.models import Usuario

class BitacoraSistema(models.Model):
    ESTADOS_ACCION = (
        ('exitoso', 'Exitoso'),
        ('fallido', 'Fallido'),
        ('advertencia', 'Advertencia'),
    )
    
    id_bitacora = models.BigAutoField(primary_key=True)  # BIGINT <<PK>> <<Auto>>
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, null=True, blank=True)  # id_usuario <<FK>>
    fecha_accion = models.DateTimeField(auto_now_add=True)  # TIMESTAMP
    accion = models.CharField(max_length=100)  # VARCHAR(100)
    estado = models.CharField(max_length=20, choices=ESTADOS_ACCION, default='exitoso')  # ENUM equivalent
    ip = models.GenericIPAddressField(null=True, blank=True)  # VARCHAR(45) - dirección IP del usuario
    
    class Meta:
        db_table = 'bitacora_sistema'
        verbose_name = 'Bitácora del Sistema'
        verbose_name_plural = 'Bitácoras del Sistema'
        ordering = ['-fecha_accion']
    
    def __str__(self):
        return f"{self.accion} - {self.estado} - {self.fecha_accion.strftime('%Y-%m-%d %H:%M')}"
    
    @classmethod
    def registrar_accion(cls, usuario, accion, estado='exitoso', ip=None):
        """
        Método helper para registrar acciones en la bitácora desde el frontend
        """
        return cls.objects.create(
            usuario=usuario,
            accion=accion,
            estado=estado,
            ip=ip
        )
class ConfiguracionSistema(models.Model):
    id_config = models.AutoField(primary_key=True)  # INT <<PK>> <<Auto>>
    clave = models.CharField(max_length=100, unique=True)  # VARCHAR(100) <<Unique>>
    valor = models.TextField()  # TEXT
    descripcion = models.TextField(null=True, blank=True)  # TEXT
    
    @classmethod
    def obtener_configuracion(cls, clave):
        """Obtener valor de configuración"""
        try:
            config = cls.objects.get(clave=clave)
            return config.valor
        except cls.DoesNotExist:
            return None
    
    @classmethod
    def establecer_configuracion(cls, clave, valor, descripcion=None):
        """Establecer o actualizar configuración"""
        config, created = cls.objects.get_or_create(
            clave=clave,
            defaults={'valor': valor, 'descripcion': descripcion}
        )
        
        if not created:
            config.valor = valor
            if descripcion:
                config.descripcion = descripcion
            config.save()
        
        return config

    class Meta:
        db_table = 'configuracion_sistema'
        verbose_name = 'Configuración del Sistema'
        verbose_name_plural = 'Configuraciones del Sistema'
    
    def __str__(self):
        return self.clave





