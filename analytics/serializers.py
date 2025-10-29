# analytics/serializers.py
from rest_framework import serializers
from .models import ReporteGenerado

class ReporteGeneradoSerializer(serializers.ModelSerializer):
    usuario_nombre = serializers.CharField(source='usuario.get_full_name', read_only=True)
    tipo_comando_display = serializers.CharField(source='get_tipo_comando_display', read_only=True)
    tipo_reporte_display = serializers.CharField(source='get_tipo_reporte_display', read_only=True)
    formato_salida_display = serializers.CharField(source='get_formato_salida_display', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    
    class Meta:
        model = ReporteGenerado
        fields = '__all__'
        read_only_fields = ('fecha_generacion', 'estado', 'url_descarga')

class ReporteSolicitudSerializer(serializers.Serializer):
    tipo_reporte = serializers.ChoiceField(choices=ReporteGenerado.TIPOS_REPORTE)
    formato_salida = serializers.ChoiceField(choices=ReporteGenerado.FORMATOS_SALIDA)
    fecha_inicio = serializers.DateField(required=False)
    fecha_fin = serializers.DateField(required=False)
    categoria_id = serializers.IntegerField(required=False)
    cliente_id = serializers.IntegerField(required=False)