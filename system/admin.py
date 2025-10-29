# system/admin.py - ADMIN ACTUALIZADO
from django.contrib import admin
from .models import BitacoraSistema, ConfiguracionSistema

@admin.register(BitacoraSistema)
class BitacoraSistemaAdmin(admin.ModelAdmin):
    list_display = ('id_bitacora', 'usuario', 'accion', 'estado', 'ip', 'fecha_accion')
    list_filter = ('estado', 'fecha_accion')
    search_fields = ('accion', 'usuario__email', 'ip')
    readonly_fields = ('fecha_accion',)
    list_per_page = 50
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('usuario')

@admin.register(ConfiguracionSistema)
class ConfiguracionSistemaAdmin(admin.ModelAdmin):
    list_display = ('clave', 'valor', 'descripcion')
    search_fields = ('clave', 'descripcion')
    list_editable = ('valor',)