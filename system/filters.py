# system/filters.py
import django_filters
from django.db.models import Q
from .models import BitacoraSistema

class BitacoraSistemaFilter(django_filters.FilterSet):
    usuario_search = django_filters.CharFilter(method='filter_by_usuario', label='Buscar por nombre, apellido o email de usuario')
    fecha_desde = django_filters.DateFilter(field_name='fecha_accion', lookup_expr='gte')
    fecha_hasta = django_filters.DateFilter(field_name='fecha_accion', lookup_expr='lte')
    accion = django_filters.CharFilter(field_name='accion', lookup_expr='icontains')

    class Meta:
        model = BitacoraSistema
        fields = ['estado', 'usuario_search', 'fecha_desde', 'fecha_hasta', 'accion']

    def filter_by_usuario(self, queryset, name, value):
        if not value:
            return queryset
        
        return queryset.filter(
            Q(usuario__nombre__icontains=value) |
            Q(usuario__apellido__icontains=value) |
            Q(usuario__email__icontains=value)
        )
