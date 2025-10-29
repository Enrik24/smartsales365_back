# voice_commands/serializers.py
from rest_framework import serializers
from .models import ComandoVoz, ComandoTexto

class ComandoVozSerializer(serializers.ModelSerializer):
    usuario_nombre = serializers.CharField(source='usuario.get_full_name', read_only=True)
    
    class Meta:
        model = ComandoVoz
        fields = '__all__'

class ComandoTextoSerializer(serializers.ModelSerializer):
    usuario_nombre = serializers.CharField(source='usuario.get_full_name', read_only=True)
    
    class Meta:
        model = ComandoTexto
        fields = '__all__'

class ProcesarComandoSerializer(serializers.Serializer):
    texto = serializers.CharField(required=False)
    transcript = serializers.CharField(required=False)
    contexto = serializers.ChoiceField(choices=ComandoVoz.CONTEXTOS_APLICACION, default='reports')
    
    def validate(self, data):
        if not data.get('texto') and not data.get('transcript'):
            raise serializers.ValidationError("Debe proporcionar texto o transcript")
        return data