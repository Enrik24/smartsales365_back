# ai_models/serializers.py
from rest_framework import serializers
from .models import ModeloIA, PrediccionVentas

class ModeloIASerializer(serializers.ModelSerializer):
    class Meta:
        model = ModeloIA
        fields = '__all__'

class PrediccionVentasSerializer(serializers.ModelSerializer):
    modelo_nombre = serializers.CharField(source='modelo.nombre_modelo', read_only=True)
    categoria_nombre = serializers.CharField(source='categoria.nombre_categoria', read_only=True)
    
    class Meta:
        model = PrediccionVentas
        fields = '__all__'

class EntrenamientoSerializer(serializers.Serializer):
    fecha_inicio = serializers.DateField()
    fecha_fin = serializers.DateField()
    parametros = serializers.JSONField(required=False)

class PrediccionSolicitudSerializer(serializers.Serializer):
    modelo_id = serializers.IntegerField()
    fecha_inicio = serializers.DateField()
    fecha_fin = serializers.DateField()
    categoria_id = serializers.IntegerField(required=False, allow_null=True)