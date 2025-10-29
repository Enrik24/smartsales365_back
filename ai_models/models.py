# ai_models/models.py
from django.db import models
from django.utils import timezone

class ModeloIA(models.Model):
    nombre_modelo = models.CharField(max_length=100)
    version = models.CharField(max_length=50)
    ruta_modelo = models.CharField(max_length=512, null=True, blank=True)
    fecha_entrenamiento = models.DateTimeField(null=True, blank=True)
    parametros = models.JSONField(null=True, blank=True)
    estado = models.CharField(max_length=50, default='entrenado')  # entrenado, entrenando, error
    precision = models.FloatField(null=True, blank=True)
    
    def actualizar_modelo(self, nueva_ruta, nueva_version=None):
        """Actualizar versión del modelo"""
        self.ruta_modelo = nueva_ruta
        if nueva_version:
            self.version = nueva_version
        self.fecha_entrenamiento = timezone.now()
        self.save()

    class Meta:
        db_table = 'modelos_ia'

class PrediccionVentas(models.Model):
    modelo = models.ForeignKey(ModeloIA, on_delete=models.CASCADE)
    fecha_prediccion = models.DateTimeField(auto_now_add=True)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    categoria = models.ForeignKey('products.Categoria', on_delete=models.CASCADE, null=True, blank=True)
    resultado_prediccion = models.JSONField()  # {fecha: valor_prediccion}
    metricas = models.JSONField(null=True, blank=True)  # RMSE, MAE, etc.
    
    class Meta:
        db_table = 'predicciones_ventas'