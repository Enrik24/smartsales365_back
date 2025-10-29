# system/serializers.py - SERIALIZER ACTUALIZADO
from rest_framework import serializers
from .models import BitacoraSistema, ConfiguracionSistema

class BitacoraSistemaSerializer(serializers.ModelSerializer):
    usuario_email = serializers.EmailField(source='usuario.email', read_only=True)
    usuario_nombre = serializers.CharField(source='usuario.get_full_name', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    
    class Meta:
        model = BitacoraSistema
        fields = ('id_bitacora', 'usuario', 'usuario_email', 'usuario_nombre', 
                'fecha_accion', 'accion', 'estado', 'estado_display', 'ip')
        read_only_fields = ('fecha_accion',)

class BitacoraSistemaCreateSerializer(serializers.ModelSerializer):
    """Serializer específico para creación desde frontend"""
    class Meta:
        model = BitacoraSistema
        fields = ('usuario', 'accion', 'estado', 'ip')
    
    def create(self, validated_data):
        # Asegurar que la IP se capture si no se proporciona
        request = self.context.get('request')
        if request and not validated_data.get('ip'):
            validated_data['ip'] = self.get_client_ip(request)
        
        return super().create(validated_data)
    
    def get_client_ip(self, request):
        """Obtener IP real del cliente"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

class ConfiguracionSistemaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConfiguracionSistema
        fields = '__all__'