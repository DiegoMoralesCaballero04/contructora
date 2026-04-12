import django_filters
from .models import Licitacion


class LicitacionFilter(django_filters.FilterSet):
    importe_min = django_filters.NumberFilter(field_name='importe_base', lookup_expr='gte')
    importe_max = django_filters.NumberFilter(field_name='importe_base', lookup_expr='lte')
    fecha_desde = django_filters.DateFilter(field_name='fecha_publicacion', lookup_expr='gte')
    fecha_hasta = django_filters.DateFilter(field_name='fecha_publicacion', lookup_expr='lte')
    vencimiento_antes = django_filters.DateFilter(
        field_name='fecha_limite_oferta', lookup_expr='date__lte'
    )

    class Meta:
        model = Licitacion
        fields = ['estado', 'provincia', 'procedimiento', 'pdf_descargado', 'es_relevante']
