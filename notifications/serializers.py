# notifications/serializers.py
from rest_framework import serializers
from .models import Notificacion, PreferenciaNotificacionUsuario

class NotificacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notificacion
        fields = '__all__'
        read_only_fields = ('fecha_creacion', 'fecha_envio', 'estado')

class PreferenciaNotificacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PreferenciaNotificacionUsuario
        fields = '__all__'

class MarcarLeidaSerializer(serializers.Serializer):
    notificacion_id = serializers.IntegerField()